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
        # Robust navigate: event-bus -> CDP -> page.goto, with verification + logs
        await _robust_navigate(session, page, apply_url)
        # Re-focus active page in case navigation opened or switched tabs
        try:
            current = await getattr(session, "get_current_page")()  # type: ignore[attr-defined]
            if current is not None and current is not page:
                page = current
                try:
                    log_event("apply.page_focus.changed", reason="post_navigate"); await _close_stray_about_blank_tabs(session)
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

        plan = await self.build_plan_in_browser(page)

        # Enable resume widget first: set location to activate disabled upload button variants
        await _set_structured_location(
            page,
            input_selector=plan.contact_fields.get("location") or "#location-input",
            hidden_selector=plan.contact_fields.get("location_hidden") or "#selected-location",
            value=profile.defaults.get("location"),
        )

        # Upload resume with robust fallbacks + success detection
        resume_path = str(profile.resolve_resume_path())
        uploaded = await _upload_resume(session, page, plan.resume_input, resume_path)
        if not uploaded:\n            # grace re-check in case UI just updated\n            try:\n                if await _wait_for_resume_upload(page, plan.resume_input, timeout=1.0):\n                    uploaded = True\n            except Exception:\n                pass\n            if not uploaded:
            if mode != "auto":
                print("Resume upload not detected. Please attach manually in the browser, then press Enterâ€¦")
                try:
                    input()
                except Exception:
                    pass
                # Re-check after manual attach
                uploaded = await _wait_for_resume_upload(page, plan.resume_input, timeout=10.0)
            if not uploaded:\n            # grace re-check in case UI just updated\n            try:\n                if await _wait_for_resume_upload(page, plan.resume_input, timeout=1.0):\n                    uploaded = True\n            except Exception:\n                pass\n            if not uploaded:
                return Reason(code="resume_upload_failed", message="Resume not attached")

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
        # Structured location already handled above to enable resume upload

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
        await _click(page, plan.submit_button)
        await asyncio.sleep(2.0)
        # hCaptcha check after click
        # Detect blocking captcha only after submit attempt, using visibility/overlay heuristics
        try:
            cstate = await _hcaptcha_state(page)
            if cstate.get("blocking"):
                log_event("captcha.blocking_visible", details=cstate)
                return Reason(code="captcha_blocked", message="hCaptcha visible and blocking submission")
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
        import io, contextlib
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


async def _close_stray_about_blank_tabs(session: BrowserSession) -> None:\nasync def _close_stray_about_blank_tabs(session: BrowserSession) -> None:
    """Best-effort: close background about:blank/new-tab pages via CDP if available."""
    try:
        if not hasattr(session, "get_or_create_cdp_session"):
            return
        cdp_session = await session.get_or_create_cdp_session()  # type: ignore[attr-defined]
        cdp = getattr(cdp_session, "cdp_client", None)
        sid = getattr(cdp_session, "session_id", None)
        current_target = getattr(cdp_session, "target_id", None)
        if cdp is None:
            return
        # Get all targets
        targets = await cdp.send.Target.getTargets(params={}, session_id=sid)
        items = targets.get("targetInfos") or targets.get("targetInfo") or []
        for t in items:
            try:
                tid = t.get("targetId") or t.get("targetID")
                if not tid or (current_target and str(tid) == str(current_target)):
                    continue
                if t.get("type") != "page":
                    continue
                url = (t.get("url") or "").lower().strip()
                if url in ("about:blank", "chrome://newtab", "chrome://new-tab-page/"):
                    try:
                        await cdp.send.Target.closeTarget(params={"targetId": tid}, session_id=sid)
                    except Exception:
                        pass
            except Exception:
                continue
    except Exception:
        return\nasync def _robust_navigate(session: BrowserSession, page, url: str) -> None:
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
            "has_event_bus": bool(getattr(session, "event_bus", None)) if session is not None else False,
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
                await page.evaluate("(sel) => { const btn = document.querySelector('a.visible-resume-upload') || document.querySelector(sel); if (btn) btn.click(); }", selector)
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
        await page.evaluate("() => { const btn = document.querySelector('a.visible-resume-upload'); if (btn) btn.click(); }")
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
        use_llm = os.getenv("AUTO_APPLY_USE_LLM_LOCATOR", "0").strip() not in ("", "0", "false", "False")
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
                            from browser_use.llm.google import ChatGoogle as _BUGemini  # type: ignore
                            llm_obj = _BUGemini()
                        except Exception:
                            llm_obj = None
                    if llm_obj is None and (_os.getenv("OPENROUTER_API_KEY") or _os.getenv("OPENAI_API_KEY")):
                        try:
                            if _os.getenv("OPENROUTER_API_KEY") and not _os.getenv("OPENAI_API_KEY"):
                                _os.environ["OPENAI_API_KEY"] = _os.getenv("OPENROUTER_API_KEY") or ""
                                if not _os.getenv("OPENAI_BASE_URL") and not _os.getenv("OPENAI_API_BASE"):
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
                                    llm_obj.model = model_name  # best-effort; some clients accept assignment
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        element = await page.must_get_element_by_prompt(
                            "the resume upload input element (the <input type=\\\"file\\\"> used to attach a resume) inside the application form; not the submit button",
                            llm=llm_obj,
                        )
                    else:
                        element = await page.must_get_element_by_prompt(
                            "the resume upload input element (the <input type=\\\"file\\\"> used to attach a resume) inside the application form; not the submit button",
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
                        "the file upload control (input[type=\\\"file\\\"]) used to attach a resume/CV inside the application form",
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
                    log_event("resume_upload.llm_locator.result", css_selector=new_selector, backend_node_id=backend_id)
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
                    log_event("resume_upload.llm_locator.result", css_selector=None, backend_node_id=None)
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
        if await _cdp_set_file_input_files(page, selector, path, backend_node_id=backend_id, session=session):
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


async def _wait_for_resume_upload(page, selector: str, *, timeout: float = 25.0) -> bool:
    """Wait until the resume input reflects an attached file or Lever shows success.

    Signals considered success:
    - input.files.length > 0
    - hidden input resumeStorageId populated
    - .resume-upload-success or .application-upload-success visible OR span.filename has text
    Failure signals (return False early):
    - .resume-upload-failure visible
    - .resume-upload-oversize visible
    """
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
                  return { ok: (ok1 || ok2 || ok3 || ok4), fail: (fail1 || fail2), files };
                }
                """,
                selector,
            )
            if state and state.get("ok"):
                # Short settle: ensure state remains OK briefly and no failure banners appear
                try:
                    settle_end = asyncio.get_event_loop().time() + 1.0
                except Exception:
                    settle_end = 0
                while asyncio.get_event_loop().time() < settle_end:
                    try:
                        s2 = await _evaluate_quiet(
                            """
                            (sel) => {
                              const el = document.querySelector(sel);
                              const files = el && el.files ? el.files.length : 0;
                              const ok2 = !!document.querySelector('input[name="resumeStorageId"][value]:not([value=""])');
                              const fail = (() => {
                                const f = document.querySelector('.resume-upload-failure');
                                const o = document.querySelector('.resume-upload-oversize');
                                const v = (n) => { if (!n) return false; const s = window.getComputedStyle(n); return s.display !== 'none' && s.visibility !== 'hidden'; };
                                return v(f) || v(o);
                              })();
                              return { ok: (files>0 || ok2) && !fail, fail };
                            }
                            """,
                            selector,
                        )
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
        except Exception:
            pass
        await asyncio.sleep(0.3)
    # Final diagnostic snapshot (optional)
    try:
        import os
        debug = os.getenv("AUTO_APPLY_DEBUG_RESUME_WIDGET", "0").strip() not in ("", "0", "false", "False")
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















