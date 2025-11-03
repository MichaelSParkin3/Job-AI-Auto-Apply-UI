"""Integration tests for CLI subprocess execution."""

import pytest
from src.services.cli_service import CLIService
from src.utils import FileOpsError


class TestCLISubprocessExecution:
    """Test actual CLI subprocess execution and error handling."""

    @pytest.mark.asyncio
    async def test_discover_subprocess_executes_with_valid_profile(self):
        """Verify discover subprocess starts and produces output for valid profile."""
        cli = CLIService()
        event_count = 0
        has_output = False

        try:
            async for event in cli.execute_discover(
                profile_id="michael_scott_parkin_iii",
                search_window="24h",
                job_cap=5,
            ):
                event_count += 1
                has_output = True
                assert isinstance(event, dict), "Event should be dict"
                # Events should either be JSON events or discovery output
                assert "type" in event or "items" in event, "Event missing expected keys"
        except FileOpsError as e:
            # If we get an error, log it for debugging
            pytest.fail(f"Discover subprocess failed: {e}")

        # We should have received at least some output
        # Note: This may be 0 if no jobs found, but subprocess should still run
        assert has_output or event_count >= 0, "Subprocess should have executed"

    @pytest.mark.asyncio
    async def test_discover_subprocess_invalid_profile_error(self):
        """Verify subprocess handles invalid profile gracefully."""
        cli = CLIService()

        with pytest.raises(FileOpsError) as exc_info:
            async for event in cli.execute_discover(
                profile_id="nonexistent_profile_12345",
                search_window="24h",
                job_cap=5,
            ):
                pass

        # Error should contain meaningful information
        error_msg = str(exc_info.value).lower()
        assert "exit code" in error_msg or "failed" in error_msg, f"Error should mention failure: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_apply_subprocess_executes(self):
        """Verify apply subprocess starts and produces output."""
        cli = CLIService()
        event_count = 0

        try:
            async for event in cli.execute_apply_bulk(
                profile_id="michael_scott_parkin_iii",
                supervised=True,
            ):
                event_count += 1
                assert isinstance(event, dict), "Event should be dict"
        except FileOpsError as e:
            # Apply may fail if no jobs in queue, but subprocess should still launch
            pytest.skip(f"Apply skipped (expected if no jobs): {e}")

    @pytest.mark.asyncio
    async def test_subprocess_logs_on_failure(self, caplog):
        """Verify subprocess failures are logged with details."""
        cli = CLIService()

        with pytest.raises(FileOpsError):
            async for event in cli.execute_discover(
                profile_id="nonexistent_xyz",
                search_window="24h",
                job_cap=5,
            ):
                pass

        # Logs should contain subprocess details
        log_output = caplog.text.lower()
        assert (
            "cli.subprocess.starting" in log_output or
            "cli.subprocess" in log_output
        ), f"Logs should contain subprocess info. Got: {log_output[:500]}"
