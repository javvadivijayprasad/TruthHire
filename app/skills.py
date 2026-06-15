"""AI skills-consistency scoring (S21 / TH-032).

Generates domain questions calibrated to a candidate's *claimed* seniority, then
scores answer depth against what that seniority should produce. A large gap
(deep claim, shallow answers) raises SKILLS_MISMATCH. Deterministic and offline;
a production deployment can swap the heuristic scorer for an LLM rubric."""
from __future__ import annotations
import re
from typing import Dict, List, Optional

# question bank: (min_level, question). level 1=junior .. 4=principal
BANK: Dict[str, List] = {
    "software": [
        (1, "Explain the difference between a list and a dictionary, with a use case for each."),
        (2, "How would you find and fix a memory leak in a long-running service?"),
        (2, "Describe how you would add caching to a slow API endpoint and its trade-offs."),
        (3, "Walk through designing a rate limiter for a multi-tenant API."),
        (3, "How do you guarantee idempotency in a payment-processing pipeline?"),
        (4, "Describe a system you re-architected for 10x scale: bottlenecks, decisions, results."),
    ],
    "data": [
        (1, "What is the difference between supervised and unsupervised learning?"),
        (2, "How do you detect and handle data leakage in a model pipeline?"),
        (3, "Explain how you'd evaluate a fraud model where positives are 1% of data."),
        (4, "Describe leading a data platform migration: schema, lineage, and rollback strategy."),
    ],
    "management": [
        (1, "How do you run an effective 1:1 with a direct report?"),
        (2, "Describe how you handled an underperforming team member."),
        (3, "How do you set and track quarterly goals across multiple teams?"),
        (4, "Describe a re-org you led: rationale, communication, and measured outcome."),
    ],
    "general": [
        (1, "Describe a recent project and your specific contribution."),
        (2, "Tell me about a difficult problem you solved and how."),
        (3, "Describe a decision you made with incomplete information."),
        (4, "Describe how you set technical or organisational strategy."),
    ],
}

EXPECTED_DEPTH = {1: 15, 2: 30, 3: 45, 4: 55}   # calibrated expected depth by level
_TOOLS = re.compile(r"\b(python|java|sql|redis|kafka|docker|kubernetes|aws|gcp|postgres|"
                    r"react|fastapi|spark|airflow|terraform|ci/cd|oauth|index|latency|"
                    r"throughput|sla|p99|sharding|replication|idempoten)\w*", re.I)


def seniority_level(claimed_years: Optional[float]) -> int:
    y = claimed_years or 0
    if y <= 2: return 1
    if y <= 6: return 2
    if y <= 12: return 3
    return 4


def domain_for(candidate) -> str:
    jobs = (candidate.get("jobs") if isinstance(candidate, dict) else getattr(candidate, "jobs", None)) or []
    titles = " ".join(str((j.get("title") if isinstance(j, dict) else getattr(j, "title", "")) or "") for j in jobs).lower()
    if any(w in titles for w in ("data", "scientist", "ml", "analyst")): return "data"
    if any(w in titles for w in ("manager", "director", "lead", "head", "vp")): return "management"
    if any(w in titles for w in ("engineer", "developer", "architect", "swe")): return "software"
    return "general"


def generate_questions(domain: str, level: int, n: int = 3) -> List[str]:
    bank = BANK.get(domain, BANK["general"])
    at_level = [q for lvl, q in bank if lvl >= min(level, 4)] or [q for _, q in bank]
    return at_level[:n] if len(at_level) >= n else (at_level + [q for _, q in bank])[:n]


def score_answer(answer: str) -> int:
    """Heuristic 0-100 depth: length + technical specificity + concrete detail."""
    if not answer or not answer.strip():
        return 0
    words = len(answer.split())
    length = min(50, words / 4)                       # up to 50 pts for substance
    tools = min(30, 10 * len(set(m.group(0).lower() for m in _TOOLS.finditer(answer))))
    specifics = min(20, 5 * len(re.findall(r"\b\d+(\.\d+)?%?\b", answer)))  # numbers/metrics
    return int(min(100, length + tools + specifics))


def assess(candidate, answers: List[str], domain: Optional[str] = None) -> Dict:
    claimed = candidate.get("total_claimed_years") if isinstance(candidate, dict) else getattr(candidate, "total_claimed_years", None)
    level = seniority_level(claimed)
    dom = domain or domain_for(candidate)
    expected = EXPECTED_DEPTH[level]
    depths = [score_answer(a) for a in answers] if answers else []
    avg = round(sum(depths) / len(depths), 1) if depths else 0.0
    flags = []
    if depths and avg < expected - 20:
        flags.append({"code": "SKILLS_MISMATCH", "severity": "HIGH", "weight": 25,
                      "layer": "skills",
                      "message": f"Answer depth {avg} is far below the ~{expected} expected for "
                                 f"{claimed or 0:g} claimed years ({dom}, level {level})."})
    return {"domain": dom, "claimed_years": claimed, "seniority_level": level,
            "expected_depth": expected, "answer_depths": depths, "avg_depth": avg, "flags": flags}
