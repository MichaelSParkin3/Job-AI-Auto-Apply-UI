"""Profile service for managing user profiles."""

import os
from pathlib import Path
from typing import List, Optional
from src.models import Profile
from src.utils import load_toml, save_toml, FileOpsError


class ProfileService:
    """Service for profile CRUD operations."""

    def __init__(self, profiles_dir: str = "profiles"):
        """Initialize ProfileService.

        Args:
            profiles_dir: Directory containing profile TOML files
        """
        self.profiles_dir = Path(profiles_dir)
        self._active_profile: Optional[str] = None

    def list_profiles(self) -> List[Profile]:
        """
        List all available profiles.

        Returns:
            List of Profile objects

        Raises:
            FileOpsError: If unable to read profiles directory
        """
        try:
            if not self.profiles_dir.exists():
                return []

            profiles = []
            for toml_file in self.profiles_dir.glob("*.toml"):
                try:
                    data = load_toml(toml_file)
                    profile = Profile(**data)
                    profiles.append(profile)
                except Exception:
                    # Skip invalid profile files
                    continue

            return profiles
        except Exception as e:
            raise FileOpsError(f"Failed to list profiles: {e}")

    def get_profile(self, profile_id: str) -> Profile:
        """
        Get a specific profile by ID.

        Args:
            profile_id: Profile ID (filename without .toml)

        Returns:
            Profile object

        Raises:
            FileOpsError: If profile not found or invalid
        """
        profile_path = self.profiles_dir / f"{profile_id}.toml"

        if not profile_path.exists():
            raise FileOpsError(f"Profile not found: {profile_id}")

        try:
            data = load_toml(profile_path)
            return Profile(**data)
        except Exception as e:
            raise FileOpsError(f"Failed to load profile {profile_id}: {e}")

    def update_profile(self, profile_id: str, profile_data: Profile) -> Profile:
        """
        Update a profile.

        Args:
            profile_id: Profile ID
            profile_data: Updated Profile object

        Returns:
            Updated Profile object

        Raises:
            FileOpsError: If validation or save fails
        """
        # Validate required fields
        if not profile_data.id:
            raise FileOpsError("Profile ID is required")
        if not profile_data.name:
            raise FileOpsError("Profile name is required")
        if not profile_data.resume_path:
            raise FileOpsError("Resume path is required")

        profile_path = self.profiles_dir / f"{profile_id}.toml"

        try:
            # Convert Pydantic model to dict for TOML serialization
            data = profile_data.model_dump(exclude_unset=True)
            save_toml(profile_path, data)
            return profile_data
        except Exception as e:
            raise FileOpsError(f"Failed to save profile {profile_id}: {e}")

    def get_active_profile(self) -> Optional[str]:
        """
        Get the currently active profile ID.

        Returns:
            Active profile ID or None
        """
        return self._active_profile

    def set_active_profile(self, profile_id: str) -> None:
        """
        Set the active profile.

        Args:
            profile_id: Profile ID to activate

        Raises:
            FileOpsError: If profile does not exist
        """
        # Verify profile exists
        profile_path = self.profiles_dir / f"{profile_id}.toml"
        if not profile_path.exists():
            raise FileOpsError(f"Profile not found: {profile_id}")

        self._active_profile = profile_id

    def delete_profile(self, profile_id: str) -> None:
        """
        Delete a profile.

        Args:
            profile_id: Profile ID to delete

        Raises:
            FileOpsError: If profile not found or delete fails
        """
        profile_path = self.profiles_dir / f"{profile_id}.toml"

        if not profile_path.exists():
            raise FileOpsError(f"Profile not found: {profile_id}")

        try:
            profile_path.unlink()
            if self._active_profile == profile_id:
                self._active_profile = None
        except Exception as e:
            raise FileOpsError(f"Failed to delete profile {profile_id}: {e}")
