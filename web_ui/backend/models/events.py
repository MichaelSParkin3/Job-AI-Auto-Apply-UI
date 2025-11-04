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


class ActionPromptOption(BaseModel):
    """Option for action prompt."""

    action: str = Field(..., description="Action identifier (submit, skip, block, retry)")
    label: str = Field(..., description="Human-readable label (Submit Form, Skip Job)")
    key: Optional[str] = Field(None, description="Keyboard shortcut (Enter, S, B)")


class PromptContext(BaseModel):
    """Context information for user prompt."""

    item_id: Optional[str] = Field(None, description="Job item ID")
    screenshot_path: Optional[str] = Field(None, description="Path to screenshot artifact")
    company: Optional[str] = Field(None, description="Company name")
    title: Optional[str] = Field(None, description="Job title")


class ActionPromptEvent(BaseModel):
    """Event requesting user action via prompt."""

    type: str = Field(default="prompt.action_required")
    prompt_id: str = Field(..., description="Unique prompt ID for response matching")
    message: str = Field(..., description="Prompt message")
    options: list[ActionPromptOption] = Field(..., description="Available action options")
    context: Optional[PromptContext] = Field(None, description="Context for the prompt")
    timeout_seconds: int = Field(default=300, description="Timeout for response (seconds)")


class UserResponseMessage(BaseModel):
    """Message from client responding to prompt."""

    type: str = Field(default="user_response")
    prompt_id: str = Field(..., description="ID of the prompt being responded to")
    action: str = Field(..., description="Action chosen by user")
