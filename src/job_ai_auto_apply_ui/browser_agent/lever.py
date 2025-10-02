"""Utilities for analyzing Lever forms and configuring browser sessions."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final
from xml.etree import ElementTree as ET

from ..application_queue import ApplicationItem, Artifacts
from ..config import Settings, load_settings
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


@dataclass(slots=True)
class LeverBrowserOptions:
    """Options controlling diagnostics capture and domain safety for sessions."""

    allowed_domains: tuple[str, ...]
    capture_video: bool = False
    capture_har: bool = False
    artifacts_dir: Path = Path("data") / "artifacts" / "browser"

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        *,
        profile: Profile | None = None,
    ) -> "LeverBrowserOptions":
        """Create options using project settings and optional profile context.

        Args:
            settings: Optional configuration instance. When ``None`` the
                settings are loaded from the environment.
            profile: Profile whose identifier namespaces the artifacts folder.

        Returns:
            LeverBrowserOptions: Diagnostics and domain configuration values.

        """
        resolved_settings = settings or load_settings()
        allowed = tuple(
            domain.strip()
            for domain in resolved_settings.allowed_domains
            if domain and domain.strip()
        )
        artifacts_root = Path(resolved_settings.artifacts_root)
        if profile is not None:
            artifacts_root = artifacts_root / profile.id
        capture_video = bool(
            resolved_settings.diagnostics_enabled
            or resolved_settings.diagnostics_capture_video
        )
        capture_har = bool(
            resolved_settings.diagnostics_enabled
            or resolved_settings.diagnostics_capture_har
        )
        return cls(
            allowed_domains=allowed,
            capture_video=capture_video,
            capture_har=capture_har,
            artifacts_dir=artifacts_root,
        )

    def to_browser_use_kwargs(self) -> dict[str, object]:
        """Return keyword arguments for ``browser_use`` session factories.

        Returns:
            dict[str, object]: Keyword arguments compatible with browser-use
            session constructors.

        """
        kwargs: dict[str, object] = {
            "allowed_domains": list(self.allowed_domains),
            "artifacts_dir": str(self.artifacts_dir),
        }
        if self.capture_video:
            kwargs["record_video"] = True
        if self.capture_har:
            kwargs["record_har"] = True
        return kwargs


def analyze_form(html: str) -> LeverFormPlan:
    """Inspect Lever HTML and extract the selectors we care about.

    Args:
        html: Raw HTML content from a Lever application form.

    Returns:
        LeverFormPlan: Parsed selectors and metadata required for automation.

    """
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

    def __init__(
        self,
        planner: Callable[[str], LeverFormPlan] | None = None,
        *,
        options: LeverBrowserOptions | None = None,
    ) -> None:
        """Initialise the agent with a planner function and browser options.

        Args:
            planner: Callable that transforms HTML into a :class:`LeverFormPlan`.
            options: Browser diagnostics and safety configuration.

        """
        self._planner = planner or analyze_form
        self._options = options or LeverBrowserOptions.from_settings()

    def build_plan(self, html: str) -> LeverFormPlan:
        """Return a form plan from raw HTML.

        Args:
            html: Form markup to analyse for selectors.

        Returns:
            LeverFormPlan: Parsed selectors ready for execution.

        """
        return self._planner(html)

    def submit_stub(self, *, profile: Profile, item: ApplicationItem) -> Artifacts:
        """Stub submission used until browser automation is implemented.

        Args:
            profile: Active profile responsible for the submission.
            item: Queue item currently being processed.

        Returns:
            Artifacts: Confirmation artifacts that mimic a successful submit.

        """
        if item.details and item.details.apply_url:
            ensure_allowed_domain(item.details.apply_url, self._options.allowed_domains)
        log_event("apply.stub", profile=profile.id, item=item.id)
        return Artifacts(confirmation_text="submitted (stub)")


def ensure_allowed_domain(url: str, allowed_domains: Iterable[str]) -> None:
    """Validate that ``url`` matches the configured ``allowed_domains`` pattern list.

    Args:
        url: Absolute URL that will be opened in the browser session.
        allowed_domains: Domain glob patterns that are permitted.

    Raises:
        ValueError: If the URL host is not allowed.

    """
    if not is_allowed_domain(url, allowed_domains):
        raise ValueError(f"Unsafe form domain: {url}")


def is_allowed_domain(url: str, allowed_domains: Iterable[str]) -> bool:
    """Return ``True`` when ``url`` hosts match any of the allowed domain globs.

    Args:
        url: Absolute URL evaluated for safety.
        allowed_domains: Domain glob patterns (supports ``*.example.com`` and
            ``example.*`` shorthands).

    Returns:
        bool: ``True`` when the URL host is permitted, ``False`` otherwise.

    """
    match = _ALLOWED_DOMAIN_REGEX.match(url)
    if not match:
        return False
    host = match.group("host").lower()
    for domain in allowed_domains:
        pattern = domain.lower()
        if pattern == host:
            return True
        if pattern.startswith("*."):
            suffix = pattern[1:]
            if host.endswith(suffix):
                return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            if host.startswith(prefix):
                return True
        if pattern in host:
            return True
    return False


_ALLOWED_DOMAIN_REGEX: Final[re.Pattern[str]] = re.compile(r"^https?://(?P<host>[^/]+)")


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
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(cleaned.split())
