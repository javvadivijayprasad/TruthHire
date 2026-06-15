"""GitHub Activity (S4 / TH-017). Free public API — goes live with no key.
Live input: candidate.github_username. Slice: {"account_year": int, "active": bool}."""
from __future__ import annotations
import os
from typing import List, Optional
from .base import Provider, Signal, _get
from . import http


class GitHubProvider(Provider):
    name = "github"; display_name = "GitHub Activity"
    description = "Checks GitHub account age and contribution history against claimed developer experience."
    source = "GitHub API"; layer = "digital"; slice = "github"; requires_key = False

    def fetch_live(self, candidate) -> Optional[dict]:
        user = _get(candidate, "github_username")
        if not user:
            return None
        u = http.get_json(f"https://api.github.com/users/{user}",
                          headers={"Accept": "application/vnd.github+json"})
        if not u or "created_at" not in u:
            return None
        ev = http.get_json(f"https://api.github.com/users/{user}/events/public",
                           params={"per_page": 5}) or []
        return {"account_year": int(str(u["created_at"])[:4]), "active": bool(ev)}

    def evaluate(self, data, candidate) -> List[Signal]:
        out: List[Signal] = []
        claimed = _get(candidate, "graduation_year") or 0
        acct = data.get("account_year")
        if acct and claimed and acct > claimed + 1:
            out.append(Signal("GITHUB_NEW_ACCOUNT", "LOW", 10,
                f"GitHub account created {acct}, after claimed career start {claimed}.", self.layer))
        if data.get("active") is False:
            out.append(Signal("GITHUB_INACTIVE", "MEDIUM", 20,
                "No GitHub activity during claimed software-development years.", self.layer))
        if not out and data.get("active") is True:
            out.append(Signal("GITHUB_ACTIVE", "LOW", 0,
                "GitHub activity corroborates claims.", self.layer, passed=True))
        return out
