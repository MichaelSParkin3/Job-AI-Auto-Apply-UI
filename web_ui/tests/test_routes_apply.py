"""Tests for apply-related API routes."""

import pytest


@pytest.mark.asyncio
async def test_apply_with_valid_profile(async_client, test_profile_id):
    """Test POST /api/apply with valid profile."""
    response = await async_client.post(
        "/api/apply",
        json={
            "profile_id": test_profile_id,
            "supervised": True,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "task_id" in data
    assert "message" in data
    assert "websocket_url" in data
    assert test_profile_id in data["message"]
    assert data["websocket_url"].startswith("/ws/apply/")


@pytest.mark.asyncio
async def test_apply_with_invalid_profile(async_client):
    """Test POST /api/apply with non-existent profile."""
    response = await async_client.post(
        "/api/apply",
        json={
            "profile_id": "nonexistent_profile_xyz",
            "supervised": True,
        },
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_apply_response_structure(async_client, test_profile_id):
    """Test apply response has correct structure."""
    response = await async_client.post(
        "/api/apply",
        json={
            "profile_id": test_profile_id,
            "supervised": True,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["task_id"], str)
    assert len(data["task_id"]) > 0
    assert isinstance(data["message"], str)
    assert isinstance(data["websocket_url"], str)


@pytest.mark.asyncio
async def test_apply_with_all_flags(async_client, test_profile_id):
    """Test apply with all optional flags."""
    response = await async_client.post(
        "/api/apply",
        json={
            "profile_id": test_profile_id,
            "job_id": "test_job_123",
            "supervised": False,
            "llm_provider": "openrouter",
            "llm_model": "test-model",
            "use_llm_locator": True,
            "debug_resume_widget": True,
            "resume_wait_timeout_seconds": 30,
            "review_mode": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data


@pytest.mark.asyncio
async def test_apply_defaults(async_client, test_profile_id):
    """Test apply uses correct defaults when flags not specified."""
    response = await async_client.post(
        "/api/apply",
        json={
            "profile_id": test_profile_id,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
