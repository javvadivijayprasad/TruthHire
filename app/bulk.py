"""Bulk CSV candidate screening (S20). CSV in -> scored rows out."""
from __future__ import annotations
import csv
import io
from typing import Dict, List

from .scoring import score_candidate

_INT = {"age", "graduation_year"}
_FLOAT = {"total_claimed_years"}


def parse_rows(csv_text: str) -> List[Dict]:
    out = []
    for row in csv.DictReader(io.StringIO(csv_text)):
        c = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
        for k in list(c):
            if c[k] == "":
                c[k] = None
            elif k in _INT and c[k] is not None:
                try: c[k] = int(c[k])
                except ValueError: c[k] = None
            elif k in _FLOAT and c[k] is not None:
                try: c[k] = float(c[k])
                except ValueError: c[k] = None
        out.append(c)
    return out


def score_csv(csv_text: str, layers=None) -> List[Dict]:
    results = []
    for c in parse_rows(csv_text):
        ref = c.pop("reference_id", None) or c.get("email") or c.get("name")
        r = score_candidate(c, layers)
        results.append({"reference_id": ref, "name": c.get("name"),
                        "risk_score": r["risk_score"], "risk_level": r["risk_level"],
                        "flags": ";".join(f["code"] for f in r["flags"])})
    return results


def to_csv(results: List[Dict]) -> str:
    if not results:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(results[0].keys()))
    w.writeheader(); w.writerows(results)
    return buf.getvalue()
