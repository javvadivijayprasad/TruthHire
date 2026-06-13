"""Score combiner + risk thresholds.

Sprint 1 only implements the timeline layer, so the final risk_score is the
timeline score. The structure is ready for Phases 2-4 (digital / company /
network) to contribute additional signal points, still capped at 100.

Risk thresholds (from the docs' Risk Thresholds table):
    0-20   LOW      Auto-pass to next stage
    21-50  MEDIUM   Flag for human review - request documentation
    51-75  HIGH     Senior recruiter review required before proceeding
    76-100 CRITICAL Auto-reject - do not proceed without legal review
"""
from __future__ import annotations

from typing import Dict, List

from .timeline import timeline_score, FlagDC

THRESHOLDS = [
    (0, 20, "LOW", "Auto-pass to next stage"),
    (21, 50, "MEDIUM", "Flag for human review - request documentation"),
    (51, 75, "HIGH", "Senior recruiter review required before proceeding"),
    (76, 100, "CRITICAL", "Auto-reject - do not proceed without legal review"),
]


def risk_level(score: int):
    for lo, hi, level, rec in THRESHOLDS:
        if lo <= score <= hi:
            return level, rec
    return "CRITICAL", THRESHOLDS[-1][3]


def score_candidate(candidate, layers: List[str] | None = None) -> Dict:
    """Run requested layers and return a structured result dict."""
    layers = layers or ["timeline"]
    flags: List[FlagDC] = []
    passed: List[str] = []
    layer_scores = {"timeline": 0, "digital": 0, "company": 0, "network": 0}

    if "timeline" in layers:
        t_score, t_flags, t_passed = timeline_score(candidate)
        layer_scores["timeline"] = t_score
        flags.extend(t_flags)
        passed.extend(t_passed)

    # Phase 2-4 layers would add here:
    # if "digital" in layers: ...
    # if "company" in layers: ...
    # if "network" in layers: ...

    total = min(sum(layer_scores.values()), 100)
    level, rec = risk_level(total)

    return {
        "risk_score": total,
        "risk_level": level,
        "recommendation": rec,
        "flags": [f.__dict__ for f in flags],
        "passed_checks": passed,
        "layer_scores": layer_scores,
    }
