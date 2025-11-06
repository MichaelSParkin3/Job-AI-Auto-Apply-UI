"""Routes for settings management."""

import os
import re
import httpx
import structlog
from pathlib import Path
from typing import Dict, Any, Tuple

from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv, set_key, unset_key

from ..models.settings import (
    SettingsResponse,
    SettingsCategory,
    SettingField,
    SettingValidation,
    SettingsUpdateRequest,
    SettingsUpdateResponse,
    ValidationResult,
    ValidationRequest,
    CategoriesResponse,
    ResetRequest,
)
from job_ai_auto_apply_ui.config import Settings, load_settings

router = APIRouter()
logger = structlog.get_logger()

# Settings categories
CATEGORIES = [
    SettingsCategory(
        id="llm",
        name="LLM & AI Configuration",
        description="API keys, model selection, and LLM behavior",
        icon="🧠",
    ),
    SettingsCategory(
        id="browser",
        name="Browser & Automation",
        description="Browser settings, stealth, and automation behavior",
        icon="🌐",
    ),
    SettingsCategory(
        id="general",
        name="General Behavior",
        description="Discovery, timing, and retry settings",
        icon="⚙️",
    ),
    SettingsCategory(
        id="network",
        name="Network & Proxy",
        description="Proxy, domains, and networking settings",
        icon="🔗",
    ),
    SettingsCategory(
        id="diagnostics",
        name="Diagnostics & Artifacts",
        description="Capture and debugging settings",
        icon="📊",
    ),
    SettingsCategory(
        id="advanced",
        name="Advanced (Resume & CAPTCHA)",
        description="Advanced resume upload and CAPTCHA detection",
        icon="🔧",
    ),
]

# Setting field definitions
SETTINGS_DEFINITIONS = {
    "llm": [
        SettingField(
            key="LLM_PROVIDER",
            label="LLM Provider",
            description="Choose between OpenRouter and Google (Gemini)",
            type="string",
            default="",
            current="",
            sensitive=False,
            validation=SettingValidation(options=["openrouter", "google"]),
        ),
        SettingField(
            key="LLM_MODEL",
            label="LLM Model",
            description="Model identifier for selected provider",
            type="string",
            default="",
            current="",
            sensitive=False,
        ),
        SettingField(
            key="OPENROUTER_API_KEY",
            label="OpenRouter API Key",
            description="API key for OpenRouter (keep secret)",
            type="password",
            default="",
            current="",
            sensitive=True,
        ),
        SettingField(
            key="GOOGLE_API_KEY",
            label="Google API Key",
            description="API key for Google (Gemini)",
            type="password",
            default="",
            current="",
            sensitive=True,
        ),
        SettingField(
            key="LLM_TEMPERATURE",
            label="Temperature",
            description="Controls randomness (0.0 = deterministic, 2.0 = creative)",
            type="float",
            default=0.0,
            current=0.0,
            sensitive=False,
            validation=SettingValidation(min=0.0, max=2.0),
        ),
        SettingField(
            key="LLM_TIMEOUT_SECONDS",
            label="Request Timeout",
            description="Timeout for LLM requests in seconds",
            type="int",
            default=30,
            current=30,
            sensitive=False,
            validation=SettingValidation(min=5, max=300),
        ),
        SettingField(
            key="LLM_REFERER",
            label="Referer Header",
            description="Optional referer header for branding",
            type="string",
            default="",
            current="",
            sensitive=False,
        ),
        SettingField(
            key="LLM_USER_AGENT",
            label="User Agent",
            description="Optional user agent override for branding",
            type="string",
            default="",
            current="",
            sensitive=False,
        ),
    ],
    "browser": [
        SettingField(
            key="BROWSER_LOCALE",
            label="Browser Locale",
            description="Browser locale (e.g., en-US, fr-FR)",
            type="string",
            default="en-US",
            current="en-US",
            sensitive=False,
        ),
        SettingField(
            key="BROWSER_TIMEZONE",
            label="Browser Timezone",
            description="Browser timezone (IANA format)",
            type="string",
            default="America/Los_Angeles",
            current="America/Los_Angeles",
            sensitive=False,
        ),
        SettingField(
            key="BROWSER_VIEWPORT_WIDTH",
            label="Viewport Width",
            description="Browser viewport width in pixels",
            type="int",
            default=1280,
            current=1280,
            sensitive=False,
            validation=SettingValidation(min=320, max=3840),
        ),
        SettingField(
            key="BROWSER_VIEWPORT_HEIGHT",
            label="Viewport Height",
            description="Browser viewport height in pixels",
            type="int",
            default=800,
            current=800,
            sensitive=False,
            validation=SettingValidation(min=240, max=2160),
        ),
        SettingField(
            key="AUTO_APPLY_DISABLE_DEFAULT_EXTENSIONS",
            label="Disable Extensions",
            description="Disable browser extensions (1 = disabled, 0 = enabled)",
            type="bool",
            default=True,
            current=True,
            sensitive=False,
        ),
        SettingField(
            key="AUTO_APPLY_CHROME_ARGS",
            label="Chrome Arguments",
            description="Semicolon-separated Chrome command line arguments",
            type="list",
            default="--disable-autofill;--disable-autofill-keyboard-accessory-view;--disable-features=Autofill,AutofillServerCommunication",
            current="--disable-autofill;--disable-autofill-keyboard-accessory-view;--disable-features=Autofill,AutofillServerCommunication",
            sensitive=False,
        ),
    ],
    "general": [
        SettingField(
            key="DWELL_SECONDS",
            label="Dwell Time",
            description="Delay between actions in seconds",
            type="float",
            default=0.8,
            current=0.8,
            sensitive=False,
            validation=SettingValidation(min=0.1, max=5.0),
        ),
        SettingField(
            key="JITTER_SECONDS",
            label="Jitter",
            description="Random variance in delays",
            type="float",
            default=0.4,
            current=0.4,
            sensitive=False,
            validation=SettingValidation(min=0.0, max=2.0),
        ),
        SettingField(
            key="MAX_TABS",
            label="Max Concurrent Tabs",
            description="Maximum concurrent browser tabs",
            type="int",
            default=3,
            current=3,
            sensitive=False,
            validation=SettingValidation(min=1, max=10),
        ),
        SettingField(
            key="RETRIES",
            label="Retry Attempts",
            description="Retry attempts for failed operations",
            type="int",
            default=2,
            current=2,
            sensitive=False,
            validation=SettingValidation(min=0, max=5),
        ),
        SettingField(
            key="DISCOVERY_WINDOW_HOURS",
            label="Discovery Window",
            description="Default discovery time window in hours",
            type="int",
            default=24,
            current=24,
            sensitive=False,
            validation=SettingValidation(min=1, max=8760),
        ),
        SettingField(
            key="DISCOVERY_CAP",
            label="Discovery Cap",
            description="Default maximum jobs to discover",
            type="int",
            default=10,
            current=10,
            sensitive=False,
            validation=SettingValidation(min=1, max=100),
        ),
        SettingField(
            key="AUTO_APPLY_PROFILES_DIR",
            label="Profiles Directory",
            description="Directory path for job profiles",
            type="string",
            default="profiles",
            current="profiles",
            sensitive=False,
        ),
    ],
    "network": [
        SettingField(
            key="PROXY_URL",
            label="Proxy URL",
            description="Full proxy URL with credentials: http://user:pass@host:port",
            type="password",
            default="",
            current="",
            sensitive=True,
        ),
        SettingField(
            key="HTTP_PROXY",
            label="HTTP Proxy",
            description="HTTP proxy for requests",
            type="password",
            default="",
            current="",
            sensitive=True,
        ),
        SettingField(
            key="HTTPS_PROXY",
            label="HTTPS Proxy",
            description="HTTPS proxy for secure requests",
            type="password",
            default="",
            current="",
            sensitive=True,
        ),
        SettingField(
            key="USER_AGENT",
            label="Custom User-Agent",
            description="Custom User-Agent header override",
            type="string",
            default="",
            current="",
            sensitive=False,
        ),
        SettingField(
            key="ALLOWED_DOMAINS",
            label="Allowed Domains",
            description="Comma-separated domains allowed (supports wildcards)",
            type="list",
            default="google.*,jobs.lever.co",
            current="google.*,jobs.lever.co",
            sensitive=False,
        ),
    ],
    "diagnostics": [
        SettingField(
            key="AUTO_APPLY_DIAGNOSTICS",
            label="Enable Diagnostics",
            description="Enable ALL diagnostic captures (master switch)",
            type="bool",
            default=False,
            current=False,
            sensitive=False,
        ),
        SettingField(
            key="AUTO_APPLY_CAPTURE_VIDEO",
            label="Record Video",
            description="Record browser session video",
            type="bool",
            default=False,
            current=False,
            sensitive=False,
        ),
        SettingField(
            key="AUTO_APPLY_CAPTURE_HAR",
            label="Record Network (HAR)",
            description="Record network traffic in HAR format",
            type="bool",
            default=False,
            current=False,
            sensitive=False,
        ),
        SettingField(
            key="AUTO_APPLY_ARTIFACTS_DIR",
            label="Artifacts Directory",
            description="Directory to store diagnostic artifacts",
            type="string",
            default="data/artifacts",
            current="data/artifacts",
            sensitive=False,
        ),
    ],
    "advanced": [
        SettingField(
            key="AUTO_APPLY_USE_LLM_LOCATOR",
            label="LLM Resume Locator",
            description="Enable LLM-powered resume input field detection",
            type="bool",
            default=False,
            current=False,
            sensitive=False,
        ),
        SettingField(
            key="AUTO_APPLY_DEBUG_RESUME_WIDGET",
            label="Debug Resume Upload",
            description="Emit DOM snapshot on resume upload failure",
            type="bool",
            default=False,
            current=False,
            sensitive=False,
        ),
        SettingField(
            key="AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS",
            label="Resume Upload Timeout",
            description="Maximum wait time for resume upload completion",
            type="int",
            default=25,
            current=25,
            sensitive=False,
            validation=SettingValidation(min=5, max=120),
        ),
        SettingField(
            key="AUTO_APPLY_CAPTCHA_VISUAL_CHECK",
            label="Visual CAPTCHA Detection",
            description="Enable vision-based CAPTCHA detection",
            type="bool",
            default=False,
            current=False,
            sensitive=False,
        ),
        SettingField(
            key="AUTO_APPLY_CAPTCHA_VISION_MODEL",
            label="Vision Model",
            description="Vision model for CAPTCHA analysis",
            type="string",
            default="google/gemini-2.0-flash-exp:free",
            current="google/gemini-2.0-flash-exp:free",
            sensitive=False,
        ),
        SettingField(
            key="CAPTCHA_VISUAL_DELAY_SECONDS",
            label="CAPTCHA Detection Delay",
            description="Wait before taking screenshot for analysis",
            type="float",
            default=3.0,
            current=3.0,
            sensitive=False,
            validation=SettingValidation(min=1.0, max=10.0),
        ),
        SettingField(
            key="AUTO_APPLY_CAPTCHA_TIMEOUT_SECONDS",
            label="Manual CAPTCHA Timeout",
            description="Timeout for manual CAPTCHA solving",
            type="int",
            default=60,
            current=60,
            sensitive=False,
            validation=SettingValidation(min=10, max=300),
        ),
    ],
}


def get_env_path() -> Path:
    """Get path to .env file."""
    return Path(__file__).parent.parent.parent.parent / ".env"


def mask_sensitive(key: str, value: str) -> str:
    """Mask sensitive values for API responses."""
    if not value:
        return ""

    sensitive_keys = ["API_KEY", "SECRET", "PASSWORD", "TOKEN", "PROXY"]

    if any(s in key.upper() for s in sensitive_keys):
        # Show last 4 characters
        if len(value) > 4:
            return f"••••{value[-4:]}"
        return "••••••••"

    return value


def read_current_settings() -> Dict[str, Any]:
    """Read current settings from environment."""
    settings = {}
    for category_fields in SETTINGS_DEFINITIONS.values():
        for field in category_fields:
            env_value = os.getenv(field.key, field.default)
            settings[field.key] = env_value

    return settings


def validate_settings(updates: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate settings before persisting.
    Returns dict of key -> error message.
    """
    errors = {}

    # Find all field definitions
    all_fields = {}
    for category_fields in SETTINGS_DEFINITIONS.values():
        for field in category_fields:
            all_fields[field.key] = field

    for key, value in updates.items():
        if key not in all_fields:
            errors[key] = "Unknown setting"
            continue

        field = all_fields[key]

        # Type validation
        if field.type == "int":
            try:
                int_val = int(value)
                if field.validation and field.validation.min is not None:
                    if int_val < field.validation.min:
                        errors[key] = f"Must be at least {field.validation.min}"
                if field.validation and field.validation.max is not None:
                    if int_val > field.validation.max:
                        errors[key] = f"Must be at most {field.validation.max}"
            except (ValueError, TypeError):
                errors[key] = "Must be a valid integer"

        elif field.type == "float":
            try:
                float_val = float(value)
                if field.validation and field.validation.min is not None:
                    if float_val < field.validation.min:
                        errors[key] = f"Must be at least {field.validation.min}"
                if field.validation and field.validation.max is not None:
                    if float_val > field.validation.max:
                        errors[key] = f"Must be at most {field.validation.max}"
            except (ValueError, TypeError):
                errors[key] = "Must be a valid number"

        elif field.type == "string":
            if field.validation and field.validation.options:
                if value not in field.validation.options:
                    errors[key] = (
                        f"Must be one of: {', '.join(field.validation.options)}"
                    )
            if field.validation and field.validation.pattern:
                if not re.match(field.validation.pattern, str(value)):
                    errors[key] = "Invalid format"

        elif field.type == "bool":
            # Bool values should be 0/1 or true/false
            if value not in [True, False, 0, 1, "0", "1", "true", "false"]:
                errors[key] = "Must be true or false"

        # Path validation for directories
        if key in ["AUTO_APPLY_PROFILES_DIR", "AUTO_APPLY_ARTIFACTS_DIR"]:
            try:
                path = Path(value)
                # Try to create if doesn't exist
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors[key] = f"Invalid path: {str(e)}"

    return errors


async def test_api_key(provider: str, api_key: str) -> Tuple[bool, str]:
    """
    Test if API key is valid by making a simple API call.
    Returns (is_valid, error_message).
    """
    if not api_key:
        return False, "API key is empty"

    if provider == "openrouter":
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10,
                )
                if response.status_code == 200:
                    return True, ""
                else:
                    return False, f"API returned status {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    elif provider == "google":
        try:
            # For Google, we'll do a simple validation by checking key format
            # Full validation would require making an actual API call
            if len(api_key) > 10:
                return True, ""
            else:
                return False, "API key too short"
        except Exception as e:
            return False, str(e)

    return False, "Unknown provider"


def to_env_value(key: str, value: Any) -> str:
    """Convert Python value to .env file format (all strings)."""
    if isinstance(value, bool):
        # Boolean to 0/1
        return "1" if value else "0"

    if isinstance(value, list):
        # List to comma or semicolon separated
        if key == "AUTO_APPLY_CHROME_ARGS":
            return ";".join(str(v) for v in value)
        else:
            return ",".join(str(v) for v in value)

    if isinstance(value, (int, float)):
        return str(value)

    return str(value)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """
    Get all settings grouped by category with current values.
    Sensitive values are masked.
    """
    try:
        current_settings = read_current_settings()

        # Build response with current values
        fields_by_category = {}
        for category_id, category_fields in SETTINGS_DEFINITIONS.items():
            fields_by_category[category_id] = []
            for field_def in category_fields:
                current_value = current_settings.get(
                    field_def.key, field_def.default
                )
                # Mask sensitive values
                if field_def.sensitive:
                    current_value = mask_sensitive(field_def.key, str(current_value))

                field = SettingField(
                    key=field_def.key,
                    label=field_def.label,
                    description=field_def.description,
                    type=field_def.type,
                    default=field_def.default,
                    current=current_value,
                    sensitive=field_def.sensitive,
                    validation=field_def.validation,
                )
                fields_by_category[category_id].append(field)

        logger.info("settings.get", action="get_all_settings")

        return SettingsResponse(categories=CATEGORIES, fields=fields_by_category)

    except Exception as e:
        logger.error("settings.get.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/validate", response_model=ValidationResult)
async def validate_settings_endpoint(request: ValidationRequest):
    """
    Validate settings without persisting.
    """
    try:
        errors = validate_settings(request.settings)

        valid = len(errors) == 0
        result = ValidationResult(valid=valid, errors=errors, warnings=[])

        # Test API keys if provided
        if "OPENROUTER_API_KEY" in request.settings:
            key_valid, key_error = await test_api_key(
                "openrouter", request.settings["OPENROUTER_API_KEY"]
            )
            if not key_valid:
                result.warnings.append(
                    f"OPENROUTER_API_KEY: {key_error}"
                )

        if "GOOGLE_API_KEY" in request.settings:
            key_valid, key_error = await test_api_key(
                "google", request.settings["GOOGLE_API_KEY"]
            )
            if not key_valid:
                result.warnings.append(
                    f"GOOGLE_API_KEY: {key_error}"
                )

        logger.info(
            "settings.validate",
            valid=valid,
            error_count=len(errors),
            warning_count=len(result.warnings),
        )

        return result

    except Exception as e:
        logger.error("settings.validate.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings", response_model=SettingsUpdateResponse)
async def update_settings(request: SettingsUpdateRequest):
    """
    Update settings and persist to .env file.
    """
    try:
        # Validate first
        errors = validate_settings(request.updates)
        if errors:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "message": "Validation failed", "errors": errors},
            )

        # Test API keys if provided
        warnings = []
        if "OPENROUTER_API_KEY" in request.updates:
            key_valid, key_error = await test_api_key(
                "openrouter", request.updates["OPENROUTER_API_KEY"]
            )
            if not key_valid:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "message": f"OpenRouter API key invalid: {key_error}",
                    },
                )

        if "GOOGLE_API_KEY" in request.updates:
            key_valid, key_error = await test_api_key(
                "google", request.updates["GOOGLE_API_KEY"]
            )
            if not key_valid:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "message": f"Google API key invalid: {key_error}",
                    },
                )

        # Write to .env file
        env_path = get_env_path()
        for key, value in request.updates.items():
            env_value = to_env_value(key, value)
            set_key(str(env_path), key, env_value)
            # Update in-memory environment
            os.environ[key] = env_value

        # Get updated settings
        current_settings = read_current_settings()
        updated_fields = {}
        for key in request.updates.keys():
            # Find field definition
            field_def = None
            for category_fields in SETTINGS_DEFINITIONS.values():
                for f in category_fields:
                    if f.key == key:
                        field_def = f
                        break
                if field_def:
                    break

            if field_def:
                current_value = current_settings.get(key, field_def.default)
                if field_def.sensitive:
                    current_value = mask_sensitive(key, str(current_value))

                updated_fields[key] = SettingField(
                    key=key,
                    label=field_def.label,
                    description=field_def.description,
                    type=field_def.type,
                    default=field_def.default,
                    current=current_value,
                    sensitive=field_def.sensitive,
                    validation=field_def.validation,
                )

        logger.info(
            "settings.update",
            updated_keys=list(request.updates.keys()),
            count=len(request.updates),
        )

        return SettingsUpdateResponse(
            success=True,
            message="Settings saved successfully",
            updated_keys=list(request.updates.keys()),
            requires_restart=False,
            updated_settings=updated_fields,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("settings.update.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/categories", response_model=CategoriesResponse)
async def get_categories():
    """
    Get category definitions.
    """
    try:
        logger.info("settings.categories.get", action="get_categories")
        return CategoriesResponse(categories=CATEGORIES)
    except Exception as e:
        logger.error("settings.categories.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/reset", response_model=SettingsUpdateResponse)
async def reset_settings(request: ResetRequest):
    """
    Reset specific settings to defaults.
    """
    try:
        env_path = get_env_path()
        keys_to_reset = []

        if request.reset_all:
            # Reset all settings
            for category_fields in SETTINGS_DEFINITIONS.values():
                for field in category_fields:
                    keys_to_reset.append(field.key)
        elif request.keys:
            keys_to_reset = request.keys
        else:
            raise HTTPException(
                status_code=400,
                detail="Either keys or reset_all must be provided",
            )

        # Reset each key to default
        for key in keys_to_reset:
            # Find field definition to get default
            field_def = None
            for category_fields in SETTINGS_DEFINITIONS.values():
                for f in category_fields:
                    if f.key == key:
                        field_def = f
                        break
                if field_def:
                    break

            if field_def:
                default_value = to_env_value(key, field_def.default)
                set_key(str(env_path), key, default_value)
                os.environ[key] = default_value

        # Get updated settings
        current_settings = read_current_settings()
        updated_fields = {}
        for key in keys_to_reset:
            field_def = None
            for category_fields in SETTINGS_DEFINITIONS.values():
                for f in category_fields:
                    if f.key == key:
                        field_def = f
                        break
                if field_def:
                    break

            if field_def:
                current_value = current_settings.get(key, field_def.default)
                if field_def.sensitive:
                    current_value = mask_sensitive(key, str(current_value))

                updated_fields[key] = SettingField(
                    key=key,
                    label=field_def.label,
                    description=field_def.description,
                    type=field_def.type,
                    default=field_def.default,
                    current=current_value,
                    sensitive=field_def.sensitive,
                    validation=field_def.validation,
                )

        logger.info("settings.reset", reset_all=request.reset_all, count=len(keys_to_reset))

        return SettingsUpdateResponse(
            success=True,
            message=f"Reset {len(keys_to_reset)} settings to defaults",
            updated_keys=keys_to_reset,
            requires_restart=False,
            updated_settings=updated_fields,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("settings.reset.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
