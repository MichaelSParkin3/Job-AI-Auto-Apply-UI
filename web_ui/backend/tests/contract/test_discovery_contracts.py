"""Contract tests for Discovery API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.app import app


class TestDiscoveryContracts:
    """Contract tests for Discovery API endpoints."""

    @pytest.fixture(autouse=True)
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_discover_execute_request_schema(self, client):
        """Test POST /discover/execute accepts correct schema."""
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "profile_id": "test_profile",
                "search_window": "24h",
                "job_cap": 10,
            },
        )
        assert response.status_code == 200

    def test_discover_execute_response_schema(self, client):
        """Test POST /discover/execute returns correct response schema."""
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "profile_id": "test_profile",
                "search_window": "24h",
                "job_cap": 10,
            },
        )
        data = response.json()

        # Validate response structure
        assert "status" in data
        assert "profile_id" in data
        assert "search_window" in data
        assert "job_cap" in data
        assert "message" in data

        # Validate field types
        assert isinstance(data["status"], str)
        assert isinstance(data["profile_id"], str)
        assert isinstance(data["search_window"], str)
        assert isinstance(data["job_cap"], int)
        assert isinstance(data["message"], str)

    def test_discover_execute_with_custom_query(self, client):
        """Test POST /discover/execute accepts custom_query parameter."""
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "profile_id": "test_profile",
                "search_window": "24h",
                "job_cap": 10,
                "custom_query": "python developer remote",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"

    def test_discover_execute_missing_profile_id(self, client):
        """Test POST /discover/execute fails without profile_id."""
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "search_window": "24h",
                "job_cap": 10,
            },
        )
        # Should fail due to missing profile_id
        assert response.status_code in [400, 422]

    def test_discover_status_schema(self, client):
        """Test GET /discover/status returns correct response schema."""
        response = client.get(
            "/api/v1/discover/status",
            params={"profile_id": "test_profile"},
        )
        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "profile_id" in data
        assert "status" in data
        assert "progress" in data
        assert "message" in data

        # Validate field types
        assert isinstance(data["profile_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["progress"], int)
        assert isinstance(data["message"], str)

        # Validate field values
        assert 0 <= data["progress"] <= 100

    def test_discover_last_options_schema(self, client):
        """Test GET /discover/last-options/{profile_id} returns correct schema."""
        response = client.get(
            "/api/v1/discover/last-options/test_profile",
        )
        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "profile_id" in data
        assert "operation_type" in data
        assert "search_window" in data
        assert "job_cap" in data
        assert "custom_query" in data

        # Validate field types
        assert isinstance(data["profile_id"], str)
        assert isinstance(data["operation_type"], str)
        assert isinstance(data["search_window"], str)
        assert isinstance(data["job_cap"], int)
        assert data["custom_query"] is None or isinstance(data["custom_query"], str)

        # Validate defaults
        assert data["search_window"] == "24h"
        assert data["job_cap"] == 10
        assert data["operation_type"] == "discover"

    def test_discover_last_options_nonexistent_profile(self, client):
        """Test GET /discover/last-options returns defaults for nonexistent profile."""
        response = client.get(
            "/api/v1/discover/last-options/nonexistent_profile_12345",
        )
        # Should return defaults, not error
        assert response.status_code == 200
        data = response.json()
        assert data["search_window"] == "24h"
        assert data["job_cap"] == 10

    def test_discover_execute_invalid_job_cap(self, client):
        """Test POST /discover/execute with invalid job_cap."""
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "profile_id": "test_profile",
                "search_window": "24h",
                "job_cap": 5000,
            },
        )
        # Should accept it (validation is frontend)
        assert response.status_code == 200

    def test_discover_execute_invalid_search_window(self, client):
        """Test POST /discover/execute with invalid search_window."""
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "profile_id": "test_profile",
                "search_window": "invalid_window",
                "job_cap": 10,
            },
        )
        # Should still execute (backend passes to CLI)
        assert response.status_code == 200

    def test_discover_endpoints_return_json(self, client):
        """Test all discovery endpoints return JSON content type."""
        # POST /discover/execute
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "profile_id": "test_profile",
                "search_window": "24h",
                "job_cap": 10,
            },
        )
        assert "application/json" in response.headers["content-type"]

        # GET /discover/status
        response = client.get(
            "/api/v1/discover/status",
            params={"profile_id": "test_profile"},
        )
        assert "application/json" in response.headers["content-type"]

        # GET /discover/last-options
        response = client.get(
            "/api/v1/discover/last-options/test_profile",
        )
        assert "application/json" in response.headers["content-type"]

    def test_discover_endpoints_error_responses(self, client):
        """Test discovery endpoints return proper error responses."""
        # Missing required parameter should fail
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "search_window": "24h",
                # Missing profile_id
            },
        )
        assert response.status_code != 200
        data = response.json()
        # Error response should have detail or error field
        assert "detail" in data or "error" in data

    def test_discover_execute_defaults(self, client):
        """Test POST /discover/execute with default parameters."""
        response = client.post(
            "/api/v1/discover/execute",
            params={
                "profile_id": "test_profile",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Should use defaults
        assert data["search_window"] == "24h"
        assert data["job_cap"] == 10

    def test_discover_status_progress_range(self, client):
        """Test that discovery status progress is in valid range."""
        response = client.get(
            "/api/v1/discover/status",
            params={"profile_id": "test_profile"},
        )
        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["progress"] <= 100

    def test_discover_last_options_job_cap_positive(self, client):
        """Test that last options returns positive job cap."""
        response = client.get(
            "/api/v1/discover/last-options/test_profile",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["job_cap"] > 0
