"""Utilities for analyzing Lever forms and configuring browser sessions."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final, Literal
from xml.etree import ElementTree as ET

from browser_use.browser.session import BrowserSession

from .. import saved_state
from ..application_queue import ApplicationItem, Artifacts, JobDetails, Reason
from ..config import Settings, load_settings
from ..llm.openrouter_client import OpenRouterClient, OpenRouterError
from ..llm.prompt_builder import PromptBuilder, Question
from ..profile_manager import Profile
from ..telemetry import log_event


@dataclass(slots=True)
class DynamicQuestion:
    """Long-form or structured question extracted from Lever dynamic cards."""

    prompt: str
    required: bool
    cache_key: str
    answer_selector: str | None = None
    field_name: str | None = None
    field_type: str = "textarea"
    options: dict[str, str] = field(default_factory=dict)
    option_pairs: list[tuple[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class EeoField:
    """EEO survey field (select/radio) with normalized options."""

    name: str
    label: str
    field_type: Literal["select", "radio"]
    selector: str | None
    options: dict[str, str] = field(default_factory=dict)
    option_pairs: list[tuple[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class LeverFormPlan:
    """Key selectors and metadata needed to complete a Lever form."""

    resume_input: str
    contact_fields: dict[str, str]
    link_fields: dict[str, str]
    dynamic_questions: list[DynamicQuestion] = field(default_factory=list)
    eeo_fields: list[EeoField] = field(default_factory=list)
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
            resolved_settings.diagnostics_enabled or resolved_settings.diagnostics_capture_video
        )
        capture_har = bool(
            resolved_settings.diagnostics_enabled or resolved_settings.diagnostics_capture_har
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
            disable_default_extensions=bool(
                getattr(resolved_settings, "disable_default_extensions", True)
            ),
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
    answer_nodes: dict[str, tuple[str, dict[str, str | None]]] = {}
    choice_values: dict[str, set[str]] = {}
    eeo_fields: list[EeoField] = []
    eeo_radio_groups: dict[str, dict[str, object]] = {}
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

            if name and "[field" in name:
                answer_nodes.setdefault(name, (tag, attrs.copy()))
                input_type = (attrs.get("type") or "").lower()
                if input_type in {"radio", "checkbox"}:
                    choice_values.setdefault(name, set()).add(attrs.get("value") or "")
            input_type = (attrs.get("type") or "").lower()
            if name and name.startswith("eeo[") and input_type == "radio":
                group = eeo_radio_groups.setdefault(
                    name,
                    {
                        "name": name,
                        "label": name,
                        "selector": _selector_for(tag, attrs),
                        "options": [],
                    },
                )
                if group.get("selector") is None:
                    group["selector"] = _selector_for(tag, attrs)
                value = (attrs.get("value") or "").strip()
                display = (attrs.get("aria-label") or value).strip()
                group["options"].append((value, display))
        elif tag == "textarea":
            name = attrs.get("name")
            if name:
                answer_nodes.setdefault(name, (tag, attrs.copy()))
        elif tag == "select":
            name = attrs.get("name")
            if name and name.startswith("eeo["):
                selector = _selector_for(tag, attrs)
                label_text = attrs.get("aria-label") or attrs.get("data-label") or name
                option_pairs: list[tuple[str, str]] = []
                options_map: dict[str, str] = {}
                for child in list(node):
                    if not hasattr(child, "tag"):
                        continue
                    if str(child.tag).lower() != "option":
                        continue
                    value = (child.attrib.get("value") or "").strip()
                    text = (child.text or "").strip()
                    if not value and not text:
                        continue
                    option_pairs.append((value, text))
                    for key in (text, value):
                        normalized = _normalize_choice_key(key)
                        if normalized:
                            options_map[normalized] = value or text
                eeo_fields.append(
                    EeoField(
                        name=name,
                        label=label_text,
                        field_type="select",
                        selector=selector,
                        options=options_map,
                        option_pairs=option_pairs,
                    )
                )
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
            node_info = answer_nodes.get(answer_name)
            answer_selector = None
            node_tag = None
            if node_info:
                node_tag, node_attrs = node_info
                answer_selector = _selector_for(node_tag, node_attrs)
            field_type = str(field_spec.get("type", "")).strip().lower()
            if not field_type:
                field_type = "textarea" if node_tag == "textarea" else "text"
            elif field_type in {"long_text", "paragraph"}:
                field_type = "textarea"
            elif field_type in {"short_text"}:
                field_type = "text"
            if field_type in {"multiple-choice", "multiple_choice", "select"}:
                options_map: dict[str, str] = {}
                option_pairs: list[tuple[str, str]] = []
                values_seen = choice_values.get(answer_name) or set()
                for option in field_spec.get("options", []) or []:
                    opt_text = str(option.get("text", "")).strip()
                    opt_id = str(option.get("optionId", "")).strip()
                    target = _resolve_option_value(opt_text, opt_id, values_seen)
                    value_choice = target or opt_id or opt_text
                    if not value_choice and not opt_text:
                        continue
                    option_pairs.append((value_choice, opt_text))
                    key_candidates = {opt_text, opt_id, value_choice}
                    if target:
                        key_candidates.add(target)
                    for key in key_candidates:
                        normalized = _normalize_choice_key(key)
                        if normalized:
                            options_map[normalized] = value_choice
                dynamic_questions.append(
                    DynamicQuestion(
                        prompt=prompt,
                        required=required,
                        cache_key=_normalize_question_key(prompt),
                        answer_selector=answer_selector,
                        field_name=answer_name,
                        field_type="multiple_choice",
                        options=options_map,
                        option_pairs=option_pairs,
                    )
                )
            else:
                dynamic_questions.append(
                    DynamicQuestion(
                        prompt=prompt,
                        required=required,
                        cache_key=_normalize_question_key(prompt),
                        answer_selector=answer_selector,
                        field_name=answer_name,
                        field_type="textarea"
                        if (node_tag == "textarea" or field_type == "textarea")
                        else "text",
                    )
                )

    for group in eeo_radio_groups.values():
        option_pairs = list(group.get("options", []))
        options_map: dict[str, str] = {}
        for value, text in option_pairs:
            for key in (text, value):
                normalized = _normalize_choice_key(key)
                if normalized:
                    options_map[normalized] = value or text
        eeo_fields.append(
            EeoField(
                name=str(group.get("name")),
                label=str(group.get("label") or group.get("name")),
                field_type="radio",
                selector=(str(group.get("selector")) if group.get("selector") else None),
                options=options_map,
                option_pairs=option_pairs,
            )
        )

    return LeverFormPlan(
        resume_input=resume_selector,
        contact_fields=contact_fields,
        link_fields=link_fields,
        dynamic_questions=dynamic_questions,
        eeo_fields=eeo_fields,
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

    async def build_plan_in_browser(self, page) -> LeverFormPlan:
        """Inspect the live DOM and return a plan without HTML parsing brittlety."""
        payload = await page.evaluate(
            """
            () => {
              const pickSelector = (el, tag='input') => {
                if (!el) return null;
                if (el.id) return `#${el.id}`;
                if (el.name) return `${tag}[name='${el.name}']`;
                if (el.getAttribute('data-qa')) return `${tag}[data-qa='${el.getAttribute('data-qa')}']`;
                const cls = el.className && String(el.className).split(/\\s+/)[0];
                if (cls) return `${tag}.${cls}`;
                return tag;
              };

              const q = (sel) => document.querySelector(sel);
              const qa = (sel) => Array.from(document.querySelectorAll(sel));

              const resumeEl = q("input#resume-upload-input[name='resume']") || q("input[name='resume']");
              const contact = {};
              const nameEl = q("input[data-qa='name-input'][name='name']") || q("input[name='name']");
              if (nameEl) contact.name = pickSelector(nameEl);
              const emailEl = q("input[data-qa='email-input'][name='email']") || q("input[name='email']");
              if (emailEl) contact.email = pickSelector(emailEl);
              const phoneEl = q("input[data-qa='phone-input'][name='phone']") || q("input[name='phone']");
              if (phoneEl) contact.phone = pickSelector(phoneEl);
              const locEl = q("input#location-input.location-input") || q("input#location-input");
              if (locEl) contact.location = pickSelector(locEl);
              const locHidden = q("input#selected-location");
              if (locHidden) contact.location_hidden = pickSelector(locHidden);

              const links = {};
              qa("input[name^='urls[']").forEach((el) => {
                const sel = pickSelector(el);
                if (sel && el.name) links[el.name] = sel;
              });

              const templates = qa("input[name$='[baseTemplate]']");
              const questions = [];
              templates.forEach((tpl) => {
                const name = tpl.name;
                const prefix = name.replace(/\\[baseTemplate\\]$/, '');
                let fields = [];
                try { fields = JSON.parse(tpl.value || '{}').fields || []; } catch {/*ignore*/}
                fields.forEach((f, idx) => {
                  if (!f || !f.text) return;
                  const answerName = `${prefix}[field${idx}]`;
                  const textareaEl = q(`textarea[name='${answerName}']`);
                  const inputEl = q(`input[name='${answerName}']`);
                  const optionEls = qa(`input[name='${answerName}']`);
                  let answerEl = textareaEl || inputEl;
                  let fieldType = (f.type || '').toString().toLowerCase();
                  if (!fieldType && textareaEl) {
                    fieldType = 'textarea';
                  } else if (!fieldType && inputEl) {
                    fieldType = 'text';
                  }
                  if (fieldType === 'long_text' || fieldType === 'paragraph') {
                    fieldType = 'textarea';
                  } else if (fieldType === 'short_text') {
                    fieldType = 'text';
                  }
                  let options = [];
                  const optionTypes = optionEls.map((el) => (el.getAttribute('type') || '').toLowerCase());
                  const hasChoiceInputs = optionTypes.some((t) => t === 'radio' || t === 'checkbox');
                  if (hasChoiceInputs) {
                    fieldType = 'multiple_choice';
                    options = optionEls.map((el) => {
                      const label = el.closest('label');
                      const text = label ? label.innerText.trim() : (el.getAttribute('aria-label') || el.value || '').trim();
                      return {
                        value: el.value || '',
                        text,
                      };
                    });
                    if (!answerEl && optionEls.length) {
                      answerEl = optionEls[0];
                    }
                  } else if (!fieldType) {
                    fieldType = textareaEl ? 'textarea' : 'text';
                  }
                  const answerSelector = answerEl ? pickSelector(answerEl, (answerEl.tagName === 'TEXTAREA') ? 'textarea' : 'input') : null;
                  questions.push({
                    prompt: String(f.text || '').trim(),
                    required: !!f.required,
                    answerSelector,
                    fieldName: answerName,
                    fieldType,
                    options,
                  });
                });
              });

              // Second pass: capture standalone custom card fields from rendered HTML
              // These appear in data-qa="additional-cards" sections and aren't in baseTemplate JSON
              const cardContainer = q('[data-qa="additional-cards"]');
              if (cardContainer) {
                // Find all select and input elements within card sections
                const cardSelects = qa('[data-qa="additional-cards"] select[name^="cards["]');
                const cardInputs = qa('[data-qa="additional-cards"] input[name^="cards["][type="text"], [data-qa="additional-cards"] input[name^="cards["][type="email"], [data-qa="additional-cards"] input[name^="cards["][type="tel"]');
                const cardTextareas = qa('[data-qa="additional-cards"] textarea[name^="cards["]');
                const cardRadios = qa('[data-qa="additional-cards"] input[name^="cards["][type="radio"]');

                // Process select dropdowns
                cardSelects.forEach((selectEl) => {
                  const name = selectEl.name;
                  if (!name) return;
                  // Extract label from the question container
                  const questionContainer = selectEl.closest('.application-question');
                  const labelEl = questionContainer?.querySelector('.application-label .text');
                  const prompt = labelEl ? labelEl.textContent.trim() : name;
                  const required = selectEl.hasAttribute('required');
                  const opts = Array.from(selectEl.querySelectorAll('option'))
                    .filter((opt) => opt.value) // Skip empty "Select..." options
                    .map((opt) => ({
                      value: opt.value || '',
                      text: (opt.textContent || '').trim()
                    }));
                  if (opts.length > 0) {
                    questions.push({
                      prompt,
                      required,
                      answerSelector: pickSelector(selectEl, 'select'),
                      fieldName: name,
                      fieldType: 'select',
                      options: opts,
                    });
                  }
                });

                // Process text inputs
                cardInputs.forEach((inputEl) => {
                  const name = inputEl.name;
                  if (!name) return;
                  const questionContainer = inputEl.closest('.application-question');
                  const labelEl = questionContainer?.querySelector('.application-label .text');
                  const prompt = labelEl ? labelEl.textContent.trim() : name;
                  const required = inputEl.hasAttribute('required');
                  questions.push({
                    prompt,
                    required,
                    answerSelector: pickSelector(inputEl, 'input'),
                    fieldName: name,
                    fieldType: 'text',
                    options: [],
                  });
                });

                // Process textareas
                cardTextareas.forEach((textareaEl) => {
                  const name = textareaEl.name;
                  if (!name) return;
                  const questionContainer = textareaEl.closest('.application-question');
                  const labelEl = questionContainer?.querySelector('.application-label .text');
                  const prompt = labelEl ? labelEl.textContent.trim() : name;
                  const required = textareaEl.hasAttribute('required');
                  questions.push({
                    prompt,
                    required,
                    answerSelector: pickSelector(textareaEl, 'textarea'),
                    fieldName: name,
                    fieldType: 'textarea',
                    options: [],
                  });
                });

                // Process radio button groups
                const radioGroupMap = new Map();
                cardRadios.forEach((radioEl) => {
                  const name = radioEl.name;
                  if (!name) return;
                  if (!radioGroupMap.has(name)) {
                    const questionContainer = radioEl.closest('.application-question');
                    const labelEl = questionContainer?.querySelector('.application-label .text');
                    const prompt = labelEl ? labelEl.textContent.trim() : name;
                    const required = radioEl.hasAttribute('required');
                    radioGroupMap.set(name, {
                      prompt,
                      required,
                      answerSelector: null,
                      fieldName: name,
                      fieldType: 'multiple_choice',
                      options: [],
                    });
                  }
                  const group = radioGroupMap.get(name);
                  if (!group.answerSelector) {
                    group.answerSelector = pickSelector(radioEl, 'input');
                  }
                  const lbl = radioEl.closest('label');
                  const text = lbl ? lbl.innerText.trim() : (radioEl.getAttribute('aria-label') || radioEl.value || '');
                  if (text || radioEl.value) {
                    group.options.push({
                      value: radioEl.value || text,
                      text,
                    });
                  }
                });
                radioGroupMap.forEach((group) => {
                  questions.push(group);
                });
              }

              const eeoFields = [];
              qa("select[name^='eeo[']").forEach((el) => {
                const labelContainer = el.closest('.application-question')?.querySelector('.application-label') || el.closest('label')?.querySelector('.application-label');
                const labelText = labelContainer ? labelContainer.textContent.trim() : el.getAttribute('aria-label') || el.name;
                const opts = Array.from(el.querySelectorAll('option'))
                  .map((opt) => ({ value: opt.value || '', text: (opt.textContent || '').trim() }))
                  .filter((opt) => opt.value || opt.text);
                eeoFields.push({
                  name: el.name,
                  label: labelText,
                  fieldType: 'select',
                  selector: pickSelector(el, 'select'),
                  options: opts,
                });
              });
              const radioGroups = new Map();
              qa("input[type='radio'][name^='eeo[']").forEach((inputEl) => {
                const name = inputEl.name;
                if (!radioGroups.has(name)) {
                  const fieldLabel = inputEl.closest('.application-question')?.querySelector('.application-label');
                  const labelText = fieldLabel ? fieldLabel.textContent.trim() : name;
                  radioGroups.set(name, {
                    name,
                    label: labelText,
                    fieldType: 'radio',
                    selector: pickSelector(inputEl, 'input'),
                    options: [],
                  });
                }
                const group = radioGroups.get(name);
                if (!group.selector) {
                  group.selector = pickSelector(inputEl, 'input');
                }
                const lbl = inputEl.closest('label');
                const text = lbl ? lbl.innerText.trim() : (inputEl.getAttribute('aria-label') || inputEl.value || '');
                if (!text && !inputEl.value) return;
                group.options.push({ value: inputEl.value || text, text });
              });
              radioGroups.forEach((group) => {
                eeoFields.push(group);
              });

              // FINAL PASS: Universal catch-all for any remaining form fields
              // This ensures we capture fields like opportunityLocationId that don't match specific patterns
              const formEl = q('form#application-form') || q('form');
              if (formEl) {
                const seenNames = new Set();

                // Track already-captured field names to avoid duplicates
                questions.forEach(q => q.fieldName && seenNames.add(q.fieldName));
                // Contact fields: track by extracting 'name' attribute from each selector
                Object.values(contact).forEach(sel => {
                  const match = sel && sel.match(/name=['"]([^'"]+)['"]/);
                  if (match) seenNames.add(match[1]);
                });
                // Also track the contact object keys themselves (name, email, phone, location, org, etc.)
                Object.keys(contact).forEach(fieldKey => {
                  seenNames.add(fieldKey);
                  // Also add common variations
                  if (fieldKey === 'org') seenNames.add('organization');
                });
                Object.keys(links).forEach(name => seenNames.add(name));
                eeoFields.forEach(f => seenNames.add(f.name));

                // IMPORTANT: Reserve cover letter fields for dedicated handler (runs later in Python)
                // This prevents universal scanner from filling them with generic answers
                const coverLetterEl = q('textarea[name="comments"]') || q('#additional-information');
                if (coverLetterEl) {
                  if (coverLetterEl.name) seenNames.add(coverLetterEl.name);
                  if (coverLetterEl.id) seenNames.add(coverLetterEl.id);
                  seenNames.add('comments');
                  seenNames.add('additional-information');
                }

                // Helper to extract label text for any field
                const extractLabel = (el) => {
                  const questionContainer = el.closest('.application-question');
                  if (questionContainer) {
                    const labelEl = questionContainer.querySelector('.application-label .text') ||
                                    questionContainer.querySelector('.application-label');
                    if (labelEl) return labelEl.textContent.trim();
                  }
                  const label = el.closest('label');
                  if (label) return label.textContent.trim();
                  return el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.name || '';
                };

                // Scan all select dropdowns in the form
                const allSelects = qa('form select[name]');
                allSelects.forEach(selectEl => {
                  if (seenNames.has(selectEl.name)) return;
                  if (!selectEl.name) return;

                  const prompt = extractLabel(selectEl);
                  const required = selectEl.hasAttribute('required');
                  const opts = Array.from(selectEl.querySelectorAll('option'))
                    .filter((opt) => opt.value) // Skip empty "Select..." options
                    .map((opt) => ({
                      value: opt.value || '',
                      text: (opt.textContent || '').trim()
                    }));

                  if (opts.length > 0 && prompt) {
                    questions.push({
                      prompt,
                      required,
                      answerSelector: pickSelector(selectEl, 'select'),
                      fieldName: selectEl.name,
                      fieldType: 'select',
                      options: opts,
                    });
                    seenNames.add(selectEl.name);
                  }
                });

                // Scan all text/email/tel inputs in the form
                const allInputs = qa('form input[name][type="text"], form input[name][type="email"], form input[name][type="tel"], form input[name]:not([type])');
                allInputs.forEach(inputEl => {
                  if (seenNames.has(inputEl.name)) return;
                  if (!inputEl.name) return;
                  if (inputEl.type === 'hidden' || inputEl.type === 'file') return;

                  const prompt = extractLabel(inputEl);
                  const required = inputEl.hasAttribute('required');

                  if (prompt) {
                    questions.push({
                      prompt,
                      required,
                      answerSelector: pickSelector(inputEl, 'input'),
                      fieldName: inputEl.name,
                      fieldType: 'text',
                      options: [],
                    });
                    seenNames.add(inputEl.name);
                  }
                });

                // Scan all textareas in the form
                const allTextareas = qa('form textarea[name]');
                allTextareas.forEach(textareaEl => {
                  if (seenNames.has(textareaEl.name)) return;
                  if (!textareaEl.name) return;

                  const prompt = extractLabel(textareaEl);
                  const required = textareaEl.hasAttribute('required');

                  if (prompt) {
                    questions.push({
                      prompt,
                      required,
                      answerSelector: pickSelector(textareaEl, 'textarea'),
                      fieldName: textareaEl.name,
                      fieldType: 'textarea',
                      options: [],
                    });
                    seenNames.add(textareaEl.name);
                  }
                });

                // Scan all radio button groups in the form
                const catchAllRadioGroups = new Map();
                qa('form input[type="radio"][name]').forEach(radioEl => {
                  if (seenNames.has(radioEl.name)) return;
                  if (!radioEl.name) return;

                  if (!catchAllRadioGroups.has(radioEl.name)) {
                    const prompt = extractLabel(radioEl);
                    const required = radioEl.hasAttribute('required');
                    catchAllRadioGroups.set(radioEl.name, {
                      prompt,
                      required,
                      answerSelector: null,
                      fieldName: radioEl.name,
                      fieldType: 'multiple_choice',
                      options: [],
                    });
                  }
                  const group = catchAllRadioGroups.get(radioEl.name);
                  if (!group.answerSelector) {
                    group.answerSelector = pickSelector(radioEl, 'input');
                  }
                  const lbl = radioEl.closest('label');
                  const text = lbl ? lbl.innerText.trim() : (radioEl.getAttribute('aria-label') || radioEl.value || '');
                  if (text || radioEl.value) {
                    group.options.push({
                      value: radioEl.value || text,
                      text,
                    });
                  }
                });
                catchAllRadioGroups.forEach((group) => {
                  if (group.prompt && group.options.length > 0) {
                    questions.push(group);
                    seenNames.add(group.fieldName);
                  }
                });

                // Scan all standalone checkboxes in the form
                // Important: handle consent/agreement checkboxes that are often required
                const allCheckboxes = qa('form input[type="checkbox"][name]');
                allCheckboxes.forEach(checkboxEl => {
                  if (seenNames.has(checkboxEl.name)) return;
                  if (!checkboxEl.name) return;

                  const prompt = extractLabel(checkboxEl);
                  const required = checkboxEl.hasAttribute('required');

                  if (prompt) {
                    // Check if this is a consent/agreement checkbox
                    const promptLower = prompt.toLowerCase();
                    const nameLower = checkboxEl.name.toLowerCase();
                    const isConsent = nameLower.includes('consent')
                                      || nameLower.includes('agree')
                                      || promptLower.includes('agree')
                                      || promptLower.includes('concordo')
                                      || promptLower.includes('aceito')
                                      || promptLower.includes('privacy')
                                      || promptLower.includes('terms');

                    if (required && isConsent) {
                      // Auto-check required consent boxes (GDPR, privacy policy, terms of service)
                      // These are typically mandatory for form submission
                      try {
                        checkboxEl.checked = true;
                        checkboxEl.dispatchEvent(new Event('change', { bubbles: true }));
                      } catch (e) {
                        // If auto-check fails, add to questions for manual handling
                        questions.push({
                          prompt,
                          required,
                          answerSelector: pickSelector(checkboxEl, 'input'),
                          fieldName: checkboxEl.name,
                          fieldType: 'checkbox',
                          options: [],
                        });
                      }
                    } else {
                      // Optional checkboxes or non-consent checkboxes: add to questions
                      questions.push({
                        prompt,
                        required,
                        answerSelector: pickSelector(checkboxEl, 'input'),
                        fieldName: checkboxEl.name,
                        fieldType: 'checkbox',
                        options: [],
                      });
                    }
                    seenNames.add(checkboxEl.name);
                  }
                });
              }

              const submitEl = q('button#btn-submit');
              const captchaEl = q('div#h-captcha');

              return JSON.stringify({
                resumeInput: pickSelector(resumeEl),
                contactFields: contact,
                linkFields: links,
                dynamicQuestions: questions,
                eeoFields: eeoFields,
                submitButton: pickSelector(submitEl, 'button') || 'button#btn-submit',
                captchaSelector: captchaEl ? pickSelector(captchaEl, 'div') : null,
              });
            }
            """
        )
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except Exception:
                data = {}
        else:
            data = payload or {}

        resume_input = data.get("resumeInput") or "input[name='resume']"
        contact_fields = data.get("contactFields") or {}
        link_fields = data.get("linkFields") or {}
        questions_raw = data.get("dynamicQuestions") or []
        dynamic_questions: list[DynamicQuestion] = []
        for q in questions_raw:
            prompt = str(q.get("prompt", "")).strip()
            if not prompt:
                continue
            answer_selector = q.get("answerSelector")
            field_name = q.get("fieldName")
            field_type = str(q.get("fieldType", "")).strip().lower()
            if field_type in {"long_text", "paragraph"}:
                field_type = "textarea"
            elif field_type in {"multiple-choice"}:
                field_type = "multiple_choice"
            elif field_type == "short_text":
                field_type = "text"
            elif not field_type:
                field_type = (
                    "textarea"
                    if (isinstance(answer_selector, str) and "textarea" in answer_selector)
                    else "text"
                )
            options_map: dict[str, str] = {}
            option_pairs: list[tuple[str, str]] = []
            for opt in q.get("options", []) or []:
                opt_text = str(opt.get("text", "")).strip()
                opt_value = str(opt.get("value", "")).strip()
                if not opt_text and not opt_value:
                    continue
                option_pairs.append((opt_value or opt_text, opt_text))
                for key in (opt_text, opt_value):
                    normalized = _normalize_choice_key(key)
                    if normalized:
                        options_map[normalized] = opt_value or opt_text
            dynamic_questions.append(
                DynamicQuestion(
                    prompt=prompt,
                    required=bool(q.get("required", False)),
                    cache_key=_normalize_question_key(prompt),
                    answer_selector=str(answer_selector) if answer_selector else None,
                    field_name=str(field_name) if field_name else None,
                    field_type=field_type,
                    options=options_map,
                    option_pairs=option_pairs,
                )
            )
        eeo_fields_raw = data.get("eeoFields") or []
        eeo_fields: list[EeoField] = []
        for entry in eeo_fields_raw:
            name = str(entry.get("name") or "").strip()
            if not name:
                continue
            field_type = str(entry.get("fieldType", "select")).strip().lower()
            if field_type == "multiple-choice":
                field_type = "radio"
            label = str(entry.get("label") or name).strip()
            selector = entry.get("selector")
            options_map: dict[str, str] = {}
            option_pairs: list[tuple[str, str]] = []
            for opt in entry.get("options", []) or []:
                opt_text = str(opt.get("text", "")).strip()
                opt_value = str(opt.get("value", "")).strip()
                if not opt_text and not opt_value:
                    continue
                option_pairs.append((opt_value or opt_text, opt_text))
                for key in (opt_text, opt_value):
                    normalized = _normalize_choice_key(key)
                    if normalized:
                        options_map[normalized] = opt_value or opt_text
            eeo_fields.append(
                EeoField(
                    name=name,
                    label=label,
                    field_type="radio" if field_type == "radio" else "select",
                    selector=str(selector) if selector else None,
                    options=options_map,
                    option_pairs=option_pairs,
                )
            )
        return LeverFormPlan(
            resume_input=resume_input,
            contact_fields={str(k): str(v) for k, v in contact_fields.items()},
            link_fields={str(k): str(v) for k, v in link_fields.items()},
            dynamic_questions=dynamic_questions,
            eeo_fields=eeo_fields,
            submit_button=str(data.get("submitButton", "button#btn-submit")),
            captcha_selector=(
                str(data.get("captchaSelector")) if data.get("captchaSelector") else None
            ),
        )

    async def execute_in_browser(
        self,
        *,
        session: BrowserSession,
        profile: Profile,
        item: ApplicationItem,
        mode: str,
        review_mode: bool = False,
    ) -> Artifacts | Reason:
        """Open the apply URL in the given session, fill, and optionally submit.

        Args:
            session: Active browser session.
            profile: User profile with defaults and credentials.
            item: Application item being processed.
            mode: "auto" or "supervised" mode indicator.
            review_mode: If True, save pre-submit artifacts and pause without submitting.

        Returns:
            Artifacts on success or Reason on failure/review.
        """
        apply_url = item.details.apply_url if item.details and item.details.apply_url else item.url
        ensure_allowed_domain(apply_url, self._options.allowed_domains)

        page = await session.get_current_page() or await session.new_page()
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
        await _wait_for_any(
            page, ["form#application-form", "#application"]
        )  # removed presence-only captcha wait
        try:
            state = await _hcaptcha_state(page)
            if state.get("present") and not state.get("visible"):
                log_event("captcha.present", visible=False)
            elif state.get("visible"):
                log_event("captcha.present", visible=True)
        except Exception:
            pass

        plan = await self.build_plan_in_browser(page)

        # Track all filled values for saving to pre.json
        filled_values: dict[str, str] = {}

        # Upload resume FIRST to prevent form resets from clearing fields filled earlier
        # (Lever's resume processing can trigger JavaScript that resets form state)
        resume_path = str(profile.resolve_resume_path())
        uploaded = await _upload_resume(session, page, plan.resume_input, resume_path)
        if not uploaded:
            try:
                if await _wait_for_resume_upload(page, plan.resume_input, timeout=1.0):
                    uploaded = True
            except Exception:
                pass

        if not uploaded and mode != "auto":
            print(
                "Resume upload not detected. Please attach manually in the browser, then press Enter…"
            )
            try:
                await asyncio.sleep(1.0)
            except Exception:
                pass
            try:
                uploaded = await _wait_for_resume_upload(page, plan.resume_input, timeout=5.0)
            except Exception:
                pass

        if not uploaded:
            try:
                if await _wait_for_resume_upload(page, plan.resume_input, timeout=1.0):
                    uploaded = True
            except Exception:
                pass

        resume_detection_failed = not uploaded
        if resume_detection_failed:
            try:
                log_event("resume_upload.review_required", mode=mode)
            except Exception:
                pass

        # Fill contact fields from profile defaults (with sensible fallbacks)
        name_value = profile.defaults.get("name") or profile.name
        if plan.contact_fields.get("name"):
            await _fill_if_available(page, plan.contact_fields.get("name"), name_value)
            filled_values["name"] = name_value

        email_value = profile.defaults.get("email")
        if plan.contact_fields.get("email") and email_value:
            await _fill_if_available(page, plan.contact_fields.get("email"), email_value)
            filled_values["email"] = email_value

        phone_value = profile.defaults.get("phone")
        if plan.contact_fields.get("phone") and phone_value:
            await _fill_if_available(page, plan.contact_fields.get("phone"), phone_value)
            filled_values["phone"] = phone_value

        # Current company/org
        org_value = profile.defaults.get("current_company") or profile.defaults.get("company")
        org_selector = plan.contact_fields.get("org") or "input[data-qa='org-input'][name='org']"
        if org_value:
            await _fill_if_available(page, org_selector, org_value)
            filled_values["org"] = org_value

        # Fill location field AFTER resume upload to avoid being cleared by form resets
        location_value = profile.defaults.get("location")
        location_valid = await _set_structured_location(
            page,
            input_selector=plan.contact_fields.get("location") or "#location-input",
            hidden_selector=plan.contact_fields.get("location_hidden") or "#selected-location",
            value=location_value,
        )
        if location_valid and location_value:
            filled_values["location"] = location_value
        if not location_valid and mode != "auto":
            log_event("form.location.needs_manual_selection", mode=mode)
            print(
                "⚠️  Location field needs manual selection from dropdown. Please select a location from the suggestions."
            )

        # Pronouns (optional checkboxes). Supports single string or comma-separated list.
        pronouns_raw = profile.defaults.get("pronouns")
        if pronouns_raw:
            await _set_pronouns(page, pronouns_raw)

        # Fill link fields if defaults contain recognizable keys
        for field_name, selector in plan.link_fields.items():
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
                filled_values[field_name] = value

        # Dynamic questions (text inputs, selects, radios, and long-form textareas)
        if plan.dynamic_questions:
            try:
                client = OpenRouterClient.from_settings()
            except OpenRouterError:
                client = None
            prompt_builder = PromptBuilder(profile=profile)
            for q in plan.dynamic_questions:
                field_type = (q.field_type or "textarea").lower()
                if field_type == "multiple_choice":
                    desired = _default_choice_answer(profile, q)
                    # LLM fallback if no profile match found
                    if not desired and client and q.option_pairs:
                        # Build prompt with options for LLM to choose from
                        options_text = (
                            "\n".join([f"- {opt[1]}" for opt in q.option_pairs])
                            if q.option_pairs
                            else ""
                        )
                        plan_msg = prompt_builder.build_question_prompt(
                            question=Question(
                                id=q.cache_key,
                                text=f"{q.prompt}\n\nAvailable options:\n{options_text}\n\nRespond with ONLY the exact text of one option above.",
                                required=q.required,
                            ),
                            job=item.details or JobDetails(),
                            extra_context=None,
                        )
                        try:
                            desired = client.complete(plan_msg.messages)
                        except Exception:
                            desired = None
                    value = None
                    if desired:
                        value = q.options.get(_normalize_choice_key(desired))
                        if value is None:
                            normalized = _normalize_yes_no_value(desired)
                            if normalized:
                                value = q.options.get(_normalize_choice_key(normalized))
                        # Fuzzy match for yes/no answers: if profile says "No" and option contains "no", match it
                        if value is None and normalized:
                            norm_lower = normalized.lower()
                            for opt_key, opt_value in q.options.items():
                                if norm_lower == "yes" and (
                                    "yes" in opt_key.lower() or "required" in opt_key.lower()
                                ):
                                    value = opt_value
                                    break
                                elif norm_lower == "no" and (
                                    "no" in opt_key.lower()
                                    or "not" in opt_key.lower()
                                    or "don't" in opt_key.lower()
                                ):
                                    value = opt_value
                                    break
                    if value is not None and q.field_name:
                        await _select_choice_option(page, q.field_name, value)
                        filled_values[q.field_name] = value
                    continue
                if field_type == "select":
                    # Handle select dropdowns (common in custom Lever cards)
                    # Try to match from profile defaults first, then use LLM if needed
                    desired = _default_choice_answer(profile, q)
                    if not desired and client:
                        # Build prompt with options for LLM to choose from
                        options_text = (
                            "\n".join([f"- {opt[1]}" for opt in q.option_pairs])
                            if q.option_pairs
                            else ""
                        )
                        plan_msg = prompt_builder.build_question_prompt(
                            question=Question(
                                id=q.cache_key,
                                text=f"{q.prompt}\n\nAvailable options:\n{options_text}\n\nRespond with ONLY the exact text of one option above.",
                                required=q.required,
                            ),
                            job=item.details or JobDetails(),
                            extra_context=None,
                        )
                        try:
                            desired = client.complete(plan_msg.messages)
                        except Exception:
                            desired = None
                    if desired and q.answer_selector:
                        await _set_select_value(page, q.answer_selector, desired)
                        filled_values[q.answer_selector] = desired
                    continue
                if field_type == "text":
                    text_answer = _default_text_answer(profile, q)
                    # LLM fallback if no profile match found
                    if not text_answer and client:
                        plan_msg = prompt_builder.build_question_prompt(
                            question=Question(id=q.cache_key, text=q.prompt, required=q.required),
                            job=item.details or JobDetails(),
                            extra_context=None,
                        )
                        try:
                            text_answer = client.complete(plan_msg.messages)
                        except Exception:
                            text_answer = None
                    if text_answer and q.answer_selector:
                        await _fill_if_available(page, q.answer_selector, text_answer)
                        filled_values[q.answer_selector] = text_answer
                    continue
                if field_type == "checkbox":
                    # Handle checkbox fields (consent, agreements, optional preferences)
                    # Most required consents are auto-checked in JavaScript, but handle any that slip through
                    log_event(
                        "form.checkbox.start",
                        prompt=q.prompt[:80] if q.prompt else None,
                        selector=q.answer_selector,
                    )
                    if q.answer_selector:
                        try:
                            # Check the checkbox
                            await page.evaluate(
                                f"""(sel) => {{
                                    const el = document.querySelector(sel);
                                    if (el && !el.checked) {{
                                        el.checked = true;
                                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }}({json.dumps(q.answer_selector)})"""
                            )
                            filled_values[q.answer_selector] = "checked"
                            log_event("form.checkbox.tracked", selector=q.answer_selector)
                        except Exception as exc:
                            log_event(
                                "form.checkbox.failed",
                                selector=q.answer_selector,
                                error=str(exc),
                            )
                    continue

                # Treat remaining questions as long-form text areas
                answer: str | None = _default_text_answer(profile, q)
                if not answer and client:
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
                    answer = profile.prompts.get("fallback_answer") or profile.prompts.get(
                        "default_long_form"
                    )
                if answer and q.answer_selector:
                    await _fill_textarea(page, q.answer_selector, answer)
                    filled_values[q.answer_selector] = answer

        if plan.eeo_fields:
            eeo_values = await _fill_eeo_fields(page, plan.eeo_fields, profile)
            filled_values.update(eeo_values)
            disability_sig = await _fill_disability_signature(page, profile)
            if disability_sig:
                filled_values.update(disability_sig)

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
                exists_named = await page.evaluate(
                    "() => !!document.querySelector('textarea[name=\\'comments\\']')"
                )
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
                    {
                        "role": "system",
                        "content": (
                            "You write concise, tailored cover letters. 180-220 words, positive, specific, no fluff. "
                            "Include a sentence on impact, a brief skills-to-role bridge, and a polite close."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "job": job.to_dict(),
                                "profile": {
                                    "name": profile.name,
                                    "resume_summary": profile.prompts.get("resume_summary"),
                                    "key_accomplishments": profile.prompts.get(
                                        "key_accomplishments"
                                    ),
                                    **profile_links,
                                },
                                "hint": profile.prompts.get("cover_letter"),
                            },
                            ensure_ascii=False,
                        ),
                    },
                ]
                cover_text = client.complete(messages, temperature=0.2)
            except Exception:
                cover_text = profile.prompts.get("cover_letter")
            if cover_text:
                await _fill_textarea(page, cover_selector, cover_text)
                filled_values[cover_selector] = cover_text

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
                await _apply_llm_assist(
                    page, profile=profile, job=item.details, invalid_fields=invalid_fields
                )
            if not await _form_check_validity(page):
                return Reason(code="validation_failed", message="Form still invalid after autofill")

        # After validation and AI assist, show review message if resume wasn't confirmed
        if resume_detection_failed:
            review_message = (
                "⚠️  Resume upload could not be confirmed automatically. "
                "Please verify the resume is attached, then press Enter to submit."
            )
            if mode != "auto":
                pause_reason = await _supervised_pause(prompt=review_message)
                if pause_reason is not None:
                    return pause_reason
            else:
                print(review_message)
                try:
                    await asyncio.sleep(5.0)
                except Exception:
                    pass

        # Review-mode: capture pre-submission artifacts and pause
        if review_mode:
            log_event("apply.review_mode.start", item_id=item.id, profile=profile.id)
            try:
                pre_json_path, pre_screenshot_path = await capture_pre_artifacts(
                    session, page, profile, item, plan, filled_values
                )
                log_event(
                    "review_mode.artifacts_captured",
                    item_id=item.id,
                    pre_json=str(pre_json_path),
                    pre_screenshot=str(pre_screenshot_path),
                )
                return Reason(
                    code="saved_for_review",
                    message="Form filled and saved for review. Submit manually or use resume-job --submit.",
                )
            except Exception as exc:
                log_event("review_mode.artifacts_failed", error=str(exc))
                return Reason(
                    code="review_failed", message=f"Failed to capture review artifacts: {exc}"
                )

        # Supervised pause before submit (robust to non-interactive stdin)
        if mode != "auto":
            pause_reason = await _supervised_pause()
            if pause_reason is not None:
                return pause_reason

        # Submit and capture confirmation
        await _click(page, plan.submit_button)
        await asyncio.sleep(2.0)
        # hCaptcha check after click
        # Detect blocking captcha only after submit attempt, using visibility/overlay heuristics
        try:
            cstate = await _hcaptcha_state(page)
            if cstate.get("blocking"):
                log_event("captcha.blocking_visible", details=cstate)
                # Capture pre-submission artifacts before failing
                try:
                    await capture_pre_artifacts(session, page, profile, item, plan, filled_values)
                    log_event("captcha.artifacts_captured", item_id=item.id)
                except Exception as exc:
                    log_event("captcha.artifacts_failed", error=str(exc))
                return Reason(
                    code="captcha_blocked", message="hCaptcha visible and blocking submission"
                )
        except Exception:
            pass

        # Post-submit sanity: page should either navigate or hide form
        still_has_form = await page.evaluate(
            "() => !!document.querySelector('form#application-form')"
        )
        if still_has_form:
            # If form remains, re-check validity â€" likely a client-side validation
            if not await _form_check_validity(page):
                return Reason(
                    code="validation_failed", message="Client-side validation blocked submission"
                )

        confirmation_text = await _extract_confirmation_text(page)

        # Capture post-submission screenshot
        post_screenshot_path = None
        try:
            post_path = await capture_post_screenshot(session, page, profile, item)
            post_screenshot_path = str(post_path)
        except Exception as exc:
            log_event("artifacts.post_screenshot.error", error=str(exc))

        # Save confirmation data to confirmation.json
        try:
            from datetime import datetime

            settings = load_settings()
            artifacts_dir = settings.artifacts_path(profile.id) / item.id
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            confirmation_json_path = artifacts_dir / "confirmation.json"

            confirmation_payload = {
                "confirmation_text": confirmation_text[:500] if confirmation_text else "submitted",
                "confirmation_id": None,
                "captured_at": datetime.now().isoformat(),
            }
            saved_state.write_confirmation(confirmation_json_path, confirmation_payload)
            log_event("artifacts.confirmation.saved", path=str(confirmation_json_path))
        except Exception as exc:
            log_event("artifacts.confirmation.failed", error=str(exc))

        artifacts = Artifacts(
            confirmation_text=(confirmation_text[:500] if confirmation_text else "submitted"),
            confirmation_id=None,
            screenshot_after_path=post_screenshot_path,
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
    except Exception as e:
        try:
            log_event("evaluate_quiet.fallback", error=str(e), error_type=type(e).__name__)
        except Exception:
            pass
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
                        await cdp.send.Target.closeTarget(
                            params={"targetId": target_id}, session_id=sid
                        )
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


async def _upload_resume(session: BrowserSession | None, page, selector: str, path: str) -> bool:
    """Attach a resume file using best available mechanism and wait for success.

    Strategy (in order):
    1) Playwright locator.set_input_files if available
    2) Playwright page.set_input_files if available
    3) File chooser flow: click the visible button and set files on chooser
    After attempting, wait for UI signals that upload succeeded.
    """
    # Ensure input exists in DOM
    backend_id = None  # may be populated by LLM locator for CDP fallback
    try:
        await page.get_elements_by_css_selector(selector)
    except Exception:
        return False
    # Capabilities snapshot for diagnostics
    try:
        caps = {
            "has_locator": bool(getattr(page, "locator", None)),
            "has_set_input_files": bool(getattr(page, "set_input_files", None)),
            "has_frame_locator": bool(getattr(page, "frame_locator", None)),
            "has_expect_file_chooser": bool(getattr(page, "expect_file_chooser", None)),
            "has_event_bus": bool(getattr(session, "event_bus", None))
            if session is not None
            else False,
        }
        log_event("resume_upload.start", selector=selector, capabilities=caps)
    except Exception:
        pass

    # 1) Locator-based API (works even if input is hidden)
    try:
        if hasattr(page, "locator"):
            try:
                log_event("resume_upload.attempt", method="locator", selector=selector)
            except Exception:
                pass
            await page.locator(selector).set_input_files(path)
            ok = await _wait_for_resume_upload(page, selector)
            if ok:
                try:
                    log_event("resume_upload.success", method="locator")
                except Exception:
                    pass
                return True
    except Exception:
        pass

    # 2) Page-level API
    try:
        if hasattr(page, "set_input_files"):
            try:
                log_event("resume_upload.attempt", method="page", selector=selector)
            except Exception:
                pass
            await page.set_input_files(selector, path)
            ok = await _wait_for_resume_upload(page, selector)
            if ok:
                try:
                    log_event("resume_upload.success", method="page")
                except Exception:
                    pass
                return True
    except Exception:
        pass

    # 2b) Frame-scoped attempt (Playwright only)
    try:
        if hasattr(page, "frame_locator") and hasattr(page, "locator"):
            # Try a handful of iframes
            for i in range(0, 20):
                try:
                    try:
                        log_event("resume_upload.attempt", method="frame_locator", index=i)
                    except Exception:
                        pass
                    frame_loc = page.frame_locator("iframe").nth(i)
                    # Best-effort: ensure the input is present before setting files
                    try:
                        exists = await frame_loc.locator(selector).count()
                        if hasattr(exists, "__await__"):
                            exists = await exists
                        if not exists:
                            continue
                    except Exception:
                        pass
                    loc = frame_loc.locator(selector)
                    await loc.set_input_files(path)
                    ok = await _wait_for_resume_upload(page, selector)
                    if ok:
                        try:
                            log_event("resume_upload.success", method="frame_locator", index=i)
                        except Exception:
                            pass
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    # 3) File chooser flow if supported (click visible button => chooser)
    try:
        # Some wrappers expose expect_file_chooser or wait_for_event('filechooser')
        if hasattr(page, "expect_file_chooser"):
            try:
                log_event("resume_upload.attempt", method="file_chooser")
            except Exception:
                pass
            async with page.expect_file_chooser() as fc_info:
                await page.evaluate(
                    "(sel) => { const btn = document.querySelector('a.visible-resume-upload') || document.querySelector(sel); if (btn) btn.click(); }",
                    selector,
                )
            fc = await fc_info
            await fc.set_files(path)
            ok = await _wait_for_resume_upload(page, selector)
            if ok:
                try:
                    log_event("resume_upload.success", method="file_chooser")
                except Exception:
                    pass
                return True
    except Exception:
        pass

    # 4) Optional: try clicking the anchor to reveal/recreate input, then set again
    try:
        try:
            log_event("resume_upload.attempt", method="click_anchor_then_retry")
        except Exception:
            pass
        await page.evaluate(
            "() => { const btn = document.querySelector('a.visible-resume-upload'); if (btn) btn.click(); }"
        )
        # Give the page a brief moment to render/recreate the input
        try:
            await asyncio.sleep(0.4)
        except Exception:
            pass
        # Refresh the selector in case the input was re-mounted
        try:
            new_selector = await page.evaluate(
                """
                () => {
                  const el = document.querySelector('input#resume-upload-input[name="resume"]')
                          || document.querySelector('input[name="resume"]')
                          || document.querySelector('input[type="file"]');
                  if (!el) return null;
                  if (el.id) return `#${el.id}`;
                  if (el.name) return `input[name='${el.name}']`;
                  return 'input[type="file"]';
                }
                """
            )
            if isinstance(new_selector, str) and new_selector:
                selector = new_selector
        except Exception:
            pass
        if hasattr(page, "locator"):
            await page.locator(selector).set_input_files(path)
            ok = await _wait_for_resume_upload(page, selector)
            if ok:
                try:
                    log_event("resume_upload.success", method="click_anchor_then_retry")
                except Exception:
                    pass
                return True
    except Exception:
        pass

    # 5) LLM-locator fallback (optional)
    try:
        import os

        use_llm = os.getenv("AUTO_APPLY_USE_LLM_LOCATOR", "0").strip() not in (
            "",
            "0",
            "false",
            "False",
        )
    except Exception:
        use_llm = False
    if use_llm:
        try:
            try:
                log_event("resume_upload.llm_locator.start", flag=True)
            except Exception:
                pass
            if hasattr(page, "must_get_element_by_prompt"):
                # Try to pass an explicit LLM if available; otherwise rely on defaults
                element = None
                try:
                    import os as _os

                    llm_obj = None
                    if _os.getenv("GOOGLE_API_KEY"):
                        try:
                            from browser_use.llm.google import (
                                ChatGoogle as _BUGemini,  # type: ignore
                            )

                            llm_obj = _BUGemini()
                        except Exception:
                            llm_obj = None
                    if llm_obj is None and (
                        _os.getenv("OPENROUTER_API_KEY") or _os.getenv("OPENAI_API_KEY")
                    ):
                        try:
                            if _os.getenv("OPENROUTER_API_KEY") and not _os.getenv(
                                "OPENAI_API_KEY"
                            ):
                                _os.environ["OPENAI_API_KEY"] = (
                                    _os.getenv("OPENROUTER_API_KEY") or ""
                                )
                                if not _os.getenv("OPENAI_BASE_URL") and not _os.getenv(
                                    "OPENAI_API_BASE"
                                ):
                                    _os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
                            from browser_use.llm.openai import ChatOpenAI as _BUChat

                            llm_obj = _BUChat()
                        except Exception:
                            llm_obj = None
                    if llm_obj is not None:
                        # Pass model from env if available to improve accuracy (OpenRouter/Google)
                        try:
                            import os as _os

                            model_name = _os.getenv("LLM_MODEL")
                            if model_name and hasattr(llm_obj, "model"):
                                try:
                                    llm_obj.model = (
                                        model_name  # best-effort; some clients accept assignment
                                    )
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        element = await page.must_get_element_by_prompt(
                            'the resume upload input element (the <input type=\\"file\\"> used to attach a resume) inside the application form; not the submit button',
                            llm=llm_obj,
                        )
                    else:
                        element = await page.must_get_element_by_prompt(
                            'the resume upload input element (the <input type=\\"file\\"> used to attach a resume) inside the application form; not the submit button',
                        )
                except Exception:
                    element = None
            else:
                try:
                    log_event("resume_upload.llm_locator.unavailable", reason="page_method_missing")
                except Exception:
                    pass
                element = None
            if element is None:
                # Retry with a couple of prompt variants to increase recall
                try:
                    alt_prompts = [
                        'the file upload control (input[type=\\"file\\"]) used to attach a resume/CV inside the application form',
                        "the resume/CV chooser input element in the application form",
                    ]
                    for ptxt in alt_prompts:
                        try:
                            if llm_obj is not None and hasattr(page, "must_get_element_by_prompt"):
                                element = await page.must_get_element_by_prompt(ptxt, llm=llm_obj)
                            elif hasattr(page, "must_get_element_by_prompt"):
                                element = await page.must_get_element_by_prompt(ptxt)
                            if element is not None:
                                break
                        except Exception:
                            element = None
                except Exception:
                    element = None
            if element is not None:
                new_selector = None
                try:
                    new_selector = getattr(element, "css_selector", None)
                except Exception:
                    new_selector = None
                try:
                    backend_id = getattr(element, "backend_node_id", None)
                except Exception:
                    backend_id = None
                try:
                    log_event(
                        "resume_upload.llm_locator.result",
                        css_selector=new_selector,
                        backend_node_id=backend_id,
                    )
                except Exception:
                    pass
                if isinstance(new_selector, str) and new_selector:
                    try:
                        if hasattr(page, "locator"):
                            await page.locator(new_selector).set_input_files(path)
                            ok = await _wait_for_resume_upload(page, new_selector)
                            if ok:
                                try:
                                    log_event("resume_upload.success", method="llm_selector")
                                except Exception:
                                    pass
                                return True
                    except Exception:
                        pass
                    try:
                        if hasattr(page, "set_input_files"):
                            await page.set_input_files(new_selector, path)
                            ok = await _wait_for_resume_upload(page, new_selector)
                            if ok:
                                try:
                                    log_event("resume_upload.success", method="llm_selector_page")
                                except Exception:
                                    pass
                                return True
                    except Exception:
                        pass
                try:
                    if hasattr(page, "expect_file_chooser"):
                        async with page.expect_file_chooser() as fc_info:
                            try:
                                await page.evaluate(
                                    "(sel) => { const el = document.querySelector(sel); if (el) el.click(); }",
                                    new_selector or selector,
                                )
                            except Exception:
                                await page.evaluate(
                                    "() => { const btn = document.querySelector('a.visible-resume-upload'); if (btn) btn.click(); }",
                                )
                        fc = await fc_info
                        await fc.set_files(path)
                        ok = await _wait_for_resume_upload(page, new_selector or selector)
                        if ok:
                            try:
                                log_event("resume_upload.success", method="llm_file_chooser")
                            except Exception:
                                pass
                            return True
                except Exception:
                    pass
            else:
                try:
                    log_event(
                        "resume_upload.llm_locator.result", css_selector=None, backend_node_id=None
                    )
                except Exception:
                    pass
        except Exception as _e:
            try:
                log_event("resume_upload.llm_locator.error", error=str(_e))
            except Exception:
                pass

    # 6) CDP fallback (best-effort)
    try:
        try:
            log_event("resume_upload.cdp.start", selector=selector)
        except Exception:
            pass
        if await _cdp_set_file_input_files(
            page, selector, path, backend_node_id=backend_id, session=session
        ):
            # Nudge UI listeners in case the widget needs explicit events
            try:
                await _dispatch_file_input_events(page, selector)
            except Exception:
                pass
            ok = await _wait_for_resume_upload(page, selector)
            if ok:
                try:
                    log_event("resume_upload.success", method="cdp")
                except Exception:
                    pass
                return True
    except Exception as e:
        try:
            log_event("resume_upload.cdp.error", error=str(e))
        except Exception:
            pass

    # 7) Event-bus upload fallback (browser-use CDP sessions)
    try:
        if session is not None:
            try:
                log_event("resume_upload.eventbus.start")
            except Exception:
                pass
            ok = await _eventbus_upload_resume(session, selector, path)
            if ok:
                done = await _wait_for_resume_upload(page, selector)
                if done:
                    try:
                        log_event("resume_upload.success", method="event_bus")
                    except Exception:
                        pass
                    return True
    except Exception as e:
        try:
            log_event("resume_upload.eventbus.error", error=str(e))
        except Exception:
            pass

    # No branch succeeded; emit compact postmortem for diagnostics
    try:
        await _log_resume_postmortem(page, selector)
    except Exception:
        pass
    try:
        log_event("resume_upload.failed_all_branches", selector=selector)
    except Exception:
        pass
    return False


async def _wait_for_resume_upload(page, selector: str, *, timeout: float = 10.0) -> bool:
    """Wait until the resume input reflects an attached file or Lever shows success.

    Signals considered success:
    - input.files.length > 0
    - hidden input resumeStorageId populated
    - .resume-upload-success or .application-upload-success visible OR span.filename has text
    Failure signals (return False early):
    - .resume-upload-failure visible
    - .resume-upload-oversize visible
    """
    # Sanity check: verify page.evaluate() works before polling
    try:
        sanity = await _evaluate_quiet(page, "() => 'ok'")
        if sanity != "ok":
            try:
                log_event(
                    "resume_upload.detect.sanity_check_failed", result=sanity, selector=selector
                )
            except Exception:
                pass
    except Exception as e:
        try:
            log_event(
                "resume_upload.detect.sanity_check_exception",
                error=str(e),
                error_type=type(e).__name__,
                selector=selector,
            )
        except Exception:
            pass

    # Allow environment override
    try:
        import os

        env_to = float(os.getenv("AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS", "0") or 0)
        if env_to > 0:
            timeout = env_to
    except Exception:
        pass
    deadline = asyncio.get_event_loop().time() + max(1.0, timeout)
    while asyncio.get_event_loop().time() < deadline:
        try:
            state = await _evaluate_quiet(
                page,
                """
                (sel) => {
                  const el = document.querySelector(sel);
                  const files = el && el.files ? el.files.length : 0;
                  const ok1 = files && files > 0;
                  const ok2 = !!document.querySelector('input[name="resumeStorageId"][value]:not([value=""])');
                  const visible = (n) => { if (!n) return false; const st = window.getComputedStyle(n); return st && st.display !== 'none' && st.visibility !== 'hidden'; };
                  const ok3 = (() => {
                    const s1 = document.querySelector('.resume-upload-success');
                    const s2 = document.querySelector('.application-upload-success');
                    return visible(s1) || visible(s2);
                  })();
                  const ok4 = (() => {
                    const container = el ? el.closest('.application-question.resume') : document.querySelector('.application-question.resume');
                    const nameSpan = container ? container.querySelector('span.filename') : null;
                    const text = nameSpan && nameSpan.textContent ? nameSpan.textContent.trim() : '';
                    return !!text;
                  })();
                  const fail1 = (() => {
                    const f = document.querySelector('.resume-upload-failure');
                    if (!f) return false;
                    const style = window.getComputedStyle(f);
                    return style && style.display !== 'none' && style.visibility !== 'hidden';
                  })();
                  const fail2 = (() => {
                    const o = document.querySelector('.resume-upload-oversize');
                    if (!o) return false;
                    const style = window.getComputedStyle(o);
                    return style && style.display !== 'none' && style.visibility !== 'hidden';
                  })();
                  const hasSuccess = ok1 || ok2 || ok3 || ok4;
                  // IMPORTANT: Lever sometimes shows .resume-upload-failure ("Couldn't auto-read resume")
                  // even when upload succeeds (failure = OCR failed, not upload failed).
                  // Only treat failure banner as blocking if NO success indicators are present.
                  const hardFail = (fail1 || fail2) && !hasSuccess;
                  return { ok: hasSuccess, fail: hardFail, files };
                }
                """,
                selector,
            )
            # Parse JSON string if page.evaluate() returns string instead of dict
            if isinstance(state, str):
                import json

                try:
                    state = json.loads(state)
                except (json.JSONDecodeError, TypeError):
                    pass
            if state is None:
                try:
                    log_event("resume_upload.detect.poll_returned_none", selector=selector)
                except Exception:
                    pass
            # Debug logging to diagnose type issues
            try:
                log_event(
                    "resume_upload.detect.state_debug",
                    state_type=type(state).__name__,
                    state_repr=repr(state)[:200],
                    selector=selector,
                )
            except Exception:
                pass
            if state and state.get("ok"):
                # Short settle: ensure state remains OK briefly and no failure banners appear
                try:
                    settle_end = asyncio.get_event_loop().time() + 1.0
                except Exception:
                    settle_end = 0
                while asyncio.get_event_loop().time() < settle_end:
                    try:
                        s2 = await _evaluate_quiet(
                            page,
                            """
                            (sel) => {
                              const el = document.querySelector(sel);
                              const files = el && el.files ? el.files.length : 0;
                              const ok2 = !!document.querySelector('input[name="resumeStorageId"][value]:not([value=""])');
                              const failBannersVisible = (() => {
                                const f = document.querySelector('.resume-upload-failure');
                                const o = document.querySelector('.resume-upload-oversize');
                                const v = (n) => { if (!n) return false; const s = window.getComputedStyle(n); return s.display !== 'none' && s.visibility !== 'hidden'; };
                                return v(f) || v(o);
                              })();
                              const hasSuccess = files > 0 || ok2;
                              // Only fail if failure banner visible AND no success indicators
                              const hardFail = failBannersVisible && !hasSuccess;
                              return { ok: hasSuccess, fail: hardFail };
                            }
                            """,
                            selector,
                        )
                        # Parse JSON string if needed
                        if isinstance(s2, str):
                            import json

                            try:
                                s2 = json.loads(s2)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        if s2 and s2.get("fail"):
                            return False
                        if s2 and s2.get("ok"):
                            pass
                    except Exception:
                        pass
                    await asyncio.sleep(0.15)
                return True
            if state and state.get("fail"):
                return False
        except Exception as e:
            try:
                log_event(
                    "resume_upload.detect.poll_exception",
                    error=str(e),
                    error_type=type(e).__name__,
                    selector=selector,
                )
            except Exception:
                pass
        await asyncio.sleep(0.3)
    # Final diagnostic snapshot (optional)
    try:
        import os

        debug = os.getenv("AUTO_APPLY_DEBUG_RESUME_WIDGET", "0").strip() not in (
            "",
            "0",
            "false",
            "False",
        )
    except Exception:
        debug = False
    if debug:
        try:
            snapshot = await _evaluate_quiet(
                """
                (sel) => {
                  const el = document.querySelector(sel);
                  const files = el && el.files ? el.files.length : 0;
                  const storage = document.querySelector('input[name=\"resumeStorageId\"]');
                  const storageVal = storage ? (storage.value || '') : '';
                  const success = document.querySelector('.resume-upload-success') || document.querySelector('.application-upload-success');
                  const fail = document.querySelector('.resume-upload-failure');
                  const oversize = document.querySelector('.resume-upload-oversize');
                  const styleStr = (n) => {
                    if (!n) return "";
                    try { const s = window.getComputedStyle(n); return (s.display||"") + "|" + (s.visibility||""); } catch { return ""; }
                  };
                  const container = el ? el.closest('.application-question.resume') : document.querySelector('.application-question.resume');
                  const filename = (() => {
                    const nameSpan = container ? container.querySelector('span.filename') : null;
                    return nameSpan && nameSpan.textContent ? nameSpan.textContent.trim() : '';
                  })();
                  const outer = container ? container.outerHTML : (el ? el.outerHTML : '');
                  return {
                    files,
                    storage_id_len: storageVal.length,
                    success_style: styleStr(success),
                    failure_style: styleStr(fail),
                    oversize_style: styleStr(oversize),
                    filename,
                    outer_truncated: outer ? outer.slice(0, 4000) : '',
                  };
                }
                """,
                selector,
            )
            try:
                log_event("resume_upload_snapshot", snapshot)
            except Exception:
                pass
        except Exception:
            pass
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
                log_event(
                    "resume_upload.eventbus.unavailable",
                    has_bus=has_bus,
                    has_get_by_index=bool(get_by_index),
                    has_is_file_input=bool(is_file_input),
                )
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


async def _cdp_set_file_input_files(
    page,
    selector: str,
    path: str,
    backend_node_id: int | None = None,
    session: BrowserSession | None = None,
) -> bool:
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
                await send(
                    "DOM.setFileInputFiles",
                    {"files": [path], "backendNodeId": int(backend_node_id)},
                )
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
                    return {k: v for k, v in zip(it, it)}
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
    except Exception as e:
        try:
            log_event(
                "resume_upload.postmortem.exception",
                error=str(e),
                error_type=type(e).__name__,
                selector=selector,
            )
        except Exception:
            pass
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


async def _check_location_gate(page, *, hidden_selector: str) -> tuple[bool, dict]:
    """Validate that the hidden location field contains valid JSON with a name.

    Args:
        page: Playwright page instance.
        hidden_selector: CSS selector for hidden location field (e.g., '#selected-location').

    Returns:
        Tuple of (is_valid, state_dict) where state_dict contains parsed JSON and metadata.
    """
    try:
        state = await page.evaluate(
            """
            (args) => {
              const { hiddenSel } = args || {};
              const hidden = document.querySelector(hiddenSel);
              const raw = hidden ? hidden.value || '' : '';
              let parsed = null;
              try { parsed = raw ? JSON.parse(raw) : null; } catch {}
              const name = parsed && typeof parsed === 'object' ? (parsed.name || '') : '';
              return {
                hasHidden: !!hidden,
                rawLength: raw.length,
                parsed: parsed,
                name: String(name).trim(),
              };
            }
            """,
            {"hiddenSel": hidden_selector},
        )
        # Ensure state is a dict (Playwright may return different types, including JSON strings)
        if isinstance(state, str):
            try:
                import json

                state = json.loads(state)
            except Exception:
                state = {}
        if not isinstance(state, dict):
            state = {}
    except Exception:
        state = {}

    is_valid = bool(state.get("name"))
    return (is_valid, state)


async def _set_structured_location(
    page, *, input_selector: str, hidden_selector: str, value: str | None
) -> bool:
    """Type location with proper keyboard events, wait for suggestions, and select via keyboard or click.

    Implements a multi-phase strategy:
    1. Type character-by-character with full KeyboardEvent simulation
    2. Wait adaptively for dropdown suggestions (2-5s)
    3. Try keyboard selection (ArrowDown + Enter) up to 3 times
    4. Fall back to clicking visible dropdown items
    5. Validate hidden field contains valid JSON with name

    Args:
        page: Playwright page instance.
        input_selector: CSS selector for visible location input.
        hidden_selector: CSS selector for hidden location JSON field.
        value: Location string to type.

    Returns:
        True if location gate is satisfied (hidden field has valid name), False otherwise.
    """
    if not value:
        return False

    try:
        # Phase 1: Type with proper keyboard events (character-by-character)
        await page.evaluate(
            """
            (args) => {
              const { selector, value } = args || {};
              const el = document.querySelector(selector);
              if (!el) return false;
              el.focus();
              const proto = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
              if (proto && proto.set) proto.set.call(el, ''); else el.value = '';

              const dispatchKey = (type, key, code, keyCode) => {
                const eventInit = {
                  key,
                  code: code || key,
                  keyCode: typeof keyCode === 'number' ? keyCode : undefined,
                  which: typeof keyCode === 'number' ? keyCode : undefined,
                  bubbles: true,
                };
                try { el.dispatchEvent(new KeyboardEvent(type, eventInit)); } catch {}
              };

              const typeChar = (ch) => {
                const key = String(ch);
                let code = key;
                let keyCode = undefined;
                if (key.length === 1) {
                  const upper = key.toUpperCase();
                  if (/^[A-Z]$/.test(upper)) {
                    code = `Key${upper}`;
                    keyCode = upper.charCodeAt(0);
                  } else if (/^[0-9]$/.test(key)) {
                    code = `Digit${key}`;
                    keyCode = key.charCodeAt(0);
                  } else if (key === ' ') {
                    code = 'Space';
                    keyCode = 32;
                  } else if (key === ',') {
                    code = 'Comma';
                    keyCode = 188;
                  }
                }
                dispatchKey('keydown', key, code, keyCode);
                if (proto && proto.set) proto.set.call(el, el.value + key); else el.value = el.value + key;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                dispatchKey('keyup', key, code, keyCode);
              };

              for (const ch of String(value)) typeChar(ch);
              el.dispatchEvent(new Event('change', { bubbles: true }));
              return true;
            }
            """,
            {"selector": input_selector, "value": value},
        )

        # Phase 2: Simple wait for dropdown suggestions to appear
        # Check if already valid before waiting
        is_valid, _ = await _check_location_gate(page, hidden_selector=hidden_selector)
        if is_valid:
            log_event("form.location.already_valid")
            return True

        # Fixed wait - simpler and more reliable than complex detection
        wait_seconds = 7.0
        await asyncio.sleep(wait_seconds)
        log_event("form.location.waited_for_suggestions", seconds=wait_seconds)

        # Phase 3: Try keyboard selection (ArrowDown + Enter) up to 3 times
        for attempt in range(3):
            # Check BEFORE sending keyboard events - avoid clearing already-valid values
            is_valid, state = await _check_location_gate(page, hidden_selector=hidden_selector)
            if is_valid:
                log_event(
                    "form.location.keyboard_selected", attempt=attempt + 1, name=state.get("name")
                )
                return True

            # Log attempt start with dropdown state
            dropdown_info = await page.evaluate(
                """
                () => {
                  const dropdown = document.querySelector('.dropdown-container, .dropdown-results');
                  const options = document.querySelectorAll('.dropdown-location, [role="option"], .Select-option, li[role="option"]');
                  const hidden = document.querySelector('#selected-location');
                  return {
                    dropdownVisible: dropdown ? window.getComputedStyle(dropdown).display !== 'none' : false,
                    optionCount: options.length,
                    hiddenValue: hidden ? hidden.value : null,
                  };
                }
                """
            )
            log_event(
                "form.location.keyboard_attempt.start", attempt=attempt + 1, dropdown=dropdown_info
            )

            # Only send keyboard events if not yet valid
            await page.evaluate(
                """
                (args) => {
                  const { selector } = args || {};
                  const el = document.querySelector(selector);
                  if (!el) return false;

                  const dispatchKey = (type, key, code, keyCode) => {
                    const eventInit = {
                      key,
                      code,
                      keyCode,
                      which: keyCode,
                      bubbles: true,
                    };
                    try { el.dispatchEvent(new KeyboardEvent(type, eventInit)); } catch {}
                  };

                  dispatchKey('keydown', 'ArrowDown', 'ArrowDown', 40);
                  dispatchKey('keyup', 'ArrowDown', 'ArrowDown', 40);
                  dispatchKey('keydown', 'Enter', 'Enter', 13);
                  dispatchKey('keyup', 'Enter', 'Enter', 13);
                  return true;
                }
                """,
                {"selector": input_selector},
            )
            await asyncio.sleep(0.4)

            # Log state after keyboard events
            post_state = await _check_location_gate(page, hidden_selector=hidden_selector)
            log_event(
                "form.location.keyboard_attempt.end",
                attempt=attempt + 1,
                valid=post_state[0],
                state=post_state[1],
            )

        # Phase 4: Click fallback - find and click visible dropdown items
        click_result = await page.evaluate(
            """
            (args) => {
              const { typed } = args || {};
              const SEL = '.dropdown-location, [role="option"], .Select-option, li[role="option"], li, [data-value], .Select-option div';

              const isVisible = (node) => {
                if (!node) return false;
                try {
                  const style = window.getComputedStyle(node);
                  if (!style || style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                } catch {
                  return false;
                }
                const rect = node.getBoundingClientRect();
                return rect && rect.width > 0 && rect.height > 0;
              };

              const nodes = Array.from(document.querySelectorAll(SEL)).filter(isVisible);
              if (!nodes.length) return { clicked: false, reason: 'no-visible-candidates' };

              const norm = (s) => String(s || '').trim().toLowerCase();
              const t = norm(typed);
              let choice = nodes.find(n => norm(n.textContent) === t)
                         || nodes.find(n => norm(n.textContent).startsWith(t))
                         || nodes[0];

              const payload = {
                text: (choice.textContent || '').trim(),
                tag: choice.tagName,
                classes: choice.className,
              };

              // Emit full event sequence for maximum compatibility
              const emitMouse = (type) => {
                try {
                  choice.dispatchEvent(new MouseEvent(type, { bubbles: true, button: 0, clientX: 5, clientY: 5 }));
                } catch {}
              };

              const emitPointer = (type) => {
                try {
                  if (typeof PointerEvent === 'function') {
                    choice.dispatchEvent(new PointerEvent(type, { bubbles: true, button: 0, clientX: 5, clientY: 5 }));
                  }
                } catch {}
              };

              emitPointer('pointerover');
              emitPointer('pointerdown');
              emitMouse('mouseover');
              emitMouse('mousedown');
              emitPointer('pointerup');
              emitMouse('mouseup');

              try {
                if (typeof choice.click === 'function') {
                  choice.click();
                } else {
                  choice.dispatchEvent(new MouseEvent('click', { bubbles: true, button: 0 }));
                }
              } catch {}

              return { clicked: true, ...payload };
            }
            """,
            {"typed": value},
        )
        # Ensure click_result is a dict (Playwright may return different types)
        if not isinstance(click_result, dict):
            click_result = {}

        if click_result.get("clicked"):
            log_event("form.location.click_attempted", result=click_result)
            # Wait up to 1 second after clicking, checking every 0.2s
            for _ in range(5):
                await asyncio.sleep(0.2)
                is_valid, state = await _check_location_gate(page, hidden_selector=hidden_selector)
                if is_valid:
                    log_event("form.location.click_succeeded", name=state.get("name"))
                    return True
        else:
            log_event("form.location.click_failed", reason=click_result.get("reason"))

        # Phase 5: Final validation
        is_valid, final_state = await _check_location_gate(page, hidden_selector=hidden_selector)
        if is_valid:
            log_event("form.location.validated", name=final_state.get("name"))
            return True
        else:
            log_event("form.location.validation_failed", state=final_state)
            return False

    except Exception as exc:
        log_event("form.location.error", error=str(exc))
        return False


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

        return _json.loads(raw or "[]")
    except Exception:
        return []


async def _apply_llm_assist(
    page, *, profile: Profile, job: JobDetails | None, invalid_fields: list[dict]
) -> None:
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
    for name, value in data.items() if isinstance(data, dict) else []:
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


async def _supervised_pause(
    timeout_seconds: int | None = None,
    *,
    prompt: str | None = None,
) -> Reason | None:
    """Pause for human review; be robust to non-interactive stdin.

    Returns a Reason if the user aborts (Ctrl+C), otherwise None.
    """
    if timeout_seconds is None:
        try:
            import os

            timeout_seconds = int(os.getenv("AUTO_APPLY_SUPERVISED_TIMEOUT", "15"))
        except Exception:
            timeout_seconds = 15
    message = (
        prompt
        or "Review filled form in the browser. Press Enter to submit, or wait to auto-continue..."
    )
    print(message)
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


def _normalize_choice_key(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def _resolve_option_value(option_text: str, option_id: str, candidates: set[str]) -> str | None:
    normalized_candidates = {c.lower(): c for c in candidates if c}
    if option_text:
        lowered = option_text.lower()
        if lowered in normalized_candidates:
            return normalized_candidates[lowered]
    if option_id:
        lowered_id = option_id.lower()
        if lowered_id in normalized_candidates:
            return normalized_candidates[lowered_id]
    if option_text:
        return option_text
    if option_id:
        return option_id
    return None


def _eeo_opt_out_value(field: EeoField) -> str | None:
    for value, text in field.option_pairs:
        combined = f"{value} {text}".lower()
        if "decline" in combined or "do not" in combined or "prefer not" in combined:
            return value or text
    return None


def _normalize_yes_no_value(raw: object | None) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return "Yes" if raw else "No"
    value = str(raw).strip()
    if not value:
        return None
    lowered = value.lower()
    yes_tokens = (
        "yes",
        "y",
        "true",
        "1",
        "authorized to work",
        "authorized",
        "eligible to work",
        "us citizen",
        "u.s. citizen",
        "citizen",
        "permanent resident",
        "green card",
    )
    no_tokens = (
        "no",
        "n",
        "false",
        "0",
        "not at this time",
        "no sponsorship",
        "do not require",
        "do not need",
        "never",
        "none",
        "not authorized",
    )
    if any(token in lowered for token in yes_tokens):
        return "Yes"
    if any(token in lowered for token in no_tokens):
        return "No"
    return value


def _default_text_answer(profile: Profile, question: DynamicQuestion) -> str | None:
    defaults = profile.defaults
    prompt_lower = question.prompt.lower()
    if "zip" in prompt_lower and "code" in prompt_lower:
        return defaults.get("zip_code") or defaults.get("postal_code")
    if "postal" in prompt_lower and "code" in prompt_lower:
        return defaults.get("postal_code") or defaults.get("zip_code")
    if "salary" in prompt_lower and ("expect" in prompt_lower or "desired" in prompt_lower):
        return defaults.get("salary_expectation")
    if "linkedin" in prompt_lower:
        return defaults.get("linkedin_url") or defaults.get("linkedin")
    if "github" in prompt_lower:
        return defaults.get("github_url") or defaults.get("github")
    if "portfolio" in prompt_lower or "website" in prompt_lower:
        return defaults.get("portfolio_url") or defaults.get("website")
    return None


def _default_choice_answer(profile: Profile, question: DynamicQuestion) -> str | None:
    defaults = profile.defaults
    prompt_lower = question.prompt.lower()
    if "legally authorized" in prompt_lower or "authorized to work" in prompt_lower:
        raw = defaults.get("work_authorized") or defaults.get("work_authorization")
        normalized = _normalize_yes_no_value(raw)
        if normalized:
            return normalized
    if (
        "require sponsorship" in prompt_lower
        or "sponsorship" in prompt_lower
        or "visa status" in prompt_lower
    ):
        raw = (
            defaults.get("requires_visa_sponsorship")
            or defaults.get("needs_visa_sponsorship")
            or defaults.get("visa_sponsorship")
            or defaults.get("sponsorship_required")
        )
        normalized = _normalize_yes_no_value(raw)
        if normalized:
            return normalized
    if (
        "previously worked" in prompt_lower
        or "worked for" in prompt_lower
        or "former employee" in prompt_lower
    ):
        raw = (
            defaults.get("worked_at_company_before")
            or defaults.get("previously_employed_at_company")
            or defaults.get("previously_employed")
        )
        normalized = _normalize_yes_no_value(raw)
        if normalized:
            return normalized
    return None


def _default_eeo_answer(profile: Profile, field: EeoField) -> str | None:
    defaults = profile.defaults
    name_lower = field.name.lower()
    label_lower = field.label.lower()

    def pick(*keys: str) -> str | None:
        for key in keys:
            if key in defaults and defaults[key] is not None:
                val = defaults[key]
                if isinstance(val, (list, tuple)):
                    if val:
                        return str(val[0])
                else:
                    return str(val)
        return None

    if "gender" in name_lower or "gender" in label_lower:
        return pick("eeo_gender", "gender", "gender_identity")
    if "race" in name_lower or "ethnicity" in name_lower or "race" in label_lower:
        return pick("eeo_race", "race_ethnicity", "race")
    if "veteran" in name_lower or "veteran" in label_lower:
        return pick("eeo_veteran_status", "veteran_status", "veteran")
    if "disability" in name_lower or "disability" in label_lower:
        return pick("eeo_disability_status", "disability_status", "disability")
    if "origin" in name_lower or "origin" in label_lower:
        return pick("eeo_ethnicity", "ethnicity")
    return pick("eeo_default_response")


async def _fill_eeo_fields(page, fields: list[EeoField], profile: Profile) -> dict[str, str]:
    """Fill EEO fields and return a dict of filled values."""
    filled = {}
    for eeo_field in fields:
        desired = _default_eeo_answer(profile, eeo_field)
        if not desired:
            desired = _eeo_opt_out_value(eeo_field)
        value = None
        if desired:
            value = eeo_field.options.get(_normalize_choice_key(desired)) or desired
        if value is None and eeo_field.option_pairs:
            # fallback to the first non-empty option
            for candidate, _display in eeo_field.option_pairs:
                if candidate:
                    value = candidate
                    break
        if value is None:
            continue
        if eeo_field.field_type == "select":
            await _set_select_value(page, eeo_field.selector, value)
            filled[eeo_field.selector] = value
        else:
            await _select_choice_option(page, eeo_field.name, value)
            filled[eeo_field.name] = value
    return filled


async def _select_choice_option(page, field_name: str | None, value: str | None) -> None:
    if not field_name or not value:
        return
    try:
        await page.evaluate(
            """
            (name, desired) => {
              const lowerDesired = String(desired || '').toLowerCase();
              const group = document.getElementsByName(name);
              let matched = false;
              for (const el of group) {
                if (!el) continue;
                const attrVal = String(el.value || '').toLowerCase();
                const label = el.closest('label');
                const labelText = label ? label.innerText.trim().toLowerCase() : '';
                // Try exact match first, then partial match (startsWith)
                if (attrVal === lowerDesired || (labelText && labelText === lowerDesired) ||
                    attrVal.startsWith(lowerDesired) || (labelText && labelText.startsWith(lowerDesired))) {
                  if (typeof el.click === 'function') {
                    el.click();
                  } else {
                    el.checked = true;
                  }
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                  matched = true;
                }
              }
              return matched;
            }
            """,
            field_name,
            value,
        )
    except Exception:
        pass


async def _set_select_value(page, selector: str | None, desired: str | None) -> None:
    if not selector or desired is None:
        return
    try:
        await page.evaluate(
            """
            (sel, desired) => {
              const el = document.querySelector(sel);
              if (!el) return false;
              const norm = (v) => String(v || '').trim().toLowerCase();
              const desiredLower = norm(desired);
              for (const opt of Array.from(el.options)) {
                const optVal = norm(opt.value);
                const optText = norm(opt.textContent);
                // Try exact match first, then partial match (startsWith)
                if (optVal === desiredLower || optText === desiredLower ||
                    optVal.startsWith(desiredLower) || optText.startsWith(desiredLower)) {
                  el.value = opt.value;
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                  return true;
                }
              }
              el.value = desired;
              el.dispatchEvent(new Event('change', { bubbles: true }));
              return true;
            }
            """,
            selector,
            desired,
        )
    except Exception:
        pass


async def _fill_disability_signature(page, profile: Profile) -> dict[str, str] | None:
    """Fill disability signature section if visible and return filled values.

    Some Lever forms conditionally show a signature section when the user
    fills out the disability status field. This function checks for visibility
    and fills the name and date fields.

    Args:
        page: Playwright page instance.
        profile: User profile with name and defaults.

    Returns:
        Dict of filled values if section was visible, None otherwise.
    """
    try:
        # Check if signature section is visible
        section_visible = await page.evaluate(
            """
            () => {
              const section = document.querySelector('#disabilitySignatureSection');
              if (!section) return false;
              const style = window.getComputedStyle(section);
              return style.display !== 'none' && style.visibility !== 'hidden';
            }
            """
        )
        if not section_visible:
            return None

        filled = {}
        # Fill signature name field
        name_value = profile.defaults.get("name") or profile.name
        if name_value:
            await _fill_if_available(page, "input[name='eeo[disabilitySignature]']", name_value)
            filled["input[name='eeo[disabilitySignature]']"] = name_value

        # Fill signature date field with current date in MM/DD/YYYY format
        current_date = datetime.now().strftime("%m/%d/%Y")
        await _fill_if_available(page, "input[name='eeo[disabilitySignatureDate]']", current_date)
        filled["input[name='eeo[disabilitySignatureDate]']"] = current_date

        log_event("eeo.disability_signature.filled", name=bool(name_value), date=current_date)
        return filled
    except Exception as exc:
        log_event("eeo.disability_signature.failed", error=str(exc))


def _build_filled_values(profile: Profile, plan: LeverFormPlan) -> dict[str, str]:
    """Build a dict of values that were/would be filled from profile and plan.

    Args:
        profile: User profile with defaults.
        plan: Form plan with field selectors.

    Returns:
        dict[str, str]: Mapping of field names/selectors to filled values.
    """
    values: dict[str, str] = {}

    # Contact fields
    if plan.contact_fields.get("name"):
        values["name"] = profile.defaults.get("name") or profile.name
    if plan.contact_fields.get("email"):
        email = profile.defaults.get("email")
        if email:
            values["email"] = email
    if plan.contact_fields.get("phone"):
        phone = profile.defaults.get("phone")
        if phone:
            values["phone"] = phone
    if plan.contact_fields.get("org"):
        org = profile.defaults.get("current_company") or profile.defaults.get("company")
        if org:
            values["org"] = org
    if plan.contact_fields.get("location"):
        location = profile.defaults.get("location")
        if location:
            values["location"] = location

    # Link fields
    for field_name, selector in plan.link_fields.items():
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
            values[field_name] = value

    return values


async def capture_pre_artifacts(
    session: BrowserSession,
    page,
    profile: Profile,
    item: ApplicationItem,
    plan: LeverFormPlan,
    filled_values: dict[str, str],
) -> tuple[Path, Path]:
    """Capture pre-submission artifacts: saved state JSON and full-page screenshot.

    Args:
        session: Active browser session.
        page: Playwright page instance.
        profile: User profile for namespacing artifacts.
        item: Application item being processed.
        plan: Form plan with selectors.
        filled_values: All filled form values to persist (including LLM answers).

    Returns:
        tuple[Path, Path]: Paths to (pre.json, pre-full.jpg).

    Raises:
        OSError: If artifacts cannot be written to disk.
    """
    from ..config import load_settings

    settings = load_settings()
    artifacts_dir = settings.artifacts_path(profile.id) / item.id
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Serialize dynamic questions for saving
    dynamic_questions_data = [
        {
            "prompt": q.prompt,
            "answer_selector": q.answer_selector,
            "field_type": q.field_type,
            "field_name": q.field_name,
            "required": q.required,
        }
        for q in plan.dynamic_questions
    ]

    # Serialize EEO fields for saving
    eeo_fields_data = [
        {
            "field_name": eeo.name,
            "selector": eeo.selector,
            "field_type": eeo.field_type,
        }
        for eeo in plan.eeo_fields
    ]

    # Build SavedState v1 payload
    apply_url = item.details.apply_url if item.details and item.details.apply_url else item.url
    state_payload = {
        "version": 1,
        "captured_at": datetime.now().isoformat(),
        "profile_id": profile.id,
        "item_id": item.id,
        "url": item.url,
        "apply_url": apply_url,
        "plan": {
            "resume_input": plan.resume_input,
            "contact_fields": plan.contact_fields,
            "link_fields": plan.link_fields,
            "dynamic_questions": dynamic_questions_data,
            "eeo_fields": eeo_fields_data,
            "submit_button": plan.submit_button,
            "captcha_selector": plan.captcha_selector,
        },
        "values": filled_values,
        "labels": {
            "company": item.company,
            "title": item.title,
        },
    }

    # Write pre.json
    pre_json_path = artifacts_dir / "pre.json"
    saved_state.write_pre_state(pre_json_path, state_payload)
    log_event("artifacts.pre_state.saved", path=str(pre_json_path))

    # Capture full-page screenshot using Playwright integration
    pre_screenshot_path = artifacts_dir / "pre-full.jpg"
    try:
        # Get the current URL from browser-use page to match correct Playwright page
        current_url = await page.get_url()

        # Connect Playwright to the same Chrome instance as browser-use
        from playwright.async_api import async_playwright

        cdp_url = session.cdp_url
        playwright = await async_playwright().start()
        playwright_browser = await playwright.chromium.connect_over_cdp(cdp_url)

        # Find the correct page by URL instead of blindly using pages[0]
        playwright_page = None
        if playwright_browser.contexts:
            for context in playwright_browser.contexts:
                for p in context.pages:
                    page_url = p.url
                    if page_url == current_url:
                        playwright_page = p
                        break
                if playwright_page:
                    break

        # Fallback: if no URL match, use the last page (most recently active)
        if not playwright_page and playwright_browser.contexts:
            pages = playwright_browser.contexts[0].pages
            if pages:
                playwright_page = pages[-1]

        if playwright_page:
            # Use Playwright's native screenshot API with full_page support
            await playwright_page.screenshot(
                path=str(pre_screenshot_path), full_page=True, type="jpeg", quality=90
            )
            log_event("artifacts.pre_screenshot.saved", path=str(pre_screenshot_path))

        # Cleanup Playwright connection (don't close browser, just disconnect)
        await playwright_browser.close()
        await playwright.stop()

    except Exception as exc:
        log_event("artifacts.pre_screenshot.failed", error=str(exc))
        # Create empty file as fallback
        pre_screenshot_path.touch()

    return pre_json_path, pre_screenshot_path


async def capture_post_screenshot(
    session: BrowserSession,
    page,
    profile: Profile,
    item: ApplicationItem,
) -> Path:
    """Capture post-submission full-page screenshot.

    Args:
        session: Active browser session.
        page: Playwright page instance.
        profile: User profile for namespacing artifacts.
        item: Application item being processed.

    Returns:
        Path: Path to post-full.jpg.

    Raises:
        OSError: If screenshot cannot be written to disk.
    """
    from ..config import load_settings

    settings = load_settings()
    artifacts_dir = settings.artifacts_path(profile.id) / item.id
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    post_screenshot_path = artifacts_dir / "post-full.jpg"
    try:
        # Get the current URL from browser-use page to match correct Playwright page
        current_url = await page.get_url()

        # Connect Playwright to the same Chrome instance as browser-use
        from playwright.async_api import async_playwright

        cdp_url = session.cdp_url
        playwright = await async_playwright().start()
        playwright_browser = await playwright.chromium.connect_over_cdp(cdp_url)

        # Find the correct page by URL instead of blindly using pages[0]
        playwright_page = None
        if playwright_browser.contexts:
            for context in playwright_browser.contexts:
                for p in context.pages:
                    page_url = p.url
                    if page_url == current_url:
                        playwright_page = p
                        break
                if playwright_page:
                    break

        # Fallback: if no URL match, use the last page (most recently active)
        if not playwright_page and playwright_browser.contexts:
            pages = playwright_browser.contexts[0].pages
            if pages:
                playwright_page = pages[-1]

        if playwright_page:
            # Use Playwright's native screenshot API with full_page support
            await playwright_page.screenshot(
                path=str(post_screenshot_path), full_page=True, type="jpeg", quality=90
            )
            log_event("artifacts.post_screenshot.saved", path=str(post_screenshot_path))

        # Cleanup Playwright connection (don't close browser, just disconnect)
        await playwright_browser.close()
        await playwright.stop()

    except Exception as exc:
        log_event("artifacts.post_screenshot.failed", error=str(exc))
        # Create empty file as fallback
        post_screenshot_path.touch()

    return post_screenshot_path


async def prefill_from_saved_state(page, saved_state: dict) -> None:
    """Prefill form fields using saved state from pre.json.

    Args:
        page: Playwright page instance.
        saved_state: SavedState v1 dict loaded from pre.json.

    Raises:
        Exception: If prefilling fails due to missing selectors or page errors.

    """
    plan = saved_state.get("plan", {})
    values = saved_state.get("values", {})

    # JavaScript to set input value by selector
    js_set_value = (
        "(sel, val) => { const el = document.querySelector(sel); if (!el) return false; "
        "const proto = (el.tagName==='TEXTAREA') ? HTMLTextAreaElement.prototype : "
        "HTMLInputElement.prototype; const setter = Object.getOwnPropertyDescriptor(proto, 'value').set; "
        "setter.call(el, String(val)); el.dispatchEvent(new Event('input', {bubbles:true})); "
        "el.dispatchEvent(new Event('change', {bubbles:true})); el.blur && el.blur(); return true; }"
    )

    # Fill contact fields
    contact_fields = plan.get("contact_fields", {})
    for field_name, selector in contact_fields.items():
        if not selector:
            continue
        value = values.get(field_name)
        if value:
            try:
                await page.evaluate(js_set_value, selector, value)
                log_event("resume.prefill.field", field=field_name, selector=selector)
            except Exception as exc:
                log_event("resume.prefill.field_failed", field=field_name, error=str(exc))

    # Fill link fields
    link_fields = plan.get("link_fields", {})
    for field_name, selector in link_fields.items():
        if not selector:
            continue
        value = values.get(field_name)
        if value:
            try:
                await page.evaluate(js_set_value, selector, value)
                log_event("resume.prefill.link", field=field_name, selector=selector)
            except Exception as exc:
                log_event("resume.prefill.link_failed", field=field_name, error=str(exc))

    # Fill dynamic questions
    dynamic_questions = plan.get("dynamic_questions", [])
    for question in dynamic_questions:
        answer_selector = question.get("answer_selector")
        field_type = question.get("field_type", "text")
        field_name = question.get("field_name")

        if not answer_selector:
            continue

        # Get value using answer_selector or field_name as key
        value = values.get(answer_selector) or values.get(field_name)
        if not value:
            continue

        try:
            if field_type in ("text", "textarea"):
                # Use js_set_value for text and textarea fields
                await page.evaluate(js_set_value, answer_selector, value)
                log_event("resume.prefill.dynamic_question", field_type=field_type, selector=answer_selector)
            elif field_type == "select":
                # Set select dropdown value
                js_set_select = (
                    "(sel, val) => { const el = document.querySelector(sel); "
                    "if (!el || el.tagName !== 'SELECT') return false; "
                    "el.value = val; el.dispatchEvent(new Event('change', {bubbles:true})); return true; }"
                )
                await page.evaluate(js_set_select, answer_selector, value)
                log_event("resume.prefill.dynamic_question", field_type="select", selector=answer_selector)
            elif field_type == "checkbox" and value == "checked":
                # Check checkbox
                js_check = (
                    "(sel) => { const el = document.querySelector(sel); "
                    "if (!el || el.type !== 'checkbox') return false; "
                    "el.checked = true; el.dispatchEvent(new Event('change', {bubbles:true})); return true; }"
                )
                await page.evaluate(js_check, answer_selector)
                log_event("resume.prefill.dynamic_question", field_type="checkbox", selector=answer_selector)
            elif field_type == "multiple_choice" and field_name:
                # Select radio button by field name and value
                js_select_radio = (
                    "(name, val) => { const radios = document.querySelectorAll(`input[name='${name}']`); "
                    "for (const r of radios) { if (r.value === val) { "
                    "r.checked = true; r.dispatchEvent(new Event('change', {bubbles:true})); return true; }} "
                    "return false; }"
                )
                await page.evaluate(js_select_radio, field_name, value)
                log_event("resume.prefill.dynamic_question", field_type="multiple_choice", field_name=field_name)
        except Exception as exc:
            log_event("resume.prefill.dynamic_question_failed", field_type=field_type, error=str(exc))

    # Fill EEO fields
    eeo_fields = plan.get("eeo_fields", [])
    for eeo_field in eeo_fields:
        selector = eeo_field.get("selector")
        field_type = eeo_field.get("field_type", "select")
        field_name = eeo_field.get("field_name")

        if not selector:
            continue

        # Get value using selector or field_name as key
        value = values.get(selector) or values.get(field_name)
        if not value:
            continue

        try:
            if field_type == "select":
                # Set select dropdown value
                js_set_select = (
                    "(sel, val) => { const el = document.querySelector(sel); "
                    "if (!el || el.tagName !== 'SELECT') return false; "
                    "el.value = val; el.dispatchEvent(new Event('change', {bubbles:true})); return true; }"
                )
                await page.evaluate(js_set_select, selector, value)
                log_event("resume.prefill.eeo_field", field_type="select", selector=selector)
            else:
                # Multiple choice (radio buttons)
                js_select_radio = (
                    "(name, val) => { const radios = document.querySelectorAll(`input[name='${name}']`); "
                    "for (const r of radios) { if (r.value === val) { "
                    "r.checked = true; r.dispatchEvent(new Event('change', {bubbles:true})); return true; }} "
                    "return false; }"
                )
                await page.evaluate(js_select_radio, field_name, value)
                log_event("resume.prefill.eeo_field", field_type="multiple_choice", field_name=field_name)
        except Exception as exc:
            log_event("resume.prefill.eeo_field_failed", field_name=field_name, error=str(exc))

    # Fill any remaining fields from values (e.g., cover letter, disability signature)
    # These are fields with selectors as keys that weren't already handled above
    handled_selectors = set()

    # Collect all selectors we've already processed
    for field_dict in [contact_fields, link_fields]:
        handled_selectors.update(field_dict.values())

    for question in dynamic_questions:
        if question.get("answer_selector"):
            handled_selectors.add(question.get("answer_selector"))

    for eeo_field in eeo_fields:
        if eeo_field.get("selector"):
            handled_selectors.add(eeo_field.get("selector"))

    # Fill any unhandled fields using their selector keys
    for selector, value in values.items():
        if selector in handled_selectors or not value:
            continue

        # Skip non-selector keys (like "name", "email", "phone", "location")
        if not ("#" in selector or "[" in selector or "." in selector):
            continue

        try:
            await page.evaluate(js_set_value, selector, value)
            log_event("resume.prefill.additional_field", selector=selector)
        except Exception as exc:
            log_event("resume.prefill.additional_field_failed", selector=selector, error=str(exc))

    log_event("resume.prefill.complete")
