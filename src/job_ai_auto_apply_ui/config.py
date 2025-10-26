"""Minimal config loader for global settings.

Read environment variables and expose configuration defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "on", "yes"}


def _get_chrome_args(name: str, defaults: list[str]) -> list[str]:
    """Parse semicolon-separated Chrome args from env var, or return defaults.

    Args:
        name: Environment variable name.
        defaults: Default list of Chrome args if not set.

    Returns:
        list[str]: Chrome command-line arguments.
    """
    value = os.getenv(name)
    if not value:
        return defaults
    return [arg.strip() for arg in value.split(";") if arg.strip()]


@dataclass
class Settings:
    """Application configuration loaded from environment variables."""

    dwell_seconds: float = field(default_factory=lambda: _get_float("DWELL_SECONDS", 0.8))
    jitter_seconds: float = field(default_factory=lambda: _get_float("JITTER_SECONDS", 0.4))
    max_tabs: int = field(default_factory=lambda: _get_int("MAX_TABS", 3))
    retries: int = field(default_factory=lambda: _get_int("RETRIES", 2))
    discovery_window_hours: int = field(
        default_factory=lambda: _get_int("DISCOVERY_WINDOW_HOURS", 24)
    )
    discovery_cap: int = field(default_factory=lambda: _get_int("DISCOVERY_CAP", 10))

    # Networking
    proxy_url: str | None = field(
        default_factory=lambda: os.getenv("PROXY_URL")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
    )
    user_agent: str | None = field(default_factory=lambda: os.getenv("USER_AGENT"))
    allowed_domains: list[str] = field(
        default_factory=lambda: os.getenv("ALLOWED_DOMAINS", "google.*,jobs.lever.co").split(",")
    )
    artifacts_root: str = field(
        default_factory=lambda: os.getenv("AUTO_APPLY_ARTIFACTS_DIR", "data/artifacts")
    )

    # LLM
    llm_provider: str | None = field(default_factory=lambda: os.getenv("LLM_PROVIDER"))
    llm_model: str | None = field(default_factory=lambda: os.getenv("LLM_MODEL"))
    llm_temperature: float = field(default_factory=lambda: _get_float("LLM_TEMPERATURE", 0.0))
    llm_timeout_seconds: int = field(default_factory=lambda: _get_int("LLM_TIMEOUT_SECONDS", 30))
    llm_referer: str | None = field(default_factory=lambda: os.getenv("LLM_REFERER"))
    llm_user_agent: str | None = field(default_factory=lambda: os.getenv("LLM_USER_AGENT"))
    openrouter_api_key: str | None = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY"))
    google_api_key: str | None = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY"))

    # Diagnostics
    diagnostics_enabled: bool = field(
        default_factory=lambda: _get_bool("AUTO_APPLY_DIAGNOSTICS", False)
    )
    diagnostics_capture_video: bool = field(
        default_factory=lambda: _get_bool("AUTO_APPLY_CAPTURE_VIDEO", False)
    )
    diagnostics_capture_har: bool = field(
        default_factory=lambda: _get_bool("AUTO_APPLY_CAPTURE_HAR", False)
    )

    # Resume upload feature flags
    use_llm_locator: bool = field(
        default_factory=lambda: _get_bool("AUTO_APPLY_USE_LLM_LOCATOR", False)
    )
    debug_resume_widget: bool = field(
        default_factory=lambda: _get_bool("AUTO_APPLY_DEBUG_RESUME_WIDGET", False)
    )
    resume_wait_timeout_seconds: int = field(
        default_factory=lambda: _get_int("AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS", 25)
    )

    # Captcha detection - vision fallback
    captcha_visual_check: bool = field(
        default_factory=lambda: _get_bool("AUTO_APPLY_CAPTCHA_VISUAL_CHECK", False)
    )
    captcha_vision_model: str = field(
        default_factory=lambda: os.getenv(
            "AUTO_APPLY_CAPTCHA_VISION_MODEL",
            "google/gemini-2.0-flash-exp:free"
        )
    )
    captcha_visual_delay_seconds: float = field(
        default_factory=lambda: _get_float("CAPTCHA_VISUAL_DELAY_SECONDS", 3.0)
    )
    captcha_timeout_seconds: int = field(
        default_factory=lambda: _get_int("AUTO_APPLY_CAPTCHA_TIMEOUT_SECONDS", 30)
    )

    # Stealth / anti-detection
    browser_locale: str = field(default_factory=lambda: os.getenv("BROWSER_LOCALE", "en-US"))
    browser_timezone: str = field(
        default_factory=lambda: os.getenv("BROWSER_TIMEZONE", "America/Los_Angeles")
    )
    browser_viewport_width: int = field(
        default_factory=lambda: _get_int("BROWSER_VIEWPORT_WIDTH", 1280)
    )
    browser_viewport_height: int = field(
        default_factory=lambda: _get_int("BROWSER_VIEWPORT_HEIGHT", 800)
    )
    disable_default_extensions: bool = field(
        default_factory=lambda: _get_bool("AUTO_APPLY_DISABLE_DEFAULT_EXTENSIONS", True)
    )
    chrome_args: list[str] = field(
        default_factory=lambda: _get_chrome_args(
            "AUTO_APPLY_CHROME_ARGS",
            [
                "--disable-autofill",
                "--disable-autofill-keyboard-accessory-view",
                "--disable-features=Autofill,AutofillServerCommunication",
            ],
        )
    )

    def artifacts_path(self, profile: str | None = None) -> Path:
        """Return the artifacts directory path, optionally namespaced per profile.

        Creates the directory structure if it doesn't exist.

        Args:
            profile: Optional profile identifier appended to the artifacts root.

        Returns:
            Path: Filesystem location where diagnostic artifacts should be stored.
        """

        base = Path(self.artifacts_root)
        if profile:
            path = base / profile
            path.mkdir(parents=True, exist_ok=True)
            return path
        base.mkdir(parents=True, exist_ok=True)
        return base


def load_settings() -> Settings:
    """Return :class:`Settings` loaded from environment variables.

    Returns:
        Settings: Configuration populated from process environment variables.
    """
    return Settings()
