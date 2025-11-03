"""Tests for discover-related API routes."""

import pytest


@pytest.mark.asyncio
async def test_discover_with_valid_profile(async_client, test_profile_id):
    """Test discover endpoint with valid profile."""
    response = await async_client.post(
        "/api/discover",
        json={
            "profile_id": test_profile_id,
            "window": "24h",
            "cap": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["profile_id"] == test_profile_id
    assert "Discover started" in data["message"]


@pytest.mark.asyncio
async def test_discover_with_invalid_profile(async_client):
    """Test discover endpoint with non-existent profile."""
    response = await async_client.post(
        "/api/discover",
        json={
            "profile_id": "nonexistent_profile_xyz",
            "window": "24h",
            "cap": 10,
        },
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_discover_validation_cap_too_high(async_client, test_profile_id):
    """Test discover request validation for cap exceeding maximum."""
    response = await async_client.post(
        "/api/discover",
        json={
            "profile_id": test_profile_id,
            "cap": 200,  # Exceeds max of 100
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_discover_validation_cap_too_low(async_client, test_profile_id):
    """Test discover request validation for cap below minimum."""
    response = await async_client.post(
        "/api/discover",
        json={
            "profile_id": test_profile_id,
            "cap": 0,  # Below minimum of 1
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_discover_response_structure(async_client, test_profile_id):
    """Test discover response has correct structure."""
    response = await async_client.post(
        "/api/discover",
        json={
            "profile_id": test_profile_id,
            "window": "24h",
            "cap": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert "success" in data
    assert "items_discovered" in data
    assert "message" in data
    assert "profile_id" in data


@pytest.mark.asyncio
async def test_discover_with_different_windows(async_client, test_profile_id):
    """Test discover with different window values."""
    windows = ["24h", "7d", "1w", "1m"]

    for window in windows:
        response = await async_client.post(
            "/api/discover",
            json={
                "profile_id": test_profile_id,
                "window": window,
                "cap": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert window in data["message"]
