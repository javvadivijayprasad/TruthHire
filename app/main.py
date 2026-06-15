"""TruthHire API — FastAPI application (Sprints 1-10).

Endpoints:
  GET  /health              liveness (no auth)
  POST /verify              fraud analysis; async via options.webhook_url
  GET  /verify/{check_id}   retrieve a prior result
  POST /parse               CV text extraction
  GET  /providers           OSINT provider status (live vs offline)
  GET  /usage               current-period usage for the calling org

Interactive docs at /docs (OpenAPI auto-generated).
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

import os
from fastapi import Depends, FastAPI, BackgroundTasks, HTTPException, Header
from fastapi.responses import HTMLResponse, PlainTextResponse

from . import __version__
from .auth import require_api_key, bearer_scheme
from fastapi.security import HTTPAuthorizationCredentials
from .config import settings
from .cv_parser import parse_cv
from .errors import APIError, register
from .ratelimit import limiter
from .store import store
from .scoring import score_candidate
from .webhooks import deliver
from .providers.base import default_registry
from .network_store import network
from .credits import ledger
from . import bulk, billing, skills, governance, observability
from .auth import add_key, seed_keys
from .db import init_db
import secrets
from .schemas import (Candidate, VerifyRequest, VerifyResponse, VerifyResult, LayerScores,
                      ContributeRequest, FlagReport, FlagLookup, BulkRequest, SubscribeRequest, KeyRequest,
                      SkillsQuestionsRequest, SkillsAssessRequest, DisputeRequest)

app = FastAPI(
    title="TruthHire API",
    version=__version__,
    description="Employment-fraud intelligence — layered, explainable, advisory.",
)
register(app)
init_db()
seed_keys()
REGISTRY = default_registry()


def require_admin(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    admin = os.environ.get("TRUTHHIRE_ADMIN_KEY", "th_admin_demo_key")
    tok = creds.credentials.strip() if creds and creds.credentials else ""
    if tok != admin:
        raise HTTPException(403, detail={"error_code": "FORBIDDEN", "message": "Admin key required"})
    return "admin"
_usage: dict = {}


@app.middleware("http")
async def _timing(request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    observability.record(request.url.path, response.status_code,
                         (time.perf_counter() - t0) * 1000)
    return response


@app.get("/metrics")
def metrics(org: str = Depends(require_api_key)):
    return observability.snapshot()


@app.get("/healthz")
def healthz():
    ok = observability.db_ok()
    return {"status": "ok" if ok else "degraded", "database": "up" if ok else "down",
            "version": __version__}


def rate_limited(org: str = Depends(require_api_key)) -> str:
    if not limiter.allow(org):
        raise APIError(429, "RATE_LIMITED", "Too many requests — max "
                       f"{settings.rate_limit_per_sec}/second per API key.")
    _usage[org] = _usage.get(org, 0) + 1
    return org


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__, "env": settings.env}


def _run(candidate: Candidate, layers):
    if not candidate.jobs and candidate.cv_text:
        from .schemas import Job
        parsed = parse_cv(candidate.cv_text)
        if candidate.graduation_year is None:
            candidate.graduation_year = parsed.get("graduation_year")
        candidate.jobs = [Job(**j) for j in parsed.get("jobs", [])]
    return score_candidate(candidate, layers, REGISTRY)


def _response(req: VerifyRequest, result: dict, elapsed_ms: int) -> VerifyResponse:
    return VerifyResponse(
        check_id=f"th_chk_{uuid.uuid4().hex[:12]}",
        reference_id=req.options.reference_id,
        processing_ms=elapsed_ms,
        candidate={"name": req.candidate.name, "email": req.candidate.email},
        result=VerifyResult(
            risk_score=result["risk_score"], risk_level=result["risk_level"],
            recommendation=result["recommendation"], flags=result["flags"],
            passed_checks=result["passed_checks"],
            layer_scores=LayerScores(**result["layer_scores"]),
            adverse_action=governance.adverse_action_notice(result, req.candidate.name)),
        verified_at=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest, background: BackgroundTasks, org: str = Depends(rate_limited)):
    t0 = time.perf_counter()
    result = _run(req.candidate, req.options.layers)
    elapsed = int((time.perf_counter() - t0) * 1000)
    resp = _response(req, result, elapsed)
    store.put(resp.check_id, resp.model_dump())
    if req.options.webhook_url:
        payload = {"event": "check.complete", "check_id": resp.check_id,
                   "result": resp.result.model_dump()}
        background.add_task(deliver, req.options.webhook_url, payload)
        resp.status = "processing"
    return resp


@app.get("/verify/{check_id}", response_model=VerifyResponse)
def get_check(check_id: str, org: str = Depends(require_api_key)):
    rec = store.get(check_id)
    if rec is None:
        raise APIError(404, "NOT_FOUND", f"Check {check_id} does not exist.")
    return rec


@app.post("/parse")
def parse(payload: dict, org: str = Depends(require_api_key)):
    return parse_cv(payload.get("cv_text", ""))


@app.get("/providers")
def providers(org: str = Depends(require_api_key)):
    return {"providers": [
        {"name": p.name, "display_name": p.display_name, "description": p.description,
         "searches": p.source, "layer": p.layer,
         "mode": "live" if p.live else "offline",
         "note": getattr(p, "deprecated_vendor", None)}
        for p in REGISTRY.values()]}


@app.get("/usage")
def usage(org: str = Depends(require_api_key)):
    return {"org": org, "checks_this_session": _usage.get(org, 0),
            "rate_limit_per_sec": settings.rate_limit_per_sec, "env": settings.env,
            "credits": ledger.balance(org)}

@app.post("/contribute")
def contribute(req: ContributeRequest, org: str = Depends(rate_limited)):
    # add any fraud-confirmed profiles to the shared network, then award credits
    for pr in req.profiles:
        if pr.outcome in ("fraud_confirmed", "fraud_ring"):
            network.report(org, email=pr.email, phone=pr.phone, name=pr.name,
                           outcome="fraud_confirmed")
        elif pr.name and (pr.email or pr.phone):
            network.report(org, email=pr.email, phone=pr.phone, name=pr.name, outcome="legitimate")
    return ledger.contribute(org, [pr.model_dump() for pr in req.profiles])


@app.post("/flags/report")
def flags_report(req: FlagReport, org: str = Depends(require_api_key)):
    h = network.report(org, email=req.email, phone=req.phone, name=req.name, outcome=req.outcome)
    return {"status": "recorded", "hash": h}


@app.post("/flags/lookup")
def flags_lookup(req: FlagLookup, org: str = Depends(require_api_key)):
    res = network.lookup(req.email, req.phone, req.threshold)
    res["ring"] = network.ring(req.email, req.phone)
    return res



@app.post("/verify/bulk")
def verify_bulk(req: BulkRequest, org: str = Depends(rate_limited)):
    rows = bulk.score_csv(req.csv, req.layers)
    if req.as_csv:
        return PlainTextResponse(bulk.to_csv(rows), media_type="text/csv")
    return {"count": len(rows), "results": rows}


@app.post("/billing/subscribe")
def subscribe(req: SubscribeRequest, org: str = Depends(require_api_key)):
    return billing.create_checkout(org, req.plan)


@app.post("/webhooks/stripe")
def stripe_webhook(payload: dict):
    return billing.handle_event(payload.get("type", ""), payload.get("org", ""),
                                payload.get("plan", "free"))


@app.post("/admin/keys")
def issue_key(req: KeyRequest, _admin: str = Depends(require_admin)):
    new_key = "th_live_" + secrets.token_hex(12)
    add_key(new_key, req.label)
    return {"api_key": new_key, "label": req.label,
            "note": "store this now — it is not retrievable later"}


@app.get("/ui", response_class=HTMLResponse)
def ui():
    import pathlib
    return (pathlib.Path(__file__).parent.parent / "static" / "dashboard.html").read_text(encoding="utf-8")


@app.post("/skills/questions")
def skills_questions(req: SkillsQuestionsRequest, org: str = Depends(require_api_key)):
    level = skills.seniority_level(req.total_claimed_years)
    dom = req.domain or skills.domain_for(req.model_dump())
    return {"domain": dom, "seniority_level": level,
            "questions": skills.generate_questions(dom, level, req.n)}


@app.post("/skills/assess")
def skills_assess(req: SkillsAssessRequest, org: str = Depends(rate_limited)):
    return skills.assess(req.model_dump(), req.answers, req.domain)


@app.get("/audit/{check_id}")
def audit(check_id: str, org: str = Depends(require_api_key)):
    a = governance.audit(check_id)
    if a is None:
        raise APIError(404, "NOT_FOUND", f"Check {check_id} does not exist.")
    return a


@app.post("/dispute")
def dispute(req: DisputeRequest, org: str = Depends(require_api_key)):
    out = governance.open_dispute(req.check_id, req.reason)
    if out.get("error"):
        raise APIError(404, "NOT_FOUND", out["error"])
    return out


@app.post("/dispute/{dispute_id}/reinvestigate")
def reinvestigate(dispute_id: int, org: str = Depends(require_api_key)):
    out = governance.reinvestigate(dispute_id)
    if out.get("error"):
        raise APIError(404, "NOT_FOUND", out["error"])
    return out
