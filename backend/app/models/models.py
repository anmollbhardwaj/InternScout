import uuid
from datetime import datetime, date
from typing import List, Optional, Any, Dict
from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Boolean,
    Text,
    Date,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Academic & Eligibility profile
    degree: Mapped[str] = mapped_column(String(150), nullable=False)
    graduation_year: Mapped[int] = mapped_column(Integer, nullable=False)
    cgpa: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)

    # Job Preferences
    target_roles: Mapped[List[str]] = mapped_column(JSONB, default=list)
    primary_skills: Mapped[List[str]] = mapped_column(JSONB, default=list)
    preferred_locations: Mapped[List[str]] = mapped_column(JSONB, default=list)
    allow_remote: Mapped[bool] = mapped_column(Boolean, default=True)
    min_stipend_inr: Mapped[int] = mapped_column(Integer, default=0)
    min_duration_months: Mapped[int] = mapped_column(Integer, default=1)
    max_duration_months: Mapped[int] = mapped_column(Integer, default=6)

    # Base Resume Ground Truth
    base_resume_text: Mapped[str] = mapped_column(Text, nullable=False)
    base_resume_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    resume_versions = relationship("ResumeVersion", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")


class Internship(Base):
    __tablename__ = "internships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    internshala_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    locations: Mapped[List[str]] = mapped_column(JSONB, default=list)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    
    stipend_raw: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    stipend_min_inr: Mapped[int] = mapped_column(Integer, default=0)
    stipend_max_inr: Mapped[int] = mapped_column(Integer, default=0)
    duration_months: Mapped[int] = mapped_column(Integer, default=1)
    
    posted_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    apply_by: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    about_internship: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills_required: Mapped[List[str]] = mapped_column(JSONB, default=list)
    who_can_apply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    perks: Mapped[List[str]] = mapped_column(JSONB, default=list)
    number_of_openings: Mapped[int] = mapped_column(Integer, default=1)

    # Processing & AI evaluation
    status: Mapped[str] = mapped_column(
        String(50), 
        default="DISCOVERED", 
        index=True
    )  # DISCOVERED, EVALUATING, MATCHED, DISQUALIFIED, APPLIED, SKIPPED
    match_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    eligibility_verdict: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    missing_skills: Mapped[List[str]] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    resume_versions = relationship("ResumeVersion", back_populates="internship", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="internship", cascade="all, delete-orphan")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    internship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)

    tailored_headline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tailored_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bullet_diffs: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    skills_highlighted: Mapped[List[str]] = mapped_column(JSONB, default=list)
    cover_letter_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_qa_answers: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict)
    pdf_storage_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), 
        default="PENDING_APPROVAL"
    )  # PENDING_APPROVAL, APPROVED, MODIFIED, REJECTED

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="resume_versions")
    internship = relationship("Internship", back_populates="resume_versions")
    application = relationship("Application", back_populates="resume_version", uselist=False)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    internship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), index=True)
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), 
        default="QUEUED", 
        index=True
    )  # QUEUED, IN_PROGRESS, SUBMITTED, FAILED, MANUAL_INTERVENTION_REQUIRED

    submitted_answers: Mapped[Dict[str, str]] = mapped_column(JSONB, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submission_screenshot_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="applications")
    internship = relationship("Internship", back_populates="applications")
    resume_version = relationship("ResumeVersion", back_populates="application")


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)  # HOURLY_DELTA, DAILY_DEEP_SYNC, MANUAL
    items_scraped: Mapped[int] = mapped_column(Integer, default=0)
    new_items_saved: Mapped[int] = mapped_column(Integer, default=0)
    high_matches_found: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED")
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
