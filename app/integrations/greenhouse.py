"""Greenhouse ATS adapter (S17 / TH-031). Maps a Greenhouse candidate to a
TruthHire verify candidate dict."""
from __future__ import annotations
from typing import Dict


def map_candidate(gh: Dict) -> Dict:
    emails = gh.get("email_addresses") or []
    phones = gh.get("phone_numbers") or []
    jobs = []
    for e in gh.get("employments", []):
        jobs.append({"title": e.get("title"), "company": e.get("company_name"),
                     "start": (e.get("start_date") or "")[:7] or None,
                     "end": (e.get("end_date") or "present")[:7] or "present",
                     "employment_type": "full_time"})
    return {
        "name": " ".join(filter(None, [gh.get("first_name"), gh.get("last_name")])) or gh.get("name"),
        "email": (emails[0].get("value") if emails else None),
        "phone": (phones[0].get("value") if phones else None),
        "jobs": jobs,
    }
