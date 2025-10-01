"""Integration tests for Lever form selector discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.browser_agent import lever


@pytest.fixture()
def lever_form_html() -> str:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "lever_form.html"
    return fixture_path.read_text(encoding="utf-8")


def test_extract_form_blueprint_maps_core_inputs(lever_form_html: str) -> None:
    """Blueprint includes resume upload, contact inputs, and links."""
    blueprint = lever.extract_form_blueprint(lever_form_html)

    assert blueprint["form"] == "form#application-form"
    assert blueprint["resume_input"] == "input#resume-upload-input[name='resume']"
    assert blueprint["contact_fields"]["name"] == "input[data-qa='name-input'][name='name']"
    assert blueprint["contact_fields"]["email"] == "input[data-qa='email-input'][name='email']"
    assert blueprint["contact_fields"]["phone"] == "input[data-qa='phone-input'][name='phone']"
    assert blueprint["location_field"] == "input#location-input.location-input"
    assert blueprint["link_fields"]["linkedin"] == "input[name=\"urls[LinkedIn]\"]"
    assert blueprint["link_fields"]["github"] == "input[name=\"urls[GitHub (If applicable)]\"]"
    assert blueprint["link_fields"]["portfolio"] == "input[name=\"urls[Portfolio (If applicable)]\"]"


def test_extract_form_blueprint_parses_long_form_questions(
    lever_form_html: str,
) -> None:
    """Blueprint exposes long-form question metadata and hCaptcha flag."""
    blueprint = lever.extract_form_blueprint(lever_form_html)

    assert blueprint["long_form_questions"] == [
        {"text": "Why?", "required": True, "input_name": "cards[abc][field0]"}
    ]
    assert blueprint["hcaptcha_present"] is True
