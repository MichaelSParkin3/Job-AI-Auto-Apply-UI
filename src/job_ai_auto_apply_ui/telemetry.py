"""Structured logging helpers for the auto-apply assistant."""
from __future__ import annotations

import logging
import sys

import structlog

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    stream=sys.stderr,
)

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


def log_event(event: str, **fields: object) -> None:
    """Emit a structured event."""
    _logger.info(event, **fields)


def bind_timeline(step: str, **fields: object):
    """Create a bound logger for a specific step."""
    return _logger.bind(step=step, **fields)
