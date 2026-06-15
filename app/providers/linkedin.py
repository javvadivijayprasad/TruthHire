"""LinkedIn Profile (S7 / TH-020,021).

DEPRECATED VENDOR: Proxycurl shut down July 2025 after LinkedIn's lawsuit. Live
mode calls a configurable compliant provider (env LINKEDIN_PROVIDER_URL +
LINKEDIN_PROVIDER_KEY) — choose a vendor and confirm legality. Input:
candidate.linkedin_url."""
from __future__ import annotations
import os
from typing import List, Optional
from .base import Provider, Signal, _get
from . import http


class LinkedInProvider(Provider):
    name = "linkedin"; display_name = "LinkedIn Profile"
    description = "Compares LinkedIn profile age and connections to the claimed career start."
    source = "LinkedIn (compliant vendor required)"; layer = "digital"; slice = "linkedin"
    env_key = "LINKEDIN_PROVIDER_KEY"
    deprecated_vendor = "Proxycurl (shut down 2025) — replace with a compliant source"

    def fetch_live(self, candidate) -> Optional[dict]:
        li = _get(candidate, "linkedin_url"); url = os.environ.get("LINKEDIN_PROVIDER_URL")
        if not (li and url and self.api_key):
            return None
        d = http.get_json(url, params={"profile": li},
                          headers={"Authorization": f"Bearer {self.api_key}"})
        if not d:
            return None
        return {"created_year": d.get("created_year"), "connections": d.get("connections"),
                "senior_claim": True}

    def evaluate(self, data, candidate) -> List[Signal]:
        out: List[Signal] = []
        created = data.get("created_year"); claimed = _get(candidate, "graduation_year")
        if created and claimed and created > claimed + 2:
            out.append(Signal("LINKEDIN_DATE_MISMATCH", "HIGH", 30,
                f"LinkedIn profile created {created}, well after claimed career start {claimed}.",
                self.layer))
        conns = data.get("connections")
        if data.get("senior_claim") and conns is not None and conns < 50:
            out.append(Signal("LINKEDIN_NO_CONNECTIONS", "MEDIUM", 15,
                f"Senior role claimed but only {conns} LinkedIn connections.", self.layer))
        return out
