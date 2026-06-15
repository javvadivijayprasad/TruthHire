"""Contribution-credit ledger (TH-026, TH-027) — DB-backed (CreditAccount).

Outcome-symmetric reward (the paper's correction): a verified outcome is rewarded
for being audited, not for being a fraud verdict."""
from __future__ import annotations
from typing import List
from .db import SessionLocal
from .models import CreditAccount, Contribution
from .plans import plan

SYMMETRIC = {"fraud_confirmed": 1.0, "legitimate": 1.0, "inconclusive": 0.0,
             "partial": 0.3, "fraud_ring": 1.5, "duplicate": 0.0}
NAIVE = {"fraud_confirmed": 2.0, "legitimate": 1.0, "inconclusive": 0.0,
         "partial": 0.3, "fraud_ring": 3.0, "duplicate": 0.0}


class CreditLedger:
    def __init__(self, schedule: str = "symmetric"):
        self.rates = SYMMETRIC if schedule == "symmetric" else NAIVE

    def _account(self, s, org: str) -> CreditAccount:
        a = s.get(CreditAccount, org)
        if not a:
            a = CreditAccount(org=org, plan="free", balance=0.0); s.add(a)
        return a

    def set_plan(self, org: str, plan_name: str) -> None:
        with SessionLocal() as s:
            a = self._account(s, org)
            a.plan = plan_name
            a.balance = round(a.balance + (plan(plan_name)["base_credits"] or 0), 3)
            s.commit()

    def contribute(self, org: str, profiles: List[dict]) -> dict:
        with SessionLocal() as s:
            a = self._account(s, org)
            mult = plan(a.plan)["multiplier"]
            earned = 0.0; accepted = rejected = 0
            for p in profiles:
                if p.get("duplicate"):
                    rejected += 1; continue
                oc = p.get("outcome", "inconclusive")
                earned += self.rates.get(oc, 0.0); accepted += 1
                s.add(Contribution(org=org, outcome=oc, credits=self.rates.get(oc, 0.0)))
            earned = round(earned * mult, 3)
            a.balance = round(a.balance + earned, 3)
            rate = plan(a.plan)["check_rate"]; bal = a.balance
            s.commit()
        return {"profiles_accepted": accepted, "profiles_rejected": rejected,
                "credits_earned": earned,
                "account_balance": {"credits_available": round(bal, 3),
                                    "cash_equivalent": round(bal * rate, 2),
                                    "checks_covered": int(bal)}}

    def balance(self, org: str) -> dict:
        with SessionLocal() as s:
            a = s.get(CreditAccount, org)
            plan_name = a.plan if a else "free"
            bal = round(a.balance, 3) if a else 0.0
        rate = plan(plan_name)["check_rate"]
        return {"credits_available": bal, "cash_equivalent": round(bal * rate, 2),
                "checks_covered": int(bal), "plan": plan_name}

    def reset(self) -> None:
        with SessionLocal() as s:
            s.query(Contribution).delete(); s.query(CreditAccount).delete(); s.commit()


ledger = CreditLedger()
