"""Phone Validation (S4/S9 / TH-019). Live: Twilio Lookup v2 (line type intelligence).
Env: TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN. Input: candidate.phone."""
from __future__ import annotations
import os
from typing import List, Optional
from .base import Provider, Signal, _get
from . import http


class PhoneProvider(Provider):
    name = "phone"; display_name = "Phone Validation"
    description = "Detects prepaid/burner numbers and validates the line via carrier lookup."
    source = "Twilio Lookup"; layer = "digital"; slice = "phone"; env_key = "TWILIO_AUTH_TOKEN"

    def fetch_live(self, candidate) -> Optional[dict]:
        phone = _get(candidate, "phone"); sid = os.environ.get("TWILIO_ACCOUNT_SID")
        if not (phone and sid and self.api_key):
            return None
        d = http.get_json(f"https://lookups.twilio.com/v2/PhoneNumbers/{phone}",
                          params={"Fields": "line_type_intelligence"}, auth=(sid, self.api_key))
        if not d:
            return None
        lti = d.get("line_type_intelligence") or {}
        t = str(lti.get("type") or "").lower()
        return {"valid": bool(d.get("valid", True)),
                "prepaid": t in ("nonfixedvoip", "voicemail", "pager")}

    def evaluate(self, data, candidate) -> List[Signal]:
        out: List[Signal] = []
        if data.get("prepaid") is True:
            out.append(Signal("PHONE_PREPAID", "LOW", 10,
                "Phone number is prepaid/disposable carrier.", self.layer))
        if data.get("valid") is True and not out:
            out.append(Signal("PHONE_VALID", "LOW", 0, "Phone number valid.", self.layer, passed=True))
        return out
