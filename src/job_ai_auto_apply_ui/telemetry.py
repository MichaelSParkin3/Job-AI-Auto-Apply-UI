"""Structured logging helpers for the auto-apply assistant."""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    import structlog
except ImportError:  # pragma: no cover - fallback
    structlog = None

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    stream=sys.stderr,
)

_file_log_path: Path | None = None

if structlog is not None:
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    _logger = structlog.stdlib.get_logger("auto_apply")

    def log_event(event: str, **fields: Any) -> None:
        """Emit a structured event using structlog when available."""

        _logger.info(event, **fields)

    def bind_timeline(step: str, **fields: Any):
        """Create a bound logger for a specific step."""

        return _logger.bind(step=step, **fields)

else:
    _logger = logging.getLogger("auto_apply")

    class _BoundTimeline:
        def __init__(self, logger: logging.Logger, step: str, fields: dict[str, Any]) -> None:
            self._logger = logger
            self._fields = {"step": step, **fields}

        def info(self, event: str, **fields: Any) -> None:
            merged = {**self._fields, **fields}
            self._logger.info("%s %s", event, merged)

        def warning(self, event: str, **fields: Any) -> None:
            merged = {**self._fields, **fields}
            self._logger.warning("%s %s", event, merged)

    def log_event(event: str, **fields: Any) -> None:
        """Fallback logging that emits human-readable key/value output."""

        _logger.info("%s %s", event, fields)

    def bind_timeline(step: str, **fields: Any):
        """Return a lightweight logger with bound context when structlog is absent."""

        return _BoundTimeline(_logger, step, fields)


def configure_file_logging(log_dir: str | Path, profile_id: str) -> Path | None:
    """Configure file-based logging to save structured logs to disk.

    Args:
        log_dir: Directory where log files should be saved (e.g., "logs/")
        profile_id: Profile identifier to include in filename

    Returns:
        Path: Path to the created log file, or None if configuration failed

    """
    global _file_log_path
    try:
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)

        # Create timestamped filename: profile_id_YYYY-MM-DDTHH-MM-SS.jsonl
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        log_filename = f"{profile_id}_{timestamp}.jsonl"
        log_file_path = log_dir_path / log_filename

        # Add file handler to Python's standard logging
        file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(message)s"))

        # Get the root logger that structlog writes to
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        _file_log_path = log_file_path
        return log_file_path
    except Exception:
        return None


def get_log_file_path() -> Path | None:
    """Return the path to the current log file, if file logging is enabled.

    Returns:
        Path | None: Path to log file, or None if file logging not configured

    """
    return _file_log_path
