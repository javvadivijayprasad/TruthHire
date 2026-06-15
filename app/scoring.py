"""Score combiner across all layers (S3 + Phase 2).

Resolves the two-model ambiguity in the v1.0 spec in favour of a single,
explainable ADDITIVE model: risk_score = min(100, sum of fired flag weights),
with per-layer subtotals. Higher = more suspicious (field named risk_score,
not the inverted trust_score)."""
from __future__ import annotations
from typing import Dict, List, Optional

from .timeline import timeline_score
from .providers.base import default_registry
from .config import settings

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


def score_candidate(candidate, layers: Optional[List[str]] = None, registry=None) -> Dict:
    layers = layers or settings.default_layers
    registry = default_registry() if registry is None else registry

    flags: List[dict] = []
    passed: List[str] = []

    if "timeline" in layers:
        _, tflags, tpassed = timeline_score(candidate)
        for f in tflags:
            flags.append({"code": f.code, "severity": f.severity, "message": f.message,
                          "weight": f.weight, "layer": "timeline"})
        passed.extend(tpassed)

    for prov in registry.values():
        if prov.layer in layers:
            for sig in prov.check(candidate):
                if sig.passed:
                    passed.append(sig.code)
                else:
                    flags.append(sig.as_flag())

    layer_scores = {"timeline": 0, "digital": 0, "company": 0, "network": 0}
    for f in flags:
        L = f.get("layer", "timeline")
        layer_scores[L] = min(100, layer_scores.get(L, 0) + f["weight"])

    total = min(100, sum(f["weight"] for f in flags))
    level, rec = risk_level(total)
    return {"risk_score": total, "risk_level": level, "recommendation": rec,
            "flags": flags, "passed_checks": passed, "layer_scores": layer_scores}
