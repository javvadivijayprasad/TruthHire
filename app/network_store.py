"""Anonymised shared fraud network (TH-028, TH-029) — DB-backed.

Stores only SHA-256 hashes (never raw PII). Cross-org report counts (distinct
orgs) with a corroboration threshold, plus fraud-ring detection (one identifier
under multiple names)."""
from __future__ import annotations
import hashlib
from typing import Optional, Set
from .db import SessionLocal
from .models import NetworkReport, NetworkIdentity


def h(value: Optional[str]) -> Optional[str]:
    return hashlib.sha256(value.strip().lower().encode()).hexdigest() if value else None


def combo(email: Optional[str], phone: Optional[str]) -> str:
    return hashlib.sha256(f"{(email or '').strip().lower()}|{(phone or '').strip()}".encode()).hexdigest()


class FraudNetwork:
    def report(self, org: str, email=None, phone=None, name=None,
               outcome: str = "fraud_confirmed") -> str:
        c = combo(email, phone)
        with SessionLocal() as s:
            if outcome == "fraud_confirmed":
                if not s.query(NetworkReport).filter_by(combo_hash=c, org=org).first():
                    s.add(NetworkReport(combo_hash=c, org=org))
            if name:
                nmh = h(name)
                for idh in (h(phone), h(email)):
                    if idh and not s.query(NetworkIdentity).filter_by(id_hash=idh, name_hash=nmh).first():
                        s.add(NetworkIdentity(id_hash=idh, name_hash=nmh))
            s.commit()
        return c

    def lookup(self, email=None, phone=None, threshold: int = 1) -> dict:
        c = combo(email, phone)
        with SessionLocal() as s:
            n = s.query(NetworkReport).filter_by(combo_hash=c).count()
        return {"hash": c, "reports": n, "flagged": n >= threshold}

    def ring(self, email=None, phone=None) -> dict:
        name_hashes: Set[str] = set()
        with SessionLocal() as s:
            for idh in (h(phone), h(email)):
                if idh:
                    for row in s.query(NetworkIdentity).filter_by(id_hash=idh):
                        name_hashes.add(row.name_hash)
        return {"identities": len(name_hashes), "is_ring": len(name_hashes) > 1}

    def reset(self) -> None:
        with SessionLocal() as s:
            s.query(NetworkReport).delete(); s.query(NetworkIdentity).delete(); s.commit()


network = FraudNetwork()
