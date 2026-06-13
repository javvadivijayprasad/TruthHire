"""API-level tests (TH-001, TH-003, TH-012) using FastAPI's TestClient."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer th_sandbox_demo_key"}


def test_health_no_auth():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_verify_requires_auth():
    r = client.post("/verify", json={"candidate": {"name": "X"}})
    assert r.status_code == 401


def test_verify_rejects_bad_key():
    r = client.post("/verify", json={"candidate": {"name": "X"}},
                    headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_verify_flags_impossible_candidate():
    payload = {
        "candidate": {
            "name": "John Smith",
            "email": "john.smith@gmail.com",
            "age": 24,
            "total_claimed_years": 15,
        },
        "options": {"layers": ["timeline"], "reference_id": "JOB-1"},
    }
    r = client.post("/verify", json=payload, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["reference_id"] == "JOB-1"
    assert body["result"]["risk_score"] == 50
    # 50 falls in the 21-50 MEDIUM band per the documented Risk Thresholds.
    assert body["result"]["risk_level"] == "MEDIUM"
    assert any(f["code"] == "TIMELINE_IMPOSSIBLE" for f in body["result"]["flags"])
    assert body["check_id"].startswith("th_chk_")


def test_verify_passes_clean_candidate():
    payload = {"candidate": {
        "name": "Real Person", "age": 40, "total_claimed_years": 12,
        "graduation_year": 2008,
        "jobs": [{"start": "2009-01", "end": "2015-01"},
                 {"start": "2015-02", "end": "2021-01"}],
    }}
    r = client.post("/verify", json=payload, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["result"]["risk_level"] == "LOW"


def test_verify_from_cv_text():
    cv = ("Bad Actor\nbad@x.com\nB.S. 2023\n"
          "MegaCorp Senior Architect 2009 - 2021\n")
    payload = {"candidate": {"name": "Bad Actor", "cv_text": cv}}
    r = client.post("/verify", json=payload, headers=AUTH)
    