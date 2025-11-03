"""Pydantic models for WebSocket events and streaming responses."""

from typing import Optional

from pydantic import BaseModel, Field


class ReasonDetail(BaseModel):
    """Reason for failure."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")


class ApplyStartEvent(BaseModel):
    """Event emitted when apply starts."""

    type: str = Field(default="apply.start")
    profile_id: str = Field(..., description="Profile being applied with")
    timestamp: str = Field(..., description="ISO timestamp of event")


class ItemStartEvent(BaseModel):
    """Event emitted when processing a job item."""

    type: str = Field(default="item.start")
    item_id: str = Field(..., description="Item/job ID")
    company: str = Field(..., description="Company name")
    title: str = Field(..., description="Job title")


class ItemSubmittedEvent(BaseModel):
    """Event emitted when application submitted successfully."""

    type: str = Field(default="item.submitted")
    item_id: str = Field(..., description="Item/job ID")
    confirmation_id: str = Field(..., description="Confirmation ID from form")


class ItemFailedEvent(BaseModel):
    """Event emitted when application fails."""

    type: str = Field(default="item.failed")
    item_id: str = Field(..., description="Item/job ID")
    reason: ReasonDetail = Field(..., description="Failure reason")


class ApplyEndEvent(BaseModel):
    """Event emitted when apply completes."""

    type: str = Field(default="apply.end")
    submitted: int = Field(..., description="Number successfully submitted")
    failed: int = Field(..., description="Number failed")


class ApplyErrorEvent(BaseModel):
    """Event emitted on WebSocket error."""

    type: str = Field(default="error")
    message: str = Field(..., description="Error message")
