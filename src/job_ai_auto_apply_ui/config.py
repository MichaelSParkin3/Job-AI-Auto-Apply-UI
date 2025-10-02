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
    llm_temperature: float = field(
        default_factory=lambda: _get_float("LLM_TEMPERATURE", 0.0)
    )
    llm_timeout_seconds: int = field(
        default_factory=lambda: _get_int("LLM_TIMEOUT_SECONDS", 30)
    )
    llm_referer: str | None = field(default_factory=lambda: os.getenv("LLM_REFERER"))
    llm_user_agent: str | None = field(default_factory=lambda: os.getenv("LLM_USER_AGENT"))
    openrouter_api_key: str | None = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY")
    )
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

    def artifacts_path(self, profile: str | None = None) -> Path:
        """Return the artifacts directory path, optionally namespaced per profile.

        Args:
            profile: Optional profile identifier appended to the artifacts root.

        Returns:
            Path: Filesystem location where diagnostic artifacts should be stored.
        """

        base = Path(self.artifacts_root)
        if profile:
            return base / profile
        return base


def load_settings() -> Settings:
    """Return :class:`Settings` loaded from environment variables.

    Returns:
        Settings: Configuration populated from process environment variables.
    """
    return Settings()

