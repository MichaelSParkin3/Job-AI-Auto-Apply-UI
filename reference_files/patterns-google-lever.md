# Google + Lever Selectors and Patterns (reference)

Practical, minimal selectors and URL patterns distilled from provided HTML samples. Use these to keep scraping and form‑fill robust across minor UI changes.

## Google Search (Discovery)

- Primary query input
  - CSS: `textarea#gLFyf, textarea#APjFqb`
  - Preferred: build URL directly to avoid fragile UI steps.

- Build search URL (programmatic)
  - Base: `https://www.google.com/search?q=site:jobs.lever.co+<encoded+keywords>`
  - Time filter via `tbs` parameter:
    - Past hour: `tbs=qdr:h`
    - Past 24 hours: `tbs=qdr:d`
    - Past week: `tbs=qdr:w`
    - Past month: `tbs=qdr:m`
    - Past year: `tbs=qdr:y`
    - Custom range: `tbs=cdr:1,cd_min:MM/DD/YYYY,cd_max:MM/DD/YYYY`

- Result metadata (optional)
  - Capture `source_query` (constructed query) and `source_rank` per result for traceability.

## Lever Posting Page (Details)

- Title
  - CSS: `.posting-headline h2`
  - Map → `ApplicationItem.details.posting_text` (excerpt + full text) and `title`.

- Categories (normalize to JobDetails)
  - Location: `.posting-categories .location` → `details.location`
  - Department/team: `.posting-categories .department` → `details.department`
  - Employment/commitment: `.posting-categories .commitment` → derive `details.employment_type`
  - Work model: `.posting-categories .workplaceTypes` → `details.work_model`

- Description container
  - CSS: `[data-qa="job-description"]` (inner text)
  - Save two variants:
    - `details.posting_excerpt` (≤1500 chars, trimmed paragraphs)
    - `details.posting_text` (≤8192 chars, cleaned of HTML)

- Apply button (navigate to form)
  - CSS: `a.postings-btn.template-btn-submit[href*="/apply"]`
  - Attribute: `href` → `details.apply_url`

## Lever Application Form (Apply)

- Form root
  - CSS: `form#application-form`

- File upload (Resume)
  - Visible trigger: `.visible-resume-upload`
  - File input: `input#resume-upload-input[name="resume"]`

- Contact fields
  - Full name: `input[data-qa="name-input"][name="name"]`
  - Email: `input[data-qa="email-input"][name="email"]`
  - Phone: `input[data-qa="phone-input"][name="phone"]`
  - Current location:
    - Text input: `input#location-input.location-input`
    - Hidden selected: `input#selected-location`

- Links section
  - LinkedIn: `input[name="urls[LinkedIn]"]`
  - GitHub: `input[name="urls[GitHub (If applicable)]"]`
  - Portfolio: `input[name="urls[Portfolio (If applicable)]"]`

- Additional information (cover letter / notes)
  - Textarea: `textarea#additional-information[name="comments"]`

- Dynamic question cards (long‑form Q&A)
  - Hidden JSON template:
    - CSS: `input[name^="cards"][name$="[baseTemplate]"]`
    - Value: JSON with `fields[]` objects → use to create stable keys in `AnswerCache`.
  - Corresponding answers:
    - CSS: `textarea.card-field-input[name^="cards"][name$=]` (names like `cards[<id>][fieldN]`)
  - Strategy:
    - Parse baseTemplate JSON, build a list of `{id, type, text, required}`.
    - For each rendered `textarea.card-field-input`, map by index to the corresponding template field.

- Submit controls
  - Main button: `button#btn-submit[data-qa="btn-submit"]` (type="button" → JS submit)
  - hCaptcha auto submit helper: `button#hcaptchaSubmitBtn.hidden`
  - hCaptcha presence: `div#h-captcha.h-captcha`, iframes from `newassets.hcaptcha.com`
  - Persistence:
    - On CAPTCHA detect, save `form values`, `current URL`, `step index`, plus DOM/screenshot artifacts.

## Mapping to Data Model

- ApplicationItem core
  - `url`, `company`, `title`, `hash` (sha256 of url|company|title)

- JobDetails (populate on discovery/apply)
  - `location`, `work_model`, `employment_type`, `department`
  - `posting_excerpt`, `posting_text`, `tech_tags` (optional keyword pass)
  - `apply_url`, `source_query`, `source_rank`, `extracted_at`

- Artifacts
  - `dom_snapshot_path` (details/apply page), `screenshot_path` (errors), optional `video_path`, `har_path`

## Notes & Tips

- Prefer building Google search URLs with `tbs` instead of clicking UI elements (more deterministic and faster).
- Many Lever pages share the same class names; fall back to text heuristics if classes change (e.g., label text near inputs).
- For long‑form answers, keep `AnswerCache.type=long_form` and avoid reuse by default; store `question_key` as a normalized version of the template field `text`.
- Some sites set `btn-submit` to `type="button"`; always click it to trigger JS handlers rather than submitting the form element directly.
- Detect closed/404 postings by checking absence of `.posting-headline` and form root; mark `details.closed = true` and record artifact.

