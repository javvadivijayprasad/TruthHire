"""Unit tests for the Timeline Intelligence Engine (TH-007..TH-011)."""
from app.scoring import score_candidate, risk_level
from app.timeline import timeline_score


def cand(**kw):
    base = {"name": "Test", "jobs": []}
    base.update(kw)
    return base


def codes(flags):
    return {f.code for f in flags}


# --- Check 1: age vs experience ------------------------------------------
def test_age_24_claims_15_years_is_impossible():
    score, flags, _ = timeline_score(cand(age=24, total_claimed_years=15))
    assert "TIMELINE_IMPOSSIBLE" in codes(flags)
    assert score == 50


def test_age_40_claims_15_years_is_fine():
    score, flags, passed = timeline_score(cand(age=40, total_claimed_years=15))
    assert "TIMELINE_IMPOSSIBLE" not in codes(flags)
    assert "AGE_EXPERIENCE_CONSISTENT" in passed
    assert score == 0


def test_dob_is_used_when_age_absent():
    score, flags, _ = timeline_score(
        cand(date_of_birth="2002-01-01", total_claimed_years=12))
    assert "TIMELINE_IMPOSSIBLE" in codes(flags)


# --- Check 2: graduation vs first job ------------------------------------
def test_job_before_graduation():
    c = cand(graduation_year=2020, jobs=[{"start": "2017", "end": "2021"}])
    score, flags, _ = timeline_score(c)
    assert "JOB_BEFORE_GRADUATION" in codes(flags)


def test_job_same_year_as_graduation_is_allowed():
    c = cand(graduation_year=2020, jobs=[{"start": "2020-06", "end": "2023"}])
    _, flags, passed = timeline_score(c)
    assert "JOB_BEFORE_GRADUATION" not in codes(flags)
    assert "GRADUATION_CONSISTENT" in passed


# --- Check 3: overlapping employment -------------------------------------
def test_overlapping_full_time_jobs():
    c = cand(jobs=[
        {"start": "2018-01", "end": "2021-01"},
        {"start": "2019-01", "end": "2022-01"},
    ])
    _, flags, _ = timeline_score(c)
    assert "EMPLOYMENT_OVERLAP" in codes(flags)


def test_short_overlap_within_tolerance_is_ignored():
    c = cand(jobs=[
        {"start": "2018-01", "end": "2020-03"},
        {"start": "2020-02", "end": "2022-01"},  # 1 month overlap
    ])
    _, flags, passed = timeline_score(c)
    assert "EMPLOYMENT_OVERLAP" not in codes(flags)
    assert "NO_EMPLOYMENT_OVERLAP" in passed


def test_part_time_overlap_not_flagged():
    c = cand(jobs=[
        {"start": "2018-01", "end": "2021-01", "employment_type": "full_time"},
        {"start": "2019-01", "end": "2020-01", "employment_type": "part_time"},
    ])
    _, flags, _ = timeline_score(c)
    assert "EMPLOYMENT_OVERLAP" not in codes(flags)


# --- Check 4: experience inflation ---------------------------------------
def test_experience_inflation():
    c = cand(total_claimed_years=10, jobs=[
        {"start": "2019-01", "end": "2022-01"},  # 3 yrs
    ])
    _, flags, _ = timeline_score(c)
    assert "EXPERIENCE_INFLATION" in codes(flags)


# --- scoring / thresholds -------------------------------------------------
def test_score_is_capped_at_100():
    c = cand(age=20, total_claimed_years=15, graduation_year=2024,
             jobs=[
                 {"start": "2010", "end": "2020"},
                 {"start": "2011", "end": "2021"},
                 {"start": "2012", "end": "2022"},
             ])
    res = score_candidate(c)
    assert res["risk_score"] == 100
    assert res["risk_level"] == "CRITICAL"


def test_threshold_bands():
    assert risk_level(10)[0] == "LOW"
    assert risk_level(34)[0] == "MEDIUM"
    assert risk_level(60)[0] == "HIGH"
    assert risk_level(90)[0] == "CRITICAL"


def test_clean_candidate_passes():
    c = cand(age=35, total_claimed_years=10, graduation_year=2012,
             jobs=[
                 {"start": "2013-01", "end": "2017-01"},
                 {"start": "2017-02", "end": "2023-01"},
             ])
    res = score_candidate(c)
    assert res["risk_score"] == 0
    assert res["risk_level"] == "LOW"
    assert res["flags"] == []
