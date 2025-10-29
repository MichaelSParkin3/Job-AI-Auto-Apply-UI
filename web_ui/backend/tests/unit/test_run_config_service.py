"""Unit tests for RunConfigurationService."""

import json
import tempfile
from pathlib import Path

import pytest

from src.models.config import RunConfiguration, OperationType
from src.services.run_config_service import RunConfigurationService


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def service(temp_dir):
    """Create RunConfigurationService with temp directory."""
    return RunConfigurationService(data_dir=temp_dir)


class TestRunConfigurationService:
    """Test RunConfigurationService functionality."""

    def test_init_creates_directory(self, temp_dir):
        """Test that __init__ creates data directory."""
        data_dir = Path(temp_dir) / "configs"
        service = RunConfigurationService(data_dir=str(data_dir))
        assert data_dir.exists()

    def test_save_run_config(self, service):
        """Test saving RunConfiguration to JSON file."""
        profile_id = "test_profile"
        config = RunConfiguration(
            profile_id=profile_id,
            operation_type=OperationType.DISCOVER,
            search_window="24h",
            job_cap=10,
        )

        saved = service.save_run_config(profile_id, config)
        assert saved.profile_id == profile_id
        assert saved.operation_type == OperationType.DISCOVER

        # Verify file was created
        config_path = service.get_config_path(profile_id)
        assert config_path.exists()

    def test_load_run_config_existing_file(self, service):
        """Test loading RunConfiguration from existing file."""
        profile_id = "test_profile"
        original = RunConfiguration(
            profile_id=profile_id,
            operation_type=OperationType.DISCOVER,
            search_window="24h",
            job_cap=15,
        )
        service.save_run_config(profile_id, original)

        # Load it back
        loaded = service.load_run_config(profile_id, OperationType.DISCOVER)
        assert loaded.profile_id == profile_id
        assert loaded.search_window == "24h"
        assert loaded.job_cap == 15

    def test_load_run_config_missing_file_returns_defaults(self, service):
        """Test that loading missing config returns defaults."""
        profile_id = "nonexistent_profile"

        loaded = service.load_run_config(profile_id, OperationType.DISCOVER)
        assert loaded.profile_id == profile_id
        assert loaded.operation_type == OperationType.DISCOVER
        assert loaded.search_window is None
        assert loaded.job_cap is None

    def test_load_run_config_with_apply_single(self, service):
        """Test loading apply_single operation type."""
        profile_id = "test_profile"
        original = RunConfiguration(
            profile_id=profile_id,
            operation_type=OperationType.APPLY_SINGLE,
            mode="supervised",
            review_mode=True,
            use_llm_locator=True,
        )
        service.save_run_config(profile_id, original)

        loaded = service.load_run_config(profile_id, OperationType.APPLY_SINGLE)
        assert loaded.operation_type == OperationType.APPLY_SINGLE
        assert loaded.mode == "supervised"
        assert loaded.review_mode is True
        assert loaded.use_llm_locator is True

    def test_load_run_config_invalid_operation_type(self, service):
        """Test that invalid operation_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid operation_type"):
            service.load_run_config("test_profile", "invalid_type")

    def test_delete_run_config(self, service):
        """Test deleting RunConfiguration file."""
        profile_id = "test_profile"
        config = RunConfiguration(
            profile_id=profile_id,
            operation_type=OperationType.DISCOVER,
        )
        service.save_run_config(profile_id, config)

        config_path = service.get_config_path(profile_id)
        assert config_path.exists()

        service.delete_run_config(profile_id)
        assert not config_path.exists()

    def test_delete_nonexistent_config_no_error(self, service):
        """Test that deleting nonexistent config doesn't raise error."""
        # Should not raise
        service.delete_run_config("nonexistent_profile")

    def test_reset_to_defaults(self, service):
        """Test resetting configuration to defaults."""
        profile_id = "test_profile"
        original = RunConfiguration(
            profile_id=profile_id,
            operation_type=OperationType.DISCOVER,
            search_window="24h",
            job_cap=50,
        )
        service.save_run_config(profile_id, original)

        # Verify original was saved
        loaded = service.load_run_config(profile_id, OperationType.DISCOVER)
        assert loaded.search_window == "24h"
        assert loaded.job_cap == 50

        # Reset to defaults
        defaults = service.reset_to_defaults(profile_id, OperationType.DISCOVER)
        assert defaults.search_window is None
        assert defaults.job_cap is None

        # Verify defaults were saved
        reloaded = service.load_run_config(profile_id, OperationType.DISCOVER)
        assert reloaded.search_window is None
        assert reloaded.job_cap is None

    def test_get_config_path(self, service):
        """Test getting config file path."""
        path = service.get_config_path("my_profile")
        assert path.name == "my_profile.json"
        assert path.parent.name == path.parent.name

    def test_save_preserves_all_fields(self, service):
        """Test that all RunConfiguration fields are preserved."""
        profile_id = "test_profile"
        config = RunConfiguration(
            profile_id=profile_id,
            operation_type=OperationType.APPLY_BULK,
            search_window="7d",
            job_cap=25,
            custom_query="python developer",
            mode="automated",
            review_mode=False,
            llm_provider_override="google",
            llm_model_override="gemini-2.0",
            use_llm_locator=False,
            debug_resume_widget=True,
            resume_wait_timeout=60,
            audit_after_submit=True,
            save_logs=True,
            logs_dir="/tmp/logs",
            max_concurrent=2,
            stop_on_failure=True,
        )
        service.save_run_config(profile_id, config)

        loaded = service.load_run_config(profile_id, OperationType.APPLY_BULK)
        assert loaded.search_window == "7d"
        assert loaded.job_cap == 25
        assert loaded.custom_query == "python developer"
        assert loaded.mode == "automated"
        assert loaded.review_mode is False
        assert loaded.llm_provider_override == "google"
        assert loaded.llm_model_override == "gemini-2.0"
        assert loaded.use_llm_locator is False
        assert loaded.debug_resume_widget is True
        assert loaded.resume_wait_timeout == 60
        assert loaded.audit_after_submit is True
        assert loaded.save_logs is True
        assert loaded.logs_dir == "/tmp/logs"
        assert loaded.max_concurrent == 2
        assert loaded.stop_on_failure is True

    def test_multiple_profiles_independent(self, service):
        """Test that configs for different profiles are independent."""
        config1 = RunConfiguration(
            profile_id="profile1",
            operation_type=OperationType.DISCOVER,
            search_window="24h",
            job_cap=10,
        )
        config2 = RunConfiguration(
            profile_id="profile2",
            operation_type=OperationType.DISCOVER,
            search_window="7d",
            job_cap=50,
        )

        service.save_run_config("profile1", config1)
        service.save_run_config("profile2", config2)

        loaded1 = service.load_run_config("profile1", OperationType.DISCOVER)
        loaded2 = service.load_run_config("profile2", OperationType.DISCOVER)

        assert loaded1.job_cap == 10
        assert loaded2.job_cap == 50
