"""Check retrieval store (TH-005, TH-014) — DB-backed (CheckRecord)."""
from __future__ import annotations
import json
from typing import Optional
from .db import SessionLocal
from .models import CheckRecord


class CheckStore:
    def put(self, check_id: str, result: dict, org: str = "") -> None:
        with SessionLocal() as s:
            rec = s.get(CheckRecord, check_id)
            if rec:
                rec.payload = json.dumps(result)
            else:
                s.add(CheckRecord(check_id=check_id, org=org, payload=json.dumps(result)))
            s.commit()

    def get(self, check_id: str) -> Optional[dict]:
        with SessionLocal() as s:
            rec = s.get(CheckRecord, check_id)
            return json.loads(rec.payload) if rec else None

    def reset(self) -> None:
        with SessionLocal() as s:
            s.query(CheckRecord).delete(); s.commit()


store = CheckStore()
