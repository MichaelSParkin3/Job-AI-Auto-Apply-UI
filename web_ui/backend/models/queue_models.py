"""Pydantic models for queue and job-related API responses and requests."""

from typing import Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


# Job Details Response
class JobDetailsResponse(BaseModel):
    """Full details about a job posting."""

    location: Optional[str] = Field(None, description="Job location")
    work_model: str = Field("unknown", description="Work model (remote, hybrid, on-site)")
    employment_type: str = Field("unknown", description="Employment type (full-time, etc)")
    department: Optional[str] = Field(None, description="Department")
    posting_date: Optional[datetime] = Field(None, description="When job was posted")
    compensation: Optional[dict[str, Any]] = Field(None, description="Compensation details")
    posting_excerpt: Optional[str] = Field(None, description="Job description excerpt")
    posting_text: Optional[str] = Field(None, description="Full job description")
    tech_tags: List[str] = Field(default_factory=list, description="Technology tags")
    source_query: Optional[str] = Field(None, description="Search query that found this job")
    source_rank: Optional[int] = Field(None, description="Rank in search results")
    apply_url: Optional[str] = Field(None, description="Direct apply URL")
    closed: bool = Field(False, description="Whether job is closed")
    extracted_at: Optional[datetime] = Field(None, description="When details were extracted")


# Artifacts Response
class ArtifactsResponse(BaseModel):
    """Captured artifacts for an application attempt."""

    dom_snapshot_path: Optional[str] = Field(None, description="Path to DOM snapshot")
    screenshot_path: Optional[str] = Field(None, description="Path to screenshot")
    video_path: Optional[str] = Field(None, description="Path to video recording")
    har_path: Optional[str] = Field(None, description="Path to HAR network log")
    confirmation_text: Optional[str] = Field(None, description="Text from confirmation page")
    confirmation_id: Optional[str] = Field(None, description="Confirmation ID from job site")
    form_state_path: Optional[str] = Field(None, description="Path to form state snapshot")
    screenshot_before_path: Optional[str] = Field(None, description="Screenshot before submit")
    screenshot_after_path: Optional[str] = Field(None, description="Screenshot after submit")


# Reason Response (for failures)
class ReasonResponse(BaseModel):
    """Failure or status reason metadata."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")


# Job Item Response
class JobItemResponse(BaseModel):
    """A single job application item from the queue."""

    id: str = Field(..., description="Application item ID (ULID)")
    url: str = Field(..., description="Job posting URL")
    company: str = Field(..., description="Company name")
    title: str = Field(..., description="Job title")
    status: str = Field(..., description="Application status")
    discovered_at: datetime = Field(..., description="When job was discovered")
    last_updated_at: datetime = Field(..., description="Last status update time")
    details: Optional[JobDetailsResponse] = Field(None, description="Full job details")
    artifacts: Optional[ArtifactsResponse] = Field(None, description="Captured artifacts")
    reason: Optional[ReasonResponse] = Field(None, description="Failure reason if applicable")


# Queue Group Response
class QueueGroupResponse(BaseModel):
    """A group of jobs with the same status."""

    label: str = Field(..., description="Friendly label (e.g., 'Jobs Waiting')")
    status_values: List[str] = Field(..., description="Associated ApplicationStatus enum values")
    count: int = Field(..., description="Number of items in this group")
    items: List[JobItemResponse] = Field(
        default_factory=list, description="Job items in this group"
    )


# Full Queue Response
class QueueResponse(BaseModel):
    """Full queue view with grouped jobs."""

    profile_id: str = Field(..., description="Profile ID")
    total_count: int = Field(..., description="Total jobs across all groups")
    groups: List[QueueGroupResponse] = Field(
        default_factory=list, description="Status groups with their jobs"
    )


# Job Detail Page Response
class JobDetailPageResponse(BaseModel):
    """Complete data for a single job detail page."""

    job: JobItemResponse = Field(..., description="Job item with all details")
    profile_id: str = Field(..., description="Profile ID for context")
    answer_cache: Optional[dict[str, str]] = Field(
        None, description="Cached answers from previous application attempts"
    )
