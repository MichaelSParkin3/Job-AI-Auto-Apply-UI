"""Pydantic models for settings management."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, Any, Dict


class SettingsCategory(BaseModel):
    """Settings category metadata."""

    id: str = Field(..., description="Category identifier (e.g., 'llm')")
    name: str = Field(..., description="User-facing category name")
    description: str = Field(..., description="Category description")
    icon: Optional[str] = Field(None, description="Icon name (e.g., 'brain', 'settings')")


class SettingValidation(BaseModel):
    """Validation rules for a setting."""

    min: Optional[float] = None
    max: Optional[float] = None
    pattern: Optional[str] = None  # Regex pattern
    options: Optional[list[str]] = None  # Valid enum values


class SettingField(BaseModel):
    """Individual setting field."""

    key: str = Field(..., description="Environment variable name")
    label: str = Field(..., description="User-facing label")
    description: str = Field(..., description="Help text")
    type: Literal["string", "int", "float", "bool", "list", "password"] = Field(...)
    default: Any = Field(..., description="Default value")
    current: Any = Field(..., description="Current value (masked if sensitive)")
    sensitive: bool = Field(False, description="Whether to mask in responses")
    validation: Optional[SettingValidation] = None


class SettingsResponse(BaseModel):
    """Settings GET response."""

    categories: list[SettingsCategory]
    fields: Dict[str, list[SettingField]] = Field(
        ..., description="Category ID -> Fields"
    )


class SettingsUpdateRequest(BaseModel):
    """Settings PUT request."""

    updates: Dict[str, Any] = Field(..., description="Key -> Value pairs to update")


class SettingsUpdateResponse(BaseModel):
    """Settings update response."""

    success: bool
    message: str
    updated_keys: list[str]
    requires_restart: bool = False
    updated_settings: Optional[Dict[str, SettingField]] = None


class ValidationResult(BaseModel):
    """Validation result."""

    valid: bool
    errors: Dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ValidationRequest(BaseModel):
    """Validation request."""

    settings: Dict[str, Any] = Field(..., description="Settings to validate")


class CategoriesResponse(BaseModel):
    """Categories response."""

    categories: list[SettingsCategory]


class ResetRequest(BaseModel):
    """Reset request."""

    keys: Optional[list[str]] = None
    reset_all: bool = False
