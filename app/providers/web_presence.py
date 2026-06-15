"""Web Presence (S8 / TH-022). Live: SerpAPI Google search (env SERPAPI_KEY).
Input: candidate.name + first employer."""
from __future__ import annotations
from typing import List, Optional
from .base import Provider, Signal, _get, _first_company
from . import http


class WebPresenceProvider(Provider):
    name = "web"; display_name = "Web Presence"
    description = "Searches the web for the candidate in connection with the claimed employer."
    source = "Google (SerpAPI)"; layer = "digital"; slice = "web"; env_key = "SERPAPI_KEY"

    def fetch_live(self, candidate) -> Optional[dict]:
        name = _get(candidate, "name"); emp = _first_company(candidate)
        if not (name and emp and self.api_key):
            return None
        d = http.get_json("https://serpapi.com/search",
                          params={"engine": "google", "q": f'"{name}" "{emp}"',
                                  "api_key": self.api_key, "num": 10})
        if not d:
            return None
        return {"mentions_at_employer": len(d.get("organic_results", []))}

    def evaluate(self, data, candidate) -> List[Signal]:
        if data.get("mentions_at_employer") == 0:
            return [Signal("NO_WEB_PRESENCE", "HIGH", 25,
                "No web results connect the candidate to a claimed employer "
                "(advisory; common for privacy-conscious candidates).", self.layer)]
        return []
