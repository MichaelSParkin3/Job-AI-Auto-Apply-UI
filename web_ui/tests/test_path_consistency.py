"""Tests for path configuration consistency between CLI and web UI."""

from pathlib import Path

import pytest

from web_ui.backend.config import web_settings


class TestPathConsistency:
    """Test that paths are configured correctly."""

    def test_paths_resolve_correctly(self):
        """Ensure paths point to expected locations."""
        assert Path(web_settings.profiles_dir).name == "profiles"
        assert Path(web_settings.queues_dir).name == "queues"

    def test_directories_exist(self):
        """Ensure required directories exist."""
        assert Path(web_settings.profiles_dir).exists(), (
            f"Profiles directory does not exist: {web_settings.profiles_dir}"
        )
        assert Path(web_settings.queues_dir).exists(), (
            f"Queues directory does not exist: {web_settings.queues_dir}"
        )

    def test_artifacts_dir_exists(self):
        """Ensure artifacts directory exists or can be created."""
        artifacts_path = Path(web_settings.artifacts_dir)
        artifacts_path.mkdir(parents=True, exist_ok=True)
        assert artifacts_path.exists()

    def test_profile_file_accessible(self, test_profile_id):
        """Ensure profile TOML file can be read."""
        profile_file = Path(web_settings.profiles_dir) / f"{test_profile_id}.toml"
        assert profile_file.exists(), (
            f"Profile file not found: {profile_file}"
        )

    def test_queue_file_exists(self, queue_file_path):
        """Ensure queue JSON file exists for test profile."""
        assert queue_file_path.exists(), (
            f"Queue file not found: {queue_file_path}"
        )

    def test_queue_file_format(self, queue_file_path):
        """Ensure queue file has valid JSON format."""
        import json

        with open(queue_file_path) as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "items" in data
        assert isinstance(data["items"], list)
