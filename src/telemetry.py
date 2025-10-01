"""Structured logging helpers for the auto-apply assistant."""
from __future__ import annotations

import logging

import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

_logger = structlog.get_logger("auto_apply")


def log_event(event: str, **fields: object) -> None:
    """Emit a structured event."""
    _logger.info(event, **fields)


def bind_timeline(step: str, **fields: object):
    """Create a bound logger for a specific step."""
    return _logger.bind(step=step, **fields)
