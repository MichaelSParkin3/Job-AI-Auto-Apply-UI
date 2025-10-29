"""Configuration and settings models."""

from typing import Optional, List, Any, Dict
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class OperationType(str, Enum):
    """Operation type enumeration."""

    DISCOVER = "discover"
    APPLY_SINGLE = "apply_single"
    APPLY_BULK = "apply_bulk"


class ApplyMode(str, Enum):
    """Apply mode enumeration."""

    SUPERVISED = "supervised"
    AUTOMATED = "automated"


class RunConfiguration(BaseModel):
    """Runtime configuration for discovery and apply operations."""

    profile_id: str = Field(..., description="Active profile ID")
    operation_type: OperationType = Field(..., description="discover, apply_single, apply_bulk")

    # Discovery options
    search_window: Optional[str] = Field(None, description="Time window for discovery (e.g., 24h)")
    job_cap: Optional[int] = Field(None, description="Maximum jobs to discover")
    custom_query: Optional[str] = Field(None, description="Custom search query override")

    # Apply options
    mode: Optional[ApplyMode] = Field(None, description="supervised or automated")
    review_mode: Optional[bool] = Field(None, description="Review form before submit")

    # LLM overrides
    llm_provider_override: Optional[str] = Field(None, description="openrouter, google, etc.")
    llm_model_override: Optional[str] = Field(None, description="Model identifier override")

    # Diagnostics
    use_llm_locator: Optional[bool] = Field(None, description="LLM-assisted element finding")
    debug_resume_widget: Optional[bool] = Field(None, description="Debug resume upload")
    resume_wait_timeout: Optional[int] = Field(None, description="Resume upload timeout seconds")

    # Post-apply
    audit_after_submit: Optional[bool] = Field(None, description="Audit page after submit")
    save_logs: Optional[bool] = Field(None, description="Save execution logs")
    logs_dir: Optional[str] = Field(None, description="Directory to save logs")

    # Bulk apply
    max_concurrent: Optional[int] = Field(None, description="Max concurrent applications")
    stop_on_failure: Optional[bool] = Field(None, description="Stop on first failure")

    # Metadata
    last_updated: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="When config was last updated"
    )


class SettingInputType(str, Enum):
    """Setting input type for UI rendering."""

    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    TEXTAREA = "textarea"


class SettingCategory(str, Enum):
    """Setting category for grouping."""

    SERVER = "server"
    DISCOVERY = "discovery"
    APPLICATION = "application"
    LLM = "llm"
    DIAGNOSTICS = "diagnostics"
    PERFORMANCE = "performance"


class Setting(BaseModel):
    """Environment setting with metadata."""

    key: str = Field(..., description="Environment variable name")
    value: Optional[str] = Field(None, description="Current value")
    description: str = Field(..., description="Human-readable description")
    category: SettingCategory = Field(..., description="Setting category")
    input_type: SettingInputType = Field(..., description="UI input type")
    default_value: Optional[str] = Field(None, description="Default value")
    options: Optional[List[str]] = Field(None, description="Available options for select")
    min: Optional[int] = Field(None, description="Minimum value for numbers")
    max: Optional[int] = Field(None, description="Maximum value for numbers")
    is_secret: bool = Field(False, description="Hide value in responses")
    required: bool = Field(False, description="Is required")

    def to_api_response(self) -> "Setting":
        """Return safe value for API (mask secrets)."""
        if self.is_secret and self.value:
            return self.model_copy(update={"value": "***REDACTED***"})
        return self


# Built-in settings catalog
SETTINGS_CATALOG: Dict[str, Setting] = {
    "BACKEND_HOST": Setting(
        key="BACKEND_HOST",
        description="Backend server host",
        category=SettingCategory.SERVER,
        input_type=SettingInputType.TEXT,
        default_value="127.0.0.1",
    ),
    "BACKEND_PORT": Setting(
        key="BACKEND_PORT",
        description="Backend server port",
        category=SettingCategory.SERVER,
        input_type=SettingInputType.NUMBER,
        default_value="5000",
    ),
    "DISCOVERY_WINDOW_HOURS": Setting(
        key="DISCOVERY_WINDOW_HOURS",
        description="Hours to look back for job postings",
        category=SettingCategory.DISCOVERY,
        input_type=SettingInputType.NUMBER,
        default_value="24",
        min=1,
        max=365,
    ),
    "DISCOVERY_CAP": Setting(
        key="DISCOVERY_CAP",
        description="Maximum jobs to discover per run",
        category=SettingCategory.DISCOVERY,
        input_type=SettingInputType.NUMBER,
        default_value="10",
        min=1,
        max=500,
    ),
    "DWELL_SECONDS": Setting(
        key="DWELL_SECONDS",
        description="Delay between actions",
        category=SettingCategory.APPLICATION,
        input_type=SettingInputType.NUMBER,
        default_value="0.8",
    ),
    "MAX_TABS": Setting(
        key="MAX_TABS",
        description="Maximum concurrent browser tabs",
        category=SettingCategory.APPLICATION,
        input_type=SettingInputType.NUMBER,
        default_value="3",
        min=1,
        max=10,
    ),
    "LLM_PROVIDER": Setting(
        key="LLM_PROVIDER",
        description="LLM provider",
        category=SettingCategory.LLM,
        input_type=SettingInputType.SELECT,
        default_value="openrouter",
        options=["openrouter", "google"],
    ),
    "LLM_MODEL": Setting(
        key="LLM_MODEL",
        description="LLM model identifier",
        category=SettingCategory.LLM,
        input_type=SettingInputType.TEXT,
        default_value="anthropic/claude-opus-4",
    ),
    "OPENROUTER_API_KEY": Setting(
        key="OPENROUTER_API_KEY",
        description="OpenRouter API key",
        category=SettingCategory.LLM,
        input_type=SettingInputType.TEXT,
        is_secret=True,
    ),
    "GOOGLE_API_KEY": Setting(
        key="GOOGLE_API_KEY",
        description="Google API key",
        category=SettingCategory.LLM,
        input_type=SettingInputType.TEXT,
        is_secret=True,
    ),
    "AUTO_APPLY_DIAGNOSTICS": Setting(
        key="AUTO_APPLY_DIAGNOSTICS",
        description="Enable all diagnostics",
        category=SettingCategory.DIAGNOSTICS,
        input_type=SettingInputType.BOOLEAN,
        default_value="false",
    ),
    "AUTO_APPLY_USE_LLM_LOCATOR": Setting(
        key="AUTO_APPLY_USE_LLM_LOCATOR",
        description="Use LLM for element finding",
        category=SettingCategory.DIAGNOSTICS,
        input_type=SettingInputType.BOOLEAN,
        default_value="false",
    ),
    "LOG_LEVEL": Setting(
        key="LOG_LEVEL",
        description="Logging level",
        category=SettingCategory.PERFORMANCE,
        input_type=SettingInputType.SELECT,
        default_value="INFO",
        options=["DEBUG", "INFO", "WARNING", "ERROR"],
    ),
}
