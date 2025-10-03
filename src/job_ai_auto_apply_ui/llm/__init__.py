"""Lightweight LLM configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import load_settings

__all__ = ["LLMConfig", "load_llm_config"]


@dataclass(slots=True)
class LLMConfig:
    """Configuration for prompting providers."""

    provider: str | None
    model: str | None
    temperature: float
    timeout_seconds: int
    referer: str | None
    user_agent: str | None


def load_llm_config() -> LLMConfig:
    """Load LLM configuration from global settings."""
    settings = load_settings()
    return LLMConfig(
        provider=settings.llm_provider,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        timeout_seconds=settings.llm_timeout_seconds,
        referer=settings.llm_referer,
        user_agent=settings.llm_user_agent,
    )
