"""Bulk CSV, billing, ATS adapters, key issuance, dashboard (S11,S12,S16,S17,S20)."""
import importlib
import pytest
from fastapi.testclient import TestClient

from app import bulk, billing
from app.credits import ledger
from app.integrations import greenhouse, bamboohr

AUTH = {"Authorization": "Bearer th_sandbox_demo_key"}
ADMIN = {"Authorization": "Bearer th_admin_demo_key"}


@pytest.fixture(autouse=True)
def _reset():
    ledger.reset(); yield; ledger.reset()


def fresh_client():
    import app.ratelimit as rl, app.main as main
    importlib.reload(rl); importlib.reload(main)
    return TestClient(main.app)


# ---- bulk CSV (S20) ----
def test_bulk_csv_scoring():
    csv = "name,age,total_claimed_years\nJohn,24,15\nJane,40,12\n"
    rows = bulk.score_csv(csv, ["timeline"])
    by = {r["name"]: r for r in rows}
    assert by["John"]["risk_level"] in ("MEDIUM", "HIGH", "CRITICAL")
    assert by["Jane"]["risk_score"] == 0
    assert "risk_score" in bulk.to_csv(rows).splitlines()[0]


def test_bulk_endpoint():
    c = fresh_client()
    r = c.post("/verify/bulk", headers=AUTH,
               json={"csv": "name,age,total_claimed_years\nX,24,15\n", "layers": ["timeline"]})
    assert r.json()["count"] == 1 and r.json()["results"][0]["risk_score"] == 50


# ---- billing (S16) ----
def test_billing_sandbox_activates_plan():
    out = billing.create_checkout("orgZ", "growth")
    assert out["mode"] == "sandbox" and out["activated"] is True
    assert ledger.balance("orgZ")["plan"] == "growth"


def test_billing_webhook_suspends_on_failure():
    billing.create_checkout("orgZ", "scale")
    out = billing.handle_event("invoice.payment_failed", "orgZ")
    assert out["status"] == "suspended_to_free"
    assert ledger.balance("orgZ")["plan"] == "free"


def test_subscribe_endpoint():
    c = fresh_client()
    r = c.post("/billing/subscribe", headers=AUTH, json={"plan": "starter"})
    assert r.json()["plan"] == "starter"


# ---- ATS adapters (S17) ----
def test_greenhouse_mapping():
    gh = {"first_name": "Jane", "last_name": "Doe",
          "email_addresses": [{"value": "jane@x.com"}],
          "phone_numbers": [{"value": "+1555"}],
          "employments": [{"title": "Eng", "company_name": "Acme",
                           "start_date": "2015-01-01", "end_date": "2020-01-01"}]}
    c = greenhouse.map_candidate(gh)
    assert c["name"] == "Jane Doe" and c["email"] == "jane@x.com"
    assert c["jobs"][0]["company"] == "Acme" and c["jobs"][0]["start"] == "2015-01"


def test_bamboohr_mapping():
    bh = {"firstName": "Jon", "lastName": "Roe", "email": "jon@x.com",
          "workExperience": [{"jobTitle": "Dev", "companyName": "Globex",
                              "startDate": "2018-06-01", "endDate": ""}]}
    c = bamboohr.map_candidate(bh)
    assert c["name"] == "Jon Roe" and c["jobs"][0]["company"] == "Globex"
    assert c["jobs"][0]["end"] == "present"


# ---- key issuance (S12) ----
def test_issue_key_requires_admin():
    c = fresh_client()
    assert c.post("/admin/keys", headers=AUTH, json={"label": "Acme"}).status_code == 403


def test_issue_key_and_use_it():
    c = fresh_client()
    r = c.post("/admin/keys", headers=ADMIN, json={"label": "AcmeCorp"})
    assert r.status_code == 200
    new = r.json()["api_key"]
    # the new key authenticates a real verify call
    v = c.post("/verify", headers={"Authorization": f"Bearer {new}"},
               json={"candidate": {"name": "X"}, "options": {"layers": ["timeline"]}})
    assert v.status_code == 200


# ---- dashboard (S11) ----
def test_dashboard_html():
    c = fresh_client()
    r = c.get("/ui")
    assert r.status_code == 200 and "TruthHire" in r.text and "Verify" in r.text
