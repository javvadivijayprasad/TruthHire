"""S24 scale hardening: metrics + healthz."""
import importlib
from fastapi.testclient import TestClient
H = {"Authorization": "Bearer th_sandbox_demo_key"}


def client():
    import app.ratelimit as rl, app.main as main
    importlib.reload(rl); importlib.reload(main)
    return TestClient(main.app)


def test_healthz_reports_db_up():
    c = client()
    j = c.get("/healthz").json()
    assert j["status"] == "ok" and j["database"] == "up"


def test_metrics_counts_requests():
    c = client()
    c.get("/health"); c.get("/health")
    c.post("/verify", headers=H, json={"candidate": {"name": "X"}, "options": {"layers": ["timeline"]}})
    m = c.get("/metrics", headers=H).json()
    assert m["requests"] >= 3 and "avg_latency_ms" in m and m["by_status"].get("200", 0) >= 1
