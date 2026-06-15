"""Company Registry (S9 / TH-023). Live: OpenCorporates (env OPENCORPORATES_KEY).
Input: first employer name."""
from __future__ import annotations
from typing import List, Optional
from .base import Provider, Signal, _get, _first_company
from . import http


class CompanyProvider(Provider):
    name = "company"; display_name = "Company Registry"
    description = "Verifies the employer exists in a company registry and pre-dates the claimed tenure."
    source = "OpenCorporates"; layer = "company"; slice = "company"
    env_key = "OPENCORPORATES_KEY"; requires_key = False  # free tier works

    def fetch_live(self, candidate) -> Optional[dict]:
        emp = _first_company(candidate)
        if not emp:
            return None
        params = {"q": emp}
        if self.api_key:
            params["api_token"] = self.api_key
        d = http.get_json("https://api.opencorporates.com/v0.4/companies/search", params=params)
        if not d:
            return None
        comps = (d.get("results") or {}).get("companies") or []
        if not comps:
            return {"exists": False, "registered_year": None}
        inc = (comps[0].get("company") or {}).get("incorporation_date")
        reg = int(str(inc)[:4]) if inc else None
        return {"exists": True, "registered_year": reg}

    def evaluate(self, data, candidate) -> List[Signal]:
        out: List[Signal] = []
        if data.get("exists") is False:
            return [Signal("COMPANY_NOT_FOUND", "CRITICAL", 50,
                "Claimed employer not found in any company registry.", self.layer)]
        reg = data.get("registered_year")
        jobs = _get(candidate, "jobs") or []
        earliest = None
        for j in jobs:
            s = j.get("start") if isinstance(j, dict) else getattr(j, "start", None)
            try:
                y = int(str(s).split("-")[0]); earliest = y if earliest is None else min(earliest, y)
            except (ValueError, TypeError):
                pass
        if reg and earliest and reg > earliest:
            out.append(Signal("COMPANY_POST_DATES", "CRITICAL", 50,
                f"Claimed employer registered {reg}, after employment start {earliest}.", self.layer))
        elif data.get("exists") is True and not out:
            out.append(Signal("COMPANY_EXISTS", "LOW", 0, "Employer exists in registry.",
                              self.layer, passed=True))
        return out
