"""Offline provider signal tests (S4, S7-S9)."""
from app.providers.base import default_registry
from app.scoring import score_candidate

R = default_registry()


def cand(**kw):
    base = {"name": "T", "jobs": [], "graduation_year": 2010}
    base.update(kw); return base


def codes(layers, osint):
    res = score_candidate(cand(osint=osint), layers=layers, registry=R)
    return {f["code"] for f in res["flags"]}, res


def test_github_inactive():
    c, _ = codes(["digital"], {"github": {"account_year": 2009, "active": False}})
    assert "GITHUB_INACTIVE" in c


def test_github_new_account():
    c, _ = codes(["digital"], {"github": {"account_year": 2024, "active": True}})
    assert "GITHUB_NEW_ACCOUNT" in c


def test_email_new_and_low_presence_are_low_weight():
    c, res = codes(["digital"], {"email": {"age_days": 5, "platforms": 1}})
    assert "EMAIL_NEWLY_CREATED" in c and "EMAIL_LOW_PRESENCE" in c
    assert res["layer_scores"]["digital"] == 20  # advisory, low


def test_phone_prepaid():
    c, _ = codes(["digital"], {"phone": {"valid": True, "prepaid": True}})
    assert "PHONE_PREPAID" in c


def test_web_no_presence():
    c, _ = codes(["digital"], {"web": {"mentions_at_employer": 0}})
    assert "NO_WEB_PRESENCE" in c


def test_company_not_found():
    c, _ = codes(["company"], {"company": {"exists": False}})
    assert "COMPANY_NOT_FOUND" in c


def test_company_post_dates():
    res = score_candidate(cand(jobs=[{"start": "2015", "end": "2020"}],
                               osint={"company": {"exists": True, "registered_year": 2018}}),
                          layers=["company"], registry=R)
    assert any(f["code"] == "COMPANY_POST_DATES" for f in res["flags"])


def test_linkedin_date_mismatch():
    c, _ = codes(["digital"], {"linkedin": {"created_year": 2024}})
    assert "LINKEDIN_DATE_MISMATCH" in c


def test_network_flags():
    c1, _ = codes(["network"], {"network": {"reports": 1}})
    c3, _ = codes(["network"], {"network": {"reports": 3}})
    assert "NETWORK_FLAG_1" in c1 and "NETWORK_FLAG_3PLUS" in c3


def test_abstain_without_data():
    res = score_candidate(cand(), layers=["digital", "company", "network"], registry=R)
    assert res["flags"] == [] and res["risk_score"] == 0


def test_layers_combine_and_cap():
    osint = {"company": {"exists": False}, "network": {"reports": 3}}
    res = score_candidate(cand(age=24, total_claimed_years=15, osint=osint),
                          layers=["timeline", "company", "network"], registry=R)
    # timeline impossible(50) + company not found(50) + network(60) -> capped 100
    assert res["risk_score"] == 100 and res["risk_level"] == "CRITICAL"
    assert res["layer_scores"]["company"] == 50 and res["layer_scores"]["network"] == 60
