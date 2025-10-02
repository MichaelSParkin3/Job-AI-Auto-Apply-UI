"""Lever form parsing and automation scaffolding."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from ..application_queue import ApplicationItem, Artifacts
from ..profile_manager import Profile
from ..telemetry import log_event


@dataclass(slots=True)
class DynamicQuestion:
    """Long-form question extracted from Lever dynamic cards."""

    prompt: str
    required: bool
    answer_selector: str
    cache_key: str


@dataclass(slots=True)
class LeverFormPlan:
    """Key selectors and metadata needed to complete a Lever form."""

    resume_input: str
    contact_fields: dict[str, str]
    link_fields: dict[str, str]
    dynamic_questions: list[DynamicQuestion] = field(default_factory=list)
    submit_button: str = "button#btn-submit"
    captcha_selector: str | None = "div#h-captcha"


def analyze_form(html: str) -> LeverFormPlan:
    """Inspect Lever HTML and extract the selectors we care about."""
    sanitized = _strip_doctype(html)
    root = ET.fromstring(sanitized)

    resume_selector: str | None = None
    contact_fields: dict[str, str] = {}
    link_fields: dict[str, str] = {}
    template_specs: list[tuple[str, list[dict[str, object]]]] = []
    answer_inputs: dict[str, str] = {}
    submit_selector: str | None = None
    captcha_selector: str | None = None

    for node in root.iter():
        tag = node.tag.lower()
        attrs = {key: value for key, value in node.attrib.items()}
        if tag == "input":
            name = attrs.get("name")
            node_id = attrs.get("id")
            data_qa = attrs.get("data-qa")
            if resume_selector is None and (name == "resume" or node_id == "resume-upload-input"):
                resume_selector = _selector_for(tag, attrs)
            if data_qa == "name-input":
                contact_fields["name"] = _selector_for(tag, attrs)
            elif data_qa == "email-input":
                contact_fields["email"] = _selector_for(tag, attrs)
            elif data_qa == "phone-input":
                contact_fields["phone"] = _selector_for(tag, attrs)
            elif node_id == "location-input":
                contact_fields["location"] = _selector_for(tag, attrs)
            elif node_id == "selected-location":
                contact_fields["location_hidden"] = _selector_for(tag, attrs)

            if name and name.startswith("urls["):
                link_fields[name] = _selector_for(tag, attrs)
            if name and name.endswith("[baseTemplate]"):
                group_prefix = name.split("[baseTemplate]")[0]
                try:
                    payload = json.loads(attrs.get("value", "{}"))
                except json.JSONDecodeError:
                    continue
                fields = payload.get("fields", [])
                template_specs.append((group_prefix, fields))
        elif tag == "textarea":
            name = attrs.get("name")
            if name:
                answer_inputs[name] = _selector_for(tag, attrs)
        elif tag == "button" and attrs.get("id") == "btn-submit":
            submit_selector = _selector_for(tag, attrs)
        elif tag == "div" and attrs.get("id") == "h-captcha":
            captcha_selector = _selector_for(tag, attrs)

    if resume_selector is None:
        raise ValueError("Lever form missing resume upload input")

    dynamic_questions: list[DynamicQuestion] = []
    for group_prefix, fields in template_specs:
        for index, field_spec in enumerate(fields):
            prompt = str(field_spec.get("text", "")).strip()
            if not prompt:
                continue
            required = bool(field_spec.get("required", False))
            answer_name = f"{group_prefix}[field{index}]"
            answer_selector = answer_inputs.get(answer_name)
            if not answer_selector:
                continue
            dynamic_questions.append(
                DynamicQuestion(
                    prompt=prompt,
                    required=required,
                    answer_selector=answer_selector,
                    cache_key=_normalize_question_key(prompt),
                )
            )

    return LeverFormPlan(
        resume_input=resume_selector,
        contact_fields=contact_fields,
        link_fields=link_fields,
        dynamic_questions=dynamic_questions,
        submit_button=submit_selector or "button#btn-submit",
        captcha_selector=captcha_selector,
    )


class LeverApplyAgent:
    """High-level helper that coordinates Lever form submission.

    This is intentionally light-weight: we surface the plan and rely on
    downstream browser automation (browser-use/Playwright) to execute it.
    """

    def __init__(self, planner: Callable[[str], LeverFormPlan] | None = None) -> None:
        self._planner = planner or analyze_form

    def build_plan(self, html: str) -> LeverFormPlan:
        """Return a form plan from raw HTML."""
        return self._planner(html)

    def submit_stub(self, *, profile: Profile, item: ApplicationItem) -> Artifacts:
        """Stub submission used until browser automation is implemented."""
        log_event("apply.stub", profile=profile.id, item=item.id)
        return Artifacts(confirmation_text="submitted (stub)")


def _strip_doctype(html: str) -> str:
    return re.sub(r"<!DOCTYPE[^>]*>", "", html, flags=re.IGNORECASE).strip()


def _selector_for(tag: str, attrs: Mapping[str, str | None]) -> str:
    element_id = attrs.get("id")
    if element_id:
        return f"#{element_id}"
    name = attrs.get("name")
    if name:
        return f"{tag}[name='{name}']"
    data_qa = attrs.get("data-qa")
    if data_qa:
        return f"{tag}[data-qa='{data_qa}']"
    classes = attrs.get("class")
    if classes:
        first = classes.split()[0]
        return f"{tag}.{first}"
    return tag


def _normalize_question_key(text: str) -> str:
    return " ".join(text.lower().split())
