"""Utilities for analyzing Lever forms and configuring browser sessions."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
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
        self._planner = planner or analyze_form
        self._options = options or LeverBrowserOptions.from_settings()

    def build_plan(self, html: str) -> LeverFormPlan:
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
                  const answerName = `${prefix}[field${idx}]`;
                  const answerEl = q(`textarea[name='${answerName}']`);
                  if (answerEl && f && f.text) {
                    questions.push({
                      prompt: String(f.text || '').trim(),
                      required: !!f.required,
                      answerSelector: pickSelector(answerEl, 'textarea')
                    });
                  }
                });
              });

              const submitEl = q('button#btn-submit');
              const captchaEl = q('div#h-captcha');

              return JSON.stringify({
                resumeInput: pickSelector(resumeEl),
                contactFields: contact,
                linkFields: links,
                dynamicQuestions: questions,
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
            dynamic_questions.append(
                DynamicQuestion(
                    prompt=prompt,
                    required=bool(q.get("required", False)),
                    answer_selector=str(q.get("answerSelector")),
                    cache_key=_normalize_question_key(prompt),
                )
            )
        return LeverFormPlan(
            resume_input=resume_input,
            contact_fields={str(k): str(v) for k, v in contact_fields.items()},
            link_fields={str(k): str(v) for k, v in link_fields.items()},
            dynamic_questions=dynamic_questions,
            submit_button=str(data.get("submitButton", "button#btn-submit")),
            captcha_selector=(str(data.get("captchaSelector")) if data.get("captchaSelector") else None),
        )

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
        await page.goto(apply_url)
        # Wait for form root or captcha
        await _wait_for_any(page, ["form#application-form", "div#h-captcha", "#application"])

        # Detect CAPTCHA early
        if await _exists(page, self._options, selector="div#h-captcha"):
            return Reason(code="captcha_blocked", message="hCaptcha detected on form")

        plan = await self.build_plan_in_browser(page)

        # Upload resume
        resume_path = str(profile.resolve_resume_path())
        try:
            if hasattr(page, "set_input_files"):
                await page.set_input_files(plan.resume_input, resume_path)
            else:
                # Try a JS-based fallback (may not work for file inputs)
                await page.evaluate(
                    f"(sel) => {{ const el = document.querySelector(sel); if(el) el.value=''; }}",
                    plan.resume_input,
                )
        except Exception:
            # If supervised, allow manual attach
            if mode != "auto":
                print("Please attach your resume manually in the browser, then press Enter to continue...")
                try:
                    input()
                except Exception:
                    pass
            else:
                return Reason(code="resume_upload_failed", message="Could not attach resume file")

        # Fill contact fields from profile defaults (with sensible fallbacks)
        await _fill_if_available(
            page,
            plan.contact_fields.get("name"),
            profile.defaults.get("name") or profile.name,
        )
        await _fill_if_available(page, plan.contact_fields.get("email"), profile.defaults.get("email"))
        await _fill_if_available(page, plan.contact_fields.get("phone"), profile.defaults.get("phone"))
        # Current company/org
        await _fill_if_available(
            page,
            # detect common selector directly if planner didn't capture it
            plan.contact_fields.get("org") or "input[data-qa='org-input'][name='org']",
            profile.defaults.get("current_company") or profile.defaults.get("company"),
        )
        # Structured location: type and select first suggestion; fallback to hidden
        await _set_structured_location(
            page,
            input_selector=plan.contact_fields.get("location") or "#location-input",
            hidden_selector=plan.contact_fields.get("location_hidden") or "#selected-location",
            value=profile.defaults.get("location"),
        )

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

        # Dynamic questions via LLM (long-form textareas)
        if plan.dynamic_questions:
            try:
                client = OpenRouterClient.from_settings()
            except OpenRouterError:
                client = None
            prompt_builder = PromptBuilder(profile=profile)
            for q in plan.dynamic_questions:
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

        # Multiple-choice dynamic cards (checkboxes/radios) — simple heuristics
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
        await _click(page, plan.submit_button)
        await asyncio.sleep(2.0)
        # hCaptcha check after click
        if plan.captcha_selector and await _exists(page, self._options, selector=plan.captcha_selector):
            return Reason(code="captcha_blocked", message="hCaptcha shown on submit")

        # Post-submit sanity: page should either navigate or hide form
        still_has_form = await page.evaluate("() => !!document.querySelector('form#application-form')")
        if still_has_form:
            # If form remains, re-check validity – likely a client-side validation
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
    """Wait until any of the selectors appear or timeout."""
    deadline = asyncio.get_event_loop().time() + 12.0
    while asyncio.get_event_loop().time() < deadline:
        for sel in selectors:
            try:
                els = await page.get_elements_by_css_selector(sel)
            except Exception:
                els = []
            if els:
                return
        await asyncio.sleep(0.3)
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


async def _fill_textarea(page, selector: str, value: str) -> None:
    try:
        await page.evaluate(
            "(sel, val) => { const el = document.querySelector(sel); if (!el) return false; const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set; setter.call(el, String(val)); el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); el.blur && el.blur(); return true; }",
            selector,
            value,
        )
    except Exception:
        pass


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
        await asyncio.sleep(0.6)
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
    for name, value in (data.items() if isinstance(data, dict) else []):
        try:
            if isinstance(value, str):
                # Try select first; if not a select, treat as text input
                applied = await page.evaluate(
                    "(n, v) => { const el = document.querySelector(`[name="${n}"]`);\n                     if (!el) return false;\n                     if (el.tagName==='SELECT') {\n                       for (const opt of el.options) { if ((opt.textContent||'').trim().toLowerCase() === String(v).trim().toLowerCase() || String(opt.value).toLowerCase() === String(v).trim().toLowerCase()) { el.value = opt.value; el.dispatchEvent(new Event('change', {bubbles:true})); return true; } }\n                       return false;\n                     } else if (el.type==='checkbox' || el.type==='radio') {\n                       const group = document.querySelectorAll(`[name="${n}"]`);\n                       for (const g of group) { if ((g.value||'').trim().toLowerCase() === String(v).trim().toLowerCase()) { g.checked = true; g.dispatchEvent(new Event('change', {bubbles:true})); return true; } }\n                       return false;\n                     } else {\n                       const proto = (el.tagName==='TEXTAREA') ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;\n                       const setter = Object.getOwnPropertyDescriptor(proto, 'value').set; setter.call(el, String(v));\n                       el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); el.blur && el.blur();\n                       return true; } }",
                    name,
                    value,
                )
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
