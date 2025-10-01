"""Lever-specific browser automation utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List

from bs4 import BeautifulSoup


@dataclass
class LongFormQuestion:
    """Minimal representation of a dynamic Lever question."""

    text: str
    required: bool
    input_name: str

    def as_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "required": self.required, "input_name": self.input_name}


def extract_form_blueprint(html: str) -> Dict[str, Any]:
    """Inspect Lever application form markup and return selector blueprint."""
    soup = BeautifulSoup(html, "html.parser")

    def require(selector: str) -> None:
        if soup.select_one(selector) is None:
            raise ValueError(f"Required selector missing: {selector}")

    blueprint: Dict[str, Any] = {
        "form": "form#application-form",
        "resume_input": "input#resume-upload-input[name='resume']",
        "contact_fields": {
            "name": "input[data-qa='name-input'][name='name']",
            "email": "input[data-qa='email-input'][name='email']",
            "phone": "input[data-qa='phone-input'][name='phone']",
        },
        "location_field": "input#location-input.location-input",
        "link_fields": {
            "linkedin": "input[name=\"urls[LinkedIn]\"]",
            "github": "input[name=\"urls[GitHub (If applicable)]\"]",
            "portfolio": "input[name=\"urls[Portfolio (If applicable)]\"]",
        },
        "long_form_questions": [],
        "hcaptcha_present": soup.select_one("div#h-captcha.h-captcha") is not None,
    }

    require(blueprint["form"])
    require(blueprint["resume_input"])
    for selector in blueprint["contact_fields"].values():
        require(selector)
    require(blueprint["location_field"])
    for selector in blueprint["link_fields"].values():
        require(selector)

    blueprint["long_form_questions"] = _parse_long_form_questions(soup)

    return blueprint


def _parse_long_form_questions(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    templates = soup.select('input[name^="cards"][name$="[baseTemplate]"]')
    answers = soup.select("textarea.card-field-input")
    questions: List[Dict[str, Any]] = []
    for index, template in enumerate(templates):
        try:
            data = json.loads(template.get("value", "{}"))
        except json.JSONDecodeError:  # pragma: no cover - fixtures should stay valid
            continue
        fields = data.get("fields", [])
        if not fields:
            continue
        field = fields[0]
        input_name = answers[index].get("name") if index < len(answers) else None
        if not input_name:
            continue
        questions.append(
            LongFormQuestion(
                text=str(field.get("text", "")).strip(),
                required=bool(field.get("required", False)),
                input_name=input_name,
            ).as_dict()
        )
    return questions
