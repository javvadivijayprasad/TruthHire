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
    date_of_birth: Optional[str] = Field(None, description="YYYY-MM-DD")
    age: Optional[int] = Field(None, ge=14, le=100)
    graduation_year: Optional[int] = Field(None, ge=1950, le=2100)
    total_claimed_years: Optional[float] = Field(
        None, ge=0, description="Total years of experience the candidate claims"
    )
    jobs: List[Job] = Field(default_factory=list)
    cv_text: Optional[str] = None


class Options(BaseModel):
    depth: Literal["express", "standard", "deep"] = "standard"
    layers: List[str] = Field(default_factory=lambda: ["timeline"])
    reference_id: Optional[str] = None


class VerifyRequest(BaseModel):
    candidate: Candidate
    options: Options = Field(default_factory=Options)


class Flag(BaseModel):
    code: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    message: str
    weight: int


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


class VerifyResponse(BaseModel):
    check_id: str
    reference_id: Optional[str] = None
    status: str = "complete"
    processing_ms: int
    candidate: dict
    result: VerifyResult
    verified_at: str
