"""Data models for application items, jobs, profiles, and artifacts."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class ApplicationStatus(str, Enum):
    """Application status enumeration."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    FAILED = "failed"
    CAPTCHA_BLOCKED = "captcha_blocked"

    @classmethod
    def normalize(cls, value: str) -> str:
        """Normalize status value to lowercase enum value.

        Maps legacy uppercase and non-standard status values to valid enum values.

        Args:
            value: Status value (may be uppercase or non-standard)

        Returns:
            Normalized lowercase enum value
        """
        if not isinstance(value, str):
            return value

        # Map to lowercase for comparison
        normalized = value.lower()

        # Map non-standard values to valid enum values
        status_mapping = {
            "submitted": cls.SUBMITTED.value,
            "failed": cls.FAILED.value,
            "pending_review": cls.SUBMITTED.value,  # Legacy value -> submitted
            "skipped": cls.FAILED.value,  # Legacy value -> failed
            "new": cls.NEW.value,
            "in_progress": cls.IN_PROGRESS.value,
            "captcha_blocked": cls.CAPTCHA_BLOCKED.value,
        }

        return status_mapping.get(normalized, value)


class JobDetails(BaseModel):
    """Extracted job details from Lever posting."""

    location: Optional[str] = Field(None, description="Job location")
    work_model: Optional[str] = Field(
        None, description="Work model (Remote, Hybrid, On-site)"
    )
    employment_type: Optional[str] = Field(
        None, description="Employment type (Full-time, Contract, etc.)"
    )
    department: Optional[str] = Field(None, description="Department")
    compensation: Optional[str] = Field(None, description="Compensation range")
    posting_text: Optional[str] = Field(None, description="Full posting text")
    tech_tags: Optional[List[str]] = Field(None, description="Technologies/skills")
    apply_url: Optional[str] = Field(None, description="Direct apply URL")
    posting_date: Optional[str] = Field(None, description="Date posted")

    class Config:
        extra = "allow"  # Allow additional fields from Lever


class Artifacts(BaseModel):
    """Captured artifacts from application process."""

    screenshot_path: Optional[str] = Field(None, description="Path to screenshot")
    dom_snapshot_path: Optional[str] = Field(
        None, description="Path to DOM snapshot"
    )
    video_path: Optional[str] = Field(None, description="Path to video recording")
    har_path: Optional[str] = Field(None, description="Path to HAR file")
    confirmation_text: Optional[str] = Field(
        None, description="Success page text"
    )
    confirmation_id: Optional[str] = Field(None, description="Confirmation ID")
    paths: Optional[List[str]] = Field(None, description="All artifact file paths")
    capture_timestamp: Optional[str] = Field(
        None, description="When artifacts were captured"
    )


class FailureReason(BaseModel):
    """Reason for application failure."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")


class ApplicationItem(BaseModel):
    """Application queue item."""

    id: str = Field(..., description="ULID application ID")
    url: str = Field(..., description="Lever job posting URL")
    company: str = Field(..., description="Company name")
    title: str = Field(..., description="Job title")
    status: ApplicationStatus = Field(
        default=ApplicationStatus.NEW, description="Current status"
    )
    details: Optional[JobDetails] = Field(
        None, description="Extracted job details"
    )
    artifacts: Optional[Artifacts] = Field(
        None, description="Captured artifacts"
    )
    reason: Optional[FailureReason] = Field(
        None, description="Failure reason if FAILED"
    )
    date_discovered: Optional[str] = Field(
        None, description="When job was discovered"
    )
    date_applied: Optional[str] = Field(None, description="When applied")
    source_query: Optional[str] = Field(None, description="Search query used")
    source_rank: Optional[int] = Field(None, description="Rank in search results")
    hash: Optional[str] = Field(
        None,
        description="SHA256 hash of url|company|title for deduplication",
    )


class ProfileDefaults(BaseModel):
    """Default values for profile."""

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None


class ProfileKeywords(BaseModel):
    """Keywords and preferences for profile."""

    roles: Optional[List[str]] = Field(None, description="Target roles")
    tech_stack: Optional[List[str]] = Field(None, description="Technologies")


class ProfileExperience(BaseModel):
    """Work experience entry."""

    company: str
    role: str
    dates: str
    highlights: List[str]
    tech_stack: Optional[List[str]] = None
    metrics: Optional[Dict[str, str]] = None


class ProfilePrompts(BaseModel):
    """Custom prompts for LLM."""

    cover_letter: Optional[str] = None
    resume_summary: Optional[str] = None
    key_accomplishments: Optional[str] = None
    experience_selection: Optional[str] = None


class Profile(BaseModel):
    """User profile for application automation."""

    id: str = Field(..., description="Profile ID")
    name: str = Field(..., description="Full name")
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    resume_path: str = Field(..., description="Path to resume PDF")
    preferred_browser: Optional[str] = Field(None, description="chrome, chromium, msedge")
    user_data_dir: Optional[str] = Field(None, description="Browser profile directory")
    defaults: Optional[ProfileDefaults] = None
    keywords: Optional[ProfileKeywords] = None
    experience: Optional[List[ProfileExperience]] = None
    prompts: Optional[ProfilePrompts] = None

    class Config:
        extra = "allow"
