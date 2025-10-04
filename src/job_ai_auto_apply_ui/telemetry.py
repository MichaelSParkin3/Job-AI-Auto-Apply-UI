"""Structured logging helpers for the auto-apply assistant."""
from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, Sequence
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


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(val) for key, val in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_normalize_value(item) for item in value]
    return value


def _normalize_fields(fields: Mapping[str, Any] | dict[str, Any]) -> dict[str, Any]:
    base = dict(fields)
    return {str(key): _normalize_value(value) for key, value in base.items()}


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

        payload = _normalize_fields(fields)
        _logger.info(event, **payload)

    def bind_timeline(step: str, **fields: Any):
        """Create a bound logger for a specific step."""

        payload = _normalize_fields({"step": step, **fields})
        return _logger.bind(**payload)

else:
    _logger = logging.getLogger("auto_apply")

    class _BoundTimeline:
        def __init__(self, logger: logging.Logger, step: str, fields: dict[str, Any]) -> None:
            self._logger = logger
            self._fields = _normalize_fields({"step": step, **fields})

        def info(self, event: str, **fields: Any) -> None:
            merged = {**self._fields, **_normalize_fields(fields)}
            self._logger.info("%s %s", event, merged)

        def warning(self, event: str, **fields: Any) -> None:
            merged = {**self._fields, **_normalize_fields(fields)}
            self._logger.warning("%s %s", event, merged)

    def log_event(event: str, **fields: Any) -> None:
        """Fallback logging that emits human-readable key/value output."""

        _logger.info("%s %s", event, _normalize_fields(fields))

    def bind_timeline(step: str, **fields: Any):
        """Return a lightweight logger with bound context when structlog is absent."""

        return _BoundTimeline(_logger, step, fields)
