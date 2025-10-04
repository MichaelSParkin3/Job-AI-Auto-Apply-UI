# Deterministic **FormPlan** for Lever Applications (Browser‑Use)

**Objective.** Build a single, deterministic “FormPlan” from the live DOM, then execute it with zero guesswork. Keep LLMs out of planning; only use them for gap‑fill when a field is truly unmapped or semantically ambiguous.

---

## What the FormPlan returns

A single JSON object that your executor can use end‑to‑end:

```json
{
  "meta": {
    "formRoot": "form#application-form, #application",
    "eeoRoot": ".eeo-survey, #eeo-survey",
    "captchaSelector": ".h-captcha, .g-recaptcha",
    "requiresLocationGate": true
  },
  "widgets": {
    "resume": {
      "input": "#resume-upload-input,[data-qa=\"input-resume\"],input[type=\"file\"][name=\"resume\"]",
      "triggers": ["[data-qa='input-resume']"],
      "successSignals": [
        ".resume-upload-success",
        ".application-upload-success",
        ".filename",
        "input[name='resumeStorageId']"
      ],
      "failureSignals": [".resume-upload-failure",".resume-upload-oversize"]
    }
  },
  "fields": [
    {
      "name": "name",
      "label": "Full name",
      "selector": "input[name='name'][data-qa='name-input']",
      "type": "text",
      "required": true
    },
    {
      "name": "email",
      "label": "Email",
      "selector": "input[name='email'][data-qa='email-input']",
      "type": "email",
      "required": true,
      "pattern": "[a-zA-Z0-9.#$%&'*+\\/=?^_`{|}~][a-zA-Z0-9.!#$%&'*+\\/=?^_`{|}~-]*@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*"
    },
    {
      "name": "phone",
      "label": "Phone",
      "selector": "input[name='phone'][data-qa='phone-input']",
      "type": "text",
      "required": false
    },
    {
      "name": "location",
      "label": "Current location",
      "selector": "#location-input",
      "type": "text",
      "required": false,
      "aux": { "selectedLocationHidden": "input#selected-location[name='selectedLocation']" }
    }
  ],
  "submit": { "selector": "button[type='submit'], input[type='submit']" }
}
```

> The keys above align with your current apply phase: resume widget success/failure banners, contact fields with `data-qa` attributes, the structured location hidden input, and submit control.


---

## Deterministic DOM‑scan (build once per page)

**Selector precedence** (use first that exists): `name` → `id` → `data-qa` → aria/role → text‑anchored CSS → nth‑index fallback. Record `primarySelector` and `alternates[]` if useful.

### 1) Find form, EEO, CAPTCHA, & gates

```js
const root = document.querySelector('form#application-form, #application');
const eeoRoot = root?.querySelector('.eeo-survey, #eeo-survey') || null;
const captcha = root?.querySelector('.h-captcha, .g-recaptcha') || null;
const requiresLocationGate = !!root?.querySelector('#location-input') && !!root?.querySelector('input[name="selectedLocation"]');
```

### 2) Resume widget (selectors & signals)

Prefer stable attributes found in Lever’s template:

- Input: `#resume-upload-input`, `[data-qa="input-resume"]`, or `input[type="file"][name="resume"]`
- Success: `.resume-upload-success`, `.application-upload-success`, `.filename`
- Failure: `.resume-upload-failure`, `.resume-upload-oversize`
- Hidden storage id (when present): `input[name="resumeStorageId"]`

### 3) Contact & link fields

Harvest standard fields under `.application-question`:

- **Name** — `input[name="name"][data-qa="name-input"]` (required)
- **Email** — `input[name="email"][data-qa="email-input"]` (required; capture `pattern`)
- **Phone** — `input[name="phone"][data-qa="phone-input"]`
- **Location** — visible `#location-input` plus hidden `input#selected-location[name="selectedLocation"]`

Detect likely **links** by `name/id/placeholder` including “linkedin”, “github”, “portfolio”.

### 4) Generic questions

Walk `.application-question, .application-additional` under `formRoot`. For each field, capture:

- `label` (from `.application-label` text)
- `type` (`input.type` or tag name)
- `required`, `pattern`, and options for `select/radio/checkbox` (extract values & labels)

### 5) Submit control

Prefer semantic attributes: `button[type="submit"], input[type="submit"]` (fall back to a text‑match “Submit”).


---

## Single‑shot builder: `build_plan_in_browser(page)`

Run exactly once after navigation lands. Returns a JSON‑serializable object.

```python
# Python (Browser-Use Actor) – call once to build the plan
plan = await page.evaluate("""
(() => {
  const root = document.querySelector('form#application-form, #application');
  const q   = (sel, r=root) => r?.querySelector(sel);
  const qa  = (sel, r=root) => Array.from(r?.querySelectorAll(sel) ?? []);

  const toSelector = (el) => {
    if (!el) return null;
    const tag = el.tagName.toLowerCase();
    return el.name ? `${tag}[name="${el.name}"]`
         : el.id   ? `#${el.id}`
         : el.getAttribute('data-qa') ? `[data-qa="${el.getAttribute('data-qa')}"]`
         : null;
  };

  const fields = [];
  qa('.application-question, .application-additional').forEach(li => {
    const label = li.querySelector('.application-label')?.textContent?.trim() || '';
    const input = li.querySelector('input, textarea, select');
    if (!input) return;
    const type = input.type || input.tagName.toLowerCase();

    const optionVals = input.tagName === 'SELECT'
      ? Array.from(input.options).map(o => ({ value: o.value, label: o.textContent.trim() }))
      : undefined;

    fields.push({
      name: input.name || null,
      label,
      selector: toSelector(input),
      type,
      required: !!input.required,
      pattern: input.pattern || null,
      options: optionVals
    });
  });

  return {
    meta: {
      formRoot: 'form#application-form, #application',
      eeoRoot: '.eeo-survey',
      captchaSelector: '.h-captcha, .g-recaptcha',
      requiresLocationGate: !!q('#location-input') && !!q('input[name="selectedLocation"]')
    },
    widgets: {
      resume: {
        input: '#resume-upload-input,[data-qa="input-resume"],input[type="file"][name="resume"]',
        triggers: ['[data-qa="input-resume"]'],
        successSignals: ['.resume-upload-success','.application-upload-success','.filename','input[name="resumeStorageId"]'],
        failureSignals: ['.resume-upload-failure','.resume-upload-oversize']
      }
    },
    fields,
    submit: { selector: 'button[type="submit"], input[type="submit"]' }
  };
})()
""")
```


---

## Executing the FormPlan deterministically

### A) Use the **Actor** for low‑level, Playwright‑like control

```python
from browser_use import Browser

browser = Browser()         # configure allowed_domains, user_data_dir, etc.
await browser.start()
page = await browser.new_page(apply_url)

# Build plan once
plan = await page.evaluate(... as above ...)

# Fill contact fields
for f in plan["fields"]:
    if f["name"] in {"name", "email", "phone"} and f["selector"]:
        el = (await page.get_elements_by_css_selector(f["selector"]))[0]
        await el.fill(profile_defaults[f["name"]])

# Location gate
if plan["meta"]["requiresLocationGate"]:
    loc_el = (await page.get_elements_by_css_selector("#location-input"))[0]
    await loc_el.fill(profile_defaults.get("location",""))
    await page.press("Enter")  # pick top suggestion if dropdown appears
    # verify hidden selectedLocation updated
    hidden = (await page.get_elements_by_css_selector("input[name='selectedLocation']"))[0]
    assert (await hidden.get_attribute("value")) not in ("", "{\"name\":\"\"}")

# Resume upload (deterministic branch first)
resume_sel = plan["widgets"]["resume"]["input"]
in_el = (await page.get_elements_by_css_selector(resume_sel))[0]
await in_el.fill(profile["resume_path"])   # CDP file input set

# Verify success signals or bail early on failure signal
for ss in plan["widgets"]["resume"]["successSignals"]:
    if (await page.get_elements_by_css_selector(ss)):
        break
else:
    raise RuntimeError("Resume upload not detected")

# Validate before submit
is_valid = await page.evaluate("( ) => { const f = document.querySelector('form#application-form, #application'); f?.reportValidity(); return !!f?.checkValidity(); }")
if not is_valid:
    # collect :invalid for LLM/human pass
    invalid = await page.evaluate("() => Array.from(document.querySelectorAll('form#application-form :invalid')).map(x => x.name || x.id || x.outerHTML.slice(0,80))")
    print({"invalid": invalid})
```

**Notes**

- Prefer Actor methods (`get_elements_by_css_selector`, `fill`, `press`, `evaluate`) for precise DOM work and timing you control.
- Only escalate to LLM after you’ve collected the list of `:invalid` fields.


### B) Wrap deterministic steps as **Tools** for the Agent (when you *do* use LLM)

```python
from browser_use import Tools, ActionResult, Browser

tools = Tools()

@tools.action(description="Upload a resume file into the detected input", allowed_domains=["*.jobs.lever.co"])  # restrict domain
def upload_resume(resume_path: str, browser: Browser) -> ActionResult:
    page = browser.get_current_page_sync()
    # (Use the same selectors your plan generated; this is just a minimal example)
    input_els = page.get_elements_by_css_selector_sync('#resume-upload-input,[data-qa="input-resume"],input[type="file"][name="resume"]')
    if not input_els:
        return "resume input not found"
    input_els[0].fill_sync(resume_path)
    return "resume uploaded"

# Later in your Agent(...), include tools=tools
```

**Tips**

- Give tools **descriptive names** and limit them via `allowed_domains` so the LLM can’t misfire elsewhere.
- Tool functions can accept `browser` (BrowserSession) for direct Actor control and CDP access.


### C) Agent configuration you’ll actually use

- `initial_actions`: run a few deterministic actions (e.g., call your `fill_from_formplan`) before the LLM gets a turn.
- `max_actions_per_step`: cap how many fills/clicks an LLM step may emit (e.g., 6–10 fields).

```python
agent = Agent(
  task="Fill only the *remaining* empty/invalid fields based on the provided FormPlan and profile/job context.",
  llm=llm,
  browser=browser,
  tools=tools,
  initial_actions=[
    {"tool": "execute_js", "input": {"script": "() => document.querySelector('form#application-form')?.reportValidity()"}},
  ],
  max_actions_per_step=8,
)
```


### D) Lifecycle hooks for observability & guardrails

Use hooks to snapshot your plan, form validity, and block risky transitions (e.g., do not submit if `captchaSelector` is present).

```python
async def on_step_start(agent):
    # Snapshot current URL & invalids
    invalid = await agent.browser_session.get_current_page().evaluate("() => Array.from(document.querySelectorAll('form#application-form :invalid')).map(el => el.name || el.id) ")
    agent.state.debug = agent.state.get('debug', {}) | { 'invalid': invalid }

async def on_step_end(agent):
    # Prevent accidental submits behind captcha
    has_captcha = await agent.browser_session.get_current_page().evaluate("() => !!document.querySelector('.h-captcha, .g-recaptcha')")
    if has_captcha:
        agent.pause()   # handoff to supervised/manual review
```


---

## Play nicely with the browser

- **Connect or launch.** If you already run Chrome with `--remote-debugging-port=9222`, provide `cdp_url="http://localhost:9222"` when creating `Browser(...)` to reuse your real profile. Otherwise, launch a managed Chromium and set `user_data_dir` + `profile_directory` for persistence.
- **Scope navigation.** Always set `allowed_domains` to keep the agent on rails (e.g., `["*.google.com","*.jobs.lever.co"]`).


---

## Edge cases you’ll hit (and how to keep them deterministic)

1) **iFrames / hidden inputs.** Use `execute_js` for frame‑scoped queries or fall back to the CDP file input setter through the Actor when “click to open chooser” widgets intercept events.
2) **Location autocomplete.** Treat it as a gate: type, press Enter, then assert `selectedLocation` JSON has a non‑empty `name`. Only then attempt resume upload.
3) **CAPTCHA present.** Do **not** attempt to bypass. Pause, persist artifacts (screenshot, DOM snapshot), and mark the queue item for manual review.


---

## Minimal mapping from the example Lever HTML

- Resume input & success/failure banners are present and labeled via `data-qa`, `id`, and utility classes. The success/oversize/failure markers are siblings near the input.
- Email input carries a strict `pattern` you should copy into the plan for local validation.
- `#location-input` pairs with hidden `#selected-location[name='selectedLocation']` that holds a JSON string; ensure it updates before enabling submit.

These patterns are intentionally captured by the selectors/signals in the JSON spec at the top.


---

## Execution recipe (put it all together)

1) **DOM scan** → build FormPlan once.
2) **Fill deterministic**: profile name/email/phone/links; set location gate; upload resume; collect questions.
3) **Validate** with `reportValidity()`/`checkValidity()`. If invalid: collect `:invalid` and **only then** call a narrow LLM tool pass.
4) **Submit** deterministically; if the page remains or a captcha appears, persist artifacts and mark for review.

That’s it—repeatable, observable, and LLM‑minimal.

