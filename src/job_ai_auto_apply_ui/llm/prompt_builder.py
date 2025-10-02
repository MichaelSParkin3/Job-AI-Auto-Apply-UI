"""Prompt construction utilities for Lever auto-apply flows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ..application_queue import JobDetails
from ..profile_manager import Profile


@dataclass(slots=True)
class Question:
    """Represents a dynamic form question."""

    id: str
    text: str
    required: bool


@dataclass(slots=True)
class PromptPlan:
    """Structured prompt ready for LLM invocation."""

    cache_key: str
    messages: list[dict[str, str]]


class PromptBuilder:
    """Compose prompts that combine profile context and job details."""

    def __init__(
        self,
        profile: Profile,
        cache: Mapping[str, str] | None = None,
        provider: str | None = None,
    ) -> None:
        """Store profile context and optional cache settings."""
        self.profile = profile
        self._cache = cache or {}
        self.provider = provider

    def build_question_prompt(
        self,
        *,
        question: Question,
        job: JobDetails,
        extra_context: Iterable[str] | None = None,
    ) -> PromptPlan:
        """Create a prompt payload for a dynamic question."""
        cache_key = self._normalize_question_key(question.text)
        if cache_key in self._cache:
            return PromptPlan(
                cache_key=cache_key,
                messages=[
                    {
                        "role": "system",
                        "content": "Cached answer available; reuse without calling the LLM.",
                    },
                    {"role": "assistant", "content": self._cache[cache_key]},
                ],
            )

        system_content = (
            "You are a helpful assistant drafting concise, professional responses "
            "for job application forms."
        )
        if self.provider:
            system_content += f" Target provider: {self.provider}."
        user_sections = [
            f"Question: {question.text}",
            _format_profile(self.profile),
            _format_job(job),
        ]
        if extra_context:
            user_sections.extend(extra_context)
        if question.required:
            user_sections.append("This question is required; provide a confident answer.")

        user_content = "\n\n".join(section for section in user_sections if section)
        return PromptPlan(
            cache_key=cache_key,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )

    @staticmethod
    def _normalize_question_key(text: str) -> str:
        return " ".join(text.lower().split())


def _format_profile(profile: Profile) -> str:
    defaults = "\n".join(f"- {key}: {value}" for key, value in profile.defaults.items())
    keywords: list[str] = []
    for values in profile.keywords.values():
        keywords.extend(values)
    keywords_line = ", ".join(sorted(set(keywords)))
    prompts = "\n".join(f"- {key}: {value}" for key, value in profile.prompts.items())
    sections = [f"Profile: {profile.name}"]
    if defaults:
        sections.append("Defaults:\n" + defaults)
    if keywords_line:
        sections.append("Keywords: " + keywords_line)
    if prompts:
        sections.append("Prompt notes:\n" + prompts)
    return "\n\n".join(sections)


def _format_job(job: JobDetails) -> str:
    pieces = []
    if job.posting_excerpt:
        pieces.append("Posting excerpt:\n" + job.posting_excerpt)
    meta_parts = []
    if job.location:
        meta_parts.append(f"Location: {job.location}")
    if job.department:
        meta_parts.append(f"Department: {job.department}")
    if job.work_model:
        meta_parts.append(f"Work model: {job.work_model}")
    if job.employment_type:
        meta_parts.append(f"Employment type: {job.employment_type}")
    if meta_parts:
        pieces.append("; ".join(meta_parts))
    return "\n\n".join(pieces)
