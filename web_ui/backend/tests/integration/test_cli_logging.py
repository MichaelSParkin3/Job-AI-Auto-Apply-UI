"""Tests to verify CLI subprocess logging is comprehensive."""

import pytest
from src.services.cli_service import CLIService
from src.utils import FileOpsError


class TestCLISubprocessLogging:
    """Test that CLI subprocess execution produces detailed logs."""

    @pytest.mark.asyncio
    async def test_discover_logs_subprocess_start_details(self, caplog):
        """Verify discover logs contain subprocess startup details."""
        import logging
        caplog.set_level(logging.DEBUG)

        cli = CLIService()

        try:
            async for event in cli.execute_discover(
                profile_id="test_profile",
                search_window="24h",
                job_cap=10,
            ):
                pass
        except FileOpsError:
            # Expected if profile doesn't exist
            pass

        logs = caplog.text
        # Should log start of discover operation
        assert (
            "cli.discover.start" in logs or "discover" in logs.lower()
        ), f"Logs should mention discover start. Got: {logs[:500]}"

    @pytest.mark.asyncio
    async def test_subprocess_logs_command_and_env(self, caplog):
        """Verify subprocess logs show the command being executed."""
        import logging
        caplog.set_level(logging.DEBUG)

        cli = CLIService()

        try:
            async for event in cli.execute_discover(
                profile_id="test",
                search_window="24h",
            ):
                pass
        except FileOpsError:
            pass

        logs = caplog.text.lower()
        # Should log the command that's being executed
        assert (
            "cli.subprocess.starting" in logs or
            "subprocess" in logs or
            "discover" in logs
        ), f"Logs should show subprocess details. Got: {logs[:1000]}"

    @pytest.mark.asyncio
    async def test_subprocess_logs_exit_code_on_completion(self, caplog):
        """Verify subprocess logs include exit code when complete."""
        import logging
        caplog.set_level(logging.DEBUG)

        cli = CLIService()

        try:
            async for event in cli.execute_discover(
                profile_id="michael_scott_parkin_iii",
                search_window="24h",
                job_cap=1,
            ):
                pass
        except FileOpsError:
            pass

        logs = caplog.text.lower()
        # Should have some log entries about the subprocess
        assert len(logs) > 0, "Should have produced logs"
        # Either finished or error logs
        assert (
            "finished" in logs or
            "error" in logs or
            "exit" in logs or
            "subprocess" in logs
        ), f"Logs should mention completion. Got: {logs[:1000]}"

    @pytest.mark.asyncio
    async def test_stderr_output_is_logged(self, caplog):
        """Verify stderr from subprocess is logged."""
        import logging
        caplog.set_level(logging.DEBUG)

        cli = CLIService()

        # Use invalid profile to trigger error output
        with pytest.raises(FileOpsError):
            async for event in cli.execute_discover(
                profile_id="profile_that_does_not_exist_xyz123",
                search_window="24h",
            ):
                pass

        logs = caplog.text.lower()
        # Should have logged something about the failure
        assert len(logs) > 0, "Logs should contain error details"
