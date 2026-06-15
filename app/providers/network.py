"""Shared Fraud Network provider (S14/S15 / TH-028, TH-029).

Consults the in-process shared fraud network: cross-org report counts (threshold
flags) and fraud-ring detection (one identifier under multiple names). Offline,
you can still inject osint.network = {"reports": int}."""
from __future__ import annotations
from typing import List
from .base import Provider, Signal, _get
from ..network_store import network


class NetworkProvider(Provider):
    name = "network"; display_name = "Shared Fraud Network"
    description = "Checks how many other organizations have flagged this candidate, and fraud rings."
    source = "Shared fraud-hash network"; layer = "network"; slice = "network"
    requires_key = False

    def check(self, candidate) -> List[Signal]:
        email = _get(candidate, "email"); phone = _get(candidate, "phone")
        sl = self._slice(candidate) or {}
        reports = sl.get("reports")
        if reports is None and (email or phone):
            reports = network.lookup(email, phone)["reports"]
        out: List[Signal] = []
        if reports and reports >= 3:
            out.append(Signal("NETWORK_FLAG_3PLUS", "CRITICAL", 60,
                f"Candidate previously flagged by {reports} organizations.", self.layer))
        elif reports and reports >= 1:
            out.append(Signal("NETWORK_FLAG_1", "HIGH", 30,
                f"Candidate previously flagged by {reports} organization(s).", self.layer))
        if email or phone:
            r = network.ring(email, phone)
            if r["is_ring"]:
                out.append(Signal("DUPLICATE_IDENTITY", "CRITICAL", 60,
                    f"Same identifier used under {r['identities']} different names.", self.layer))
        return out

    def evaluate(self, data, candidate):  # retained for interface symmetry
        return []
