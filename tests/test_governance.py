"""Compliance/governance: consent, audit, dispute, adverse-action."""
import importlib
from fastapi.testclient import TestClient

H = {"Authorization": "Bearer th_sandbox_demo_key"}


def client():
    import app.ratelimit as rl, app.main as main
    importlib.reload(rl); importlib.reload(main)
    return TestClient(main.app)


def _critical(c):
    return c.post("/verify", headers=H, json={"candidate": {"name": "John Smith", "age": 24,
        "total_claimed_years": 15, "osint": {"company": {"exists": False}}},
        "options": {"layers": ["timeline", "company"], "consent": True}})


def test_adverse_action_on_critical():
    c = client(); r = _critical(c).json()["result"]
    assert r["risk_level"] == "CRITICAL"
    aa = r["adverse_action"]
    assert aa and aa["notice"] == "pre-adverse-action" and aa["reasons"]


def test_no_adverse_action_when_clean():
    c = client()
    r = c.post("/verify", headers=H, json={"candidate": {"name": "OK", "age": 40,
        "total_claimed_years": 10}, "options": {"layers": ["timeline"]}}).json()["result"]
    assert r["risk_level"] == "LOW" and r["adverse_action"] is None


def test_audit_explains_decision():
    c = client(); cid = _critical(c).json()["check_id"]
    a = c.get(f"/audit/{cid}", headers=H).json()
    assert a["risk_level"] == "CRITICAL" and any(e["code"] == "TIMELINE_IMPOSSIBLE" for e in a["explanations"])


def test_dispute_and_reinvestigate():
    c = client(); cid = _critical(c).json()["check_id"]
    d = c.post("/dispute", headers=H, json={"check_id": cid, "reason": "I really am senior"}).json()
    assert d["status"] == "open"
    r = c.post(f"/dispute/{d['dispute_id']}/reinvestigate", headers=H).json()
    assert r["status"] == "reinvestigated" and r["audit"]["check_id"] == cid


def test_dispute_unknown_check_404():
    c = client()
    assert c.post("/dispute", headers=H, json={"check_id": "nope", "reason": "x"}).status_code == 404
