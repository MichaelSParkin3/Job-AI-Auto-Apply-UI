"""Utilities for analyzing Lever forms and configuring browser sessions."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Final
from xml.etree import ElementTree as ET

from browser_use.browser.session import BrowserSession

from ..application_queue import ApplicationItem, Artifacts, JobDetails, Reason
from ..config import Settings, load_settings
from ..llm.openrouter_client import OpenRouterClient, OpenRouterError
from ..llm.prompt_builder import PromptBuilder, Question
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
    """Options controlling diagnostics capture, domain allow-list, and stealth."""

    allowed_domains: tuple[str, ...]
    capture_video: bool = False
    capture_har: bool = False
    artifacts_dir: Path = Path("data") / "artifacts" / "browser"
    locale: str = "en-US"
    timezone: str = "America/Los_Angeles"
    viewport_width: int = 1280
    viewport_height: int = 800
    disable_default_extensions: bool = True

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
            locale=str(resolved_settings.browser_locale or "en-US"),
            timezone=str(resolved_settings.browser_timezone or "America/Los_Angeles"),
            viewport_width=int(getattr(resolved_settings, "browser_viewport_width", 1280)),
            viewport_height=int(getattr(resolved_settings, "browser_viewport_height", 800)),
            disable_default_extensions=bool(getattr(resolved_settings, "disable_default_extensions", True)),
        )

    def to_browser_use_kwargs(self) -> dict[str, object]:
        """Return only BrowserSession-supported kwargs.

        Note: The upstream BrowserSession in this project does not accept
        env/headers/args/window_size/artifacts_dir. We limit to allowed_domains
        and record_* flags that have been supported historically.
        """
        return {"allowed_domains": list(self.allowed_domains)}

    def apply_stealth_environment(self) -> None:
        """Apply locale/timezone to process env before launching the browser.

        While BrowserSession here does not expose header/args hooks, aligning
        TZ/LANG/LC_ALL still improves JS-observable environment consistency.
        """
        try:
            import os as _os
            _os.environ["TZ"] = str(self.timezone)
            # Normalize locale for POSIX-style env
            loc = self.locale.replace("-", "_")
            if "." not in loc:
                loc = f"{loc}.UTF-8"
            _os.environ["LANG"] = loc
            _os.environ["LC_ALL"] = loc
            try:
                log_event(
                    "browser.stealth_config",
                    locale=self.locale,
                    timezone=self.timezone,
                    window_size={"width": self.viewport_width, "height": self.viewport_height},
                    disable_default_extensions=self.disable_default_extensions,
                    allowed_domains=list(self.allowed_domains),
                )
            except Exception:
                pass
        except Exception:
            pass


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

    This is intentionally light-weight: we surface the plan and can
    execute it using a browser-use session. In supervised mode we will
    pause before submission.
    """

    def __init__(
        self,
        planner: Callable[[str], LeverFormPlan] | None = None,
        *,
        options: LeverBrowserOptions | None = None,
    ) -> None:
        """Create an agent with an optional planner and browser options."""
        self._planner = planner or analyze_form
        self._options = options or LeverBrowserOptions.from_settings()

    def build_plan(self, html: str) -> LeverFormPlan:
        """Return a Lever form plan from cached HTML analysis."""
        return self._planner(html)


    async def build_plan_in_browser(self, page) -> dict[str, object]:
        """Inspect the live DOM and return a Step1-compliant deterministic plan."""

        payload = await page.evaluate(
            """
            () => {
              const toArray = (value) => Array.from(value || []);
              const dedupe = (items) => Array.from(new Set((items || []).filter(Boolean)));
              const escapeAttr = (value) => String(value).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
              const escapeText = (value) => String(value).replace(/"/g, '\\"');
              const labelText = (el) => {
                if (!el) return "";
                const id = el.id || "";
                if (id) {
                  const direct = document.querySelector(`label[for='${escapeAttr(id)}']`);
                  if (direct && direct.textContent) {
                    return direct.textContent.trim();
                  }
                }
                const closest = el.closest('.application-question');
                if (closest) {
                  const textNode = closest.querySelector('.application-label .text, .application-label');
                  if (textNode && textNode.textContent) {
                    return textNode.textContent.trim();
                  }
                }
                const aria = el.getAttribute('aria-label');
                if (aria) return aria.trim();
                return '';
              };
              const computeNth = (el) => {
                if (!el || !el.parentElement) return null;
                const tag = el.tagName.toLowerCase();
                let index = 1;
                let prev = el.previousElementSibling;
                while (prev) {
                  if (prev.tagName.toLowerCase() === tag) {
                    index += 1;
                  }
                  prev = prev.previousElementSibling;
                }
                return `${tag}:nth-of-type(${index})`;
              };
              const buildSelectorMeta = (el, kind) => {
                const defaults = {
                  primary: null,
                  alternates: [],
                  precedence:
                    kind === 'file'
                      ? ['id', 'data-qa', 'name', 'role', 'text', 'nth']
                      : kind === 'button'
                      ? ['id', 'data-qa', 'text', 'name', 'nth']
                      : ['name', 'id', 'data-qa', 'aria', 'text', 'nth'],
                };
                if (!el) return defaults;
                const tag = el.tagName.toLowerCase();
                const typeAttr = (el.getAttribute('type') || '').toLowerCase();
                const attrs = {
                  id: el.id || '',
                  name: el.getAttribute('name') || '',
                  'data-qa': el.getAttribute('data-qa') || '',
                  aria: el.getAttribute('aria-label') || labelText(el) || '',
                  role: el.getAttribute('role') || '',
                  text: labelText(el) || '',
                  nth: computeNth(el) || '',
                };
                const primaryOrder =
                  kind === 'file'
                    ? ['id', 'name', 'data-qa']
                    : kind === 'button'
                    ? ['id', 'data-qa', 'text', 'name']
                    : ['name', 'data-qa', 'id'];
                let primary = null;
                let primaryAttr = null;
                for (const key of primaryOrder) {
                  const value = attrs[key];
                  if (!value) continue;
                  if (key === 'id') {
                    primary = `#${escapeAttr(value)}`;
                  } else if (key === 'name') {
                    const typeSuffix = kind === 'file' && typeAttr ? `[type='${escapeAttr(typeAttr)}']` : '';
                    primary = `${tag}${typeSuffix}[name='${escapeAttr(value)}']`;
                    if (kind !== 'file' && attrs['data-qa']) {
                      primary += `[data-qa='${escapeAttr(attrs['data-qa'])}']`;
                    }
                  } else if (key === 'data-qa') {
                    primary = `${tag}[data-qa='${escapeAttr(value)}']`;
                  } else if (key === 'text') {
                    primary = `${tag}:has-text("${escapeText(value)}")`;
                  }
                  primaryAttr = key;
                  break;
                }
                if (!primary && attrs.id) {
                  primary = `#${escapeAttr(attrs.id)}`;
                  primaryAttr = 'id';
                }
                if (!primary) {
                  primary = tag;
                }
                const alternates = [];
                for (const key of defaults.precedence) {
                  if (key === primaryAttr) continue;
                  const value = attrs[key];
                  if (!value) continue;
                  let selector = null;
                  if (key === 'id') {
                    selector = `#${escapeAttr(value)}`;
                  } else if (key === 'name') {
                    const typeSuffix = kind === 'file' && typeAttr ? `[type='${escapeAttr(typeAttr)}']` : '';
                    selector = `${tag}${typeSuffix}[name='${escapeAttr(value)}']`;
                  } else if (key === 'data-qa') {
                    selector = `${tag}[data-qa='${escapeAttr(value)}']`;
                  } else if (key === 'aria') {
                    selector = `${tag}[aria-label='${escapeAttr(value)}']`;
                  } else if (key === 'role') {
                    selector = `${tag}[role='${escapeAttr(value)}']`;
                  } else if (key === 'text') {
                    selector = `${tag}:has-text("${escapeText(value)}")`;
                  } else if (key === 'nth') {
                    selector = attrs.nth;
                  }
                  if (selector) {
                    alternates.push(selector);
                  }
                }
                return {
                  primary,
                  alternates: dedupe(alternates),
                  precedence: defaults.precedence,
                };
              };

              const resumeInput = document.querySelector(
                "input#resume-upload-input, input[data-qa='input-resume'], input[type='file'][name='resume']"
              );
              const resumeMeta = buildSelectorMeta(resumeInput, 'file');
              const resumeTriggers = dedupe([
                resumeInput && resumeInput.id ? `label[for='${escapeAttr(resumeInput.id)}']` : null,
                "button[data-qa='input-resume']",
              ]);
              const resumeSuccessSignals = dedupe([
                '.resume-upload-success',
                '.application-upload-success',
                '.filename:not(.hidden)',
              ]);
              const resumeFailureSignals = dedupe([
                '.resume-upload-failure',
                '.resume-upload-oversize',
              ]);
              const resumeStorage = (() => {
                const el = document.querySelector("input[name='resumeStorageId']");
                if (!el) return null;
                const tag = el.tagName.toLowerCase();
                const id = el.id ? `#${escapeAttr(el.id)}` : '';
                const name = el.name ? `[name='${escapeAttr(el.name)}']` : '';
                return `${tag}${id}${name}`;
              })();

              const fields = [];
              const pushField = (el) => {
                if (!el) return;
                const tag = el.tagName.toLowerCase();
                const typeAttr = (el.getAttribute('type') || tag).toLowerCase();
                if (typeAttr === 'hidden') return;
                const selectorMeta = buildSelectorMeta(el, tag === 'button' ? 'button' : tag === 'textarea' ? 'textarea' : 'input');
                const name = el.getAttribute('name') || el.id || '';
                const entry = {
                  name,
                  label: labelText(el),
                  type: typeAttr,
                  required: !!el.required,
                  selectorMeta,
                };
                const pattern = el.getAttribute('pattern');
                if (pattern) entry.pattern = pattern;
                if (typeAttr === 'textarea') {
                  entry.longForm = { prompt: labelText(el), required: !!el.required };
                }
                if (name === 'location') {
                  const hidden = document.querySelector("input#selected-location[name='selectedLocation']");
                  if (hidden) {
                    const tagHidden = hidden.tagName.toLowerCase();
                    const selector = `${tagHidden}${hidden.id ? `#${escapeAttr(hidden.id)}` : ''}${hidden.name ? `[name='${escapeAttr(hidden.name)}']` : ''}`;
                    entry.aux = { selectedLocationHidden: selector };
                  }
                }
                fields.push(entry);
              };

              toArray(document.querySelectorAll("form#application-form input, form#application-form textarea, form#application-form select"))
                .forEach(pushField);

              const submitButton = document.querySelector('form#application-form button[type="submit"], button#btn-submit');

              return {
                meta: {
                  formRoot: 'form#application-form, #application',
                  captchaSelector: '.h-captcha, .g-recaptcha',
                  requiresLocationGate: !!document.querySelector("input#selected-location[name='selectedLocation']"),
                  eeoRoot: '.eeo-survey, #eeo-survey',
                },
                widgets: {
                  resume: {
                    input: resumeMeta,
                    triggers: resumeTriggers,
                    successSignals: resumeSuccessSignals,
                    failureSignals: resumeFailureSignals,
                    storageField: resumeStorage,
                  },
                },
                fields,
                submit: {
                  selector: buildSelectorMeta(submitButton, 'button'),
                  triggers: dedupe(['button[type="submit"]']),
                },
              };
            }
            """
        )

        if payload is None:
            payload = {}
        elif not isinstance(payload, Mapping):
            try:
                payload = json.loads(json.dumps(payload))
            except Exception:
                payload = {}

        try:
            plan = json.loads(json.dumps(payload))
        except Exception:
            plan = {}

        plan.setdefault("meta", {})
        plan.setdefault("widgets", {})
        plan.setdefault("fields", [])
        plan.setdefault("submit", {})
        return plan


def _selector_meta_from_selector(selector: str | None) -> dict[str, object]:
    base_precedence = ["name", "id", "data-qa", "aria", "text", "nth"]
    if not selector:
        return {"primary": None, "alternates": [], "precedence": base_precedence}
    return {"primary": selector, "alternates": [], "precedence": base_precedence}


def _resolve_selector(meta: Mapping[str, object] | object) -> str | None:
    if isinstance(meta, Mapping):
        candidate = meta.get("primary")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    if isinstance(meta, str) and meta.strip():
        return meta.strip()
    return None


def _selector_candidates(meta: Mapping[str, object] | object) -> list[str]:
    primary = _resolve_selector(meta)
    alternates: list[str] = []
    if isinstance(meta, Mapping):
        raw_alts = meta.get("alternates")
        if isinstance(raw_alts, Iterable) and not isinstance(raw_alts, (str, bytes)):
            alternates = [str(val) for val in raw_alts if isinstance(val, str) and val.strip()]
    candidates = [primary] if primary else []
    candidates.extend(alternates)
    seen: list[str] = []
    for value in candidates:
        if value and value not in seen:
            seen.append(value)
    return seen


def _plan_field_maps(plan: Mapping[str, object]) -> tuple[dict[str, str], dict[str, str], list[DynamicQuestion]]:
    contact_fields: dict[str, str] = {}
    link_fields: dict[str, str] = {}
    dynamic_questions: list[DynamicQuestion] = []
    fields = plan.get("fields") if isinstance(plan, Mapping) else None
    if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes)):
        for field in fields:
            if not isinstance(field, Mapping):
                continue
            name = str(field.get("name") or "").strip()
            selector = _resolve_selector(field.get("selectorMeta"))
            if not selector:
                continue
            field_type = str(field.get("type") or "").lower()
            if name in {"name", "email", "phone", "location"}:
                contact_fields[name] = selector
                aux = field.get("aux")
                if isinstance(aux, Mapping):
                    hidden = aux.get("selectedLocationHidden")
                    if isinstance(hidden, str) and hidden.strip():
                        contact_fields["location_hidden"] = hidden.strip()
            if name.startswith("urls["):
                link_fields[name] = selector
            long_form = field.get("longForm") if isinstance(field.get("longForm"), Mapping) else None
            label = str(field.get("label") or name)
            if long_form is not None or field_type == "textarea":
                prompt = str((long_form or {}).get("prompt") or label or name)
                required = bool((long_form or {}).get("required") or field.get("required"))
                dynamic_questions.append(
                    DynamicQuestion(
                        prompt=prompt,
                        required=required,
                        answer_selector=selector,
                        cache_key=_normalize_question_key(prompt),
                    )
                )
    return contact_fields, link_fields, dynamic_questions


def _coerce_step1_plan(plan: object) -> dict[str, object]:
    if isinstance(plan, Mapping):
        return plan  # Already Step1 structured
    if isinstance(plan, LeverFormPlan):
        contact_hidden = plan.contact_fields.get("location_hidden")
        fields: list[dict[str, object]] = []
        for name, selector in plan.contact_fields.items():
            if name == "location_hidden":
                continue
            meta = _selector_meta_from_selector(selector)
            entry: dict[str, object] = {
                "name": name,
                "label": name.replace("_", " ").title(),
                "type": "input",
                "required": name in {"name", "email"},
                "selectorMeta": meta,
            }
            if name == "location" and contact_hidden:
                entry["aux"] = {"selectedLocationHidden": contact_hidden}
            fields.append(entry)
        for name, selector in plan.link_fields.items():
            fields.append(
                {
                    "name": name,
                    "label": name,
                    "type": "input",
                    "required": False,
                    "selectorMeta": _selector_meta_from_selector(selector),
                }
            )
        for question in plan.dynamic_questions:
            fields.append(
                {
                    "name": question.cache_key,
                    "label": question.prompt,
                    "type": "textarea",
                    "required": question.required,
                    "selectorMeta": _selector_meta_from_selector(question.answer_selector),
                    "longForm": {"prompt": question.prompt, "required": question.required},
                }
            )
        resume_meta = _selector_meta_from_selector(plan.resume_input)
        resume_meta["precedence"] = ["id", "data-qa", "name", "role", "text", "nth"]
        submit_meta = _selector_meta_from_selector(plan.submit_button)
        submit_meta["precedence"] = ["id", "data-qa", "text", "name", "nth"]
        return {
            "meta": {
                "formRoot": "form#application-form, #application",
                "captchaSelector": plan.captcha_selector or ".h-captcha, .g-recaptcha",
                "requiresLocationGate": bool(contact_hidden),
                "eeoRoot": ".eeo-survey, #eeo-survey",
            },
            "widgets": {
                "resume": {
                    "input": resume_meta,
                    "triggers": [],
                    "successSignals": [],
                    "failureSignals": [],
                    "storageField": None,
                }
            },
            "fields": fields,
            "submit": {"selector": submit_meta},
        }
    return {"meta": {}, "widgets": {}, "fields": [], "submit": {}}

    async def execute_in_browser(
        self,
        *,
        session: BrowserSession,
        profile: Profile,
        item: ApplicationItem,
        mode: str,
    ) -> Artifacts | Reason:
        """Open the apply URL in the given session, fill, and submit.

        Returns:
            Artifacts on success or Reason on failure.
        """
        apply_url = (item.details.apply_url if item.details and item.details.apply_url else item.url)
        ensure_allowed_domain(apply_url, self._options.allowed_domains)

        page = await session.new_page()
        # Robust navigate: event-bus -> CDP -> page.goto, with verification + logs
        await _robust_navigate(session, page, apply_url)
        # Re-focus active page in case navigation opened or switched tabs
        try:
            current = await getattr(session, "get_current_page")()  # type: ignore[attr-defined]
            if current is not None and current is not page:
                page = current
                try:
                    log_event("apply.page_focus.changed", reason="post_navigate")
                    await _close_stray_about_blank_tabs(session)
                except Exception:
                    pass
        except Exception:
            pass
        # Wait for form root (captcha may be present in DOM but hidden; do not bail yet)
        await _wait_for_any(page, ["form#application-form", "#application"])  # removed presence-only captcha wait
        try:
            state = await _hcaptcha_state(page)
            if state.get("present") and not state.get("visible"):
                log_event("captcha.present", visible=False)
            elif state.get("visible"):
                log_event("captcha.present", visible=True)
        except Exception:
            pass

        raw_plan = await self.build_plan_in_browser(page)
        plan = _coerce_step1_plan(raw_plan)
        resume_widget = plan.get("widgets", {}).get("resume", {}) if isinstance(plan, Mapping) else {}
        resume_input_meta = resume_widget.get("input") if isinstance(resume_widget, Mapping) else {}
        submit_meta = plan.get("submit", {}).get("selector", {}) if isinstance(plan, Mapping) else {}
        submit_selector = _resolve_selector(submit_meta) or "button#btn-submit"

        contact_fields, link_fields, dynamic_questions = (
            _plan_field_maps(plan if isinstance(plan, Mapping) else {})
        )

        location_input_selector = contact_fields.get("location") or "#location-input"
        location_hidden_selector = contact_fields.get("location_hidden") or "#selected-location"

        await _set_structured_location(
            page,
            input_selector=location_input_selector,
            hidden_selector=location_hidden_selector,
            value=profile.defaults.get("location"),
        )

        if (
            isinstance(plan, Mapping)
            and plan.get("meta", {}).get("requiresLocationGate")
            and location_hidden_selector
        ):
            ok, gate_state = await validate_location_gate(
                page,
                input_selector=location_input_selector,
                hidden_selector=location_hidden_selector,
            )
            if not ok:
                return Reason(
                    code="location_gate_blocked",
                    message="Location must be selected from suggestions before continuing",
                )

        resume_path = str(profile.resolve_resume_path())
        uploaded = await _upload_resume(session, page, resume_widget, resume_path)
        if not uploaded:
            try:
                if await _wait_for_resume_upload(page, resume_widget, timeout=1.0):
                    uploaded = True
            except Exception:
                pass

        if not uploaded and mode != "auto":
            print(
                "Resume upload not detected. Please attach manually in the browser, then press Enter…"
            )
            try:
                input()
            except Exception:
                pass
            uploaded = await _wait_for_resume_upload(page, resume_widget, timeout=10.0)

        if not uploaded:
            try:
                if await _wait_for_resume_upload(page, resume_widget, timeout=1.0):
                    uploaded = True
            except Exception:
                pass

        if not uploaded:
            return Reason(code="resume_upload_failed", message="Resume not attached")

        await _fill_if_available(
            page,
            contact_fields.get("name"),
            profile.defaults.get("name") or profile.name,
        )
        await _fill_if_available(page, contact_fields.get("email"), profile.defaults.get("email"))
        await _fill_if_available(page, contact_fields.get("phone"), profile.defaults.get("phone"))
        # Current company/org
        await _fill_if_available(
            page,
            # detect common selector directly if planner didn't capture it
            contact_fields.get("org") or "input[data-qa='org-input'][name='org']",
            profile.defaults.get("current_company") or profile.defaults.get("company"),
        )
        # Structured location already handled above to enable resume upload

        # Pronouns (optional checkboxes). Supports single string or comma-separated list.
        pronouns_raw = profile.defaults.get("pronouns")
        if pronouns_raw:
            await _set_pronouns(page, pronouns_raw)

        # Fill link fields if defaults contain recognizable keys
        for field_name, selector in link_fields.items():
            key_lower = field_name.lower()
            value = None
            if "linkedin" in key_lower:
                value = (
                    profile.defaults.get("linkedin")
                    or profile.defaults.get("linkedin_url")
                    or profile.defaults.get("linkedinurl")
                )
            elif "github" in key_lower:
                value = (
                    profile.defaults.get("github")
                    or profile.defaults.get("github_url")
                    or profile.defaults.get("githuburl")
                )
            elif "portfolio" in key_lower or "website" in key_lower:
                value = (
                    profile.defaults.get("portfolio")
                    or profile.defaults.get("website")
                    or profile.defaults.get("portfolio_url")
                    or profile.defaults.get("website_url")
                )
            if value:
                await _fill_if_available(page, selector, value)

        invalid_selectors = await collect_invalid_field_selectors(page)

        questions_to_fill = dynamic_questions
        if questions_to_fill:
            try:
                client = OpenRouterClient.from_settings()
            except OpenRouterError:
                client = None
            prompt_builder = PromptBuilder(profile=profile)
            for q in questions_to_fill:
                answer: str | None = None
                if client:
                    plan_msg = prompt_builder.build_question_prompt(
                        question=Question(id=q.cache_key, text=q.prompt, required=q.required),
                        job=item.details or JobDetails(),
                        extra_context=None,
                    )
                    try:
                        answer = client.complete(plan_msg.messages)
                    except Exception:
                        answer = None
                if not answer and q.required:
                    answer = profile.prompts.get("fallback_answer") or profile.prompts.get("default_long_form")
                if answer:
                    await _fill_textarea(page, q.answer_selector, answer)

        # Cover letter (textarea[name='comments'] or #additional-information) via LLM
        try:
            has_cover = await page.evaluate(
                "() => !!(document.querySelector('textarea[name=\\'comments\\']') || document.querySelector('#additional-information'))"
            )
        except Exception:
            has_cover = False
        if has_cover:
            cover_selector = "textarea[name='comments']"  # prefer named textarea
            try:
                exists_named = await page.evaluate("() => !!document.querySelector('textarea[name=\\'comments\\']')")
            except Exception:
                exists_named = False
            if not exists_named:
                cover_selector = "#additional-information"
            cover_text = None
            try:
                client = OpenRouterClient.from_settings()
                # Build a concise, tailored cover letter
                job = item.details or JobDetails()
                profile_links = {
                    "portfolio_url": profile.defaults.get("portfolio_url"),
                    "github_url": profile.defaults.get("github_url"),
                    "linkedin_url": profile.defaults.get("linkedin_url"),
                }
                messages = [
                    {"role": "system", "content": (
                        "You write concise, tailored cover letters. 180-220 words, positive, specific, no fluff. "
                        "Include a sentence on impact, a brief skills-to-role bridge, and a polite close."
                    )},
                    {"role": "user", "content": json.dumps({
                        "job": job.to_dict(),
                        "profile": {
                            "name": profile.name,
                            "resume_summary": profile.prompts.get("resume_summary"),
                            "key_accomplishments": profile.prompts.get("key_accomplishments"),
                            **profile_links,
                        },
                        "hint": profile.prompts.get("cover_letter"),
                    }, ensure_ascii=False)},
                ]
                cover_text = client.complete(messages, temperature=0.2)
            except Exception:
                cover_text = profile.prompts.get("cover_letter")
            if cover_text:
                await _fill_textarea(page, cover_selector, cover_text)

        # Multiple-choice dynamic cards (checkboxes/radios) â€” simple heuristics
        try:
            await page.evaluate(
                """
                () => {
                  const blocks = Array.from(document.querySelectorAll("[data-qa='additional-cards'] .application-question.custom-question"));
                  for (const b of blocks) {
                    const labelTextEl = b.querySelector('.application-label .text');
                    const labelText = labelTextEl ? labelTextEl.textContent.trim() : '';
                    const inputs = Array.from(b.querySelectorAll("input[type='checkbox'][name*='[field'], input[type='radio'][name*='[field']"));
                    if (!inputs.length) continue;
                    const lower = labelText.toLowerCase();
                    let target = null;
                    if (lower.includes('based in the united kingdom')) {
                      target = inputs.find(i => (i.value||'').toLowerCase() === 'no') || null;
                    } else if (lower.includes('work authorization') && lower.includes('united kingdom')) {
                      target = inputs.find(i => (i.value||'').toLowerCase() === 'yes') || null;
                    }
                    if (target && typeof target.click === 'function') {
                      target.click();
                    }
                  }
                }
                """
            )
        except Exception:
            pass

        # Supervised pause before submit (robust to non-interactive stdin)
        if mode != "auto":
            pause_reason = await _supervised_pause()
            if pause_reason is not None:
                return pause_reason

        # Validate before submit
        if not await _form_check_validity(page):
            invalid_fields = await _collect_invalid_fields(page)
            if mode != "auto":
                await _form_report_validity(page)
                # Let the user fix in supervised mode
                pause_reason = await _supervised_pause()
                if pause_reason is not None:
                    return pause_reason
            else:
                # LLM assist then re-validate
                await _apply_llm_assist(page, profile=profile, job=item.details, invalid_fields=invalid_fields)
            if not await _form_check_validity(page):
                return Reason(code="validation_failed", message="Form still invalid after autofill")

        # Submit and capture confirmation
        await _click(page, submit_selector)
        await asyncio.sleep(2.0)
        # hCaptcha check after click
        # Detect blocking captcha only after submit attempt, using visibility/overlay heuristics
        try:
            cstate = await _hcaptcha_state(page)
            if cstate.get("blocking"):
                return await handle_captcha_block(page, state=cstate, capture_callback=None)
        except Exception:
            pass

        # Post-submit sanity: page should either navigate or hide form
        still_has_form = await page.evaluate("() => !!document.querySelector('form#application-form')")
        if still_has_form:
            # If form remains, re-check validity â€“ likely a client-side validation
            if not await _form_check_validity(page):
                return Reason(code="validation_failed", message="Client-side validation blocked submission")

        confirmation_text = await _extract_confirmation_text(page)
        artifacts = Artifacts(
            confirmation_text=(confirmation_text[:500] if confirmation_text else "submitted"),
            confirmation_id=None,
        )
        return artifacts


def ensure_allowed_domain(url: str, allowed_domains: Iterable[str]) -> None:
    """Validate that ``url`` matches the configured ``allowed_domains`` pattern list."""
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


async def _wait_for_any(page, selectors: list[str]) -> None:
    """Wait until any of the selectors appear or timeout.

    Emits lightweight telemetry to help diagnose timeouts (e.g., CDP disconnects).
    """
    timeout_s = 20.0
    try:
        import os as _os
        env_to = float(_os.getenv("AUTO_APPLY_FORM_WAIT_TIMEOUT_SECONDS", "0") or 0)
        if env_to > 0:
            timeout_s = max(5.0, env_to)
    except Exception:
        pass
    try:
        log_event("form.wait.start", selectors=selectors, timeoutSeconds=timeout_s)
    except Exception:
        pass
    deadline = asyncio.get_event_loop().time() + timeout_s
    poll_errors = 0
    while asyncio.get_event_loop().time() < deadline:
        for sel in selectors:
            try:
                els = await page.get_elements_by_css_selector(sel)
                if els:
                    try:
                        log_event("form.wait.found", selector=sel)
                    except Exception:
                        pass
                    return
            except Exception as e:
                poll_errors += 1
                if poll_errors <= 2:
                    try:
                        log_event("form.wait.poll_error", selector=sel, error=str(e))
                    except Exception:
                        pass
        await asyncio.sleep(0.3)
    try:
        # Try to capture current URL for context
        href = None
        try:
            href = await page.evaluate("() => window.location && window.location.href || ''")
        except Exception:
            href = None
        log_event("form.wait.timeout", selectors=selectors, pollErrors=poll_errors, url=href)
    except Exception:
        pass
    raise TimeoutError("Expected elements did not render in time")


async def _exists(page, options: LeverBrowserOptions, *, selector: str) -> bool:
    try:
        els = await page.get_elements_by_css_selector(selector)
        return bool(els)
    except Exception:
        return False


async def _fill_if_available(page, selector: str | None, value: str | None) -> None:
    if not selector or value is None:
        return
    try:
        await page.evaluate(
            "(sel, val) => { const el = document.querySelector(sel); if (!el) return false; const proto = (el.tagName==='TEXTAREA') ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype; const setter = Object.getOwnPropertyDescriptor(proto, 'value').set; setter.call(el, String(val)); el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); el.blur && el.blur(); return true; }",
            selector,
            value,
        )
    except Exception:
        pass



def _quiet_js_eval_enabled() -> bool:
    try:
        import os as _os
        v = _os.getenv("AUTO_APPLY_DEBUG_JS_EVAL", "").strip().lower()
        return v in ("1", "true", "on", "yes")
    except Exception:
        return False


async def _evaluate_quiet(page, script: str, *args):
    """Call page.evaluate while suppressing noisy stdout prints unless DEBUG is enabled."""
    if _quiet_js_eval_enabled():
        return await page.evaluate(script, *args)
    try:
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            return await page.evaluate(script, *args)
    except Exception:
        return await page.evaluate(script, *args)
async def _fill_textarea(page, selector: str, value: str) -> None:
    try:
        await page.evaluate(
            "(sel, val) => { const el = document.querySelector(sel); if (!el) return false; const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set; setter.call(el, String(val)); el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); el.blur && el.blur(); return true; }",
            selector,
            value,
        )
    except Exception:
        pass


async def _close_stray_about_blank_tabs(session: BrowserSession) -> None:
    """Best-effort: close background about:blank/new-tab pages via CDP when supported."""
    try:
        if not hasattr(session, "get_or_create_cdp_session"):
            return
        cdp_session = await session.get_or_create_cdp_session()  # type: ignore[attr-defined]
        cdp = getattr(cdp_session, "cdp_client", None)
        sid = getattr(cdp_session, "session_id", None)
        current_target = getattr(cdp_session, "target_id", None)
        if cdp is None:
            return
        targets = await cdp.send.Target.getTargets(params={}, session_id=sid)
        items = targets.get("targetInfos") or targets.get("targetInfo") or []
        for target in items:
            try:
                target_id = target.get("targetId") or target.get("targetID")
                if not target_id or (current_target and str(target_id) == str(current_target)):
                    continue
                if target.get("type") != "page":
                    continue
                url = (target.get("url") or "").lower().strip()
                if url in ("about:blank", "chrome://newtab", "chrome://new-tab-page/"):
                    try:
                        await cdp.send.Target.closeTarget(params={"targetId": target_id}, session_id=sid)
                    except Exception:
                        pass
            except Exception:
                continue
    except Exception:
        return

async def _robust_navigate(session: BrowserSession, page, url: str) -> None:
    """Navigate to URL using Browser-Use event bus, then fall back to CDP, then page.goto.

    Logs apply.navigate.start/ok/fail and final href to make failures diagnosable.
    """
    try:
        log_event("apply.navigate.start", url=url)
    except Exception:
        pass
    # 1) Browser-Use event bus
    try:
        bus = getattr(session, "event_bus", None)
        if bus is not None:
            try:
                from browser_use.browser.events import NavigateToUrlEvent  # type: ignore
            except Exception:
                NavigateToUrlEvent = None  # type: ignore
            if NavigateToUrlEvent is not None:
                try:
                    ev = session.event_bus.dispatch(NavigateToUrlEvent(url=url, new_tab=False))
                    await ev
                    await ev.event_result(raise_if_any=True, raise_if_none=False)
                except Exception:
                    pass
    except Exception:
        pass
    # Verify and return if navigated
    try:
        href = await page.evaluate("() => window.location && window.location.href || ''")
        if isinstance(href, str) and href and href != "about:blank":
            try:
                log_event("apply.navigate.ok", method="event_bus", href=href)
            except Exception:
                pass
            return
    except Exception:
        pass
    # 2) CDP Page.navigate fallback
    try:
        send = await _get_cdp_sender(page, session)
        if send is not None:
            try:
                await send("Page.enable", {})
            except Exception:
                pass
            await send("Page.navigate", {"url": url, "transitionType": "typed"})
            # brief settle
            try:
                await asyncio.sleep(0.2)
            except Exception:
                pass
            try:
                href = await page.evaluate("() => window.location && window.location.href || ''")
            except Exception:
                href = None
            if isinstance(href, str) and href and href != "about:blank":
                try:
                    log_event("apply.navigate.ok", method="cdp", href=href)
                except Exception:
                    pass
                return
    except Exception as e:
        try:
            log_event("apply.navigate.cdp.error", error=str(e))
        except Exception:
            pass
    # 3) page.goto best-effort
    try:
        if hasattr(page, "goto"):
            await page.goto(url)
            try:
                href = await page.evaluate("() => window.location && window.location.href || ''")
            except Exception:
                href = None
            if isinstance(href, str) and href and href != "about:blank":
                try:
                    log_event("apply.navigate.ok", method="page.goto", href=href)
                except Exception:
                    pass
                return
    except Exception as e:
        try:
            log_event("apply.navigate.page.error", error=str(e))
        except Exception:
            pass
    try:
        href = await page.evaluate("() => window.location && window.location.href || ''")
    except Exception:
        href = None
    try:
        log_event("apply.navigate.fail", href=href or "")
    except Exception:
        pass
    # Let caller continue to wait; _wait_for_any will timeout and log URL


async def _get_cdp_sender(page, session: BrowserSession | None):
    """Return a callable to send CDP methods or None if unavailable.

    Mirrors client discovery used in _cdp_set_file_input_files.
    """
    for obj in (page, getattr(page, "context", None), session):
        if obj is None:
            continue
        for attr in ("cdp_client", "_cdp_client", "cdp", "_cdp", "client", "_client"):
            try:
                cand = getattr(obj, attr, None)
            except Exception:
                cand = None
            if cand is None:
                continue
            for name in ("send", "execute", "call", "invoke", "call_method"):
                try:
                    fn = getattr(cand, name, None)
                except Exception:
                    fn = None
                if callable(fn):
                    return fn
    return None

async def _upload_resume(
    session: BrowserSession | None,
    page,
    widget_plan: Mapping[str, object] | object,
    path: str,
) -> bool:
    """Attach a resume file using deterministic selectors and signals."""

    input_meta = widget_plan.get("input") if isinstance(widget_plan, Mapping) else {}
    selectors = _selector_candidates(input_meta)
    if not selectors:
        if isinstance(widget_plan, Mapping):
            fallback = widget_plan.get("selector")
            if fallback:
                selectors.extend(_selector_candidates(fallback))
    selectors = [selector for selector in selectors if selector]
    if not selectors:
        selectors = ["input[type='file'][name='resume']", "#resume-upload-input"]

    success_signals = []
    failure_signals = []
    storage_selector = None
    if isinstance(widget_plan, Mapping):
        success_signals = [
            str(sel)
            for sel in widget_plan.get("successSignals", [])
            if isinstance(sel, str) and sel
        ]
        failure_signals = [
            str(sel)
            for sel in widget_plan.get("failureSignals", [])
            if isinstance(sel, str) and sel
        ]
        storage_selector = widget_plan.get("storageField")
        if isinstance(storage_selector, str) and not storage_selector:
            storage_selector = None

    try:
        log_event(
            "resume_upload.start",
            selectors=selectors,
            successSignals=success_signals,
            failureSignals=failure_signals,
        )
    except Exception:
        pass

    for selector in selectors:
        try:
            if hasattr(page, "locator"):
                try:
                    log_event("resume_upload.attempt", method="locator", selector=selector)
                except Exception:
                    pass
                await page.locator(selector).set_input_files(path)
                if await _wait_for_resume_upload(
                    page,
                    widget_plan,
                    selector=selector,
                    timeout=5.0,
                ):
                    try:
                        log_event("resume_upload.success", method="locator")
                    except Exception:
                        pass
                    return True
        except Exception:
            pass
        try:
            if hasattr(page, "set_input_files"):
                try:
                    log_event("resume_upload.attempt", method="page", selector=selector)
                except Exception:
                    pass
                await page.set_input_files(selector, path)
                if await _wait_for_resume_upload(
                    page,
                    widget_plan,
                    selector=selector,
                    timeout=5.0,
                ):
                    try:
                        log_event("resume_upload.success", method="page")
                    except Exception:
                        pass
                    return True
        except Exception:
            pass

    triggers = []
    if isinstance(widget_plan, Mapping):
        raw_triggers = widget_plan.get("triggers")
        if isinstance(raw_triggers, Iterable) and not isinstance(raw_triggers, (str, bytes)):
            triggers = [str(sel) for sel in raw_triggers if isinstance(sel, str) and sel]
    for trigger in triggers:
        try:
            await _click(page, trigger)
            await asyncio.sleep(0.3)
        except Exception:
            continue
        for selector in selectors:
            try:
                if hasattr(page, "locator"):
                    await page.locator(selector).set_input_files(path)
                elif hasattr(page, "set_input_files"):
                    await page.set_input_files(selector, path)
                if await _wait_for_resume_upload(page, widget_plan, selector=selector, timeout=5.0):
                    try:
                        log_event("resume_upload.success", method="trigger", selector=selector)
                    except Exception:
                        pass
                    return True
            except Exception:
                continue

    try:
        log_event(
            "resume_upload.failed",
            selectors=selectors,
            successSignals=success_signals,
            failureSignals=failure_signals,
        )
    except Exception:
        pass
    return False


async def _wait_for_resume_upload(
    page,
    widget_plan: Mapping[str, object] | object,
    *,
    selector: str | None = None,
    timeout: float = 25.0,
) -> bool:
    """Wait until resume upload signals indicate success while watching for failures."""

    try:
        import os

        env_to = float(os.getenv("AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS", "0") or 0)
        if env_to > 0:
            timeout = env_to
    except Exception:
        pass

    selectors = []
    if selector:
        selectors.append(selector)
    if isinstance(widget_plan, Mapping):
        selectors.extend(_selector_candidates(widget_plan.get("input", {})))
    seen: list[str] = []
    for value in selectors:
        if value and value not in seen:
            seen.append(value)
    selectors = seen or ["input#resume-upload-input", "input[type='file'][name='resume']"]

    success_signals: list[str] = []
    failure_signals: list[str] = []
    storage_selector: str | None = None
    if isinstance(widget_plan, Mapping):
        raw_success = widget_plan.get("successSignals")
        if isinstance(raw_success, Iterable) and not isinstance(raw_success, (str, bytes)):
            success_signals = [str(sel) for sel in raw_success if isinstance(sel, str) and sel]
        raw_failure = widget_plan.get("failureSignals")
        if isinstance(raw_failure, Iterable) and not isinstance(raw_failure, (str, bytes)):
            failure_signals = [str(sel) for sel in raw_failure if isinstance(sel, str) and sel]
        storage_selector = widget_plan.get("storageField") if isinstance(widget_plan.get("storageField"), str) else None

    deadline = asyncio.get_event_loop().time() + max(1.0, timeout)
    while asyncio.get_event_loop().time() < deadline:
        try:
            state = await _evaluate_quiet(
                """
                (selectors, successSelectors, failureSelectors, storageSelector) => {
                  const anyVisible = (list) => list.some((sel) => {
                    if (!sel) return false;
                    const el = document.querySelector(sel);
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    return style && style.display !== 'none' && style.visibility !== 'hidden';
                  });
                  const hasFiles = selectors.some((sel) => {
                    const el = document.querySelector(sel);
                    return !!(el && el.files && el.files.length > 0);
                  });
                  const storageEl = storageSelector ? document.querySelector(storageSelector) : null;
                  const storageOk = !!(storageEl && storageEl.value && String(storageEl.value).length > 0);
                  const success = anyVisible(successSelectors);
                  const failure = anyVisible(failureSelectors);
                  const filenameOk = (() => {
                    const el = selectors.length ? document.querySelector(selectors[0]) : null;
                    const container = el ? el.closest('.application-question') : document.querySelector('.application-question.resume');
                    const span = container ? container.querySelector('span.filename') : null;
                    return span && span.textContent && span.textContent.trim();
                  })();
                  return { ok: Boolean(hasFiles || storageOk || success || filenameOk), fail: Boolean(failure) };
                }
                """,
                selectors,
                success_signals,
                failure_signals,
                storage_selector,
            )
            if state and state.get("ok"):
                return True
            if state and state.get("fail"):
                return False
        except Exception:
            pass
        await asyncio.sleep(0.35)

    return False


async def _dispatch_file_input_events(page, selector: str) -> None:
    """Dispatch input/change events on the file input to trigger UI listeners."""
    try:
        await page.evaluate(
            """
            (sel) => {
              const el = document.querySelector(sel);
              if (!el) return false;
              try { el.dispatchEvent(new Event('input', { bubbles: true })); } catch {}
              try { el.dispatchEvent(new Event('change', { bubbles: true })); } catch {}
              return true;
            }
            """,
            selector,
        )
    except Exception:
        pass

async def _eventbus_upload_resume(session: BrowserSession, selector: str, path: str) -> bool:
    """Try to upload a file via browser-use event bus fallback.

    This approach relies on BrowserSession capabilities present in CDP-first
    environments. It attempts a few strategies conservatively and logs
    availability via telemetry in callers.

    Returns:
        bool: True if an event-bus upload was dispatched without error.
    """
    # Check for event bus and helper methods
    has_bus = hasattr(session, "event_bus")
    get_by_index = getattr(session, "get_element_by_index", None)
    is_file_input = getattr(session, "is_file_input", None)
    try:
        if not has_bus or not callable(get_by_index) or not callable(is_file_input):
            try:
                log_event("resume_upload.eventbus.unavailable", has_bus=has_bus, has_get_by_index=bool(get_by_index), has_is_file_input=bool(is_file_input))
            except Exception:
                pass
            return False
        # Heuristic: probe first N DOM elements by index and try uploading when type is file
        from browser_use.browser.events import UploadFileEvent  # type: ignore
        scanned = 0
        matched = 0
        # Increase scan window; bail early on first success
        MAX_SCAN = 300
        for idx in range(0, MAX_SCAN):
            try:
                el = await get_by_index(idx)
            except Exception:
                el = None
            if not el:
                continue
            try:
                maybe = is_file_input(el)
                try:
                    import asyncio as _asyncio
                    if _asyncio.iscoroutine(maybe):
                        ok_type = await maybe
                    else:
                        ok_type = bool(maybe)
                except Exception:
                    ok_type = False
                scanned += 1
                if not ok_type:
                    continue
                matched += 1
                try:
                    log_event("resume_upload.eventbus.try", index=idx)
                except Exception:
                    pass
            except Exception:
                continue
            try:
                ev = session.event_bus.dispatch(UploadFileEvent(node=el, file_path=path))
                await ev
                await ev.event_result(raise_if_any=True, raise_if_none=False)
                try:
                    log_event("resume_upload.eventbus.dispatched", index=idx)
                except Exception:
                    pass
                return True
            except Exception:
                continue
        try:
            log_event("resume_upload.eventbus.candidates_scanned", scanned=scanned, matched=matched)
        except Exception:
            pass
    except Exception:
        pass
    return False


async def _cdp_set_file_input_files(page, selector: str, path: str, backend_node_id: int | None = None, session: BrowserSession | None = None) -> bool:
    """Best-effort CDP fallback using DOM.setFileInputFiles.

    Tries to find a CDP client on the page/session and call the DevTools
    protocol. Limited to same-target document (no cross-target iframe walk).

    Returns:
        True if the CDP call was sent and did not error, False otherwise.
    """
    # Preferred path: use Browser-Use's typed CDP session if available
    if session is not None and hasattr(session, "get_or_create_cdp_session"):
        try:
            try:
                log_event("resume_upload.cdp.typed.start", selector=selector)
            except Exception:
                pass
            cdp_session = await session.get_or_create_cdp_session()  # type: ignore[attr-defined]
            cdp_client = getattr(cdp_session, "cdp_client", None)
            session_id = getattr(cdp_session, "session_id", None)
            if cdp_client is not None and session_id is not None:
                try:
                    await cdp_client.send.DOM.enable(session_id=session_id)
                except Exception:
                    pass
                # Runtime.evaluate to get objectId for exact selector
                evaluation = await cdp_client.send.Runtime.evaluate(
                    params={
                        "expression": f"(() => document.querySelector({json.dumps(selector)}))()",
                        "objectGroup": "file-upload",
                        "includeCommandLineAPI": True,
                        "returnByValue": False,
                        "awaitPromise": True,
                    },
                    session_id=session_id,
                )
                result = evaluation.get("result", {}) if isinstance(evaluation, dict) else {}
                object_id = result.get("objectId")
                if object_id:
                    try:
                        await cdp_client.send.DOM.setFileInputFiles(
                            params={"files": [path], "objectId": object_id},
                            session_id=session_id,
                        )
                        try:
                            log_event("resume_upload.cdp.typed.success")
                        except Exception:
                            pass
                        return True
                    finally:
                        try:
                            await cdp_client.send.Runtime.releaseObjectGroup(  # type: ignore[attr-defined]
                                params={"objectGroup": "file-upload"},
                                session_id=session_id,
                            )
                        except Exception:
                            pass
        except Exception as e:
            try:
                log_event("resume_upload.cdp.typed.error", error=str(e))
            except Exception:
                pass

    client = None
    for attr in ("cdp_client", "_cdp_client", "cdp", "_cdp", "client", "_client"):
        try:
            cand = getattr(page, attr, None)
            if cand is not None:
                client = cand
                break
        except Exception:
            continue
    if client is None:
        try:
            ctx = getattr(page, "context", None)
            if ctx is not None:
                for attr in ("cdp_client", "_cdp_client", "cdp", "_cdp"):
                    cand = getattr(ctx, attr, None)
                    if cand is not None:
                        client = cand
                        break
        except Exception:
            pass
    if client is None and session is not None:
        for attr in ("cdp_client", "_cdp_client", "cdp", "_cdp", "client", "_client"):
            try:
                cand = getattr(session, attr, None)
                if cand is not None:
                    client = cand
                    break
            except Exception:
                continue
    if client is None:
        return False
    send = None
    for name in ("send", "execute", "call", "invoke", "call_method"):
        try:
            fn = getattr(client, name, None)
            if callable(fn):
                send = fn
                break
        except Exception:
            continue
    if send is None:
        return False
    try:
        try:
            await send("DOM.enable", {})
        except Exception:
            pass
        # Preferred: Runtime.evaluate to get objectId for exact element, then set files by objectId
        try:
            evaluation = await send(
                "Runtime.evaluate",
                {
                    "expression": f"(() => document.querySelector({json.dumps(selector)}))()",
                    "objectGroup": "file-upload",
                    "includeCommandLineAPI": True,
                    "returnByValue": False,
                    "awaitPromise": True,
                },
            )
            result = evaluation.get("result", {}) if isinstance(evaluation, dict) else {}
            object_id = result.get("objectId")
            if object_id:
                try:
                    await send("DOM.setFileInputFiles", {"files": [path], "objectId": object_id})
                    return True
                finally:
                    try:
                        await send("Runtime.releaseObjectGroup", {"objectGroup": "file-upload"})
                    except Exception:
                        pass
        except Exception as _e:
            try:
                log_event("resume_upload.cdp.object_id.error", error=str(_e))
            except Exception:
                pass
        doc = await send("DOM.getDocument", {"depth": -1, "pierce": True})
        root = None
        if isinstance(doc, dict):
            root = (doc.get("root") or {}).get("nodeId")
        if not root:
            return False
        # Prefer backendNodeId if provided (more stable across rerenders)
        if backend_node_id:
            try:
                await send("DOM.setFileInputFiles", {"files": [path], "backendNodeId": int(backend_node_id)})
                return True
            except Exception:
                pass
        q = await send("DOM.querySelector", {"nodeId": root, "selector": selector})
        node_id = None
        if isinstance(q, dict):
            node_id = q.get("nodeId")
        if node_id:
            await send("DOM.setFileInputFiles", {"files": [path], "nodeId": node_id})
            return True
        # Fallback: flattened document (pierce shadow DOM) search for input[type=file]
        try:
            flat = await send("DOM.getFlattenedDocument", {"depth": -1, "pierce": True})
        except Exception:
            flat = None
        if isinstance(flat, dict):
            nodes = flat.get("nodes") or []
            def _attrs_map(n):
                attrs = n.get("attributes") or []
                try:
                    it = iter(attrs)
                    return {k:v for k,v in zip(it, it)}
                except Exception:
                    return {}
            best = None
            for n in nodes:
                try:
                    if str(n.get("nodeName") or "").upper() != "INPUT":
                        continue
                    attrs = _attrs_map(n)
                    if str(attrs.get("type", "")).lower() != "file":
                        continue
                    # Prefer name="resume" when present
                    score = 1
                    if str(attrs.get("name", "")).lower() == "resume":
                        score = 2
                    bni = n.get("backendNodeId") or n.get("backendNodeID")
                    if bni:
                        if best is None or score > best[0]:
                            best = (score, int(bni))
                except Exception:
                    continue
            if best is not None:
                try:
                    await send("DOM.setFileInputFiles", {"files": [path], "backendNodeId": best[1]})
                    return True
                except Exception:
                    pass
        return False
    except Exception:
        return False


async def _log_resume_postmortem(page, selector: str) -> None:
    """Emit a compact diagnostic snapshot regardless of debug flags."""
    try:
        snapshot = await _evaluate_quiet(
            """
            (sel) => {
              const el = document.querySelector(sel);
              const files = el && el.files ? el.files.length : 0;
              const storage = document.querySelector('input[name=\"resumeStorageId\"]');
              const storageVal = storage ? (storage.value || '') : '';
              const s1 = document.querySelector('.resume-upload-success');
              const s2 = document.querySelector('.application-upload-success');
              const f1 = document.querySelector('.resume-upload-failure');
              const o1 = document.querySelector('.resume-upload-oversize');
              const vis = (n) => { try { const s = n && window.getComputedStyle(n); return !!(s && s.display !== 'none' && s.visibility !== 'hidden'); } catch { return false; } };
              const container = el ? el.closest('.application-question.resume') : document.querySelector('.application-question.resume');
              const outer = container ? container.outerHTML : (el ? el.outerHTML : '');
              return {
                files,
                storage_id_len: storageVal.length,
                success_visible: vis(s1) || vis(s2),
                failure_visible: vis(f1),
                oversize_visible: vis(o1),
                outer_truncated: outer ? outer.slice(0, 1200) : '',
              };
            }
            """,
            selector,
        )
    except Exception:
        snapshot = None
    try:
        log_event("resume_upload.postmortem", snapshot=snapshot or {})
    except Exception:
        pass
async def _set_pronouns(page, pronouns: str | list[str]) -> None:
    """Check pronoun checkboxes by value. Accepts a string or list of strings.

    Matches by case-insensitive value, e.g., "He/him", "They/them", "Use name only".
    """
    def _normalize(x: str) -> str:
        return str(x).strip().lower()

    if isinstance(pronouns, str):
        values = [v.strip() for v in pronouns.split(",") if v.strip()]
    else:
        values = [str(v).strip() for v in pronouns if v]
    values_norm = [_normalize(v) for v in values]
    try:
        await page.evaluate(
            """
            (values) => {
              const norm = (x) => String(x).trim().toLowerCase();
              const inputs = Array.from(document.querySelectorAll("input[type='checkbox'][name='pronouns']"));
              for (const v of values) {
                for (const el of inputs) {
                  const text = el.value || el.getAttribute('aria-label') || '';
                  if (norm(text) === norm(v)) {
                    el.checked = true;
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                  }
                }
              }
            }
            """,
            values_norm,
        )
    except Exception:
        pass


async def validate_location_gate(
    page,
    *,
    input_selector: str,
    hidden_selector: str,
) -> tuple[bool, dict[str, object]]:
    """Ensure Lever's structured location hidden JSON contains a non-empty name."""

    try:
        state = await _evaluate_quiet(
            """
            (inputSel, hiddenSel) => {
              const input = document.querySelector(inputSel);
              const hidden = document.querySelector(hiddenSel);
              const raw = hidden ? hidden.value || '' : '';
              let parsed = {};
              try { parsed = raw ? JSON.parse(raw) : {}; } catch { parsed = {}; }
              const name = parsed && typeof parsed.name === 'string' ? parsed.name.trim() : '';
              return {
                inputPresent: !!input,
                hiddenPresent: !!hidden,
                raw,
                name,
              };
            }
            """,
            input_selector,
            hidden_selector,
        )
    except Exception:
        state = {}

    if not isinstance(state, dict):
        state = {}
    name = str(state.get("name") or "").strip()
    success = bool(name)
    try:
        event_name = "form.location_gate.ready" if success else "form.location_gate.missing"
        log_event(event_name, state=state, inputSelector=input_selector, hiddenSelector=hidden_selector)
    except Exception:
        pass
    return success, state


async def collect_invalid_field_selectors(page) -> list[str]:
    """Call reportValidity/checkValidity in order and gather :invalid selectors."""

    try:
        await page.evaluate(
            "() => { const form = document.querySelector('form#application-form'); if (form) try { form.reportValidity(); } catch {} }"
        )
    except Exception:
        pass

    is_valid = True
    try:
        result = await page.evaluate(
            "() => { const form = document.querySelector('form#application-form'); if (!form) return true; try { return form.checkValidity(); } catch { return false; } }"
        )
        if isinstance(result, bool):
            is_valid = result
    except Exception:
        is_valid = False

    if is_valid:
        return []

    try:
        selectors = await page.evaluate(
            """
            () => {
              const form = document.querySelector('form#application-form');
              if (!form) return [];
              const invalid = form.querySelectorAll(':invalid');
              const result = [];
              const esc = (value) => String(value).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
              invalid.forEach((el) => {
                if (el.id) {
                  result.push(`#${esc(el.id)}`);
                  return;
                }
                const name = el.getAttribute('name');
                if (name) {
                  result.push(`${el.tagName.toLowerCase()}[name='${esc(name)}']`);
                  return;
                }
                result.push(el.tagName.toLowerCase());
              });
              return result;
            }
            """
        )
    except Exception:
        selectors = []

    if not isinstance(selectors, Iterable) or isinstance(selectors, (str, bytes)):
        selectors = []

    normalized = [str(sel) for sel in selectors if isinstance(sel, str) and sel]
    if normalized:
        try:
            log_event("form.validation.invalid_fields", selectors=normalized)
        except Exception:
            pass
    return normalized


async def handle_captcha_block(
    page,
    *,
    state: Mapping[str, object] | object,
    capture_callback: Callable[[object, str], Awaitable[Mapping[str, str]]] | None = None,
) -> Reason:
    """Emit telemetry, capture artifacts, and return a blocking reason for CAPTCHA visibility."""

    try:
        log_event("captcha.blocking_visible", details=state)
    except Exception:
        pass

    if capture_callback is not None:
        try:
            await capture_callback(page, prefix="captcha-block")
        except Exception:
            pass

    return Reason(
        code="captcha_blocked",
        message="Visible CAPTCHA detected after submit; manual resolution required",
    )


async def _set_structured_location(page, *, input_selector: str, hidden_selector: str, value: str | None) -> None:
    """Type location then try to pick a suggestion; fallback to hidden input.

    Works with Lever's structured location widget that uses #location-input and a
    hidden #selected-location.
    """
    if not value:
        return
    try:
        await page.evaluate(
            "(sel, val) => { const el = document.querySelector(sel); if (el) { el.focus(); el.value = val; el.dispatchEvent(new Event('input', {bubbles:true})); }}",
            input_selector,
            value,
        )
        # Give Lever a moment to render suggestions
        await asyncio.sleep(1.2)
        # Try clicking the first suggestion
        clicked = await page.evaluate(
            "(containerSel) => {\n              const c = document.querySelector('.dropdown-results');\n              if (!c) return false;\n              const first = c.querySelector('[data-value], li, div');\n              if (first && typeof first.click === 'function') { first.click(); return true; }\n              return false;\n            }",
            ".dropdown-results",
        )
        if not clicked:
            # Fallback: set hidden selectedLocation value directly
            await page.evaluate(
                "(sel, val) => { const el = document.querySelector(sel); if (el) { el.value = val; el.dispatchEvent(new Event('change', {bubbles:true})); }}",
                hidden_selector,
                value,
            )
    except Exception:
        # Best effort only
        pass


async def _click(page, selector: str) -> None:
    try:
        await page.evaluate(
            "(sel) => { const el = document.querySelector(sel); if (el) el.click(); }",
            selector,
        )
    except Exception:
        pass


async def _extract_confirmation_text(page) -> str | None:
    try:
        return await page.evaluate("() => document.body ? document.body.innerText : ''")
    except Exception:
        return None


async def _form_check_validity(page) -> bool:
    try:
        return await page.evaluate(
            "() => { const f = document.querySelector('form#application-form'); return f ? f.checkValidity() : false; }"
        )
    except Exception:
        return False


async def _form_report_validity(page) -> None:
    try:
        await page.evaluate(
            "() => { const f = document.querySelector('form#application-form'); if (f) f.reportValidity(); }"
        )
    except Exception:
        pass


async def _hcaptcha_state(page) -> dict:
    """Return presence/visibility/blocking state of hCaptcha on the page.

    Heuristics:
    - present: div#h-captcha exists in DOM
    - visible: any hCaptcha iframe (or container) is displayed/visible with non-trivial size
    - blocking: visible and either covers notable viewport area or has pointer events enabled
    """
    try:
        state = await _evaluate_quiet(
            """
            () => {
              const res = { present: false, visible: false, blocking: false, iframes: 0, cover: 0 };
              const c = document.querySelector('div#h-captcha');
              if (!c) return res;
              res.present = true;
              const rectC = c.getBoundingClientRect();
              const styleC = window.getComputedStyle(c);
              const visC = (styleC.display !== 'none' && styleC.visibility !== 'hidden' && rectC.width > 1 && rectC.height > 1 && parseFloat(styleC.opacity || '1') > 0.01);
              let visibleIFrame = false;
              let maxCover = 0;
              const iframes = c.querySelectorAll('iframe');
              res.iframes = iframes.length;
              const vw = Math.max(1, window.innerWidth || 1);
              const vh = Math.max(1, window.innerHeight || 1);
              for (const f of iframes) {
                const r = f.getBoundingClientRect();
                const s = window.getComputedStyle(f);
                const v = (s.display !== 'none' && s.visibility !== 'hidden' && r.width > 20 && r.height > 20 && parseFloat(s.opacity || '1') > 0.01);
                if (v) {
                  visibleIFrame = true;
                  const cover = Math.min(1, (r.width * r.height) / (vw * vh));
                  if (cover > maxCover) maxCover = cover;
                }
              }
              res.visible = visC || visibleIFrame;
              res.cover = Number(maxCover.toFixed(3));
              // Blocking if visible and either large overlay or pointer-events enabled
              let pe = false;
              if (visibleIFrame) {
                for (const f of iframes) {
                  const s = window.getComputedStyle(f);
                  if (s.pointerEvents && s.pointerEvents !== 'none') { pe = true; break; }
                }
              }
              res.blocking = res.visible && (res.cover >= 0.2 || pe);
              return res;
            }
            """
        )
        if state and isinstance(state, dict):
            return state
    except Exception:
        pass
    return {"present": False, "visible": False, "blocking": False}

async def _collect_invalid_fields(page) -> list[dict]:
    try:
        raw = await page.evaluate(
            """
            () => {
              const f = document.querySelector('form#application-form');
              if (!f) return '[]';
              const fields = Array.from(f.querySelectorAll('input, textarea, select'));
              const invalids = [];
              for (const el of fields) {
                try {
                  if (el.willValidate && !el.checkValidity()) {
                    const question = el.closest('.application-question');
                    const lbl = question?.querySelector('.application-label')?.textContent?.trim() || '';
                    const type = (el.type || el.tagName || '').toLowerCase();
                    let options = [];
                    if (type === 'select-one') {
                      options = Array.from(el.options).map(o => ({ text: o.textContent.trim(), value: o.value }));
                    } else if (type === 'checkbox' || type === 'radio') {
                      const group = Array.from(document.querySelectorAll(`[name="${el.name}"]`));
                      options = group.map(g => ({ text: (g.value||'').trim(), value: (g.value||'').trim() }));
                    }
                    invalids.push({
                      name: el.name || '',
                      id: el.id || '',
                      type,
                      label: lbl || el.getAttribute('aria-label') || el.name || el.id || '',
                      options,
                    });
                  }
                } catch {}
              }
              return JSON.stringify(invalids);
            }
            """
        )
        import json as _json
        return _json.loads(raw or '[]')
    except Exception:
        return []


async def _apply_llm_assist(page, *, profile: Profile, job: JobDetails | None, invalid_fields: list[dict]) -> None:
    # Build a minimal prompt for deterministic JSON suggestions
    try:
        client = OpenRouterClient.from_settings()
    except Exception:
        return
    policy = {
        "work_authorization_regions": profile.defaults.get("work_authorization_regions", "US"),
        "prefer_not_to_disclose": bool(profile.defaults.get("prefer_not_to_disclose", False)),
    }
    import json as _json
    sysmsg = (
        "You are helping complete a job application form. "
        "Return ONLY a compact JSON object mapping HTML input names to suggested values, "
        "suitable for required fields. Prefer explicit values from provided options."
    )
    user = {
        "profile": {
            "name": profile.name,
            "defaults": dict(profile.defaults),
        },
        "job": job.to_dict() if job else {},
        "policy": policy,
        "invalid_fields": invalid_fields,
        "instructions": (
            "- For checkboxes/radios, choose one available option (match option text).\n"
            "- For selects, choose an option by visible text.\n"
            "- If demographic questions appear and policy.prefer_not_to_disclose is true, choose 'Prefer not to disclose' when available.\n"
            "- If current location is required, suggest a concrete location like 'United States'.\n"
            "Output strictly as JSON without comments."
        ),
    }
    messages = [
        {"role": "system", "content": sysmsg},
        {"role": "user", "content": _json.dumps(user, ensure_ascii=False)},
    ]
    try:
        raw = client.complete(messages, temperature=0.0)
        data = _json.loads(raw)
    except Exception:
        return
    # Apply suggestions by name
    JS_APPLY_BY_NAME = r"""
    (n, v) => {
      const lower = (x) => String(x).trim().toLowerCase();
      const list = document.getElementsByName(n);
      const el = (list && list.length) ? list[0] : null;
      if (!el) return false;
      if (el.tagName === 'SELECT') {
        for (const opt of el.options) {
          const text = (opt.textContent || '').trim();
          if (lower(text) === lower(v) || lower(opt.value) === lower(v)) {
            el.value = opt.value;
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
          }
        }
        return false;
      } else if (el.type === 'checkbox' || el.type === 'radio') {
        let matched = false;
        const group = document.getElementsByName(n);
        for (const g of group) {
          if (lower(g.value || '') === lower(v) || lower(g.getAttribute('aria-label') || '') === lower(v)) {
            g.checked = true;
            g.dispatchEvent(new Event('change', { bubbles: true }));
            matched = true;
            break;
          }
        }
        return matched;
      } else {
        const proto = (el.tagName === 'TEXTAREA') ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(el, String(v));
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        if (typeof el.blur === 'function') el.blur();
        return true;
      }
    }
    """
    for name, value in (data.items() if isinstance(data, dict) else []):
        try:
            if isinstance(value, str):
                # Try select first; if not a select, treat as text input
                applied = await page.evaluate(JS_APPLY_BY_NAME, name, value)



            else:
                applied = False
        except Exception:
            applied = False
        if not applied:
            continue


async def _supervised_pause(timeout_seconds: int | None = None) -> Reason | None:
    """Pause for human review; be robust to non-interactive stdin.

    Returns a Reason if the user aborts (Ctrl+C), otherwise None.
    """
    if timeout_seconds is None:
        try:
            import os
            timeout_seconds = int(os.getenv("AUTO_APPLY_SUPERVISED_TIMEOUT", "15"))
        except Exception:
            timeout_seconds = 15
    print("Review filled form in the browser. Press Enter to submit, or wait to auto-continue...")
    try:
        input()
        return None
    except KeyboardInterrupt:
        return Reason(code="user_aborted", message="User declined to submit in supervised mode")
    except Exception:
        # Non-interactive stdin; auto-continue after timeout
        await asyncio.sleep(max(0, timeout_seconds))
        return None


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


















