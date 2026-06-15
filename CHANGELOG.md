# Changelog

All notable changes to the TruthHire system are documented here.
This project follows semantic versioning.

## [1.1.0] — 2026-06-14

### Added
- **Real persistence:** SQLAlchemy 2.0 ORM with Alembic migrations. SQLite by
  default (`truthhire.db`), Postgres-ready via `DATABASE_URL`; in-memory SQLite
  for tests. Tables: api_keys, checks, network_reports, network_identities,
  credit_accounts, contributions, disputes.
- **Skills-consistency scoring** (`app/skills.py`): role/seniority-calibrated
  question generation and free-text answer scoring; raises `SKILLS_MISMATCH`.
  Endpoints `/skills/questions`, `/skills/assess`.
- **Compliance & governance** (`app/governance.py`): decision audit replay, a
  dispute → re-investigation workflow, and FCRA-style adverse-action notices for
  HIGH/CRITICAL outcomes. Endpoints `/audit/{check_id}`, `/dispute`,
  `/dispute/{id}/reinvestigate`.
- **Observability & scale** (`app/observability.py`): request-timing middleware,
  `/metrics` snapshot, DB-backed `/healthz` probe, and `scripts/loadtest.py`.
- Release metadata: `.zenodo.json`, `CITATION.cff`.

### Changed
- **Timeline engine:** granularity-aware overlap rule — when a contested date
  boundary is year-only ("2019"), the overlap tolerance is widened by 12 months
  to avoid phantom overlaps on real, year-granular resumes.
- Full pytest suite expanded to 88 tests.

### Fixed
- Admin key authorization via a single HTTPBearer scheme.
- Dashboard UTF-8 rendering.
