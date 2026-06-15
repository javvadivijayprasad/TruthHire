"""Pydantic models for the TruthHire API.

Naming note: the public score field is `risk_score` (0-100, higher = more
suspicious), not `trust_score`. The v1.0 documentation called it `trust_score`
while treating high values as high *risk* — an inversion flagged in the
critique. This implementation uses the unambiguous name.
"""
from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr


class Job(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    # Accept "YYYY", "YYYY-MM", or "present"/"current" for end.
    start: str = Field(..., description="Start date: 'YYYY' or 'YYYY-MM'")
    end: str = Field(..., description="End date: 'YYYY', 'YYYY-MM', or 'present'")
    employment_type: Literal["full_time", "part_time", "contract"] = "full_time"


class Candidate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    github_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    date_of_birth: Optional[str] = Field(None, description="YYYY-MM-DD")
    age: Optional[int] = Field(None, ge=14, le=100)
    graduation_year: Optional[int] = Field(None, ge=1950, le=2100)
    total_claimed_years: Optional[float] = Field(
        None, ge=0, description="Total years of experience the candidate claims"
    )
    jobs: List[Job] = Field(default_factory=list)
    cv_text: Optional[str] = None
    osint: Optional[dict] = Field(default=None, description="Provider data slices for offline/advisory signals")


class Options(BaseModel):
    depth: Literal["express", "standard", "deep"] = "standard"
    layers: List[str] = Field(default_factory=lambda: ["timeline", "digital", "company", "network"])
    reference_id: Optional[str] = None
    webhook_url: Optional[str] = None
    consent: bool = False


class VerifyRequest(BaseModel):
    candidate: Candidate
    options: Options = Field(default_factory=Options)


class Flag(BaseModel):
    code: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    message: str
    weight: int
    layer: Optional[str] = None


class LayerScores(BaseModel):
    timeline: int = 0
    digital: int = 0
    company: int = 0
    network: int = 0


class VerifyResult(BaseModel):
    risk_score: int
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    recommendation: str
    flags: List[Flag]
    passed_checks: List[str]
    layer_scores: LayerScores
    adverse_action: Optional[dict] = None


class VerifyResponse(BaseModel):
    check_id: str
    reference_id: Optional[str] = None
    status: str = "complete"
    processing_ms: int
    candidate: dict
    result: VerifyResult
    verified_at: str


class ProfileContribution(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    outcome: Literal["fraud_confirmed", "legitimate", "inconclusive", "partial", "fraud_ring"] = "inconclusive"
    duplicate: bool = False


class ContributeRequest(BaseModel):
    profiles: List[ProfileContribution] = Field(default_factory=list)


class FlagReport(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    outcome: Literal["fraud_confirmed", "legitimate", "inconclusive"] = "fraud_confirmed"


class FlagLookup(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    threshold: int = 1


class BulkRequest(BaseModel):
    csv: str
    layers: Optional[List[str]] = None
    as_csv: bool = False


class SubscribeRequest(BaseModel):
    plan: Literal["free", "starter", "growth", "scale", "enterprise"] = "starter"


class KeyRequest(BaseModel):
    label: str


class SkillsQuestionsRequest(BaseModel):
    total_claimed_years: Optional[float] = None
    domain: Optional[str] = None
    jobs: List[dict] = Field(default_factory=list)
    n: int = 3


class SkillsAssessRequest(BaseModel):
    total_claimed_years: Optional[float] = None
    domain: Optional[str] = None
    jobs: List[dict] = Field(default_factory=list)
    answers: List[str] = Field(default_factory=list)


class DisputeRequest(BaseModel):
    check_id: str
    reason: str
