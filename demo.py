"""Demo: run TruthHire across all layers without a server. `python demo.py`."""
import json
from app.scoring import score_candidate

CASES = {
    "clean senior (LOW)": {
        "name": "Real Person", "age": 40, "graduation_year": 2008,
        "total_claimed_years": 12,
        "jobs": [{"start": "2009-01", "end": "2015-01"},
                 {"start": "2015-02", "end": "2021-01"}],
        "osint": {"github": {"account_year": 2009, "active": True},
                  "company": {"exists": True, "registered_year": 1999}},
    },
    "impossible junior + osint (CRITICAL)": {
        "name": "John Smith", "age": 24, "graduation_year": 2021,
        "total_claimed_years": 15,
        "osint": {"company": {"exists": False},
                  "network": {"reports": 3},
                  "linkedin": {"created_year": 2024}},
    },
    "atypical-but-genuine (advisory only)": {
        "name": "Privacy First", "age": 47, "graduation_year": 1999,
        "total_claimed_years": 20,
        "jobs": [{"start": "2000-01", "end": "2020-01"}],
        "osint": {"web": {"mentions_at_employer": 0},
                  "email": {"age_days": 10, "platforms": 1}},
    },
}

for label, c in CASES.items():
    r = score_candidate(c, layers=["timeline", "digital", "company", "network"])
    print(f"\n=== {label} ===")
    print(f"  risk_score={r['risk_score']}  level={r['risk_level']}")
    print(f"  layer_scores={r['layer_scores']}")
    for f in r["flags"]:
        print(f"    [{f['severity']:8}] {f['code']} (+{f['weight']}, {f['layer']})")
    if not r["flags"]:
        print("    (no flags)")
