"""Compliance & governance (FCRA/GDPR): consent, audit, dispute, adverse action.

These make the system advisory and contestable — the precondition the paper sets
for any real use."""
from __future__ import annotations
from typing import Dict, List, Optional
from .db import SessionLocal
from .models import Dispute, CheckRecord
import json


def audit(check_id: str) -> Optional[dict]:
    """Why a decision was made: the flags + inputs that produced it."""
    with SessionLocal() as s:
        rec = s.get(CheckRecord, check_id)
        if not rec:
            return None
        payload = json.loads(rec.payload)
        res = payload.get("result", {})
        return {"check_id": check_id, "created_at": str(rec.created_at),
                "risk_score": res.get("risk_score"), "risk_level": res.get("risk_level"),
                "recommendation": res.get("recommendation"),
                "explanations": [{"code": f["code"], "why": f["message"], "weight": f["weight"],
                                  "layer": f.get("layer")} for f in res.get("flags", [])],
                "passed_checks": res.get("passed_checks", [])}


def open_dispute(check_id: str, reason: str) -> dict:
    with SessionLocal() as s:
        if not s.get(CheckRecord, check_id):
            return {"error": "unknown check_id"}
        d = Dispute(check_id=check_id, reason=reason, status="open")
        s.add(d); s.commit()
        return {"dispute_id": d.id, "check_id": check_id, "status": "open"}


def reinvestigate(dispute_id: int) -> dict:
    """Deterministic re-run: the deterministic layer reproduces the same flags, so a
    dispute resolves to a human-legible, reproducible explanation."""
    with SessionLocal() as s:
        d = s.get(Dispute, dispute_id)
        if not d:
            return {"error": "unknown dispute_id"}
        a = audit(d.check_id)
        d.status = "reinvestigated"
        d.resolution = json.dumps(a)
        s.commit()
        return {"dispute_id": dispute_id, "status": "reinvestigated", "audit": a}


def adverse_action_notice(result: dict, candidate_name: str = "the candidate") -> Optional[dict]:
    """FCRA-style adverse-action content for a high/critical result (advisory)."""
    if result.get("risk_level") not in ("HIGH", "CRITICAL"):
        return None
    reasons = [f["message"] for f in result.get("flags", [])]
    return {"notice": "pre-adverse-action",
            "summary": f"A verification report on {candidate_name} contributed to a tentative "
                       "adverse decision. You have the right to dispute its accuracy.",
            "reasons": reasons,
            "rights": ["request a free copy of the report", "dispute inaccuracies (/dispute)",
                       "a human reviews before any final decision"]}
