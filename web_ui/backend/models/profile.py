"""Pydantic models for profile-related API responses and requests."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


# Experience and nested structures
class ExperienceItem(BaseModel):
    """Work experience entry."""

    company: str = Field(..., description="Company name")
    role: str = Field(..., description="Job title")
    dates: str = Field(..., description="Employment dates (e.g., 'Jan 2020 - Present')")
    location: Optional[str] = Field(None, description="Work location")
    context: Optional[str] = Field(None, description="Context/description of role")
    highlights: List[str] = Field(default_factory=list, description="Key achievements")
    tech_stack: List[str] = Field(default_factory=list, description="Technologies used")
    metrics: dict[str, str] = Field(default_factory=dict, description="Key metrics")


# Profile responses for list view
class Profile(BaseModel):
    """Summary profile for list view."""

    id: str = Field(..., description="Profile identifier")
    name: str = Field(..., description="Profile name")
    resume_path: str = Field(..., description="Path to resume file")
    preferred_browser: Optional[str] = Field(
        None, description="Preferred browser (chrome, chromium, msedge)"
    )
    has_experience: bool = Field(
        False, description="Whether profile has experience section"
    )


class ProfileListResponse(BaseModel):
    """Response model for listing profiles."""

    profiles: List[Profile] = Field(
        default_factory=list, description="List of available profiles"
    )


# Detailed profile response for edit/create view
class ProfileDetailResponse(BaseModel):
    """Complete profile data for detail view and editing."""

    id: str = Field(..., description="Profile identifier (slug)")
    name: str = Field(..., description="Full name")
    resume_path: str = Field(..., description="Path to resume PDF")
    preferred_browser: Optional[str] = Field(
        None, description="Preferred browser (chrome, chromium, msedge)"
    )
    user_data_dir: Optional[str] = Field(
        None, description="Path to browser profile directory"
    )
    search_query: Optional[str] = Field(
        None, description="Custom search query for job discovery"
    )
    defaults: dict[str, str] = Field(
        default_factory=dict, description="Default form values"
    )
    keywords: dict[str, List[str]] = Field(
        default_factory=dict, description="Job search keywords"
    )
    experience: List[ExperienceItem] = Field(
        default_factory=list, description="Work experience"
    )
    prompts: dict[str, str] = Field(default_factory=dict, description="LLM prompts")


# Requests
class ProfileCreateRequest(ProfileDetailResponse):
    """Request to create a new profile."""

    pass


class ProfileUpdateRequest(BaseModel):
    """Request to update an existing profile."""

    name: Optional[str] = None
    resume_path: Optional[str] = None
    preferred_browser: Optional[str] = None
    user_data_dir: Optional[str] = None
    search_query: Optional[str] = None
    defaults: Optional[dict[str, str]] = None
    keywords: Optional[dict[str, List[str]]] = None
    experience: Optional[List[ExperienceItem]] = None
    prompts: Optional[dict[str, str]] = None


# Legacy response model for backward compatibility
class ProfileResponse(BaseModel):
    """Response model for a single profile (legacy)."""

    id: str = Field(..., description="Profile identifier")
    name: str = Field(..., description="Profile name")
    resume_path: str = Field(..., description="Path to resume file")
    preferred_browser: Optional[str] = Field(
        None, description="Preferred browser (chrome, chromium, msedge)"
    )
    has_experience: bool = Field(
        False, description="Whether profile has experience section"
    )


class ResumeUploadResponse(BaseModel):
    """Response from resume upload."""

    filename: str = Field(..., description="Uploaded filename")
    path: str = Field(..., description="Path to uploaded resume")
