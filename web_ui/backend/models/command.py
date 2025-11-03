"""Pydantic models for command-related API requests and responses."""

from typing import Optional

from pydantic import BaseModel, Field


class DiscoverRequest(BaseModel):
    """Request model for discover command."""

    profile_id: str = Field(..., description="Profile identifier")
    window: str = Field(default="24h", description="Time window (24h, 7d, 1w, etc.)")
    cap: int = Field(default=10, ge=1, le=100, description="Max jobs to discover")


class DiscoverResponse(BaseModel):
    """Response model for discover command."""

    success: bool = Field(..., description="Whether discover started successfully")
    items_discovered: int = Field(
        default=0, description="Number of items discovered (for background tasks)"
    )
    message: str = Field(..., description="Human-readable message")
    profile_id: str = Field(..., description="Profile used for discover")


class ApplyRequest(BaseModel):
    """Request model for apply command."""

    profile_id: str = Field(..., description="Profile identifier")
    job_id: Optional[str] = Field(None, description="Specific job ID to apply to")
    supervised: bool = Field(
        default=True, description="Whether to pause before submitting"
    )
    llm_provider: Optional[str] = Field(
        None, description="LLM provider override (openrouter, google, etc.)"
    )
    llm_model: Optional[str] = Field(None, description="LLM model override")
    use_llm_locator: bool = Field(
        default=False, description="Enable LLM-powered element finding"
    )
    debug_resume_widget: bool = Field(
        default=False, description="Emit structured snapshot on upload failure"
    )
    resume_wait_timeout_seconds: Optional[int] = Field(
        None, description="Resume upload timeout override"
    )
    review_mode: bool = Field(
        default=False,
        description="Capture artifacts only, do not submit applications",
    )


class ApplyResponse(BaseModel):
    """Response model for apply command start."""

    task_id: str = Field(..., description="Unique task ID for tracking")
    message: str = Field(..., description="Human-readable message")
    websocket_url: str = Field(
        ..., description="WebSocket URL for real-time progress"
    )
