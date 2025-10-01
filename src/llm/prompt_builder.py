"""Prompt building utilities for generating Lever application answers."""

from __future__ import annotations

import json
import textwrap
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from ..application_queue import JobDetails
from ..profile_manager import Profile

SYSTEM_PROMPT = (
    "You are an assistant drafting concise, first-person responses for Lever job application "
    "forms. Only use the provided profile resume context and job description details."
)


@dataclass(frozen=True)
class PromptRequest:
    """Inputs required to construct a long-form prompt."""

    profile: Profile
    job_title: str
    job_details: JobDetails
    question: str
    cached_answer: Optional[str] = None


def normalize_question_key(question: str) -> str:
    """Create a deterministic cache key from a long-form question."""
    normalized = unicodedata.normalize("NFKD", question).lower()
    result = []
    for char in normalized:
        if char.isalnum():
            result.append(char)
        elif result and result[-1] != "-":
            result.append("-")
    key = "".join(result).strip("-")
    return key or "question"


def build_long_form_prompt(request: PromptRequest) -> Dict[str, Any]:
    """Build a chat-completion payload for a Lever long-form question."""
    question_key = normalize_question_key(request.question)
    payload: Dict[str, Any] = {
        "question_key": question_key,
        "profile_id": request.profile.id,
        "job_title": request.job_title,
    }

    if request.cached_answer:
        payload.update({
            "from_cache": True,
            "cached_answer": request.cached_answer,
        })
        return payload

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(request)},
    ]

    payload.update(
        {
            "from_cache": False,
            "messages": messages,
            "response_schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
                "required": ["answer"],
                "additionalProperties": False,
            },
        }
    )
    return payload


def _build_user_prompt(request: PromptRequest) -> str:
    profile = request.profile
    job = request.job_details
    profile_defaults = _format_defaults(profile.defaults.items())
    profile_keywords = ", ".join(profile.keywords)
    prompt_directives = profile.prompts.get("long_form") if profile.prompts else ""

    job_context = textwrap.dedent(
        f"""
        Job Title: {request.job_title}
        Location: {job.location or 'Unknown'}
        Employment Type: {job.employment_type.value if hasattr(job.employment_type, 'value') else job.employment_type}
        Work Model: {job.work_model.value if hasattr(job.work_model, 'value') else job.work_model}
        Department: {job.department or 'Unknown'}
        Apply URL: {job.apply_url or 'Unknown'}
        Source Query: {job.source_query or 'Unknown'}
        Source Rank: {job.source_rank if job.source_rank is not None else 'Unknown'}
        """
    ).strip()

    excerpt = job.posting_excerpt or job.posting_text[:1500]
    resume_context = json.dumps(profile.defaults, ensure_ascii=False, indent=2)

    prompt = textwrap.dedent(
        f"""
        Use the following profile context and job description to answer the question in JSON with keys
        `answer` and optional `confidence` (high|medium|low). Keep the answer under 120 words and
        ensure it is first-person.

        Profile Name: {profile.name}
        Preferred Browser: {profile.preferred_browser or 'chromium'}
        Keywords: {profile_keywords or 'None'}
        Defaults:\n{profile_defaults or '  (none)'}
        Resume Defaults JSON:\n{resume_context}
        Additional Prompting Guidance: {prompt_directives or 'None'}

        Job Context:\n{job_context}

        Job Description Excerpt:\n{excerpt}

        Question: {request.question.strip()}
        """
    ).strip()
    return prompt


def _format_defaults(items: Iterable) -> str:
    lines = []
    for key, value in items:
        lines.append(f"  - {key}: {value}")
    return "\n".join(lines)
