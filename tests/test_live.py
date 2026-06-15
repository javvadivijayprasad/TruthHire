"""Live-mode provider tests with mocked API responses (no real network)."""
import app.providers.http as http
from app.providers.github import GitHubProvider
from app.providers.phone import PhoneProvider
from app.providers.company import CompanyProvider
from app.providers.web_presence import WebPresenceProvider


def codes(sigs): return {s.code for s in sigs}


def test_github_live(monkeypatch):
    monkeypatch.setattr(http, "get_json",
        lambda url, **kw: [{"id": "1"}] if "events" in url else {"created_at": "2024-01-01T00:00:00Z"})
    sigs = GitHubProvider(live=True).check({"github_username": "vijay", "graduation_year": 2010})
    assert "GITHUB_NEW_ACCOUNT" in codes(sigs)


def test_phone_live_prepaid(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setattr(http, "get_json",
        lambda url, **kw: {"valid": True, "line_type_intelligence": {"type": "nonFixedVoip"}})
    sigs = PhoneProvider(live=True, api_key="tok").check({"phone": "+15551234567"})
    assert "PHONE_PREPAID" in codes(sigs)


def test_company_live_post_dates(monkeypatch):
    monkeypatch.setattr(http, "get_json",
        lambda url, **kw: {"results": {"companies": [{"company": {"incorporation_date": "2018-03-01"}}]}})
    sigs = CompanyProvider(live=True).check({"jobs": [{"company": "Acme", "start": "2015", "end": "2020"}]})
    assert "COMPANY_POST_DATES" in codes(sigs)


def test_company_live_not_found(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda url, **kw: {"results": {"companies": []}})
    sigs = CompanyProvider(live=True).check({"jobs": [{"company": "Ghost", "start": "2015", "end": "2020"}]})
    assert "COMPANY_NOT_FOUND" in codes(sigs)


def test_web_live_no_presence(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda url, **kw: {"organic_results": []})
    sigs = WebPresenceProvider(live=True, api_key="k").check(
        {"name": "Jane Doe", "jobs": [{"company": "Acme"}]})
    assert "NO_WEB_PRESENCE" in codes(sigs)


def test_live_failure_abstains(monkeypatch):
    def boom(url, **kw): raise RuntimeError("network down")
    monkeypatch.setattr(http, "get_json", boom)
    # live fails -> no osint slice -> abstain (empty), never crashes
    assert GitHubProvider(live=True).check({"github_username": "x", "graduation_year": 2010}) == []


def test_live_falls_back_to_osint(monkeypatch):
    # live returns None (no identifier) but osint slice present -> still evaluated
    sigs = GitHubProvider(live=True).check(
        {"graduation_year": 2010, "osint": {"github": {"account_year": 2024, "active": False}}})
    assert "GITHUB_INACTIVE" in codes(sigs)
