"""Phase 3: shared fraud network, fraud rings, contribution credits."""
import importlib
import pytest
from fastapi.testclient import TestClient

from app.network_store import network
from app.credits import ledger, CreditLedger
from app.scoring import score_candidate


@pytest.fixture(autouse=True)
def _reset():
    network.reset(); ledger.reset()
    yield
    network.reset(); ledger.reset()


# ---- shared network ----
def test_report_and_threshold_lookup():
    network.report("orgA", email="x@y.com", phone="+1555", outcome="fraud_confirmed")
    network.report("orgB", email="x@y.com", phone="+1555", outcome="fraud_confirmed")
    r = network.lookup("x@y.com", "+1555", threshold=2)
    assert r["reports"] == 2 and r["flagged"] is True
    assert network.lookup("x@y.com", "+1555", threshold=3)["flagged"] is False


def test_only_hashes_stored():
    from app.db import SessionLocal
    from app.models import NetworkReport, NetworkIdentity
    network.report("orgA", email="secret@y.com", phone="+1999", name="Josephine")
    with SessionLocal() as s:
        blob = " ".join([r.combo_hash for r in s.query(NetworkReport)]
                        + [i.id_hash + " " + i.name_hash for i in s.query(NetworkIdentity)])
    # no raw email / phone / name anywhere — only SHA-256 hashes
    assert "secret@y.com" not in blob and "+1999" not in blob and "josephine" not in blob


def test_fraud_ring_same_phone_two_names():
    network.report("orgA", phone="+1777", name="John Smith", email="a@x.com")
    network.report("orgB", phone="+1777", name="Jon Smyth", email="b@x.com")
    ring = network.ring(email=None, phone="+1777")
    assert ring["is_ring"] is True and ring["identities"] == 2


def test_verify_picks_up_network_report():
    network.report("orgA", email="f@x.com", phone="+1888", outcome="fraud_confirmed")
    network.report("orgB", email="f@x.com", phone="+1888", outcome="fraud_confirmed")
    network.report("orgC", email="f@x.com", phone="+1888", outcome="fraud_confirmed")
    res = score_candidate({"name": "F", "email": "f@x.com", "phone": "+1888"},
                          layers=["network"])
    assert any(fl["code"] == "NETWORK_FLAG_3PLUS" for fl in res["flags"])


def test_verify_flags_ring():
    network.report("orgA", phone="+1222", name="Alpha", email="a1@x.com")
    network.report("orgB", phone="+1222", name="Beta", email="a2@x.com")
    res = score_candidate({"name": "Gamma", "phone": "+1222", "email": "a3@x.com"},
                          layers=["network"])
    assert any(fl["code"] == "DUPLICATE_IDENTITY" for fl in res["flags"])


# ---- credits (corrected symmetric incentive) ----
def test_symmetric_rewards_equal():
    L = CreditLedger("symmetric")
    out = L.contribute("org", [{"outcome": "fraud_confirmed"}, {"outcome": "legitimate"}])
    assert out["credits_earned"] == 2.0  # 1.0 + 1.0, no fraud premium
    assert out["profiles_accepted"] == 2


def test_duplicates_rejected_earn_nothing():
    out = ledger.contribute("org", [{"outcome": "legitimate"}, {"duplicate": True}])
    assert out["profiles_accepted"] == 1 and out["profiles_rejected"] == 1
    assert out["credits_earned"] == 1.0


def test_plan_base_credits_and_balance():
    ledger.set_plan("org", "growth")        # 500 base credits, 1.25x multiplier
    out = ledger.contribute("org", [{"outcome": "fraud_confirmed"}])
    assert out["credits_earned"] == 1.25    # 1.0 * 1.25 multiplier
    assert ledger.balance("org")["credits_available"] == 501.25


# ---- endpoints ----
def fresh_client():
    import app.ratelimit as rl, app.main as main
    importlib.reload(rl); importlib.reload(main)
    return TestClient(main.app)


AUTH = {"Authorization": "Bearer th_sandbox_demo_key"}


def test_flags_report_lookup_endpoints():
    c = fresh_client()
    c.post("/flags/report", headers=AUTH, json={"email": "e@x.com", "phone": "+1", "outcome": "fraud_confirmed"})
    r = c.post("/flags/lookup", headers=AUTH, json={"email": "e@x.com", "phone": "+1"})
    assert r.json()["reports"] == 1 and r.json()["flagged"] is True


def test_contribute_endpoint_awards_credits():
    c = fresh_client()
    r = c.post("/contribute", headers=AUTH,
               json={"profiles": [{"email": "a@x.com", "phone": "+1", "name": "A", "outcome": "fraud_confirmed"},
                                  {"email": "b@x.com", "phone": "+2", "name": "B", "outcome": "legitimate"}]})
    assert r.json()["credits_earned"] == 2.0
    # the fraud profile is now in the network
    assert c.post("/flags/lookup", headers=AUTH, json={"email": "a@x.com", "phone": "+1"}).json()["reports"] == 1


def test_usage_includes_credits():
    c = fresh_client()
    r = c.get("/usage", headers=AUTH)
    assert "credits" in r.json() and "credits_available" in r.json()["credits"]
