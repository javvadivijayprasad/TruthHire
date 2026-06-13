"""TruthHire API — FastAPI application (Sprint 1).

Endpoints:
    GET  /health           -> liveness check (no auth)
    POST /verify           -> run fraud analysis (auth required)
    POST /parse            -> extract structured fields from CV text (auth required)

Run locally:
    uvicorn app.main:app --reload
Interactive docs at /docs (OpenAPI auto-generated).
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI

from . import __version__
from .auth import require_api_key
from .cv_parser import parse_cv
from .schemas import (Candidate, VerifyRequest, VerifyResponse, VerifyResult,
                      LayerScores)
from .scoring import score_candidate

app = FastAPI(
    title="TruthHire API",
    version=__version__,
    description="Employment fraud intelligence — Sprint 1 core engine (timeline layer).",
)


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@app.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest, org: str = Depends(require_api_key)):
    t0 = time.perf_counter()
    candidate = req.candidate

    # If only CV text was supplied, enrich the candidate from it.
    if not candidate.jobs and candidate.cv_text:
        from .schemas import Job
        parsed = parse_cv(candidate.cv_text)
        if candidate.graduation_year is None:
            candidate.graduation_year = parsed.get("graduation_year")
        candidate.jobs = [Job(**j) for j in parsed.get("jobs", [])]

    result = score_candidate(candidate, req.options.layers)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    return VerifyResponse(
        check_id=f"th_chk_{uuid.uuid4().hex[:12]}",
        reference_id=req.options.reference_id,
        processing_ms=elapsed_ms,
        candidate={"name": candidate.name, "email": candidate.email},
        result=VerifyResult(
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            recommendation=result["recommendation"],
            flags=result["flags"],
            passed_checks=result["passed_checks"],
            layer_scores=LayerScores(**result["layer_scores"]),
        ),
        verified_at=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/parse")
def parse(payload: dict, org: str = Depends(require_api_key)):
    return parse_cv(payload.get("cv_text", ""))
