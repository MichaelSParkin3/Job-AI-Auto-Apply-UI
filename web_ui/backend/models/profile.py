"""Pydantic models for profile-related API responses."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    """Response model for a single profile."""

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

    profiles: List[ProfileResponse] = Field(
        ..., description="List of available profiles"
    )
    count: int = Field(..., description="Total number of profiles")
