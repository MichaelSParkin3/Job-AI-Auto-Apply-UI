"""Web UI-specific configuration."""

from pathlib import Path
import os


class WebSettings:
    """Web UI configuration."""

    def __init__(self):
        """Initialize web settings from environment or defaults."""
        # Profiles directory
        self.profiles_dir = os.getenv(
            "AUTO_APPLY_PROFILES_DIR",
            str(Path.cwd() / "profiles"),
        )

        # Queues directory
        self.queues_dir = os.getenv(
            "AUTO_APPLY_QUEUES_DIR",
            str(Path.cwd() / "data" / "queues"),
        )

        # Artifacts directory
        self.artifacts_dir = os.getenv(
            "AUTO_APPLY_ARTIFACTS_DIR",
            str(Path.cwd() / "data" / "artifacts"),
        )

        # Web server configuration
        self.host = os.getenv("WEB_HOST", "0.0.0.0")
        self.port = int(os.getenv("WEB_PORT", "8000"))
        self.reload = os.getenv("WEB_RELOAD", "true").lower() in {"true", "1", "yes"}


# Singleton instance
web_settings = WebSettings()
