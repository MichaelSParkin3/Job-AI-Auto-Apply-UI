# Debug Log – Lever Planner + Location Gate (Oct 4–5, 2025)

This document captures the end‑to‑end debugging and fixes we implemented while stabilizing the Lever “apply” workflow, especially the in‑page Step1 planner script and the structured location “gate”. It’s intended as a handoff for the next developer.

## TL;DR

- We fixed multiple failures in the apply flow:
  - JavaScript parse failures inside the injected Step1 planner string.
  - Python type mismatch after page.evaluate (string vs dict mapping).
  - Location gate failures due to not actually selecting a suggestion.
- We replaced fragile string escaping with JSON‑based quoting and attribute selectors; hardened Python coercion of evaluate results; implemented a keyboard‑first, retrying selection flow for the location dropdown; added a new HTML fixture and integration test for a common Lever “momentum” dropdown skin.
- Remaining follow‑ups: adjust test usage of Playwright’s evaluate signature, expand keyboard events to include keyCode/which where needed, and broaden selectors for additional Lever skins.

## A. Context and Symptoms

Command(s) exercised:
- uto-apply discover --profile … (worked after first‑time browser install)
- uto-apply apply --profile … (multiple failures over time)

Symptoms observed via logs:
1) JS parse errors while building the Step1 plan in the page:
   - SyntaxError: Invalid regular expression / missing ) after argument list in the injected code block emitted by uild_plan_in_browser.
2) After we removed parse errors, Python crashed treating a string as a dict:
   - "'str' object has no attribute 'setdefault'" where the code expected a Mapping.
3) Later, location gate failed on live pages even though suggestions visibly loaded:
   - orm.location_gate.missing followed by location_gate_blocked.
   - The app typed in location but did not select a suggestion; hidden field stayed empty.

References:
- Logs included rowser_use watchdog messages, CDP version endpoints, and our structured events emitted by 	elemetry.log_event.

## B. Root Causes and Decisions

### B1. Injected JS planner string broke due to brittle escaping
- Original helper used manual regex/string escapes like:
  `js
  String(value).replace(/\\/g, "\\\\").replace(/' /g, "\\'")
  `
- When embedded in a Python triple‑quoted string and then evaluated in the page, backslashes/quotes became mis‑escaped, producing invalid JS tokens.

Decision:
- Eliminate manual escaping and regex literals. Use:
  - q(v) = JSON.stringify(String(v)) for all quoted values inside selectors.
  - Use attribute selectors rather than #id whenever possible:
    - [id=], [name=], [data-qa=], [aria-label=].
  - Keep text selectors like :has-text() only as metadata (not for DOM queries).

File/lines:
- src/job_ai_auto_apply_ui/browser_agent/lever.py – in LeverApplyAgent.build_plan_in_browser (search for const q = and [id=
  - If Mapping → dict(payload)
  - If str → json.loads(payload)
  - Else → json.loads(json.dumps(payload)) as a last resort.

File/lines:
- src/job_ai_auto_apply_ui/browser_agent/lever.py – immediately after payload = await page.evaluate(...) inside uild_plan_in_browser.

### B3. Structured location gate not satisfied (live sites)
- We only typed the value and attempted a quick, generic click. On most Lever skins, the hidden selectedLocation JSON is set only after a real suggestion selection (keyboard or click). We also required a specific .dropdown-container+.dropdown-results visibility which some skins don’t use.

Decision:
- Make the location flow user‑like and resilient to skin differences:
  1) Focus and type char‑by‑char with input/keydown/keyup events.
  2) Wait up to 5s for either: suggestions present under .dropdown-results, ul.dropdown-results, or [role="listbox"]; or the hidden JSON already has a name.
  3) Try keyboard first: send ArrowDown+Enter up to 3 times with small waits.
  4) If still unset, click fallback: search items under those roots with a broad selector set: .dropdown-location, [role="option"], .Select-option, li[role="option"], li, [data-value].
  5) Final validation is performed separately by alidate_location_gate.

Files:
- src/job_ai_auto_apply_ui/browser_agent/lever.py
  - Function: _set_structured_location(...) – expanded wait logic, keyboard events, click fallback, and hidden JSON polling.
  - Function: alidate_location_gate(...) – unchanged logic; tests updated to tolerate empty state.

New fixture & test:
- 	ests/fixtures/lever_location_momentum.html (your captured DOM skin)
- 	ests/integration/test_lever_location_gate.py
  - Added 	est_location_gate_momentum_dropdown_selection
  - Fixed first test to avoid KeyError by using state.get("name", "").

## C. Files Touched (Summary)

- src/job_ai_auto_apply_ui/browser_agent/lever.py
  - Planner JS refactor: JSON.stringify (q) + attribute selectors; safer label [for=] usage.
  - Evaluate result coercion (str → json.loads) before setdefault.
  - Location setter _set_structured_location: user‑like typing; resilient ready wait; keyboard selection with retries; click fallback; hidden JSON poll.
- 	ests/fixtures/lever_location_momentum.html (NEW)
  - Simulates momentum dropdown: .dropdown-results > .dropdown-location and sets hidden JSON on selection.
- 	ests/integration/test_lever_location_gate.py
  - Added new test for momentum dropdown selection; fixed KeyError in initial gate test; note Playwright evaluate signature change below.

## D. What Worked / What Didn’t

Worked:
- JSON.stringify quoting (q) + attribute selectors; stopped JS parse errors.
- Post‑evaluate coercion; removed the setdefault crash.
- New momentum fixture; verifies we can satisfy the gate when .dropdown-location is present and click works.
- Longer waits and keyboard fallback improved stability on slower pages.

Didn’t (or still flaky in some skins):
- Requiring .dropdown-container visibility alone (many skins don’t use or toggle that element). We now check for multiple roots.
- Minimal keyboard events (key only). Some sites look at code/keyCode/which; we may still need to add these fields to make Enter/ArrowDown always register.
- In tests, passing multiple positional args to page.evaluate (Python API mismatch) caused a TypeError until we switched to a single object arg.

## E. Open Issues / Next Steps

1) Keyboard event completeness
   - Consider including code, keyCode, which in synthetic KeyboardEvents for ArrowDown/Enter to satisfy sites reliant on legacy props:
     `js
     new KeyboardEvent('keydown', { key:'ArrowDown', code:'ArrowDown', keyCode:40, which:40, bubbles:true })
     new KeyboardEvent('keydown', { key:'Enter',    code:'Enter',    keyCode:13, which:13, bubbles:true })
     `

2) Broaden root/item selectors further
   - Some Lever themes may use different containers. We already support:
     roots: .dropdown-results, ul.dropdown-results, [role="listbox"];
     items: .dropdown-location, [role="option"], .Select-option, li[role="option"], li, [data-value].
   - If a new site fails, capture one suggestion item’s outerHTML and add its pattern.

3) Telemetry enhancements
   - Emit an event when selection commits, including strategy used (keys vs click), total items seen, chosen item text (truncated), and final hidden JSON value snippet.

4) Tests
   - Add a keyboard‑only test case to assert ArrowDown+Enter commits selection.
   - Add fixture variants for ul.dropdown-results > li and ARIA listbox ([role="listbox"]/[role="option"]).

## F. Reproduction and Validation

Reproduce live:
- uto-apply apply --profile <profile>
- Watch for logs:
  - DEBUG: Evaluating JavaScript: block for planner → should not error.
  - orm.location_gate.missing → indicates selection didn’t commit.
- Confirm the hidden field updates by manually running in DevTools:
  `js
  document.querySelector('input#selected-location[name="selectedLocation"]').value
  // JSON string like: {"name":"Hollister, CA", "id":"…"}
  `

Run tests:
- pytest tests/integration/test_lever_location_gate.py -q
  - Expect momentum dropdown test to pass
  - The original test now uses state.get("name", "") to avoid KeyError.

## G. References

- Files:
  - src/job_ai_auto_apply_ui/browser_agent/lever.py
  - 	ests/fixtures/lever_location_momentum.html
  - 	ests/integration/test_lever_location_gate.py
- Prior specs and plans:
  - specs/001-as-a-job/plan.md, specs/001-as-a-job/spec.md, specs/001-as-a-job/contracts/cli-contracts.md
- External:
  - MDN querySelector rules for valid selectors and escaping; MDN CSS.escape
  - Chrome DevTools Protocol Runtime.evaluate (returnByValue behavior)

## H. Commit/Change Log (local)

Key changes were made across multiple edits on Oct 4–5, 2025. See git diff for exact hunks, particularly in lever.py around:
- uild_plan_in_browser (q(), attribute selectors)
- post‑evaluate coercion
- _set_structured_location (user‑like typing, waits, keyboard, click fallback)
- alidate_location_gate (unchanged logic; tests updated to tolerate empty state)

---
Maintainer note: If a site still fails the gate after these changes, please post one suggestion item’s outerHTML (while the dropdown is visible) and the value of document.querySelector('#selected-location')?.value before and after selection. We can add a selector mapping quickly.
