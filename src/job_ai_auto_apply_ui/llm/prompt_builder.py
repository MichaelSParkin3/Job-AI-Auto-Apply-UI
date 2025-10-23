"""Prompt composition utilities for Lever dynamic questions."""

from __future__ import annotations

import re
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
        """Store profile context and optional cache settings.

        Args:
            profile: Active profile whose defaults, keywords, and prompts prime the
                generated messages.
            cache: Optional cache mapping normalized question text to prepared
                answers that can bypass the LLM.
            provider: Optional provider name appended to the system prompt for
                auditing purposes.
        """
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
        """Create a prompt payload for a dynamic question.

        Args:
            question: Question metadata extracted from the Lever form.
            job: Structured job details that enrich the generated prompt.
            extra_context: Optional bullet points appended to the user message.

        Returns:
            PromptPlan: Plan describing cache key and chat messages to send.
        """
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
            "You are filling out a job application form on behalf of a candidate. "
            "Your goal is to provide suitable, professional answers that allow the "
            "application to proceed. Answer each question thoughtfully based on the "
            "profile information provided. For location/geography questions, use the "
            "profile's location. "
            "IMPORTANT: For multiple choice or select dropdown questions with a list of options, "
            "you MUST respond with ONLY the exact text of ONE option from the provided list. "
            "Do not add explanations, elaborations, or additional context—just the option "
            "text itself. For open-ended text questions, keep responses concise (2-3 sentences "
            "unless more detail is clearly needed)."
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
            user_sections.append(
                "This question is required. Provide an appropriate answer that allows "
                "the application to proceed. Do not decline or explain why you cannot answer."
            )

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
        """Normalize question text into a consistent cache key."""

        cleaned = re.sub(r"[^\w\s]", "", text.lower())
        return " ".join(cleaned.split())


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

    # Add experience data if available
    if profile.experience:
        experience_lines: list[str] = []
        for exp in profile.experience:
            company = exp.get("company", "Unknown")
            role = exp.get("role", "")
            dates = exp.get("dates", "")
            role_line = f"{company}"
            if role:
                role_line += f" - {role}"
            if dates:
                role_line += f" ({dates})"
            experience_lines.append(role_line)

            highlights = exp.get("highlights")
            if highlights and isinstance(highlights, list):
                for highlight in highlights:
                    experience_lines.append(f"  • {highlight}")

            tech_stack = exp.get("tech_stack")
            if tech_stack and isinstance(tech_stack, list):
                tech_line = ", ".join(str(t) for t in tech_stack)
                experience_lines.append(f"  Tech: {tech_line}")

            metrics = exp.get("metrics")
            if metrics and isinstance(metrics, dict):
                metric_strs = [f"{k}={v}" for k, v in metrics.items()]
                experience_lines.append(f"  Metrics: {', '.join(metric_strs)}")

            experience_lines.append("")  # Blank line between experiences

        if experience_lines:
            sections.append("Professional Experience:\n" + "\n".join(experience_lines).rstrip())

    if prompts:
        sections.append("Guidance:\n" + prompts)
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
