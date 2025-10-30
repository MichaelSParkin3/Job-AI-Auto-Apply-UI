"""RunConfiguration persistence service for storing user-selected options."""

import os
from pathlib import Path
from typing import Optional

from src.models.config import RunConfiguration, OperationType
from src.utils.file_ops import load_json, save_json, ensure_dir


class RunConfigurationService:
    """Service for loading and saving RunConfiguration per profile."""

    def __init__(self, data_dir: str = "data/run-config"):
        """Initialize with data directory for storing config files.

        Args:
            data_dir: Directory to store profile-specific run configs
        """
        self.data_dir = Path(data_dir)
        ensure_dir(str(self.data_dir))

    def get_config_path(self, profile_id: str) -> Path:
        """Get the path to a profile's config file.

        Args:
            profile_id: Profile identifier

        Returns:
            Path object for the config file
        """
        return self.data_dir / f"{profile_id}.json"

    def save_run_config(
        self, profile_id: str, config: RunConfiguration
    ) -> RunConfiguration:
        """Save RunConfiguration for a profile.

        Args:
            profile_id: Profile identifier
            config: RunConfiguration to save

        Returns:
            Saved RunConfiguration

        Raises:
            IOError: If save fails
        """
        config_path = self.get_config_path(profile_id)

        # Convert to dict, handling datetime serialization
        config_data = config.model_dump(mode="json")

        save_json(str(config_path), config_data)
        return config

    def load_run_config(
        self, profile_id: str, operation_type: OperationType
    ) -> RunConfiguration:
        """Load RunConfiguration for a profile.

        Returns defaults if file doesn't exist.

        Args:
            profile_id: Profile identifier
            operation_type: Type of operation (discover, apply_single, apply_bulk)

        Returns:
            Loaded RunConfiguration or defaults

        Raises:
            ValueError: If operation_type is invalid
        """
        if operation_type not in OperationType:
            raise ValueError(f"Invalid operation_type: {operation_type}")

        config_path = self.get_config_path(profile_id)

        # If file doesn't exist, return defaults
        if not config_path.exists():
            return RunConfiguration(
                profile_id=profile_id,
                operation_type=operation_type,
            )

        try:
            config_data = load_json(str(config_path))
            # Update profile_id and operation_type from parameters
            config_data["profile_id"] = profile_id
            config_data["operation_type"] = operation_type
            return RunConfiguration(**config_data)
        except Exception as e:
            # If load fails, return defaults
            return RunConfiguration(
                profile_id=profile_id,
                operation_type=operation_type,
            )

    def delete_run_config(self, profile_id: str) -> None:
        """Delete RunConfiguration for a profile.

        Args:
            profile_id: Profile identifier

        Raises:
            IOError: If deletion fails
        """
        config_path = self.get_config_path(profile_id)
        if config_path.exists():
            try:
                config_path.unlink()
            except OSError as e:
                raise IOError(f"Failed to delete config for {profile_id}: {e}")

    def reset_to_defaults(self, profile_id: str, operation_type: OperationType) -> RunConfiguration:
        """Reset profile configuration to defaults.

        Args:
            profile_id: Profile identifier
            operation_type: Type of operation

        Returns:
            Default RunConfiguration
        """
        defaults = RunConfiguration(
            profile_id=profile_id,
            operation_type=operation_type,
        )
        self.save_run_config(profile_id, defaults)
        return defaults
