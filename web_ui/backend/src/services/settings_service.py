"""Settings service for managing environment variables."""

from pathlib import Path
from typing import List, Optional
from src.models import Setting, SETTINGS_CATALOG
from src.utils import load_env, save_env, FileOpsError


class SettingsService:
    """Service for settings management."""

    def __init__(self, env_path: str = ".env"):
        """Initialize SettingsService.

        Args:
            env_path: Path to .env file
        """
        self.env_path = Path(env_path)

    def get_all_settings(self) -> List[Setting]:
        """Get all available settings with current values."""
        current_values = load_env(self.env_path)
        settings = []

        for key, setting in SETTINGS_CATALOG.items():
            updated = setting.model_copy()
            if key in current_values:
                updated.value = current_values[key]
            settings.append(updated.to_api_response())

        return settings

    def get_setting(self, key: str) -> Setting:
        """Get a specific setting."""
        if key not in SETTINGS_CATALOG:
            raise FileOpsError(f"Setting not found: {key}")

        setting = SETTINGS_CATALOG[key].model_copy()
        current_values = load_env(self.env_path)

        if key in current_values:
            setting.value = current_values[key]

        return setting.to_api_response()

    def update_settings(self, updates: dict) -> List[str]:
        """Update multiple settings."""
        validated = {}

        for key, value in updates.items():
            if key not in SETTINGS_CATALOG:
                raise FileOpsError(f"Unknown setting: {key}")
            validated[key] = str(value)

        save_env(self.env_path, validated)
        return list(validated.keys())

    def reset_setting(self, key: str) -> None:
        """Reset a setting to default."""
        if key not in SETTINGS_CATALOG:
            raise FileOpsError(f"Setting not found: {key}")

        current = load_env(self.env_path)
        if key in current:
            del current[key]
            save_env(self.env_path, current)

    def reset_all(self) -> None:
        """Reset all settings to defaults."""
        self.env_path.unlink(missing_ok=True)
