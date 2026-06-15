"""BambooHR ATS adapter (S17/S19). Maps a BambooHR applicant to a verify candidate."""
from __future__ import annotations
from typing import Dict


def map_candidate(bh: Dict) -> Dict:
    jobs = []
    for e in bh.get("workExperience", []):
        jobs.append({"title": e.get("jobTitle"), "company": e.get("companyName"),
                     "start": (e.get("startDate") or "")[:7] or None,
                     "end": (e.get("endDate") or "present")[:7] or "present",
                     "employment_type": "full_time"})
    return {
        "name": " ".join(filter(None, [bh.get("firstName"), bh.get("lastName")])),
        "email": bh.get("email"), "phone": bh.get("phoneNumber"), "jobs": jobs,
    }
