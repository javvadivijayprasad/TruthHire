# TruthHire (system)

The deployable TruthHire system: an API-first employment-fraud screening service
built around a deterministic, explainable **timeline-impossibility engine**.

This repository is the production system. The research paper, experiments, and
reproducibility harness live in a separate repository (TruthHire-research).

## Components

```
app/
  timeline.py    # deterministic timeline-intelligence engine (the core)
  scoring.py     # score combiner + risk thresholds
  cv_parser.py   # lightweight CV text extractor
  auth.py        # API-key authentication (hashed keys)
  schemas.py     # request/response models
  main.py        # FastAPI app: /health, /verify, /parse
tests/           # unit + API tests
```

## Run

```bash
pip install -r requirements.txt
pytest -q                         # 23 tests
uvicorn app.main:app --reload     # docs at http://127.0.0.1:8000/docs
```

## Example

```bash
curl -s http://127.0.0.1:8000/verify \
  -H "Authorization: Bearer th_sandbox_demo_key" \
  -H "Content-Type: application/json" \
  -d '{"candidate":{"name":"John Smith","age":24,"total_claimed_years":15}}'
```

## Design notes

- The score field is `risk_score` (high = suspicious), not the inverted `trust_score`.
- Timeline weights are +50 / +40 / +25 (impossible / pre-graduation / overlap & inflation).
- Inferential and network layers (Phase 2+) are advisory and human-in-the-loop by design;
  see the research repository for the framework and its FCRA/GDPR rationale.

## License
MIT (see `LICENSE`).
