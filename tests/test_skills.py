"""S21 AI skills-consistency scoring."""
from app import skills


def test_seniority_levels():
    assert skills.seniority_level(1) == 1 and skills.seniority_level(5) == 2
    assert skills.seniority_level(10) == 3 and skills.seniority_level(20) == 4


def test_domain_inference():
    assert skills.domain_for({"jobs": [{"title": "Data Scientist"}]}) == "data"
    assert skills.domain_for({"jobs": [{"title": "Engineering Manager"}]}) == "management"
    assert skills.domain_for({"jobs": [{"title": "Software Engineer"}]}) == "software"


def test_generate_questions_count_and_level():
    qs = skills.generate_questions("software", 4, 3)
    assert len(qs) == 3 and all(isinstance(q, str) for q in qs)


def test_deep_senior_answer_passes():
    deep = ("Designed a Redis sliding-window rate limiter handling 50000 req/s at p99 12ms, "
            "with sharding and replication and idempotency keys across AWS regions.")
    res = skills.assess({"total_claimed_years": 15}, [deep])
    assert res["flags"] == []


def test_shallow_senior_answer_flags():
    res = skills.assess({"total_claimed_years": 15}, ["I wrote code", "it worked"])
    assert any(f["code"] == "SKILLS_MISMATCH" for f in res["flags"])


def test_endpoints():
    import importlib
    import app.ratelimit as rl, app.main as main
    importlib.reload(rl); importlib.reload(main)
    from fastapi.testclient import TestClient
    c = TestClient(main.app); H = {"Authorization": "Bearer th_sandbox_demo_key"}
    q = c.post("/skills/questions", headers=H, json={"total_claimed_years": 12, "jobs": [{"title": "Engineer"}]})
    assert len(q.json()["questions"]) == 3
    a = c.post("/skills/assess", headers=H, json={"total_claimed_years": 12, "answers": ["short"]})
    assert a.json()["seniority_level"] == 3
