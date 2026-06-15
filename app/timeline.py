"""Layer 1 — Timeline Intelligence Engine.

Pure, deterministic logic. No external API. This is the zero-cost, highest-value,
lowest-legal-risk layer: it detects *internally inconsistent* (mathematically
impossible) experience claims from the candidate's own data.

Signal weights match the authoritative Signal Weights table in the v1.1 docs:
    TIMELINE_IMPOSSIBLE   +50  (CRITICAL)
    JOB_BEFORE_GRADUATION +40  (CRITICAL)
    EMPLOYMENT_OVERLAP    +25 each (HIGH)
    EXPERIENCE_INFLATION  +25  (HIGH)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple


# --- weights (single source of truth) -------------------------------------
WEIGHTS = {
    "TIMELINE_IMPOSSIBLE": 50,
    "JOB_BEFORE_GRADUATION": 40,
    "EMPLOYMENT_OVERLAP": 25,
    "EXPERIENCE_INFLATION": 25,
}
SEVERITY = {
    "TIMELINE_IMPOSSIBLE": "CRITICAL",
    "JOB_BEFORE_GRADUATION": "CRITICAL",
    "EMPLOYMENT_OVERLAP": "HIGH",
    "EXPERIENCE_INFLATION": "HIGH",
}
# Overlap shorter than this many months is treated as a normal transition.
OVERLAP_TOLERANCE_MONTHS = 3
# When a contested date boundary is given at year granularity ("2019" with no
# month), sub-year ordering is unknowable, so the overlap could be an artefact of
# rounding. Widen the tolerance by this many months for such pairs to avoid
# phantom overlaps on honest, year-granular resumes.
YEAR_GRANULARITY_SLACK_MONTHS = 12
# Allow this much slack before calling claimed-vs-summed an inflation.
INFLATION_TOLERANCE_YEARS = 1.0


@dataclass
class FlagDC:
    code: str
    severity: str
    message: str
    weight: int


@dataclass
class Span:
    start_month: int  # absolute month index = year*12 + (month-1)
    end_month: int
    employment_type: str = "full_time"
    label: str = ""
    start_yearonly: bool = False  # date given at year granularity (e.g. "2019")
    end_yearonly: bool = False


def _is_year_only(value) -> bool:
    """True if a date string carries only year granularity (no month)."""
    if value is None:
        return False
    v = str(value).strip().lower()
    if v in ("present", "current", "now", "ongoing"):
        return False
    return v.replace("/", "-").isdigit()


def _parse_month(value: str, *, default_to_now: bool = False) -> Optional[int]:
    """Parse 'YYYY', 'YYYY-MM', 'present'/'current' into an absolute month index."""
    if value is None:
        return None
    v = str(value).strip().lower()
    if v in ("present", "current", "now", "ongoing"):
        today = date.today()
        return today.year * 12 + (today.month - 1)
    parts = v.replace("/", "-").split("-")
    try:
        year = int(parts[0])
    except (ValueError, IndexError):
        return None
    month = 1
    if len(parts) > 1 and parts[1]:
        try:
            month = max(1, min(12, int(parts[1])))
        except ValueError:
            month = 1
    return year * 12 + (month - 1)


def _years(months: int) -> float:
    return round(months / 12.0, 2)


def _overlap_months(a: Span, b: Span) -> int:
    lo = max(a.start_month, b.start_month)
    hi = min(a.end_month, b.end_month)
    return max(0, hi - lo)


def _spans(jobs) -> List[Span]:
    out: List[Span] = []
    for j in jobs:
        start = _parse_month(getattr(j, "start", None) if not isinstance(j, dict) else j.get("start"))
        end = _parse_month(getattr(j, "end", None) if not isinstance(j, dict) else j.get("end"))
        if start is None or end is None:
            continue
        if end < start:
            start, end = end, start
        etype = (getattr(j, "employment_type", None) if not isinstance(j, dict) else j.get("employment_type")) or "full_time"
        company = (getattr(j, "company", None) if not isinstance(j, dict) else j.get("company")) or ""
        raw_start = getattr(j, "start", None) if not isinstance(j, dict) else j.get("start")
        raw_end = getattr(j, "end", None) if not isinstance(j, dict) else j.get("end")
        out.append(Span(start, end, etype, company,
                        _is_year_only(raw_start), _is_year_only(raw_end)))
    return out


def _age_from(candidate) -> Optional[int]:
    age = getattr(candidate, "age", None) if not isinstance(candidate, dict) else candidate.get("age")
    if age:
        return int(age)
    dob = getattr(candidate, "date_of_birth", None) if not isinstance(candidate, dict) else candidate.get("date_of_birth")
    if dob:
        try:
            y, m, d = (int(x) for x in str(dob).split("-")[:3])
            today = date.today()
            return today.year - y - ((today.month, today.day) < (m, d))
        except (ValueError, IndexError):
            return None
    return None


def _get(obj, name):
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def timeline_score(candidate) -> Tuple[int, List[FlagDC], List[str]]:
    """Return (capped_score, flags, passed_checks) for the timeline layer."""
    flags: List[FlagDC] = []
    passed: List[str] = []
    score = 0

    age = _age_from(candidate)
    grad_year = _get(candidate, "graduation_year")
    claimed = _get(candidate, "total_claimed_years")
    spans = _spans(_get(candidate, "jobs") or [])

    summed_years = _years(sum(s.end_month - s.start_month for s in spans)) if spans else 0.0
    effective_claimed = claimed if claimed is not None else summed_years

    # Check 1 — Age vs experience (mathematically impossible)
    if age is not None and effective_claimed is not None:
        max_possible = age - 18
        if effective_claimed > max_possible:
            score += WEIGHTS["TIMELINE_IMPOSSIBLE"]
            flags.append(FlagDC(
                "TIMELINE_IMPOSSIBLE", SEVERITY["TIMELINE_IMPOSSIBLE"],
                f"Claims {effective_claimed:g} years of experience; maximum possible "
                f"given age {age} is {max_possible} years.",
                WEIGHTS["TIMELINE_IMPOSSIBLE"]))
        else:
            passed.append("AGE_EXPERIENCE_CONSISTENT")

    # Check 2 — Graduation vs first job start
    if grad_year is not None and spans:
        first_start = min(s.start_month for s in spans)
        first_start_year = first_start // 12
        # Allow same-year (internships/part-time during final year): flag only if
        # the first job starts in a year strictly before graduation.
        if first_start_year < int(grad_year):
            score += WEIGHTS["JOB_BEFORE_GRADUATION"]
            flags.append(FlagDC(
                "JOB_BEFORE_GRADUATION", SEVERITY["JOB_BEFORE_GRADUATION"],
                f"First job starts {first_start_year}, before graduation year {grad_year}.",
                WEIGHTS["JOB_BEFORE_GRADUATION"]))
        else:
            passed.append("GRADUATION_CONSISTENT")

    # Check 3 — Overlapping full-time employment
    full = [s for s in spans if s.employment_type == "full_time"]
    overlap_count = 0
    for i in range(len(full)):
        for k in range(i + 1, len(full)):
            a, b = full[i], full[k]
            # the contested edge is the later start vs. the earlier end; if either
            # bounding date is year-granular, the apparent overlap may be a
            # rounding artefact, so widen the tolerance for this pair.
            if a.start_month <= b.start_month:
                contested_yo = b.start_yearonly or a.end_yearonly
            else:
                contested_yo = a.start_yearonly or b.end_yearonly
            tol = OVERLAP_TOLERANCE_MONTHS + (YEAR_GRANULARITY_SLACK_MONTHS if contested_yo else 0)
            if _overlap_months(a, b) > tol:
                overlap_count += 1
    if overlap_count:
        add = WEIGHTS["EMPLOYMENT_OVERLAP"] * overlap_count
        score += add
        flags.append(FlagDC(
            "EMPLOYMENT_OVERLAP", SEVERITY["EMPLOYMENT_OVERLAP"],
            f"{overlap_count} pair(s) of full-time jobs overlap by more than "
            f"{OVERLAP_TOLERANCE_MONTHS} months.",
            add))
    elif full:
        passed.append("NO_EMPLOYMENT_OVERLAP")

    # Check 4 — Experience inflation (claimed > sum of individual tenures)
    if claimed is not None and spans:
        if claimed > summed_years + INFLATION_TOLERANCE_YEARS:
            score += WEIGHTS["EXPERIENCE_INFLATION"]
            flags.append(FlagDC(
                "EXPERIENCE_INFLATION", SEVERITY["EXPERIENCE_INFLATION"],
                f"Claims {claimed:g} years but listed jobs sum to only "
                f"{summed_years:g} years.",
                WEIGHTS["EXPERIENCE_INFLATION"]))
        else:
            passed.append("EXPERIENCE_NOT_INFLATED")

    return min(score, 100), flags, passed
