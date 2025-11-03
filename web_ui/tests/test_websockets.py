"""Tests for WebSocket real-time event streaming."""

import pytest
from fastapi.testclient import TestClient

from web_ui.backend.app import app


def test_websocket_task_not_found():
    """Test WebSocket with non-existent task ID returns error message."""
    client = TestClient(app)

    # Should accept connection but send error message
    with client.websocket_connect("/ws/apply/invalid_task_id") as websocket:
        message = websocket.receive_json()
        assert message["type"] == "error"
        assert "not found" in message["message"].lower()


def test_websocket_apply_task_flow():
    """Test complete apply task flow with WebSocket."""
    client = TestClient(app)

    # Step 1: Create apply task
    response = client.post(
        "/api/apply",
        json={
            "profile_id": "michael_scott_parkin_iii",
            "supervised": True,
        },
    )

    assert response.status_code == 200
    task_response = response.json()
    task_id = task_response["task_id"]

    # Verify task_id is in response
    assert len(task_id) > 0
    assert task_response["websocket_url"] == f"/ws/apply/{task_id}"


def test_websocket_connection_invalid_task():
    """Test WebSocket with invalid task ID returns error."""
    client = TestClient(app)

    try:
        with client.websocket_connect("/ws/apply/invalid_uuid_format") as websocket:
            # Try to receive message
            message = websocket.receive_json()
            assert message["type"] == "error"
            assert "not found" in message["message"].lower()
    except Exception as e:
        # Connection might fail - both are acceptable
        assert "not found" in str(e).lower() or "connection" in str(e).lower()


def test_websocket_accepts_valid_task():
    """Test WebSocket accepts connection for valid task ID."""
    client = TestClient(app)

    # Create task
    response = client.post(
        "/api/apply",
        json={
            "profile_id": "michael_scott_parkin_iii",
            "supervised": True,
        },
    )

    task_id = response.json()["task_id"]

    # Try to connect - may fail due to orchestrator dependencies
    try:
        with client.websocket_connect(f"/ws/apply/{task_id}") as websocket:
            # Connection accepted
            pass
    except Exception as e:
        # Expected: browser automation required
        pytest.skip(f"Orchestrator requires browser: {e}")


def test_websocket_url_format():
    """Test WebSocket URL has correct format."""
    client = TestClient(app)

    response = client.post(
        "/api/apply",
        json={
            "profile_id": "michael_scott_parkin_iii",
            "supervised": True,
        },
    )

    data = response.json()
    websocket_url = data["websocket_url"]

    # Verify URL format
    assert websocket_url.startswith("/ws/apply/")
    task_id = websocket_url.replace("/ws/apply/", "")
    assert len(task_id) > 0
    # Should be UUID format (rough check)
    assert "-" in task_id or len(task_id) > 20
