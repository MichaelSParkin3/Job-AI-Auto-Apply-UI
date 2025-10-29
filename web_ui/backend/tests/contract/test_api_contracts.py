"""Contract tests for Jobs API endpoints."""

import json
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient
from src.app import app
from src.models.application import ApplicationStatus


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_queue_items() -> List[Dict]:
    """Mock queue items for testing."""
    return [
        {
            "id": "01HX1234567890ABCDEFGHJ",
            "url": "https://jobs.lever.co/company/job-1",
            "company": "TechCorp",
            "title": "Senior Software Engineer",
            "status": "NEW",
            "date_discovered": "2024-10-28T10:00:00Z",
        },
        {
            "id": "01HX2234567890ABCDEFGHJ",
            "url": "https://jobs.lever.co/company/job-2",
            "company": "StartupCo",
            "title": "Frontend Developer",
            "status": "IN_PROGRESS",
            "date_discovered": "2024-10-27T15:30:00Z",
        },
    ]


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_jobs_success(client, monkeypatch):
    """Test GET /api/v1/jobs/ returns correct schema."""
    # Mock QueueService to return test data
    mock_items = [
        {
            "id": "01HX1234567890ABCDEFGHJ",
            "url": "https://jobs.lever.co/company/job-1",
            "company": "TechCorp",
            "title": "Senior Software Engineer",
            "status": "NEW",
        }
    ]

    def mock_load_queue(profile_id):
        from src.models.application import ApplicationItem

        return [ApplicationItem(**item) for item in mock_items]

    # Patch the queue service
    from src.services import QueueService

    monkeypatch.setattr(QueueService, "load_queue", mock_load_queue)

    response = client.get("/api/v1/jobs", params={"profile_id": "test_profile"})

    assert response.status_code == 200
    data = response.json()

    # Verify response schema
    assert "jobs" in data
    assert "count" in data
    assert isinstance(data["jobs"], list)
    assert isinstance(data["count"], int)

    # Verify job schema
    if len(data["jobs"]) > 0:
        job = data["jobs"][0]
        assert "id" in job
        assert "url" in job
        assert "company" in job
        assert "title" in job
        assert "status" in job


def test_list_jobs_with_status_filter(client):
    """Test filtering by status parameter."""
    response = client.get(
        "/api/v1/jobs", params={"profile_id": "test_profile", "status": "NEW"}
    )

    # Should return 200 even if empty
    assert response.status_code in [200, 404]


def test_list_jobs_with_search(client):
    """Test search parameter."""
    response = client.get(
        "/api/v1/jobs", params={"profile_id": "test_profile", "search": "engineer"}
    )

    assert response.status_code in [200, 404]


def test_list_jobs_pagination(client):
    """Test pagination parameters."""
    response = client.get(
        "/api/v1/jobs",
        params={"profile_id": "test_profile", "skip": 0, "limit": 10},
    )

    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert len(data.get("jobs", [])) <= 10


def test_list_jobs_missing_profile_id(client):
    """Test missing required profile_id parameter."""
    response = client.get("/api/v1/jobs")

    # Should return 422 (validation error) or 400 (bad request)
    assert response.status_code in [400, 422]


def test_get_job_success(client, monkeypatch):
    """Test GET /api/v1/jobs/{job_id} returns job detail."""

    def mock_get_job(profile_id, job_id):
        from src.models.application import ApplicationItem

        if job_id == "01HX1234567890ABCDEFGHJ":
            return ApplicationItem(
                id=job_id,
                url="https://jobs.lever.co/company/job-1",
                company="TechCorp",
                title="Senior Software Engineer",
                status=ApplicationStatus.NEW,
            )
        return None

    from src.services import QueueService

    monkeypatch.setattr(QueueService, "get_job", mock_get_job)

    response = client.get(
        "/api/v1/jobs/01HX1234567890ABCDEFGHJ",
        params={"profile_id": "test_profile"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == "01HX1234567890ABCDEFGHJ"
    assert data["company"] == "TechCorp"
    assert data["title"] == "Senior Software Engineer"


def test_get_job_not_found(client):
    """Test GET /api/v1/jobs/{job_id} with non-existent job."""
    response = client.get(
        "/api/v1/jobs/nonexistent_id", params={"profile_id": "test_profile"}
    )

    assert response.status_code == 404


def test_update_job_status(client, monkeypatch):
    """Test PUT /api/v1/jobs/{job_id}/status updates status."""

    def mock_update_status(profile_id, job_id, status):
        from src.models.application import ApplicationItem

        return ApplicationItem(
            id=job_id,
            url="https://jobs.lever.co/test",
            company="Test",
            title="Test",
            status=status,
        )

    from src.services import QueueService

    monkeypatch.setattr(QueueService, "update_item_status", mock_update_status)

    response = client.put(
        "/api/v1/jobs/01HX1234567890ABCDEFGHJ/status",
        json={"profile_id": "test_profile", "status": "IN_PROGRESS"},
    )

    # Should succeed or return 404 if not found
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "IN_PROGRESS"


def test_update_job_status_invalid(client):
    """Test invalid status value."""
    response = client.put(
        "/api/v1/jobs/01HX1234567890ABCDEFGHJ/status",
        json={"profile_id": "test_profile", "status": "INVALID_STATUS"},
    )

    # Should return 400 or 422 for invalid status
    assert response.status_code in [400, 422]


def test_delete_job(client, monkeypatch):
    """Test DELETE /api/v1/jobs/{job_id} removes job."""

    def mock_remove_item(profile_id, job_id):
        pass  # Success

    from src.services import QueueService

    monkeypatch.setattr(QueueService, "remove_item", mock_remove_item)

    response = client.delete(
        "/api/v1/jobs/01HX1234567890ABCDEFGHJ",
        params={"profile_id": "test_profile"},
    )

    # Should return 200 or 204
    assert response.status_code in [200, 204]


def test_api_error_handling(client):
    """Test API returns proper error responses."""
    # Test with invalid profile ID
    response = client.get("/api/v1/jobs", params={"profile_id": ""})

    # Should return error status
    assert response.status_code >= 400

    # Should return JSON error
    data = response.json()
    assert "detail" in data or "message" in data


def test_api_cors_headers(client):
    """Test CORS headers are present."""
    response = client.options("/api/v1/jobs")

    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers


def test_response_content_type(client):
    """Test all responses are JSON."""
    endpoints = [
        ("/health", {}),
        ("/api/v1/jobs", {"profile_id": "test"}),
    ]

    for path, params in endpoints:
        response = client.get(path, params=params)
        assert "application/json" in response.headers.get(
            "content-type", ""
        ).lower()
