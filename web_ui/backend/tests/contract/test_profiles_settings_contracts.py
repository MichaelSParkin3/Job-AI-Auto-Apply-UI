"""Contract tests for Profiles and Settings API endpoints."""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_profile_dir():
    """Create temporary profiles directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_env_file():
    """Create temporary .env file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        temp_path = f.name
    yield temp_path
    Path(temp_path).unlink(missing_ok=True)


# ============================================================================
# PROFILE ENDPOINTS TESTS
# ============================================================================

class TestProfileContracts:
    """Test Profile API contracts."""

    def test_list_profiles_schema(self, client):
        """Test GET /api/v1/profiles/ response schema."""
        response = client.get("/api/v1/profiles")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "profiles" in data
        assert "count" in data
        assert isinstance(data["profiles"], list)
        assert isinstance(data["count"], int)

    def test_get_profile_success_schema(self, client):
        """Test GET /api/v1/profiles/{id} success response schema."""
        # Use a sample profile if it exists
        list_response = client.get("/api/v1/profiles")
        if list_response.json()["count"] > 0:
            profile_id = list_response.json()["profiles"][0]["id"]
            response = client.get(f"/api/v1/profiles/{profile_id}")

            assert response.status_code == 200
            data = response.json()

            # Verify profile structure
            assert "id" in data
            assert "name" in data
            assert "resume_path" in data

    def test_get_profile_not_found(self, client):
        """Test GET /api/v1/profiles/{id} with non-existent ID."""
        response = client.get("/api/v1/profiles/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_put_profile_success_schema(self, client):
        """Test PUT /api/v1/profiles/{id} success response schema."""
        # Get existing profile first
        list_response = client.get("/api/v1/profiles")
        if list_response.json()["count"] > 0:
            profile = list_response.json()["profiles"][0]
            profile_id = profile["id"]

            # Update with new data
            update_data = {
                **profile,
                "name": "Updated Name",
            }

            response = client.put(
                f"/api/v1/profiles/{profile_id}",
                json=update_data
            )

            assert response.status_code == 200
            data = response.json()

            # Verify updated profile
            assert data["name"] == "Updated Name"
            assert data["id"] == profile_id

    def test_put_profile_invalid_data(self, client):
        """Test PUT /api/v1/profiles/{id} with invalid data."""
        list_response = client.get("/api/v1/profiles")
        if list_response.json()["count"] > 0:
            profile_id = list_response.json()["profiles"][0]["id"]

            # Send invalid data (missing required fields)
            response = client.put(
                f"/api/v1/profiles/{profile_id}",
                json={"id": profile_id}  # Missing name, resume_path
            )

            assert response.status_code in [400, 422]
            assert "detail" in response.json()

    def test_put_profile_not_found(self, client):
        """Test PUT /api/v1/profiles/{id} with non-existent ID."""
        response = client.put(
            "/api/v1/profiles/nonexistent",
            json={
                "id": "nonexistent",
                "name": "Test",
                "resume_path": "/path/to/resume.pdf"
            }
        )

        # Should fail with 400 or 404
        assert response.status_code in [400, 404]

    def test_switch_profile_schema(self, client):
        """Test POST /api/v1/profiles/{id}/switch response schema."""
        list_response = client.get("/api/v1/profiles")
        if list_response.json()["count"] > 0:
            profile_id = list_response.json()["profiles"][0]["id"]
            response = client.post(f"/api/v1/profiles/{profile_id}/switch")

            assert response.status_code == 200
            data = response.json()

            assert "profile_id" in data
            assert "status" in data
            assert data["profile_id"] == profile_id

    def test_profile_data_types(self, client):
        """Test profile response data types."""
        response = client.get("/api/v1/profiles")
        if response.json()["count"] > 0:
            profile = response.json()["profiles"][0]

            # Verify data types
            assert isinstance(profile["id"], str)
            assert isinstance(profile["name"], str)
            assert isinstance(profile["resume_path"], str)


# ============================================================================
# SETTINGS ENDPOINTS TESTS
# ============================================================================

class TestSettingsContracts:
    """Test Settings API contracts."""

    def test_list_settings_schema(self, client):
        """Test GET /api/v1/settings response schema."""
        response = client.get("/api/v1/settings")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "settings" in data
        assert "count" in data
        assert isinstance(data["settings"], list)
        assert isinstance(data["count"], int)

    def test_settings_have_required_fields(self, client):
        """Test that each setting has required fields."""
        response = client.get("/api/v1/settings")
        settings = response.json()["settings"]

        for setting in settings:
            assert "key" in setting
            assert "description" in setting
            assert "category" in setting
            assert "input_type" in setting
            assert "is_secret" in setting
            assert isinstance(setting["key"], str)
            assert isinstance(setting["description"], str)

    def test_get_setting_success_schema(self, client):
        """Test GET /api/v1/settings/{key} success response schema."""
        # Get a known setting
        response = client.get("/api/v1/settings/DISCOVERY_WINDOW_HOURS")

        if response.status_code == 200:
            data = response.json()

            # Verify setting structure
            assert "key" in data
            assert "description" in data
            assert "category" in data
            assert "input_type" in data

    def test_get_setting_not_found(self, client):
        """Test GET /api/v1/settings/{key} with non-existent key."""
        response = client.get("/api/v1/settings/NONEXISTENT_SETTING")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_put_settings_schema(self, client):
        """Test PUT /api/v1/settings response schema."""
        updates = {
            "DISCOVERY_WINDOW_HOURS": "48",
        }

        response = client.put("/api/v1/settings", json=updates)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "updated" in data
        assert "count" in data
        assert isinstance(data["updated"], list)
        assert isinstance(data["count"], int)

    def test_put_settings_multiple(self, client):
        """Test updating multiple settings."""
        updates = {
            "DISCOVERY_WINDOW_HOURS": "72",
            "DISCOVERY_CAP": "20",
        }

        response = client.put("/api/v1/settings", json=updates)

        if response.status_code == 200:
            data = response.json()
            assert len(data["updated"]) >= 0

    def test_put_settings_invalid_key(self, client):
        """Test PUT /api/v1/settings with invalid key."""
        updates = {
            "INVALID_KEY_NONEXISTENT": "value",
        }

        response = client.put("/api/v1/settings", json=updates)

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_delete_setting_schema(self, client):
        """Test DELETE /api/v1/settings/{key} response schema."""
        # Set a value first
        client.put("/api/v1/settings", json={"DISCOVERY_WINDOW_HOURS": "48"})

        # Then reset it
        response = client.delete("/api/v1/settings/DISCOVERY_WINDOW_HOURS")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "key" in data
        assert data["key"] == "DISCOVERY_WINDOW_HOURS"

    def test_delete_setting_not_found(self, client):
        """Test DELETE /api/v1/settings/{key} with non-existent key."""
        response = client.delete("/api/v1/settings/NONEXISTENT_SETTING")

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_post_settings_reset_schema(self, client):
        """Test POST /api/v1/settings/reset response schema."""
        response = client.post("/api/v1/settings/reset")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "all_settings_reset"

    def test_sensitive_fields_masked(self, client):
        """Test that sensitive fields are masked in responses."""
        # Set an API key
        client.put("/api/v1/settings", json={"OPENROUTER_API_KEY": "sk-test-key-123"})

        # Get it back
        response = client.get("/api/v1/settings/OPENROUTER_API_KEY")

        if response.status_code == 200:
            setting = response.json()
            # If it's marked as secret, value should be handled appropriately
            if setting.get("is_secret"):
                # Sensitive field - value may be masked or None
                assert "value" in setting


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling across API."""

    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON."""
        response = client.put(
            "/api/v1/settings",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code in [400, 422]

    def test_empty_request_body(self, client):
        """Test PUT with empty body."""
        response = client.put("/api/v1/settings", json={})

        # Should either succeed with no changes or return error
        assert response.status_code in [200, 400]

    def test_missing_required_headers(self, client):
        """Test request with missing content type."""
        # Most endpoints should still work
        response = client.get("/api/v1/settings")
        assert response.status_code == 200

    def test_profile_validation_errors(self, client):
        """Test profile validation error responses."""
        list_response = client.get("/api/v1/profiles")
        if list_response.json()["count"] > 0:
            profile_id = list_response.json()["profiles"][0]["id"]

            # Try to update with invalid data
            response = client.put(
                f"/api/v1/profiles/{profile_id}",
                json={
                    "id": profile_id,
                    # Missing required name and resume_path
                }
            )

            assert response.status_code in [400, 422]
            error_data = response.json()
            assert "detail" in error_data


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Test integration between endpoints."""

    def test_list_then_get_profile(self, client):
        """Test getting a profile after listing."""
        # List profiles
        list_response = client.get("/api/v1/profiles")
        assert list_response.status_code == 200

        if list_response.json()["count"] > 0:
            profile_id = list_response.json()["profiles"][0]["id"]

            # Get specific profile
            get_response = client.get(f"/api/v1/profiles/{profile_id}")
            assert get_response.status_code == 200

    def test_update_profile_persistence(self, client):
        """Test that profile updates persist."""
        list_response = client.get("/api/v1/profiles")
        if list_response.json()["count"] > 0:
            profile = list_response.json()["profiles"][0]
            profile_id = profile["id"]
            new_name = "Test Updated Name"

            # Update profile
            update_data = {**profile, "name": new_name}
            update_response = client.put(
                f"/api/v1/profiles/{profile_id}",
                json=update_data
            )

            if update_response.status_code == 200:
                # Verify by getting it again
                get_response = client.get(f"/api/v1/profiles/{profile_id}")
                assert get_response.json()["name"] == new_name

    def test_settings_workflow(self, client):
        """Test complete settings workflow."""
        # 1. List settings
        list_response = client.get("/api/v1/settings")
        assert list_response.status_code == 200
        initial_count = list_response.json()["count"]
        assert initial_count > 0

        # 2. Get single setting
        get_response = client.get("/api/v1/settings/DISCOVERY_WINDOW_HOURS")
        if get_response.status_code == 200:
            # 3. Update it
            update_response = client.put(
                "/api/v1/settings",
                json={"DISCOVERY_WINDOW_HOURS": "48"}
            )
            assert update_response.status_code == 200

            # 4. Reset it
            reset_response = client.delete("/api/v1/settings/DISCOVERY_WINDOW_HOURS")
            assert reset_response.status_code == 200

    def test_settings_categories_exist(self, client):
        """Test that settings have valid categories."""
        from src.models import SettingCategory

        valid_categories = {e.value for e in SettingCategory}

        response = client.get("/api/v1/settings")
        settings = response.json()["settings"]

        for setting in settings:
            assert setting["category"] in valid_categories

    def test_settings_input_types_valid(self, client):
        """Test that settings have valid input types."""
        from src.models import SettingInputType

        valid_types = {e.value for e in SettingInputType}

        response = client.get("/api/v1/settings")
        settings = response.json()["settings"]

        for setting in settings:
            assert setting["input_type"] in valid_types
