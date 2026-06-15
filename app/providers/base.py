"""Provider interface + signal model + registry."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..config import settings


@dataclass
class Signal:
    code: str
    severity: str          # LOW | MEDIUM | HIGH | CRITICAL
    weight: int
    message: str
    layer: str             # digital | company | network
    passed: bool = False

    def as_flag(self) -> Dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "weight": self.weight,
                "message": self.message, "layer": self.layer}


class Provider:
    name: str = "base"
    display_name: str = "Base"
    description: str = ""
    source: str = ""
    layer: str = "digital"
    slice: str = "base"
    env_key: Optional[str] = None     # env var holding the live API key
    requires_key: bool = True         # GitHub etc. set this False (free API)

    def __init__(self, live: Optional[bool] = None, api_key: Optional[str] = None):
        self.api_key = api_key or (os.environ.get(self.env_key) if self.env_key else None)
        want = settings.live if live is None else live
        self.live = bool(want and (self.api_key or not self.requires_key))

    def _slice(self, candidate) -> Optional[dict]:
        osint = candidate.get("osint") if isinstance(candidate, dict) else getattr(candidate, "osint", None)
        return osint.get(self.slice) if osint else None

    def fetch_live(self, candidate) -> Optional[dict]:
        """Override: fetch the slice from a real API. Return None to abstain."""
        return None

    def evaluate(self, data: dict, candidate) -> List["Signal"]:
        raise NotImplementedError

    def check(self, candidate) -> List["Signal"]:
        data = None
        if self.live:
            try:
                data = self.fetch_live(candidate)
            except Exception:
                data = None
        if data is None:                 # offline, or live failed/abstained
            data = self._slice(candidate)
        if not data:
            return []
        return self.evaluate(data, candidate)


def _get(c, k, default=None):
    return (c.get(k, default) if isinstance(c, dict) else getattr(c, k, default))


def _first_company(candidate) -> Optional[str]:
    jobs = _get(candidate, "jobs") or []
    for j in jobs:
        comp = j.get("company") if isinstance(j, dict) else getattr(j, "company", None)
        if comp:
            return comp
    return None


def default_registry() -> Dict[str, "Provider"]:
    from .github import GitHubProvider
    from .email_presence import EmailPresenceProvider
    from .phone import PhoneProvider
    from .web_presence import WebPresenceProvider
    from .company import CompanyProvider
    from .linkedin import LinkedInProvider
    from .network import NetworkProvider
    provs = [GitHubProvider(), EmailPresenceProvider(), PhoneProvider(),
             WebPresenceProvider(), CompanyProvider(), LinkedInProvider(),
             NetworkProvider()]
    return {p.name: p for p in provs}
