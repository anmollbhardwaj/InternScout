import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, EmailStr


# ==========================================
# Profile & Ground Truth Schemas
# ==========================================
class UserProfileBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    degree: str
    graduation_year: int
    cgpa: float = Field(ge=0.0, le=10.0)
    target_roles: List[str] = Field(default_factory=list)
    primary_skills: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    allow_remote: bool = True
    min_stipend_inr: int = 0
    min_duration_months: int = 1
    max_duration_months: int = 6
    base_resume_text: str
    base_resume_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# Internship Schemas
# ==========================================
class InternshipBase(BaseModel):
    internshala_id: str
    title: str
    company_name: str
    locations: List[str] = Field(default_factory=list)
    is_remote: bool = False
    stipend_raw: Optional[str] = None
    stipend_min_inr: int = 0
    stipend_max_inr: int = 0
    duration_months: int = 1
    posted_date: Optional[date] = None
    apply_by: Optional[date] = None
    url: str
    about_internship: Optional[str] = None
    skills_required: List[str] = Field(default_factory=list)
    who_can_apply: Optional[str] = None
    perks: List[str] = Field(default_factory=list)
    number_of_openings: int = 1


class InternshipResponse(InternshipBase):
    id: uuid.UUID
    status: str
    match_score: int
    eligibility_verdict: Dict[str, Any] = Field(default_factory=dict)
    missing_skills: List[str] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# LLM Pydantic Models (Structured Output)
# ==========================================
class HardCriteriaCheck(BaseModel):
    passed: bool
    criterion_name: str  # e.g., "Graduation Year", "Duration", "Location"
    user_value: str
    job_requirement: str
    reason: str


class EligibilityEvaluation(BaseModel):
    is_eligible: bool = Field(description="True if all non-negotiable hard criteria pass")
    match_score: int = Field(ge=0, le=100, description="Semantic fit score from 0 to 100")
    hard_criteria_checks: List[HardCriteriaCheck] = Field(default_factory=list)
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    summary_verdict: str = Field(description="Brief explanation of the score and eligibility")


class BulletDiff(BaseModel):
    section: str = Field(description="Experience, Project, or Skills section")
    original_bullet: str = Field(description="Existing bullet point in base resume")
    suggested_bullet: str = Field(description="Action-verb keyword-aligned tailored bullet")
    change_type: Literal["REPLACE", "ADD", "EMPHASIZE"] = "REPLACE"
    reason: str = Field(description="Why this change increases JD alignment")


class ResumeTailoringResult(BaseModel):
    target_job_title: str
    tailored_headline: str
    tailored_summary: str
    bullet_diffs: List[BulletDiff] = Field(default_factory=list)
    skills_to_highlight: List[str] = Field(default_factory=list)
    cover_letter: str = Field(description="Why should you be hired for this role answer grounded in profile")
    assessment_answers: Dict[str, str] = Field(
        default_factory=dict, 
        description="Grounded answers to standard Internshala screening questions"
    )


# ==========================================
# Real-Time WebSocket Event Payloads
# ==========================================
class WSMatchAlertPayload(BaseModel):
    internship: InternshipResponse
    resume_version_id: uuid.UUID
    match_score: int
    summary_verdict: str
    missing_skills: List[str]
    tailored_headline: str
    tailored_summary: str
    bullet_diffs: List[BulletDiff]
    cover_letter: str
    assessment_answers: Dict[str, str]


class ApplicationApprovalRequest(BaseModel):
    resume_version_id: uuid.UUID
    modified_bullet_diffs: Optional[List[BulletDiff]] = None
    modified_cover_letter: Optional[str] = None
    modified_assessment_answers: Optional[Dict[str, str]] = None
    auto_apply_now: bool = True
