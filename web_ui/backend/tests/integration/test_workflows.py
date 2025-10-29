"""Integration tests for complete job discovery → apply workflow."""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for profiles and queues."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create required subdirectories
        Path(tmpdir).mkdir(exist_ok=True)
        profiles_dir = Path(tmpdir) / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        queues_dir = Path(tmpdir) / "queues"
        queues_dir.mkdir(exist_ok=True)
        artifacts_dir = Path(tmpdir) / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        yield tmpdir


@pytest.fixture
def sample_profile():
    """Create a sample profile for testing."""
    return {
        "id": "test-profile",
        "name": "Test User",
        "email": "test@example.com",
        "resume_path": "resumes/test-resume.pdf",
        "preferred_browser": "chromium",
        "defaults": {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "+1-555-0000",
            "location": "San Francisco, CA",
            "portfolio_url": "https://example.com",
            "github_url": "https://github.com/testuser",
            "linkedin_url": "https://linkedin.com/in/testuser",
        },
        "keywords": {
            "roles": ["Frontend Engineer", "React Developer"],
            "tech_stack": ["React", "TypeScript", "Node.js"],
        },
        "experience": [
            {
                "company": "TechCorp",
                "role": "Senior Frontend Engineer",
                "dates": "2021 – Present",
                "highlights": ["Led team of 5", "Improved performance by 40%"],
                "tech_stack": ["React", "TypeScript"],
                "metrics": {"team_size": "5", "performance_improvement": "40%"},
            }
        ],
    }


class TestDiscoveryToApplyWorkflow:
    """Test complete discovery to apply workflow."""

    def test_end_to_end_workflow(self, client, sample_profile):
        """Test complete workflow: discover → apply → view results."""
        profile_id = sample_profile["id"]

        # Step 1: Create profile
        response = client.put(
            f"/api/v1/profiles/{profile_id}",
            json=sample_profile
        )
        assert response.status_code == 200
        created_profile = response.json()
        assert created_profile["name"] == sample_profile["name"]

        # Step 2: Get profile
        response = client.get(f"/api/v1/profiles/{profile_id}")
        assert response.status_code == 200
        retrieved = response.json()
        assert retrieved["id"] == profile_id

        # Step 3: Switch to profile
        response = client.post(f"/api/v1/profiles/{profile_id}/switch")
        assert response.status_code == 200
        assert response.json()["profile_id"] == profile_id

        # Step 4: Get last-used discovery options
        response = client.get(f"/api/v1/discover/last-options/{profile_id}")
        assert response.status_code == 200
        assert response.json()["operation_type"] == "discover"

        # Step 5: Execute discovery
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "profile_id": profile_id,
                "search_window": "24h",
                "job_cap": 10,
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "started"

        # Step 6: Get discovery status
        response = client.get(
            "/api/v1/discover/status",
            params={"profile_id": profile_id}
        )
        assert response.status_code == 200
        discovery_status = response.json()
        assert "status" in discovery_status

        # Step 7: List jobs in queue (should be empty at start in test)
        response = client.get(
            "/api/v1/jobs",
            params={"profile_id": profile_id}
        )
        assert response.status_code == 200
        jobs_list = response.json()
        assert "items" in jobs_list
        assert "count" in jobs_list

        # Step 8: Get queue through profile endpoint
        response = client.get(f"/api/v1/profiles/{profile_id}/queue")
        assert response.status_code == 200
        queue = response.json()
        assert queue["profile_id"] == profile_id
        assert "status_counts" in queue

    def test_apply_workflow_with_options(self, client, sample_profile):
        """Test apply workflow with persistence of options."""
        profile_id = sample_profile["id"]

        # Setup: Create and switch profile
        client.put(f"/api/v1/profiles/{profile_id}", json=sample_profile)
        client.post(f"/api/v1/profiles/{profile_id}/switch")

        # Get initial options
        response = client.get(f"/api/v1/apply/last-options/{profile_id}")
        assert response.status_code == 200
        initial_options = response.json()

        # Update settings to simulate apply configuration
        settings_updates = {
            "DISCOVERY_WINDOW_HOURS": "48",
            "DISCOVERY_CAP": "20",
        }
        response = client.put("/api/v1/settings", json=settings_updates)
        assert response.status_code == 200

        # Get updated options
        response = client.get(f"/api/v1/apply/last-options/{profile_id}")
        assert response.status_code == 200
        updated_options = response.json()

        # Verify options structure
        assert "operation_type" in updated_options
        assert "profile_id" in updated_options

    def test_settings_persistence_workflow(self, client):
        """Test settings are persisted across operations."""
        # Get initial settings
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        initial_count = response.json()["count"]

        # Update multiple settings
        updates = {
            "DISCOVERY_WINDOW_HOURS": "72",
            "DISCOVERY_CAP": "15",
        }
        response = client.put("/api/v1/settings", json=updates)
        assert response.status_code == 200

        # Get settings again - should have same count
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        final_count = response.json()["count"]
        assert final_count == initial_count

        # Get specific setting to verify update
        response = client.get("/api/v1/settings/DISCOVERY_WINDOW_HOURS")
        assert response.status_code == 200
        assert response.json()["value"] == "72"

    def test_profile_update_and_apply_workflow(self, client, sample_profile):
        """Test updating profile then applying to jobs."""
        profile_id = sample_profile["id"]

        # Create initial profile
        response = client.put(
            f"/api/v1/profiles/{profile_id}",
            json=sample_profile
        )
        assert response.status_code == 200

        # Update profile
        updated = sample_profile.copy()
        updated["name"] = "Updated Name"
        response = client.put(
            f"/api/v1/profiles/{profile_id}",
            json=updated
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

        # Verify update persisted
        response = client.get(f"/api/v1/profiles/{profile_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

        # Get discovery options (would be used before discovery)
        response = client.get(f"/api/v1/discover/last-options/{profile_id}")
        assert response.status_code == 200

        # Get apply options (would be used before apply)
        response = client.get(f"/api/v1/apply/last-options/{profile_id}")
        assert response.status_code == 200


class TestDataPersistenceWorkflow:
    """Test data persistence across operations."""

    def test_profile_persistence(self, client, sample_profile):
        """Test profile data persists correctly."""
        profile_id = sample_profile["id"]

        # Save profile
        client.put(f"/api/v1/profiles/{profile_id}", json=sample_profile)

        # Retrieve and verify
        response = client.get(f"/api/v1/profiles/{profile_id}")
        assert response.status_code == 200
        retrieved = response.json()

        # Verify all nested structures persist
        assert retrieved["defaults"]["email"] == sample_profile["defaults"]["email"]
        assert len(retrieved["experience"]) == 1
        assert retrieved["experience"][0]["company"] == "TechCorp"

    def test_settings_value_persistence(self, client):
        """Test settings values persist through updates."""
        # Set initial value
        updates = {"DISCOVERY_WINDOW_HOURS": "24"}
        response = client.put("/api/v1/settings", json=updates)
        assert response.status_code == 200

        # Retrieve and verify
        response = client.get("/api/v1/settings/DISCOVERY_WINDOW_HOURS")
        assert response.status_code == 200
        assert response.json()["value"] == "24"

        # Update to different value
        updates = {"DISCOVERY_WINDOW_HOURS": "48"}
        response = client.put("/api/v1/settings", json=updates)
        assert response.status_code == 200

        # Verify new value
        response = client.get("/api/v1/settings/DISCOVERY_WINDOW_HOURS")
        assert response.status_code == 200
        assert response.json()["value"] == "48"


class TestMultiProfileWorkflow:
    """Test workflows with multiple profiles."""

    def test_switch_between_profiles(self, client):
        """Test switching between profiles."""
        profile1 = {
            "id": "profile-1",
            "name": "User One",
            "resume_path": "resumes/one.pdf",
        }
        profile2 = {
            "id": "profile-2",
            "name": "User Two",
            "resume_path": "resumes/two.pdf",
        }

        # Create both profiles
        client.put("/api/v1/profiles/profile-1", json=profile1)
        client.put("/api/v1/profiles/profile-2", json=profile2)

        # Switch to profile 1
        response = client.post("/api/v1/profiles/profile-1/switch")
        assert response.status_code == 200
        assert response.json()["profile_id"] == "profile-1"

        # Switch to profile 2
        response = client.post("/api/v1/profiles/profile-2/switch")
        assert response.status_code == 200
        assert response.json()["profile_id"] == "profile-2"

        # Both profiles should still be readable
        response = client.get("/api/v1/profiles/profile-1")
        assert response.status_code == 200
        assert response.json()["name"] == "User One"

        response = client.get("/api/v1/profiles/profile-2")
        assert response.status_code == 200
        assert response.json()["name"] == "User Two"

    def test_list_all_profiles(self, client):
        """Test listing all profiles."""
        profile1 = {
            "id": "test-user-1",
            "name": "Test User 1",
            "resume_path": "resumes/one.pdf",
        }
        profile2 = {
            "id": "test-user-2",
            "name": "Test User 2",
            "resume_path": "resumes/two.pdf",
        }

        # Create both
        client.put("/api/v1/profiles/test-user-1", json=profile1)
        client.put("/api/v1/profiles/test-user-2", json=profile2)

        # List all
        response = client.get("/api/v1/profiles")
        assert response.status_code == 200
        profiles = response.json()["profiles"]

        # Should have at least our two profiles
        profile_ids = [p["id"] for p in profiles]
        assert "test-user-1" in profile_ids
        assert "test-user-2" in profile_ids


class TestErrorRecoveryWorkflow:
    """Test error handling and recovery in workflows."""

    def test_handle_missing_profile(self, client):
        """Test handling of missing profile in workflow."""
        # Try to access non-existent profile
        response = client.get("/api/v1/profiles/nonexistent")
        assert response.status_code == 404

        # Try to switch to non-existent profile
        response = client.post("/api/v1/profiles/nonexistent/switch")
        assert response.status_code != 200

        # Try to update non-existent profile
        response = client.put(
            "/api/v1/profiles/nonexistent",
            json={
                "id": "nonexistent",
                "name": "Test",
                "resume_path": "test.pdf",
            }
        )
        # Should succeed (create) or fail gracefully
        assert response.status_code in [200, 201, 400]

    def test_invalid_setting_error_handling(self, client):
        """Test handling of invalid settings."""
        # Try to update non-existent setting
        response = client.put(
            "/api/v1/settings",
            json={"NONEXISTENT_SETTING": "value"}
        )
        assert response.status_code == 400

        # Try to reset non-existent setting
        response = client.delete("/api/v1/settings/NONEXISTENT_SETTING")
        assert response.status_code == 400

    def test_invalid_profile_data_handling(self, client):
        """Test handling of invalid profile data."""
        # Try to save profile with missing required fields
        invalid_profile = {
            "id": "test",
            # Missing 'name' and 'resume_path'
        }
        response = client.put("/api/v1/profiles/test", json=invalid_profile)
        assert response.status_code in [400, 422]


class TestCompleteUserJourney:
    """Test a complete user journey through the application."""

    def test_user_onboarding_and_job_management(self, client, sample_profile):
        """Test user onboarding through job discovery and application."""
        profile_id = sample_profile["id"]

        # Onboarding: User creates profile
        response = client.put(
            f"/api/v1/profiles/{profile_id}",
            json=sample_profile
        )
        assert response.status_code == 200

        # Profile setup: Get settings for customization
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        assert response.json()["count"] > 0

        # User customizes settings
        response = client.put(
            "/api/v1/settings",
            json={
                "DISCOVERY_WINDOW_HOURS": "24",
                "DISCOVERY_CAP": "10",
            }
        )
        assert response.status_code == 200

        # User activates profile
        response = client.post(f"/api/v1/profiles/{profile_id}/switch")
        assert response.status_code == 200

        # User prepares for discovery
        response = client.get(f"/api/v1/discover/last-options/{profile_id}")
        assert response.status_code == 200

        # User initiates discovery
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "profile_id": profile_id,
                "search_window": "24h",
            }
        )
        assert response.status_code == 200

        # User checks job queue
        response = client.get(f"/api/v1/profiles/{profile_id}/queue")
        assert response.status_code == 200
        queue_info = response.json()
        assert "status_counts" in queue_info
        assert queue_info["profile_id"] == profile_id

        # User prepares for application
        response = client.get(f"/api/v1/apply/last-options/{profile_id}")
        assert response.status_code == 200

        # User retrieves settings for final review
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
