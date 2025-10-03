"""Structured logging helpers for the auto-apply assistant."""
from __future__ import annotations

import logging
import sys
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
