"""Unit tests for answer cache functionality."""

import json
import re
import tempfile
from pathlib import Path

import pytest

from job_ai_auto_apply_ui.llm.prompt_builder import PromptBuilder
from job_ai_auto_apply_ui.profile_manager import Profile


def _normalize_question_key(text: str) -> str:
    """Normalize question text into a consistent cache key (matches PromptBuilder._normalize_question_key)."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(cleaned.split())


def test_cache_key_normalization_removes_punctuation() -> None:
    """Test that normalization removes punctuation and lowercases text."""
    result = _normalize_question_key("Why do you want this role?")
    assert result == "why do you want this role"


def test_cache_key_normalization_handles_special_chars() -> None:
    """Test normalization with various special characters."""
    result = _normalize_question_key("Why, do you want this role!!!")
    assert result == "why do you want this role"


def test_cache_key_normalization_collapses_whitespace() -> None:
    """Test that multiple spaces are collapsed to single spaces."""
    result = _normalize_question_key("Why   do   you   want?")
    assert result == "why do you want"


def test_cache_key_normalization_is_idempotent() -> None:
    """Test that normalizing twice gives same result as once."""
    key1 = _normalize_question_key("Why do you want this role?")
    key2 = _normalize_question_key(key1)
    assert key1 == key2


def test_prompt_builder_with_cache_hit() -> None:
    """Test that PromptBuilder uses cached answer when available."""
    profile = Profile(
        id="test",
        name="Test User",
        resume_path=Path("resume.pdf"),
        defaults={"name": "Test"},
        keywords={"roles": ["Engineer"]},
        prompts={"cover_letter": "Test cover letter"},
    )

    cache = {"why react": "Because it's performant and scalable"}
    builder = PromptBuilder(profile=profile, cache=cache)

    # Verify the cache is stored
    assert builder._cache == cache
    assert "why react" in builder._cache


def test_prompt_builder_cache_empty_by_default() -> None:
    """Test that PromptBuilder starts with empty cache if none provided."""
    profile = Profile(
        id="test",
        name="Test User",
        resume_path=Path("resume.pdf"),
        defaults={"name": "Test"},
        keywords={"roles": ["Engineer"]},
        prompts={"cover_letter": "Test cover letter"},
    )

    builder = PromptBuilder(profile=profile)
    assert builder._cache == {}


def test_build_cache_mapping_from_pre_json() -> None:
    """Test building a cache mapping from pre.json structure."""
    # Create a mock pre.json structure
    pre_json_data = {
        "version": 1,
        "plan": {
            "dynamic_questions": [
                {
                    "prompt": "Why do you want this role?",
                    "answer_selector": "cards[abc123][field0]",
                    "field_type": "textarea",
                },
                {
                    "prompt": "Tell us about your experience",
                    "answer_selector": "cards[def456][field1]",
                    "field_type": "textarea",
                },
                {
                    "prompt": "What is your expected salary?",
                    "field_name": "input[name='salary']",
                    "field_type": "text",
                },
            ]
        },
        "values": {
            "textarea[name='cards[abc123][field0]']": "I'm excited about this role because...",
            "textarea[name='cards[def456][field1]']": "Over 5 years of experience with React",
            "input[name='salary']": "130000",
        },
    }

    # Build cache mapping
    answer_cache = {}
    for q in pre_json_data["plan"]["dynamic_questions"]:
        prompt_text = q.get("prompt", "")
        answer_selector = q.get("answer_selector")
        field_name = q.get("field_name")

        if not prompt_text:
            continue

        # Normalize question text
        normalized_key = _normalize_question_key(prompt_text)

        # Find matching value
        selector_to_match = answer_selector or field_name
        if selector_to_match:
            for value_key, value in pre_json_data["values"].items():
                if selector_to_match in value_key:
                    answer_cache[normalized_key] = value
                    break

    # Verify the cache was built correctly
    assert len(answer_cache) == 3
    assert (
        answer_cache["why do you want this role"]
        == "I'm excited about this role because..."
    )
    assert (
        answer_cache["tell us about your experience"]
        == "Over 5 years of experience with React"
    )
    assert answer_cache["what is your expected salary"] == "130000"


def test_cache_loading_from_pre_json_file() -> None:
    """Test loading cache from an actual pre.json file."""
    pre_json_data = {
        "version": 1,
        "plan": {
            "dynamic_questions": [
                {
                    "prompt": "Why do you want this role?",
                    "answer_selector": "cards[xyz789][field0]",
                }
            ]
        },
        "values": {
            "textarea[name='cards[xyz789][field0]']": "Test answer for the question"
        },
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(pre_json_data, f)
        temp_path = f.name

    try:
        # Load and build cache
        with open(temp_path, "r", encoding="utf-8-sig") as f:
            saved_state = json.load(f)

        plan = saved_state.get("plan", {})
        values = saved_state.get("values", {})

        answer_cache = {}
        for q in plan.get("dynamic_questions", []):
            prompt_text = q.get("prompt", "")
            answer_selector = q.get("answer_selector")

            if not prompt_text or not answer_selector:
                continue

            normalized_key = _normalize_question_key(prompt_text)

            for value_key, value in values.items():
                if answer_selector in value_key:
                    answer_cache[normalized_key] = value
                    break

        assert answer_cache["why do you want this role"] == "Test answer for the question"
    finally:
        Path(temp_path).unlink()


def test_cache_handles_missing_prompt() -> None:
    """Test that cache building skips questions without prompt text."""
    pre_json_data = {
        "plan": {
            "dynamic_questions": [
                {
                    "prompt": "",  # Empty prompt
                    "answer_selector": "cards[abc][field0]",
                },
                {
                    "prompt": "Valid question",
                    "answer_selector": "cards[def][field1]",
                },
            ]
        },
        "values": {
            "textarea[name='cards[def][field1]']": "Valid answer",
        },
    }

    answer_cache = {}
    for q in pre_json_data["plan"]["dynamic_questions"]:
        prompt_text = q.get("prompt", "")
        answer_selector = q.get("answer_selector")

        if not prompt_text or not answer_selector:
            continue

        normalized_key = _normalize_question_key(prompt_text)
        for value_key, value in pre_json_data["values"].items():
            if answer_selector in value_key:
                answer_cache[normalized_key] = value
                break

    assert len(answer_cache) == 1
    assert answer_cache["valid question"] == "Valid answer"


def test_cache_handles_missing_values() -> None:
    """Test that cache building gracefully handles missing values."""
    pre_json_data = {
        "plan": {
            "dynamic_questions": [
                {
                    "prompt": "Question without matching value",
                    "answer_selector": "nonexistent_selector",
                }
            ]
        },
        "values": {
            "textarea[name='cards[abc][field0]']": "Some value",
        },
    }

    answer_cache = {}
    for q in pre_json_data["plan"]["dynamic_questions"]:
        prompt_text = q.get("prompt", "")
        answer_selector = q.get("answer_selector")

        if not prompt_text or not answer_selector:
            continue

        normalized_key = _normalize_question_key(prompt_text)
        for value_key, value in pre_json_data["values"].items():
            if answer_selector in value_key:
                answer_cache[normalized_key] = value
                break

    # Cache should be empty since selector wasn't found
    assert len(answer_cache) == 0


def test_cache_prefers_answer_selector_over_field_name() -> None:
    """Test that answer_selector is checked before field_name for matching."""
    pre_json_data = {
        "plan": {
            "dynamic_questions": [
                {
                    "prompt": "Test question",
                    "answer_selector": "cards[primary][field0]",
                    "field_name": "cards[backup][field1]",
                }
            ]
        },
        "values": {
            "textarea[name='cards[primary][field0]']": "Primary answer",
            "textarea[name='cards[backup][field1]']": "Backup answer",
        },
    }

    answer_cache = {}
    for q in pre_json_data["plan"]["dynamic_questions"]:
        prompt_text = q.get("prompt", "")
        answer_selector = q.get("answer_selector")
        field_name = q.get("field_name")

        if not prompt_text:
            continue

        normalized_key = _normalize_question_key(prompt_text)
        selector_to_match = answer_selector or field_name

        if selector_to_match:
            for value_key, value in pre_json_data["values"].items():
                if selector_to_match in value_key:
                    answer_cache[normalized_key] = value
                    break

    # Should use primary answer since answer_selector is checked first
    assert answer_cache["test question"] == "Primary answer"
