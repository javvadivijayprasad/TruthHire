# TruthHire (system)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20680914.svg)](https://doi.org/10.5281/zenodo.20680914)

The deployable TruthHire system: an API-first employment-fraud screening service
built around a deterministic, explainable **timeline-impossibility engine**, with
a pluggable OSINT signal layer. Outputs are advisory and human-in-the-loop by
design (see the research repository for the FCRA/GDPR rationale).

This repository is the production system. The paper, experiments, and
reproducibility harness live in a separate repository (TruthHire-research).

## Architecture (Sprints 1–24)

```
app/
  timeline.py        Layer 1 — deterministic timeline checks (impossible / pre-grad / overlap / inflation)
  scoring.py         additive risk_score (0–100) + per-layer subtotals + thresholds
  providers/         Layer 2/3 — pluggable OSINT providers (offline by default)
    github, email, phone, web, company, linkedin (deprecated vendor), network
  layers via scoring registry
  auth.py            API-key auth (SHA-256 hashed keys)
  ratelimit.py       sliding-window rate limit per key
  store.py           check retrieval store (swap for Postgres+Redis in prod)
  errors.py          structured error responses + handlers
  webhooks.py        async delivery with retry/backoff
  config.py          sandbox/production settings
  cv_parser.py       CV text extraction
  skills.py          skills-consistency questions + answer scoring (S21)
  governance.py      audit / dispute / adverse-action workflow (compliance)
  observability.py   timing metrics + DB health probe (S24)
  main.py            FastAPI app
```

### Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | liveness (no auth) |
| POST | `/verify` | run analysis; async via `options.webhook_url` |
| GET | `/verify/{check_id}` | retrieve a prior result |
| POST | `/parse` | CV text extraction |
| GET | `/providers` | OSINT provider status (live vs offline) |
| GET | `/usage` | calling org's usage + credit balance |
| POST | `/contribute` | add profiles to the shared network, earn credits (Phase 3) |
| POST | `/flags/report` | report a fraud case to the shared network |
| POST | `/flags/lookup` | threshold cross-org lookup + fraud-ring check |
| POST | `/verify/bulk` | screen a CSV of candidates, return scored CSV/JSON |
| POST | `/billing/subscribe` | activate a subscription plan (Stripe-ready) |
| POST | `/admin/keys` | issue a client API key (admin-gated) |
| GET | `/ui` | self-contained results dashboard |
| POST | `/skills/questions` | generate role-calibrated screening questions (S21) |
| POST | `/skills/assess` | score free-text answers; flags `SKILLS_MISMATCH` (S21) |
| GET | `/audit/{check_id}` | replay a stored decision with its flags (governance) |
| POST | `/dispute` | open a dispute against a check (governance) |
| POST | `/dispute/{id}/reinvestigate` | re-run and resolve a dispute (governance) |
| GET | `/metrics` | request counts + latency snapshot (S24, auth) |
| GET | `/healthz` | DB-backed readiness probe (S24, no auth) |

## Run

```bash
pip install -r requirements.txt
pytest -q                          # 88 tests
python demo.py                     # layered scoring demo, no server
uvicorn app.main:app --reload      # docs at /docs
```

## OSINT providers: offline by default, live-ready

Every external signal is a `Provider` with a real interface and a **deterministic
offline implementation** that reads a per-provider slice from `candidate.osint`,
so the whole pipeline runs and is fully tested **without any API keys**. A live
implementation populates the same slice from a real API (set the provider's env
key and pass `live=True`).

```jsonc
// candidate.osint (all optional; absent slice => provider abstains)
{
  "github":  {"account_year": 2009, "active": true},
  "email":   {"age_days": 10, "platforms": 1},     // advisory, low weight
  "phone":   {"valid": true, "prepaid": true},      // env: TWILIO_AUTH_TOKEN
  "web":     {"mentions_at_employer": 0},           // env: SERPAPI_KEY
  "company": {"exists": false, "registered_year": null}, // env: OPENCORPORATES_KEY
  "linkedin":{"created_year": 2024, "connections": 12, "senior_claim": true},
  "network": {"reports": 3}
}
```

## Going live (real API calls)

By default every provider is **offline** (reads `candidate.osint`). To make
providers call real APIs, set **`TRUTHHIRE_LIVE=1`** and supply each provider's
key + the candidate identifier it needs:

| Provider | Live source | Env var(s) | Candidate field needed |
|----------|-------------|------------|------------------------|
| GitHub Activity | GitHub API (free) | — | `github_username` |
| Company Registry | OpenCorporates | `OPENCORPORATES_KEY` (free tier ok) | `jobs[].company` |
| Phone Validation | Twilio Lookup | `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` | `phone` |
| Web Presence | SerpAPI (Google) | `SERPAPI_KEY` | `name` + `jobs[].company` |
| Email Presence | Holehe service | `HOLEHE_URL` | `email` |
| LinkedIn Profile | compliant vendor | `LINKEDIN_PROVIDER_URL` + `LINKEDIN_PROVIDER_KEY` | `linkedin_url` |
| Shared Fraud Network | internal service | `NETWORK_URL` + `NETWORK_KEY` | `email`/`phone` |

```bash
# example: enable live GitHub + Twilio + OpenCorporates
export TRUTHHIRE_LIVE=1
export TWILIO_ACCOUNT_SID=AC... TWILIO_AUTH_TOKEN=...
export OPENCORPORATES_KEY=...        # GitHub needs no key
python -m uvicorn app.main:app --reload
```

A live request carries the identifiers (vs. offline where you supply results):
```json
{ "candidate": { "name":"Vijay Javvadi", "email":"...", "phone":"+1...",
                 "github_username":"vijayjavvadi",
                 "linkedin_url":"https://linkedin.com/in/vijayjavvadi",
                 "jobs":[{"company":"Acme Corp","start":"2013-01","end":"2018-06"}] } }
```

Behaviour: a provider goes live only if `TRUTHHIRE_LIVE=1` **and** it has its key
(GitHub/Company/Email don't need one) **and** the candidate carries the identifier.
If a live call fails it **degrades gracefully** to the offline slice or abstains —
never crashes. `GET /providers` shows each provider's current `mode` (live/offline).

> **LinkedIn note:** the original design used **Proxycurl**, which shut down in
> July 2025 after LinkedIn's lawsuit. The provider is kept as an interface; a live
> implementation requires a compliant data source and carries legal risk.

## Example

```bash
curl -s http://127.0.0.1:8000/verify \
  -H "Authorization: Bearer th_sandbox_demo_key" -H "Content-Type: application/json" \
  -d '{"candidate":{"name":"John Smith","age":24,"total_claimed_years":15,
       "osint":{"company":{"exists":false},"network":{"reports":3}}}}'
# -> risk_score 100, CRITICAL, flags across timeline/company/network
```

## Network, credits & monetisation (Sprints 11-20)

- **Shared fraud network** (`/flags/report`, `/flags/lookup`): stores only SHA-256
  hashes of identifiers — never raw PII — and returns cross-org report counts above
  a corroboration threshold. A candidate reported by other orgs is flagged on the
  next `/verify`.
- **Fraud-ring detection**: one identifier (e.g. a reused phone) seen under
  multiple names raises `DUPLICATE_IDENTITY`.
- **Contribution credits** (`/contribute`): the paper's *outcome-symmetric* reward
  (verified-legitimate is worth the same as confirmed-fraud) — avoids the
  adverse-selection failure of the naive "fraud pays more" schedule. Duplicates
  earn nothing. `/usage` shows the credit balance.
- **Plans & billing** (`/billing/subscribe`): Free/Starter/Growth/Scale/Enterprise
  with base credits + per-check rate + contribution multiplier. Stripe-ready
  (offline by default; set `STRIPE_API_KEY` to go live).
- **ATS adapters**: `app/integrations/greenhouse.py` & `bamboohr.py` map an ATS
  candidate object to a verify request; plugin manifest included.
- **Bulk screening** (`/verify/bulk`): CSV in, scored CSV/JSON out.
- **Dashboard** (`/ui`): paste a candidate, see the risk badge + flags — no code.
- **Key issuance** (`/admin/keys`): mint per-client keys (admin key required).

## Database & persistence (TH-005)

State lives in a real SQL database via SQLAlchemy — it survives restarts.

- **Default:** SQLite file `truthhire.db` (zero setup, auto-created).
- **Production:** set `DATABASE_URL`, e.g. `postgresql+psycopg://user:pw@host:5432/truthhire`.
- **Tables:** `api_keys`, `checks`, `network_reports`, `network_identities`,
  `credit_accounts`, `contributions`, `disputes`.
- The shared fraud network stores **only SHA-256 hashes** (identifiers *and* names) — no raw PII.

**Migrations (Alembic):**
```bash
alembic upgrade head                              # apply migrations
alembic revision --autogenerate -m "describe change"   # after editing models
```
Tests run against in-memory SQLite (`tests/conftest.py`), so they never touch your real DB.

## Skills, governance & scale (Sprints 21–24)

- **Skills-consistency scoring** (`app/skills.py`): generates role- and
  seniority-calibrated questions, scores free-text answers (depth, tool mentions,
  specifics), and raises `SKILLS_MISMATCH` when demonstrated depth falls well
  below the level implied by the claimed title/tenure. Advisory, never auto-reject.
- **Compliance & governance** (`app/governance.py`): audit replay of any stored
  decision, a dispute → re-investigation workflow, and an FCRA-style
  adverse-action notice generated only for HIGH/CRITICAL outcomes — keeping the
  human-in-the-loop, contestable design the research paper argues for.
- **Observability & scale** (`app/observability.py`): request-timing middleware,
  a `/metrics` snapshot (counts, status breakdown, average latency), a DB-backed
  `/healthz` readiness probe, and `scripts/loadtest.py` for concurrent load.

> **Timeline engine note (granularity-aware overlap):** year-granularity dates
> ("2019" with no month) are common on real resumes and, parsed naively as
> January, manufacture *phantom* employment overlaps. The engine now widens the
> overlap tolerance by `YEAR_GRANULARITY_SLACK_MONTHS` (12) for any pair whose
> contested boundary is year-only. On a realistic messy-but-honest population
> this cuts the deterministic false-positive rate from ~24% to ~5.5% with no loss
> of fraud recall (see the research repo's `realistic_fp` experiment).

## Design notes
- Score field is `risk_score` (high = suspicious), not the inverted `trust_score`.
- Single **additive** scoring model (`min(100, Σ flag weights)`) — resolves the
  v1.0 spec's two-model ambiguity.
- Inferential (digital) and network signals are **advisory** and never auto-reject;
  `email`-age signals are deliberately low-weight per the no-penalty policy.

## License
MIT (see `LICENSE`).
