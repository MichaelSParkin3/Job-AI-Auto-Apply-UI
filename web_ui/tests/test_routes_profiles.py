"""Tests for profile-related API routes."""

import pytest


@pytest.mark.asyncio
async def test_get_profiles(async_client):
    """Test GET /api/profiles returns list of profiles."""
    response = await async_client.get("/api/profiles")

    assert response.status_code == 200
    data = response.json()

    assert "profiles" in data
    assert "count" in data
    assert isinstance(data["profiles"], list)
    assert data["count"] == len(data["profiles"])


@pytest.mark.asyncio
async def test_get_profiles_structure(async_client):
    """Test profile response structure."""
    response = await async_client.get("/api/profiles")

    assert response.status_code == 200
    data = response.json()

    # Should have at least the test profile
    assert data["count"] > 0

    profile = data["profiles"][0]
    assert "id" in profile
    assert "name" in profile
    assert "resume_path" in profile
    assert "has_experience" in profile


@pytest.mark.asyncio
async def test_get_profile_by_id(async_client, test_profile_id):
    """Test GET /api/profiles/{profile_id}."""
    response = await async_client.get(f"/api/profiles/{test_profile_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == test_profile_id
    assert "name" in data
    assert "resume_path" in data


@pytest.mark.asyncio
async def test_get_profile_not_found(async_client):
    """Test GET /api/profiles/{profile_id} with non-existent profile."""
    response = await async_client.get("/api/profiles/nonexistent_profile_xyz")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_profiles_contains_test_profile(async_client, test_profile_id):
    """Test that profiles list contains the test profile."""
    response = await async_client.get("/api/profiles")

    assert response.status_code == 200
    data = response.json()

    profile_ids = [p["id"] for p in data["profiles"]]
    assert test_profile_id in profile_ids
