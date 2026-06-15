"""Email Presence (S4 / TH-018). Live: self-hosted Holehe service (env HOLEHE_URL).
Input: candidate.email. Advisory, low weight (no-penalty policy)."""
from __future__ import annotations
import os
from typing import List, Optional
from .base import Provider, Signal, _get
from . import http


class EmailPresenceProvider(Provider):
    name = "email"; display_name = "Email Presence"
    description = "Checks email age and how many platforms it appears on (advisory, low weight)."
    source = "Holehe (email-platform checker)"; layer = "digital"; slice = "email"
    requires_key = False

    def fetch_live(self, candidate) -> Optional[dict]:
        email = _get(candidate, "email"); url = os.environ.get("HOLEHE_URL")
        if not (email and url):
            return None
        d = http.get_json(url, params={"email": email})
        if not d:
            return None
        return {"age_days": d.get("age_days"), "platforms": d.get("platforms")}

    def evaluate(self, data, candidate) -> List[Signal]:
        out: List[Signal] = []
        age = data.get("age_days"); platforms = data.get("platforms")
        if age is not None and age < 30:
            out.append(Signal("EMAIL_NEWLY_CREATED", "LOW", 10,
                f"Email created {age} days ago (advisory only).", self.layer))
        if platforms is not None and platforms < 2:
            out.append(Signal("EMAIL_LOW_PRESENCE", "LOW", 10,
                f"Email registered on {platforms} platform(s) (advisory only).", self.layer))
        return out
