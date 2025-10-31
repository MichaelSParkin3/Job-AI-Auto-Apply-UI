"""CLI service for executing auto-apply commands."""

import subprocess
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from src.models import RunConfiguration
from src.utils import FileOpsError


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

        async for event in self._execute_streaming(cmd):
            yield event

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

        async for event in self._execute_streaming(cmd):
            yield event

    async def _execute_streaming(
        self,
        cmd: List[str],
        timeout: int = 3600,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute command and stream JSON output."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

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
                            yield data
                        except json.JSONDecodeError:
                            # Skip non-JSON lines
                            continue
                except asyncio.TimeoutError:
                    process.kill()
                    raise FileOpsError("CLI command timeout")

            # Wait for process to finish
            await process.wait()

        except Exception as e:
            raise FileOpsError(f"CLI execution failed: {e}")
