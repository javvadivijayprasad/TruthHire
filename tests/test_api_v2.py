"""Phase 2 API tests: retrieval, rate limit, providers, usage, webhook path."""
import importlib
from fastapi.testclient import TestClient

import app.ratelimit as rl
import app.main as main

AUTH = {"Authorization": "Bearer th_sandbox_demo_key"}


def fresh_client():
    importlib.reload(rl)              # reset limiter state
    importlib.reload(main)
    return TestClient(main.app)


def test_retrieval_roundtrip():
    client = fresh_client()
    r = client.post("/verify", json={"candidate": {"name": "X", "age": 24,
                    "total_claimed_years": 15}, "options": {"layers": ["timeline"]}},
                    headers=AUTH)
    cid = r.json()["check_id"]
    g = client.get(f"/verify/{cid}", headers=AUTH)
    assert g.status_code == 200 and g.json()["check_id"] == cid


def test_retrieval_404():
    client = fresh_client()
    g = client.get("/verify/th_chk_nope", headers=AUTH)
    assert g.status_code == 404 and g.json()["error_code"] == "NOT_FOUND"


def test_rate_limit_429():
    client = fresh_client()
    payload = {"candidate": {"name": "X"}, "options": {"layers": ["timeline"]}}
    codes = [client.post("/verify", json=payload, headers=AUTH).status_code for _ in range(15)]
    assert 429 in codes
    assert any(client.post("/verify", json=payload, headers=AUTH).status_code == 429
               for _ in range(3)) or 429 in codes


def test_providers_endpoint():
    client = fresh_client()
    r = client.get("/providers", headers=AUTH)
    names = {p["name"] for p in r.json()["providers"]}
    assert {"github", "email", "phone", "web", "company", "linkedin", "network"} <= names
    ln = next(p for p in r.json()["providers"] if p["name"] == "linkedin")
    assert ln["mode"] == "offline" and "Proxycurl" in (ln["note"] or "")


def test_usage_endpoint():
    client = fresh_client()
    client.post("/verify", json={"candidate": {"name": "X"}, "options": {"layers": ["timeline"]}}, headers=AUTH)
    r = client.get("/usage", headers=AUTH)
    assert r.json()["checks_this_session"] >= 1


def test_webhook_async_marks_processing():
    client = fresh_client()
    delivered = {}
    async def fake_deliver(url, payload, **kw):
        delivered["url"] = url; delivered["payload"] = payload; return True
    main.deliver = fake_deliver   # avoid real network in the background task
    r = client.post("/verify", json={"candidate": {"name": "X", "age": 24,
                    "total_claimed_years": 15},
                    "options": {"layers": ["timeline"], "webhook_url": "https://example.com/cb"}},
                    headers=AUTH)
    assert r.status_code == 200 and r.json()["status"] == "processing"
    assert delivered["url"] == "https://example.com/cb"
    assert delivered["payload"]["event"] == "check.complete"


def test_full_layered_verify_with_osint():
    client = fresh_client()
    payload = {"candidate": {"name": "Fraud", "age": 24, "total_claimed_years": 15,
               "osint": {"company": {"exists": False}, "network": {"reports": 3}}}}
    r = client.post("/verify", json=payload, headers=AUTH)
    body = r.json()["result"]
    assert body["risk_score"] == 100 and body["risk_level"] == "CRITICAL"
