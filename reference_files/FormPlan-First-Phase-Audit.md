# FormPlan Phase-1 Audit (Repo vs reference_files\Step1-deterministic-fill.md)
- Timestamp: 2025-10-04 16:07 UTC
- Git HEAD: 9013598
- Scope: Phase 1 only (deterministic plan & deterministic fill)

## Executive Summary
The current Lever automation focuses on a selector-centric `LeverFormPlan` dataclass and a robust execution routine, but it diverges substantially from the Step1 deterministic spec. The builder omits the `meta`/`widgets` structure, lacks selector precedence tracking, and inlines resume signals rather than returning them. Execution mixes deterministic steps with LLM assists, skips required location JSON verification, and only conditionally calls `reportValidity()`. Captcha detection logs telemetry yet still allows submission. Observability hooks from the spec are absent. Several pieces (CDP/event-bus resume fallbacks, URL allow-listing) exceed the baseline, yet key gates remain under-specified for a fully deterministic handoff.

| Area | Status | Notes |
|------|--------|-------|
| FormPlan JSON | 🔴 Differs | Dataclass lacks `meta/widgets/fields` schema and success/failure signals. |
| Selector Strategy | 🟠 Differs | `pickSelector` prioritizes `id` before `name` and falls back to classes without alternates. |
| Resume Upload | 🟠 Differs | Strong fallbacks + signals, but includes LLM locator branch and no plan-level triggers/signal lists. |
| Location Gate | 🟠 Differs | Fills `#location-input` but never asserts `selectedLocation` JSON updated. |
| Deterministic Autofill | 🟢 Aligned | Name/email/phone/link fills pull from profile defaults deterministically. |
| Validity & Submit | 🟠 Differs | `checkValidity()` without guaranteed `reportValidity()`, invalids from `willValidate` only; submits even if captcha visible. |
| Hooks/Observability | 🔴 Missing | No lifecycle snapshots or captcha-driven submit block prior to click. |

## Spec Checklist (from Step1-deterministic-fill.md)
- FormPlan JSON exposes `meta`, `widgets.resume` (input/triggers/success/failure), `fields[]` (label/type/selector/options), and `submit` selector.
- Selector precedence order: `name` → `id` → `data-qa` → aria/role → text-anchored CSS → nth fallback; record alternates.
- Resume upload pipeline: deterministic selector, `set_input_files`, file chooser fallback, frame-aware search, CDP fallback; verify success (`resumeStorageId`, banners, filename) and abort on failure signals.
- Location gate: detect `#location-input` + hidden `input[name="selectedLocation"]`, ensure JSON value has non-empty `name` before proceeding.
- Deterministic fill: profile defaults for name/email/phone/links; only escalate to LLM for unmapped/invalid fields.
- Validity check: always `reportValidity()` then `checkValidity()`, capture `:invalid` elements for gaps.
- Deterministic submit only after valid; do not bypass CAPTCHA—on Lever, **check CAPTCHA immediately after submit** (presence before submit is normal), then pause/mark for review if visible/blocking.
- Hooks/observability: snapshot invalid fields, log artifacts, pause when captcha present.
- CDP/profile/allowed_domains configuration ready for stable deterministic runs.

## Alignment Matrix
| Spec Item | Implemented By | File/Lines | Status | Evidence/Notes |
|-----------|----------------|------------|--------|----------------|
| FormPlan schema with `meta/widgets/fields/submit` | `LeverFormPlan` dataclass & `build_plan_in_browser` | `src/job_ai_auto_apply_ui/browser_agent/lever.py`†L34-L43, L321-L364 | Differs | Plan returns flat attributes (`resume_input`, `contact_fields`, etc.) with no `meta` block or resume signal lists. |
| Selector precedence (`name`→`id`→`data-qa`→aria/role→text→nth) & alternates | `pickSelector` helper | `src/job_ai_auto_apply_ui/browser_agent/lever.py`†L246-L274 | Differs | Prefers `id` then `name`, falls back to first class token, and captures only a single selector. |
| Resume widget plan details (input + triggers/success/failure) | Same as above | `src/job_ai_auto_apply_ui/browser_agent/lever.py`†L321-L364 | Missing | Execution hardcodes signals, but plan omits them entirely. |
| Resume upload deterministic pipeline | `_upload_resume` and `_wait_for_resume_upload` | `src/job_ai_auto_apply_ui/browser_agent/lever.py`†L970-L1319, L1322-L1400 | Differs | Robust fallbacks and signal checks exist, yet pipeline adds LLM locator/event bus branches and frame attempt precedes chooser, diverging from spec’s deterministic-only sequence. |
| Location gate (`#location-input` + hidden JSON assertion) | `_set_structured_location` usage | `src/job_ai_auto_apply_ui/browser_agent/lever.py`†L410-L416, L1831-L1859 | Differs | Fills visible input and optionally hidden field but never asserts JSON structure or non-empty `name`. |
| Deterministic autofill of profile defaults | `_fill_if_available` calls | `src/job_ai_auto_apply_ui/browser_agent/lever.py`†L448-L494 | Aligned | Name/email/phone/link fields filled deterministically from profile data. |
| Validity gate (`reportValidity` + `checkValidity`, collect `:invalid`) | `_form_check_validity`, `_form_report_validity`, `_collect_invalid_fields` | `src/job_ai_auto_apply_ui/browser_agent/lever.py`†L582-L613, L1881-L1994 | Differs | Only supervised mode triggers `reportValidity()`, invalids gathered via `willValidate` loop (not `:invalid`), so browser UI hints may be missed. |
| Submit gating vs captcha | Submit branch & captcha log | `src/job_ai_auto_apply_ui/browser_agent/lever.py`†L397-L405, L548-L575 | Differs | Captcha presence logged but submission still triggered; block occurs only post-click if `blocking` inferred. |
| Hooks/observability snapshots | — | Search (`rg "on_step"`) | chunk `8c4109`†L1-L1 | Missing | No hook implementations or invalid snapshots beyond logging. |
| CDP/allowed_domains configuration | `LeverBrowserOptions` & `ensure_allowed_domain` | `src/job_ai_auto_apply_ui/browser_agent/lever.py`†L46-L139, L379-L382, L644-L688 | Aligned | Allowed domains enforced and browser options expose CDP-friendly configuration. |

## Evidence
```python
# src/job_ai_auto_apply_ui/browser_agent/lever.py:L34-L43
@dataclass(slots=True)
class LeverFormPlan:
    """Key selectors and metadata needed to complete a Lever form."""
    resume_input: str
    contact_fields: dict[str, str]
    link_fields: dict[str, str]
    dynamic_questions: list[DynamicQuestion] = field(default_factory=list)
    submit_button: str = "button#btn-submit"
    captcha_selector: str | None = "div#h-captcha"
```

```javascript
// src/job_ai_auto_apply_ui/browser_agent/lever.py:L246-L274
const pickSelector = (el, tag='input') => {
  if (!el) return null;
  if (el.id) return `#${el.id}`;
  if (el.name) return `${tag}[name='${el.name}']`;
  if (el.getAttribute('data-qa')) return `${tag}[data-qa='${el.getAttribute('data-qa')}']`;
  const cls = el.className && String(el.className).split(/\s+/)[0];
  if (cls) return `${tag}.${cls}`;
  return tag;
};
```

```python
# src/job_ai_auto_apply_ui/browser_agent/lever.py:L321-L364
return JSON.stringify({
  resumeInput: pickSelector(resumeEl),
  contactFields: contact,
  linkFields: links,
  dynamicQuestions: questions,
  submitButton: pickSelector(submitEl, 'button') || 'button#btn-submit',
  captchaSelector: captchaEl ? pickSelector(captchaEl, 'div') : null,
});
...
return LeverFormPlan(
    resume_input=resume_input,
    contact_fields={str(k): str(v) for k, v in contact_fields.items()},
    link_fields={str(k): str(v) for k, v in link_fields.items()},
    dynamic_questions=dynamic_questions,
    submit_button=str(data.get("submitButton", "button#btn-submit")),
    captcha_selector=(str(data.get("captchaSelector")) if data.get("captchaSelector") else None),
)
```

```python
# src/job_ai_auto_apply_ui/browser_agent/lever.py:L970-L1049
async def _upload_resume(...):
    # 1) Locator-based API ...
    # 2) Page-level API ...
    # 2b) Frame-scoped attempt ...
    # 3) File chooser flow ...
    # 4) Optional: click anchor ...
    # 5) LLM-locator fallback ...
```

```python
# src/job_ai_auto_apply_ui/browser_agent/lever.py:L1831-L1859
async def _set_structured_location(...):
    await page.evaluate(... '#location-input' ...)
    clicked = await page.evaluate(... '.dropdown-results' ...)
    if not clicked:
        await page.evaluate(... hidden_selector ... value ...)
```

```python
# src/job_ai_auto_apply_ui/browser_agent/lever.py:L582-L613
if not await _form_check_validity(page):
    invalid_fields = await _collect_invalid_fields(page)
    if mode != "auto":
        await _form_report_validity(page)
        pause_reason = await _supervised_pause()
        ...
    else:
        await _apply_llm_assist(...)
```

```python
# src/job_ai_auto_apply_ui/browser_agent/lever.py:L1881-L1994
async def _form_check_validity(page) -> bool:
    return await page.evaluate(... 'form#application-form' ... checkValidity())
...
async def _collect_invalid_fields(page) -> list[dict]:
    raw = await page.evaluate("... el.willValidate && !el.checkValidity() ...")
```

```python
# src/job_ai_auto_apply_ui/browser_agent/lever.py:L397-L405
state = await _hcaptcha_state(page)
if state.get("present") and not state.get("visible"):
    log_event(...)
elif state.get("visible"):
    log_event(...)
```

```python
# src/job_ai_auto_apply_ui/browser_agent/lever.py:L548-L575
await _click(page, plan.submit_button)
await asyncio.sleep(2.0)
...
if cstate.get("blocking"):
    return Reason(code="captcha_blocked", ...)
```

## Overcomplicated vs Too Simple
- **Overcomplicated**
  - Resume upload includes LLM-driven locator discovery and browser-use event-bus fallbacks even in the “deterministic” phase, adding latency and non-deterministic dependencies. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L1117-L1319】
  - Navigation attempts span event bus, CDP, and `page.goto` with telemetry logging; while robust, it exceeds Phase‑1 needs and complicates error surfaces. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L820-L918】
- **Too Simple / Missing**
  - FormPlan lacks `meta` flags (form root, EEO root, captcha selector, location gate) and resume widget signals, preventing downstream deterministic execution without re-deriving data. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L321-L364】
  - Selector extraction stores only a single CSS string with `id` priority, omitting alternates and precedence metadata, making recovery from dynamic re-render impossible. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L246-L274】
  - Location gate never validates `selectedLocation` JSON; automation may proceed without fulfilling Lever’s requirement, breaking resume uploads on gated forms. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L410-L416】【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L1831-L1859】
  - Validity pipeline lacks guaranteed `reportValidity()` and `:invalid` scraping, so UI error messages are not surfaced for LLM or human review. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L582-L613】【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L1881-L1994】
  - No lifecycle hooks capture invalid snapshots or stop submission when captcha is detected before clicking submit. 【8c4109†L1-L1】【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L397-L405】

## Risks & Prioritized Recommendations (No code changes)
- **Blockers**
  - Introduce spec-compliant FormPlan schema (`meta`, `widgets.resume`, `fields[]`, `submit`) with selector precedence metadata. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L34-L43】【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L321-L364】
  - Enforce Lever-specific CAPTCHA policy: **do not block on presence before submit**; **after the submit click**, detect if CAPTCHA is visible/blocking or an error banner indicates CAPTCHA, then pause/mark for review. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L397-L405】【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L548-L575】
- **Majors**
  - Reorder resume pipeline to remain deterministic (remove LLM locator from Phase 1, keep event bus/CDP fallbacks) and surface success/failure signals via FormPlan. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L970-L1319】
  - Add location gate assertion ensuring hidden `selectedLocation` JSON contains a non-empty `name` prior to resume upload. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L1831-L1859】
  - Guarantee `reportValidity()` + `checkValidity()` and collect `:invalid` selectors for deterministic handoff. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L582-L613】【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L1881-L1994】
- **Minors**
  - Record alternate selectors and original attribute sources in the plan for resilience. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L246-L274】
  - Include EEO root detection and meta flags for location gate/captcha in the plan. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L321-L364】
- **Nice-to-haves**
  - Simplify navigation fallbacks once deterministic path is stable; keep telemetry but reduce branches. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L820-L918】

**Quick Wins (1–3h)**
- Add a **post-submit** CAPTCHA check that pauses or returns a review reason immediately after clicking submit. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L548-L575】
- Call `reportValidity()` unconditionally before `checkValidity()` and collect `:invalid` selectors via `querySelectorAll`. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L582-L613】

**Medium (0.5–1d)**
- Extend FormPlan JSON builder to emit `meta` (form root, eeo root, captcha selector, requiresLocationGate) and resume widget signals per spec. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L321-L364】
- Update `_set_structured_location` to validate hidden JSON and return success/failure for gating logic. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L1831-L1859】

**Larger (1–3d)**
- Refactor selector extraction to record precedence order, alternates, and `fields[]` entries matching spec schema; adjust downstream execution to consume new structure. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L246-L274】【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L321-L364】
- Split deterministic execution from LLM assists, moving long-form question handling into later phases and keeping Phase 1 strictly deterministic. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L496-L575】

## Appendix
- **Search methods**: `rg "analyze_form"`, `rg "reportValidity"`, `rg "on_step"`, `rg "selectedLocation"`, `rg "resume_upload"`.
- **Assumptions**: Browser-use `page` methods behave like Playwright; supervised mode equates to manual handoff; FormPlan currently consumed directly by `execute_in_browser`.

---
