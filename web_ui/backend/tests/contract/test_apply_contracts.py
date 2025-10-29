"""Contract tests for Apply API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.app import app


class TestApplyContracts:
    """Contract tests for Apply API endpoints."""

    @pytest.fixture(autouse=True)
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_apply_single_request_schema(self, client):
        """Test POST /apply/single accepts correct schema."""
        response = client.post(
            "/api/v1/apply/single",
            params={
                "profile_id": "test_profile",
                "job_id": "job_123",
                "mode": "supervised",
            },
        )
        assert response.status_code == 200

    def test_apply_single_response_schema(self, client):
        """Test POST /apply/single returns correct response schema."""
        response = client.post(
            "/api/v1/apply/single",
            params={
                "profile_id": "test_profile",
                "job_id": "job_123",
                "mode": "supervised",
            },
        )
        data = response.json()

        # Validate response structure
        assert "status" in data
        assert "profile_id" in data
        assert "job_id" in data
        assert "message" in data

        # Validate field types
        assert isinstance(data["status"], str)
        assert isinstance(data["profile_id"], str)
        assert isinstance(data["job_id"], str)
        assert isinstance(data["message"], str)

    def test_apply_single_with_all_options(self, client):
        """Test POST /apply/single accepts all option parameters."""
        response = client.post(
            "/api/v1/apply/single",
            params={
                "profile_id": "test_profile",
                "job_id": "job_123",
                "mode": "supervised",
                "review_mode": "true",
                "use_llm_locator": "true",
                "debug_resume_widget": "true",
                "resume_wait_timeout": 30,
                "audit_after_submit": "true",
                "save_logs": "true",
                "logs_dir": "/path/to/logs",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"

    def test_apply_single_missing_profile_id(self, client):
        """Test POST /apply/single fails without profile_id."""
        response = client.post(
            "/api/v1/apply/single",
            params={
                "job_id": "job_123",
                "mode": "supervised",
            },
        )
        # Should fail due to missing profile_id
        assert response.status_code in [400, 422]

    def test_apply_single_missing_job_id(self, client):
        """Test POST /apply/single fails without job_id."""
        response = client.post(
            "/api/v1/apply/single",
            params={
                "profile_id": "test_profile",
                "mode": "supervised",
            },
        )
        # Should fail due to missing job_id
        assert response.status_code in [400, 422]

    def test_apply_bulk_request_schema(self, client):
        """Test POST /apply/bulk accepts correct schema."""
        response = client.post(
            "/api/v1/apply/bulk",
            params={
                "profile_id": "test_profile",
                "mode": "supervised",
            },
        )
        assert response.status_code == 200

    def test_apply_bulk_response_schema(self, client):
        """Test POST /apply/bulk returns correct response schema."""
        response = client.post(
            "/api/v1/apply/bulk",
            params={
                "profile_id": "test_profile",
                "mode": "supervised",
            },
        )
        data = response.json()

        # Validate response structure
        assert "status" in data
        assert "profile_id" in data
        assert "message" in data

        # Validate field types
        assert isinstance(data["status"], str)
        assert isinstance(data["profile_id"], str)
        assert isinstance(data["message"], str)

    def test_apply_bulk_with_options(self, client):
        """Test POST /apply/bulk accepts all option parameters."""
        response = client.post(
            "/api/v1/apply/bulk",
            params={
                "profile_id": "test_profile",
                "mode": "supervised",
                "max_concurrent": 5,
                "stop_on_failure": "true",
                "review_mode": "true",
                "save_logs": "true",
                "logs_dir": "/path/to/logs",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_apply_bulk_missing_profile_id(self, client):
        """Test POST /apply/bulk fails without profile_id."""
        response = client.post(
            "/api/v1/apply/bulk",
            params={
                "mode": "supervised",
            },
        )
        # Should fail due to missing profile_id
        assert response.status_code in [400, 422]

    def test_apply_status_schema(self, client):
        """Test GET /apply/status/{job_id} returns correct schema."""
        response = client.get(
            "/api/v1/apply/status/job_123",
            params={"profile_id": "test_profile"},
        )
        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "job_id" in data
        assert "status" in data

        # Validate field types
        assert isinstance(data["job_id"], str)
        assert isinstance(data["status"], str)

    def test_apply_status_with_confirmation(self, client):
        """Test GET /apply/status returns confirmation details when submitted."""
        response = client.get(
            "/api/v1/apply/status/job_123",
            params={"profile_id": "test_profile"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should have optional confirmation fields if submitted
        if data["status"] == "submitted":
            assert "confirmation_id" in data or "confirmation_text" in data

    def test_apply_logs_schema(self, client):
        """Test GET /apply/logs/{job_id} returns correct schema."""
        response = client.get(
            "/api/v1/apply/logs/job_123",
            params={"profile_id": "test_profile"},
        )
        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "job_id" in data
        assert "logs" in data or "message" in data

        # Validate field types
        assert isinstance(data["job_id"], str)

    def test_apply_last_options_schema(self, client):
        """Test GET /apply/last-options/{profile_id} returns correct schema."""
        response = client.get(
            "/api/v1/apply/last-options/test_profile",
        )
        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "profile_id" in data
        assert "single_apply" in data
        assert "bulk_apply" in data

        # Validate single_apply structure
        single = data["single_apply"]
        assert "mode" in single
        assert isinstance(single["mode"], str)

        # Validate bulk_apply structure
        bulk = data["bulk_apply"]
        assert "mode" in bulk
        assert isinstance(bulk["mode"], str)

    def test_apply_endpoints_return_json(self, client):
        """Test all apply endpoints return JSON content type."""
        # POST /apply/single
        response = client.post(
            "/api/v1/apply/single",
            params={
                "profile_id": "test_profile",
                "job_id": "job_123",
                "mode": "supervised",
            },
        )
        assert "application/json" in response.headers["content-type"]

        # POST /apply/bulk
        response = client.post(
            "/api/v1/apply/bulk",
            params={
                "profile_id": "test_profile",
                "mode": "supervised",
            },
        )
        assert "application/json" in response.headers["content-type"]

        # GET /apply/status
        response = client.get(
            "/api/v1/apply/status/job_123",
            params={"profile_id": "test_profile"},
        )
        assert "application/json" in response.headers["content-type"]

        # GET /apply/logs
        response = client.get(
            "/api/v1/apply/logs/job_123",
            params={"profile_id": "test_profile"},
        )
        assert "application/json" in response.headers["content-type"]

        # GET /apply/last-options
        response = client.get(
            "/api/v1/apply/last-options/test_profile",
        )
        assert "application/json" in response.headers["content-type"]

    def test_apply_endpoints_error_responses(self, client):
        """Test apply endpoints return proper error responses."""
        # Missing required parameter should fail
        response = client.post(
            "/api/v1/apply/single",
            params={
                "job_id": "job_123",
                # Missing profile_id
            },
        )
        assert response.status_code != 200
        data = response.json()
        # Error response should have detail or error field
        assert "detail" in data or "error" in data

    def test_apply_modes_enumeration(self, client):
        """Test apply endpoints accept valid mode values."""
        # Supervised mode
        response = client.post(
            "/api/v1/apply/single",
            params={
                "profile_id": "test_profile",
                "job_id": "job_123",
                "mode": "supervised",
            },
        )
        assert response.status_code == 200

        # Automated mode
        response = client.post(
            "/api/v1/apply/single",
            params={
                "profile_id": "test_profile",
                "job_id": "job_123",
                "mode": "automated",
            },
        )
        assert response.status_code == 200

    def test_apply_resume_timeout_validation(self, client):
        """Test apply endpoints validate resume timeout range."""
        # Valid timeout
        response = client.post(
            "/api/v1/apply/single",
            params={
                "profile_id": "test_profile",
                "job_id": "job_123",
                "resume_wait_timeout": 25,
            },
        )
        assert response.status_code == 200

        # Max timeout
        response = client.post(
            "/api/v1/apply/single",
            params={
                "profile_id": "test_profile",
                "job_id": "job_123",
                "resume_wait_timeout": 120,
            },
        )
        assert response.status_code == 200

    def test_apply_max_concurrent_validation(self, client):
        """Test apply bulk endpoint validates max concurrent range."""
        # Valid max concurrent
        response = client.post(
            "/api/v1/apply/bulk",
            params={
                "profile_id": "test_profile",
                "max_concurrent": 5,
            },
        )
        assert response.status_code == 200

        # Max concurrent at limit
        response = client.post(
            "/api/v1/apply/bulk",
            params={
                "profile_id": "test_profile",
                "max_concurrent": 10,
            },
        )
        assert response.status_code == 200
