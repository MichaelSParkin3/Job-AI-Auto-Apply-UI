"""CLI service for executing auto-apply commands."""

import subprocess
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from src.models import RunConfiguration
from src.utils import FileOpsError
import structlog

log = structlog.get_logger(__name__)


class CLIService:
    """Service for executing CLI commands and streaming results."""

    def __init__(self, cli_command: str = "auto-apply"):
        """Initialize CLIService.

        Args:
            cli_command: Base CLI command name
        """
        self.cli_command = cli_command

    async def execute_discover(
        self,
        profile_id: str,
        search_window: Optional[str] = None,
        job_cap: Optional[int] = None,
        custom_query: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute discovery command and stream JSON events.

        Args:
            profile_id: Profile ID
            search_window: Time window (e.g., '24h')
            job_cap: Max jobs to discover
            custom_query: Custom search query

        Yields:
            JSON event dictionaries
        """
        cmd = [self.cli_command, "discover", "--profile", profile_id, "--json"]

        if search_window:
            cmd.extend(["--window", search_window])
        if job_cap:
            cmd.extend(["--cap", str(job_cap)])
        if custom_query:
            cmd.extend(["--query", custom_query])

        log.info("cli.discover.start", profile_id=profile_id, window=search_window, cap=job_cap, query=custom_query)
        async for event in self._execute_streaming(cmd):
            yield event
        log.info("cli.discover.end", profile_id=profile_id)

    async def execute_apply_single(
        self,
        profile_id: str,
        job_id: str,
        review_mode: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute apply command for single job."""
        cmd = [
            self.cli_command,
            "apply",
            "--profile", profile_id,
            "--id", job_id,
            "--json",
        ]

        if review_mode:
            cmd.append("--review-mode")

        async for event in self._execute_streaming(cmd):
            yield event

    async def execute_apply_bulk(
        self,
        profile_id: str,
        supervised: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute apply command for bulk applications."""
        cmd = [self.cli_command, "apply", "--profile", profile_id, "--json"]

        if supervised:
            cmd.append("--supervised")

        log.info("cli.apply.bulk.start", profile_id=profile_id, supervised=supervised)
        async for event in self._execute_streaming(cmd):
            yield event
        log.info("cli.apply.bulk.end", profile_id=profile_id)

    async def _execute_streaming(
        self,
        cmd: List[str],
        timeout: int = 3600,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute command and stream JSON output."""
        import os
        from pathlib import Path

        # Ensure CLI can find profiles directory by setting env var
        # The CLI runs from backend dir, so we need absolute path to project root
        env = os.environ.copy()
        backend_dir = Path(__file__).parent.parent.parent.parent
        profiles_dir = (backend_dir / ".." / "profiles").resolve()
        env["AUTO_APPLY_PROFILES_DIR"] = str(profiles_dir)

        # Set CWD to project root so CLI writes to correct queue/artifacts locations
        project_root = backend_dir.parent

        log.info(
            "cli.subprocess.starting",
            cmd=" ".join(cmd),
            cwd=str(project_root),
            profiles_dir=str(profiles_dir),
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(project_root),
            )

            log.info("cli.subprocess.created", pid=process.pid)

            event_count = 0
            while True:
                try:
                    # Read with timeout
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=timeout,
                    )

                    if not line:
                        break

                    line_str = line.decode().strip()
                    if line_str:
                        try:
                            data = json.loads(line_str)
                            event_count += 1
                            event_type = data.get("type", "unknown")
                            log.debug(
                                "cli.subprocess.event",
                                event_type=event_type,
                                event_num=event_count,
                                data=data,
                            )
                            yield data
                        except json.JSONDecodeError:
                            # Log non-JSON output
                            log.warning("cli.subprocess.non_json_output", line=line_str)
                            continue
                except asyncio.TimeoutError:
                    process.kill()
                    log.error("cli.subprocess.timeout", timeout_seconds=timeout)
                    raise FileOpsError("CLI command timeout")

            # CRITICAL: Read stderr before waiting for process to avoid deadlock
            # and capture all error output
            stderr_data = await process.stderr.read()
            if stderr_data:
                stderr_str = stderr_data.decode()
                log.error("cli.subprocess.stderr", stderr=stderr_str)

            # Wait for process to finish and get exit code
            exit_code = await process.wait()
            log.info(
                "cli.subprocess.finished",
                exit_code=exit_code,
                pid=process.pid,
                total_events=event_count,
            )

            # Raise error if process exited with non-zero code
            if exit_code != 0:
                raise FileOpsError(
                    f"CLI command failed with exit code {exit_code}. "
                    f"Produced {event_count} events. See logs for stderr output."
                )

        except FileOpsError:
            raise
        except Exception as e:
            log.error("cli.subprocess.exception", error=str(e), exc_type=type(e).__name__)
            raise FileOpsError(f"CLI execution failed: {e}")
