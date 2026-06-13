"""Lightweight CV text extractor (Sprint 1, TH-002)."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?){2,4}\d{2,4}")
YEAR_RE = re.compile(r"(19|20)\d{2}")

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"])}

_DATE_TOKEN = r"(?:[A-Za-z]{3,9}\.?\s+)?(?:\d{1,2}[/\s])?(?:19|20)\d{2}"
DATE_RANGE_RE = re.compile(
    r"(?P<s>" + _DATE_TOKEN + r")"
    r"\s*(?:[-–—]|to)\s*"
    r"(?P<e>present|current|now|" + _DATE_TOKEN + r")",
    re.IGNORECASE)
GRAD_RE = re.compile(
    r"(?:graduat\w*|b\.?s\.?|b\.?tech|b\.?e\.?|bachelor|m\.?s\.?|master|degree|university|college)"
    r"[^\n]*?((?:19|20)\d{2})", re.IGNORECASE)


def _norm_date(token: str) -> Optional[str]:
    t = token.strip().lower()
    if t in ("present", "current", "now"):
        return "present"
    ym = YEAR_RE.search(t)
    if not ym:
        return None
    year = ym.group(0)
    month = None
    for name, num in MONTHS.items():
        if name in t:
            month = num
            break
    if month is None:
        mslash = re.match(r"\s*(\d{1,2})\s*/\s*(?:19|20)\d{2}", t)
        if mslash:
            month = int(mslash.group(1))
    return f"{year}-{month:02d}" if month else f"{year}"


def extract_name(text: str) -> Optional[str]:
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if EMAIL_RE.search(s) or any(ch.isdigit() for ch in s):
            continue
        words = s.split()
        if 1 < len(words) <= 4 and all(w[0].isupper() for w in words if w[:1].isalpha()):
            return s
    return None


def parse_cv(text: str) -> Dict:
    text = text or ""
    email_m = EMAIL_RE.search(text)
    phone = None
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 7 <= len(digits) <= 15:
            phone = m.group(0).strip()
            break
    grad_years = [int(m.group(1)) for m in GRAD_RE.finditer(text)]
    graduation_year = min(grad_years) if grad_years else None
    jobs: List[Dict] = []
    for m in DATE_RANGE_RE.finditer(text):
        start = _norm_date(m.group("s"))
        end = _norm_date(m.group("e"))
        if not start or not end:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        context = text[line_start:m.start()].strip(" \t|:-–—")
        jobs.append({"company": context[:80] or None, "start": start,
                     "end": end, "employment_type": "full_time"})
    return {"name": extract_name(text), "email": email_m.group(0) if email_m else None,
            "phone": phone, "graduation_year": graduation_year, "jobs": jobs}
