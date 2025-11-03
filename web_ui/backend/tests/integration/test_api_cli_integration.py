"""Integration tests for API endpoints with real CLI subprocess execution."""

import pytest


class TestDiscoveryAPIWithCLI:
    """Test discover API endpoint properly invokes CLI subprocess."""

    def test_discover_endpoint_returns_success_response(self, client):
        """Verify /discover/execute API returns successful response."""

        response = client.post(
            "/api/v1/discover/execute",
            json={
                "profile_id": "michael_scott_parkin_iii",
                "search_window": "24h",
                "job_cap": 5,
            },
        )

        # API should return 200 regardless of results
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()

        # Verify response structure
        assert "status" in data, "Response should have 'status' field"
        assert data["status"] == "completed", f"Expected 'completed', got '{data['status']}'"
        assert "total_discovered" in data, "Response should have 'total_discovered'"
        assert "total_enqueued" in data, "Response should have 'total_enqueued'"
        assert "profile_id" in data, "Response should have 'profile_id'"

    def test_discover_endpoint_handles_no_results_gracefully(self, client):
        """Verify endpoint handles CLI exit code 2 (no results) as success."""

        # Use very narrow time window to likely get 0 results
        response = client.post(
            "/api/v1/discover/execute",
            json={
                "profile_id": "michael_scott_parkin_iii",
                "search_window": "1h",  # Very narrow window
                "job_cap": 1,
            },
        )

        # Should NOT error on no results
        assert response.status_code == 200, f"Got {response.status_code}: {response.text}"
        data = response.json()

        # 0 results is valid - no error expected
        assert data["status"] == "completed"
        assert isinstance(data["total_discovered"], int)
        assert data["total_discovered"] >= 0

    def test_discover_endpoint_missing_profile_returns_error(self, client):
        """Verify endpoint handles missing profile gracefully."""

        # Omit required profile_id
        response = client.post(
            "/api/v1/discover/execute",
            json={
                "search_window": "24h",
                "job_cap": 5,
            },
        )

        # Should return validation error (400 or 422)
        assert response.status_code in [400, 422], f"Got {response.status_code}"


class TestApplyAPIWithCLI:
    """Test apply API endpoint properly invokes CLI subprocess."""

    def test_apply_bulk_endpoint_returns_response(self, client):
        """Verify /apply/bulk API returns response without crashing."""

        response = client.post(
            "/api/v1/apply/bulk",
            params={
                "profile_id": "michael_scott_parkin_iii",
                "mode": "supervised",
            },
        )

        # API should respond (may be 200 if jobs exist, or other status)
        # But should NOT be 500 (internal server error)
        assert response.status_code != 500, f"Got server error: {response.text}"
        assert response.status_code in [200, 400, 503], f"Got {response.status_code}"

        if response.status_code == 200:
            data = response.json()
            # Verify response structure when successful
            assert "status" in data
            assert "profile_id" in data

    def test_apply_bulk_missing_profile_returns_error(self, client):
        """Verify endpoint handles missing profile gracefully."""

        # Omit required profile_id
        response = client.post(
            "/api/v1/apply/bulk",
        )

        # Should return validation error (400 or 422)
        assert response.status_code in [400, 422], f"Got {response.status_code}"


class TestAPIWithCLIIntegration:
    """Test complete request flow from API to CLI subprocess."""

    def test_discover_request_flow_end_to_end(self, client):
        """Verify complete flow: API request → service → CLI subprocess → response."""

        # Make valid discover request
        response = client.post(
            "/api/v1/discover/execute",
            json={
                "profile_id": "michael_scott_parkin_iii",
                "search_window": "24h",
                "job_cap": 3,
            },
        )

        # Request should complete without crashing
        assert response.status_code == 200
        data = response.json()

        # Verify response indicates subprocess ran
        assert data["status"] in ["completed", "started"]
        assert "total_discovered" in data or "message" in data

    def test_api_calls_return_json_responses(self, client):
        """Verify API endpoints return valid JSON responses."""

        response = client.post(
            "/api/v1/discover/execute",
            json={
                "profile_id": "michael_scott_parkin_iii",
                "search_window": "24h",
                "job_cap": 2,
            },
        )

        # Should be valid JSON
        try:
            data = response.json()
            assert isinstance(data, dict), "Response should be JSON object"
        except Exception as e:
            pytest.fail(f"Response is not valid JSON: {e}")
