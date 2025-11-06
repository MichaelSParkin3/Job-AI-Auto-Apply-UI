"""Tests for settings API routes."""

import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient

from web_ui.backend.app import app
from web_ui.backend.routes.settings import validate_settings, mask_sensitive


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestValidateSettings:
    """Tests for settings validation."""

    def test_validate_dwell_seconds_valid(self):
        """Test valid dwell seconds."""
        errors = validate_settings({"DWELL_SECONDS": "1.0"})
        assert "DWELL_SECONDS" not in errors

    def test_validate_dwell_seconds_too_low(self):
        """Test dwell seconds below minimum."""
        errors = validate_settings({"DWELL_SECONDS": "0.05"})
        assert "DWELL_SECONDS" in errors

    def test_validate_dwell_seconds_too_high(self):
        """Test dwell seconds above maximum."""
        errors = validate_settings({"DWELL_SECONDS": "10.0"})
        assert "DWELL_SECONDS" in errors

    def test_validate_temperature_valid(self):
        """Test valid temperature."""
        errors = validate_settings({"LLM_TEMPERATURE": "0.5"})
        assert "LLM_TEMPERATURE" not in errors

    def test_validate_temperature_out_of_range(self):
        """Test temperature out of range."""
        errors = validate_settings({"LLM_TEMPERATURE": "3.0"})
        assert "LLM_TEMPERATURE" in errors

    def test_validate_discovery_cap_valid(self):
        """Test valid discovery cap."""
        errors = validate_settings({"DISCOVERY_CAP": "50"})
        assert "DISCOVERY_CAP" not in errors

    def test_validate_discovery_cap_too_high(self):
        """Test discovery cap above maximum."""
        errors = validate_settings({"DISCOVERY_CAP": "150"})
        assert "DISCOVERY_CAP" in errors

    def test_validate_llm_provider_valid(self):
        """Test valid LLM provider."""
        errors = validate_settings({"LLM_PROVIDER": "openrouter"})
        assert "LLM_PROVIDER" not in errors

    def test_validate_llm_provider_invalid(self):
        """Test invalid LLM provider."""
        errors = validate_settings({"LLM_PROVIDER": "invalid"})
        assert "LLM_PROVIDER" in errors

    def test_validate_multiple_errors(self):
        """Test multiple validation errors."""
        errors = validate_settings({
            "DWELL_SECONDS": "10.0",
            "DISCOVERY_CAP": "150",
            "LLM_TEMPERATURE": "3.0",
        })
        assert len(errors) == 3
        assert "DWELL_SECONDS" in errors
        assert "DISCOVERY_CAP" in errors
        assert "LLM_TEMPERATURE" in errors

    def test_validate_unknown_setting(self):
        """Test validation of unknown setting."""
        errors = validate_settings({"UNKNOWN_SETTING": "value"})
        assert "UNKNOWN_SETTING" in errors

    def test_validate_int_type(self):
        """Test integer type validation."""
        errors = validate_settings({"MAX_TABS": "not_an_int"})
        assert "MAX_TABS" in errors

    def test_validate_float_type(self):
        """Test float type validation."""
        errors = validate_settings({"DWELL_SECONDS": "not_a_float"})
        assert "DWELL_SECONDS" in errors


class TestMaskSensitive:
    """Tests for sensitive value masking."""

    def test_mask_api_key_empty(self):
        """Test masking empty API key."""
        result = mask_sensitive("OPENROUTER_API_KEY", "")
        assert result == ""

    def test_mask_api_key_long(self):
        """Test masking long API key."""
        result = mask_sensitive("OPENROUTER_API_KEY", "sk-1234567890abcdef")
        assert result == "••••cdef"
        assert "sk-" not in result

    def test_mask_api_key_short(self):
        """Test masking short API key."""
        result = mask_sensitive("OPENROUTER_API_KEY", "short")
        # Short keys show last 4 chars if available
        assert "••••" in result

    def test_mask_proxy_url(self):
        """Test masking proxy URL."""
        result = mask_sensitive("PROXY_URL", "http://user:password@proxy:8080")
        # Should mask the URL
        assert "••••" in result
        assert "password" not in result

    def test_no_mask_non_sensitive(self):
        """Test non-sensitive values are not masked."""
        result = mask_sensitive("DWELL_SECONDS", "1.0")
        assert result == "1.0"

    def test_no_mask_user_agent(self):
        """Test user agent is not masked."""
        result = mask_sensitive("USER_AGENT", "Mozilla/5.0")
        assert result == "Mozilla/5.0"


def test_get_settings(client):
    """Test GET /api/settings endpoint."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "categories" in data
    assert "fields" in data
    assert isinstance(data["categories"], list)
    assert isinstance(data["fields"], dict)

    # Check categories
    assert len(data["categories"]) > 0
    category_ids = [c["id"] for c in data["categories"]]
    assert "llm" in category_ids
    assert "browser" in category_ids
    assert "general" in category_ids

    # Check fields structure
    assert "llm" in data["fields"]
    assert len(data["fields"]["llm"]) > 0

    # Check field structure
    field = data["fields"]["llm"][0]
    assert "key" in field
    assert "label" in field
    assert "description" in field
    assert "type" in field
    assert "current" in field
    assert "default" in field

    # Check sensitive field masking
    for category_fields in data["fields"].values():
        for field in category_fields:
            if field["sensitive"] and field["current"]:
                # Sensitive fields should be masked
                assert "••••" in str(field["current"])


def test_validate_settings_valid(client):
    """Test POST /api/settings/validate with valid settings."""
    response = client.post(
        "/api/settings/validate",
        json={
            "settings": {
                "DWELL_SECONDS": "1.0",
                "MAX_TABS": "3",
            }
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert len(data["errors"]) == 0


def test_validate_settings_invalid(client):
    """Test POST /api/settings/validate with invalid settings."""
    response = client.post(
        "/api/settings/validate",
        json={
            "settings": {
                "DWELL_SECONDS": "10.0",  # Too high
                "DISCOVERY_CAP": "150",  # Too high
            }
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) == 2
    assert "DWELL_SECONDS" in data["errors"]
    assert "DISCOVERY_CAP" in data["errors"]


def test_get_categories(client):
    """Test GET /api/settings/categories endpoint."""
    response = client.get("/api/settings/categories")
    assert response.status_code == 200
    data = response.json()

    assert "categories" in data
    assert len(data["categories"]) > 0

    # Check category structure
    category = data["categories"][0]
    assert "id" in category
    assert "name" in category
    assert "description" in category


def test_update_settings_valid(client, tmp_path, monkeypatch):
    """Test PUT /api/settings with valid settings."""
    # Mock the .env file path
    mock_env = tmp_path / ".env"
    mock_env.write_text("")

    def mock_get_env_path():
        return mock_env

    import web_ui.backend.routes.settings as settings_module
    monkeypatch.setattr(settings_module, "get_env_path", mock_get_env_path)

    response = client.put(
        "/api/settings",
        json={
            "updates": {
                "DWELL_SECONDS": "1.2",
                "MAX_TABS": "5",
            }
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["updated_keys"]) == 2
    assert "DWELL_SECONDS" in data["updated_keys"]
    assert "MAX_TABS" in data["updated_keys"]


def test_update_settings_invalid(client):
    """Test PUT /api/settings with invalid settings."""
    response = client.put(
        "/api/settings",
        json={
            "updates": {
                "DWELL_SECONDS": "10.0",  # Too high
            }
        },
    )
    assert response.status_code == 400
    data = response.json()
    # Error response is wrapped in HTTPException detail
    assert "error" in str(response.text).lower() or "validation" in str(
        response.text
    ).lower()


def test_reset_settings(client, tmp_path, monkeypatch):
    """Test POST /api/settings/reset endpoint."""
    # Mock the .env file path
    mock_env = tmp_path / ".env"
    mock_env.write_text("DWELL_SECONDS=2.0\nMAX_TABS=10\n")

    def mock_get_env_path():
        return mock_env

    import web_ui.backend.routes.settings as settings_module
    monkeypatch.setattr(settings_module, "get_env_path", mock_get_env_path)

    response = client.post(
        "/api/settings/reset",
        json={
            "keys": ["DWELL_SECONDS", "MAX_TABS"],
            "reset_all": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["updated_keys"]) == 2


def test_reset_all_settings(client, tmp_path, monkeypatch):
    """Test POST /api/settings/reset with reset_all=true."""
    # Mock the .env file path
    mock_env = tmp_path / ".env"
    mock_env.write_text("")

    def mock_get_env_path():
        return mock_env

    import web_ui.backend.routes.settings as settings_module
    monkeypatch.setattr(settings_module, "get_env_path", mock_get_env_path)

    response = client.post(
        "/api/settings/reset",
        json={
            "keys": None,
            "reset_all": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Should reset all settings
    assert len(data["updated_keys"]) > 0
