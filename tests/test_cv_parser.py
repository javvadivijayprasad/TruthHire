"""Unit tests for the CV parser (TH-002)."""
from app.cv_parser import parse_cv

SAMPLE = """John Smith
john.smith@gmail.com  |  +1-555-0123

Education
B.S. Computer Science, State University, 2018

Experience
Acme Corp — Senior Engineer    Jan 2018 - Mar 2021
Globex Inc — Staff Engineer    Apr 2021 - Present
"""


def test_extracts_contact():
    p = parse_cv(SAMPLE)
    assert p["email"] == "john.smith@gmail.com"
    assert p["phone"] is not None
    assert p["name"] == "John Smith"


def test_extracts_graduation_year():
    assert parse_cv(SAMPLE)["graduation_year"] == 2018


def test_extracts_job_date_ranges():
    jobs = parse_cv(SAMPLE)["jobs"]
    assert len(jobs) == 2
    assert jobs[0]["start"] == "2018-01"
    assert jobs[0]["end"] == "2021-03"
    assert jobs[1]["end"] == "present"


def test_empty_text_is_safe():
    p = parse_cv("")
    assert p["jobs"] == []
    assert p["email"] is None


def test_parsed_cv_feeds_timeline_for_impossible_claim():
    from app.cv_parser import parse_cv
    from app.schemas import Candidate, Job
    from app.scoring import score_candidate
    text = ("Jane Doe\njane@x.com\nB.S. 2022\n"
            "BigCo Engineer 2010 - 2020\n")
    parsed = parse_cv(text)
    c = Candidate(name="Jane Doe", graduation_year=parsed["graduation_year"],
                  jobs=[Job(**j) for j in parsed["jobs"]])
    res = score_candidate(c)
    assert res["risk_score"] >= 40  # job starts long before graduation
