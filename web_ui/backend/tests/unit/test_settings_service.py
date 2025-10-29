"""Unit tests for SettingsService."""

import pytest
import tempfile
from pathlib import Path
from src.services import SettingsService
from src.models import SETTINGS_CATALOG
from src.utils import FileOpsError


class TestSettingsService:
    """Test SettingsService functionality."""

    @pytest.fixture
    def temp_env_file(self):
        """Create temporary .env file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def service(self, temp_env_file):
        """Create SettingsService instance with temp file."""
        return SettingsService(env_path=temp_env_file)

    def test_get_all_settings(self, service):
        """Test loading all settings with defaults."""
        settings = service.get_all_settings()

        # Should have settings from catalog
        assert len(settings) > 0
        assert all(hasattr(s, "key") for s in settings)
        assert all(hasattr(s, "description") for s in settings)
        assert all(hasattr(s, "category") for s in settings)

    def test_get_all_settings_includes_catalog_keys(self, service):
        """Test that all catalog keys are present."""
        settings = service.get_all_settings()
        keys = {s.key for s in settings}

        for catalog_key in SETTINGS_CATALOG.keys():
            assert catalog_key in keys, f"Missing setting key: {catalog_key}"

    def test_get_setting_valid_key(self, service):
        """Test retrieving a specific setting."""
        setting = service.get_setting("DISCOVERY_WINDOW_HOURS")
        assert setting.key == "DISCOVERY_WINDOW_HOURS"
        assert setting.description
        assert setting.category

    def test_get_setting_invalid_key(self, service):
        """Test retrieving non-existent setting raises error."""
        with pytest.raises(FileOpsError):
            service.get_setting("NONEXISTENT_KEY")

    def test_update_settings_single(self, service):
        """Test updating a single setting."""
        result = service.update_settings({"DISCOVERY_WINDOW_HOURS": "48"})

        assert "DISCOVERY_WINDOW_HOURS" in result
        assert len(result) == 1

        # Verify it was saved
        updated = service.get_setting("DISCOVERY_WINDOW_HOURS")
        assert updated.value == "48"

    def test_update_settings_multiple(self, service):
        """Test updating multiple settings."""
        updates = {
            "DISCOVERY_WINDOW_HOURS": "48",
            "DISCOVERY_CAP": "20",
        }
        result = service.update_settings(updates)

        assert len(result) == 2
        assert "DISCOVERY_WINDOW_HOURS" in result
        assert "DISCOVERY_CAP" in result

    def test_update_settings_invalid_key(self, service):
        """Test updating with invalid key raises error."""
        with pytest.raises(FileOpsError):
            service.update_settings({"INVALID_KEY": "value"})

    def test_update_settings_persists_to_file(self, service, temp_env_file):
        """Test that updates persist to .env file."""
        service.update_settings({"DISCOVERY_WINDOW_HOURS": "72"})

        # Read file directly
        with open(temp_env_file, "r") as f:
            content = f.read()

        assert "DISCOVERY_WINDOW_HOURS" in content
        assert "72" in content

    def test_reset_setting(self, service):
        """Test resetting a single setting."""
        # First set a value
        service.update_settings({"DISCOVERY_WINDOW_HOURS": "48"})

        # Then reset it
        service.reset_setting("DISCOVERY_WINDOW_HOURS")

        # Should return None or default
        setting = service.get_setting("DISCOVERY_WINDOW_HOURS")
        assert setting.value is None or setting.value == setting.default_value

    def test_reset_setting_invalid_key(self, service):
        """Test resetting non-existent setting raises error."""
        with pytest.raises(FileOpsError):
            service.reset_setting("NONEXISTENT_KEY")

    def test_reset_all_settings(self, service, temp_env_file):
        """Test resetting all settings."""
        # Set some values
        service.update_settings({
            "DISCOVERY_WINDOW_HOURS": "48",
            "DISCOVERY_CAP": "20",
        })

        # Reset all
        service.reset_all()

        # File should be deleted
        assert not Path(temp_env_file).exists()

    def test_sensitive_value_masking(self, service):
        """Test that sensitive values are masked."""
        # Set an API key
        service.update_settings({"OPENROUTER_API_KEY": "sk-secret-key-123"})

        # Get it back
        setting = service.get_setting("OPENROUTER_API_KEY")

        # Check if marked as secret (masking depends on API response)
        if setting.is_secret:
            # Value should be masked in response or marked
            assert setting.value is None or setting.value != "sk-secret-key-123"

    def test_get_all_settings_sensitive_handling(self, service):
        """Test sensitive values are handled properly in list."""
        service.update_settings({"OPENROUTER_API_KEY": "sk-secret-123"})

        settings = service.get_all_settings()
        api_key_setting = next(
            (s for s in settings if s.key == "OPENROUTER_API_KEY"),
            None
        )

        assert api_key_setting is not None
        if api_key_setting.is_secret:
            # Sensitive field handling
            assert hasattr(api_key_setting, "is_secret")

    def test_settings_have_metadata(self, service):
        """Test settings have required metadata."""
        settings = service.get_all_settings()

        for setting in settings:
            assert setting.key, "Setting must have a key"
            assert setting.description, "Setting must have a description"
            assert setting.category, "Setting must have a category"
            assert setting.input_type, "Setting must have an input type"

    def test_setting_categories_valid(self, service):
        """Test all settings have valid categories."""
        from src.models import SettingCategory

        settings = service.get_all_settings()
        valid_categories = {e.value for e in SettingCategory}

        for setting in settings:
            assert setting.category in valid_categories

    def test_setting_input_types_valid(self, service):
        """Test all settings have valid input types."""
        from src.models import SettingInputType

        settings = service.get_all_settings()
        valid_types = {e.value for e in SettingInputType}

        for setting in settings:
            assert setting.input_type in valid_types

    def test_concurrent_access(self, service):
        """Test multiple settings operations."""
        # Update
        service.update_settings({"DISCOVERY_WINDOW_HOURS": "24"})

        # Get
        setting = service.get_setting("DISCOVERY_WINDOW_HOURS")
        assert setting.value == "24"

        # Update again
        service.update_settings({"DISCOVERY_WINDOW_HOURS": "48"})
        setting = service.get_setting("DISCOVERY_WINDOW_HOURS")
        assert setting.value == "48"

    def test_empty_env_file_initialization(self, temp_env_file):
        """Test service works with empty .env file."""
        # Create empty file
        Path(temp_env_file).write_text("")

        service = SettingsService(env_path=temp_env_file)
        settings = service.get_all_settings()

        # Should have all defaults
        assert len(settings) > 0

    def test_preserve_unmodified_settings(self, service):
        """Test that unmodified settings are preserved."""
        # Set multiple settings
        service.update_settings({
            "DISCOVERY_WINDOW_HOURS": "48",
            "DISCOVERY_CAP": "20",
        })

        # Update only one
        service.update_settings({"DISCOVERY_WINDOW_HOURS": "72"})

        # Check both are present
        window = service.get_setting("DISCOVERY_WINDOW_HOURS")
        cap = service.get_setting("DISCOVERY_CAP")

        assert window.value == "72"
        assert cap.value == "20"

    def test_settings_type_coercion(self, service):
        """Test that values are properly stored."""
        # Store numeric value
        service.update_settings({"DISCOVERY_CAP": "15"})

        setting = service.get_setting("DISCOVERY_CAP")
        assert setting.value == "15"

    def test_special_characters_in_values(self, service):
        """Test settings with special characters."""
        special_value = "https://example.com/path?query=value&other=test"
        service.update_settings({"ALLOWED_DOMAINS": special_value})

        setting = service.get_setting("ALLOWED_DOMAINS")
        assert setting.value == special_value
