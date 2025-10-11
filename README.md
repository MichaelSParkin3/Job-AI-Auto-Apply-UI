# Job‑AI‑Auto‑Apply‑UI

Supervised and automated CLI to discover Lever job postings and auto‑fill application forms — including reliable resume uploads — using Browser‑Use (CDP‑first) and Playwright.

## Quick Start

Prerequisites
- Python 3.11
- A Chromium‑family browser installed (Chrome, Edge, or Chromium)
- Optional: Playwright browsers (`python -m playwright install`) if you don’t want to use a system browser channel

Install
- Create and activate a virtualenv
  - Windows (PowerShell)
    - `python -m venv .venv`
    - `.\.venv\Scripts\Activate.ps1`
  - macOS/Linux
    - `python3 -m venv .venv`
    - `source .venv/bin/activate`
- Install the package: `pip install -e .`
- Copy `.env.example` to `.env` and fill in any keys you’ll use

Profiles
- Profiles live in `profiles/*.toml` (see examples in that folder)
- Select a profile with `--profile <id>` where `<id>` matches the TOML filename (without extension)

Examples
- Discover postings for the last 24h (max 10) and enqueue:
  - `auto-apply discover --profile michael_scott_parkin_iii --window 24h --cap 10`
- Apply in supervised mode with robust resume upload diagnostics:
  - `auto-apply apply --profile michael_scott_parkin_iii --use-llm-locator --debug-resume-widget --resume-wait-timeout-seconds 25`
  - Add `--save-logs` (optionally `--logs-dir logs/run-$(date +%s)`) to persist structured logs alongside stdout/stderr
- Apply to a single specific job (auto-resets status if needed):
  - `auto-apply apply --profile michael_scott_parkin_iii --id 0199a9b79cf7f4e39afef467030c --review-mode`
- Resume a specific queued job by id:
  - `auto-apply resume-job 0199a9b79cf7f4e39afef467030c`

## CLI Commands

- `auto-apply discover`
  - `--profile` (required): profile id (TOML in `profiles/`)
  - `--window` (default `24h`): discovery window (`12h`, `7d`, `2w`, or hours like `48`)
  - `--cap` (default `10`): maximum results to enqueue
  - `--json`: machine‑readable output

- `auto-apply apply`
  - Mode: `--auto` or `--supervised` (default when neither is set: supervised)
  - `--profile` (required)
  - `--id <job_id>`: Process only this specific job (auto-resets status if FAILED/CAPTCHA_BLOCKED/SUBMITTED)
  - `--json`: machine‑readable events
  - LLM overrides: `--llm-provider`, `--llm-model`
  - Resume widget helpers:
    - `--use-llm-locator` (sets `AUTO_APPLY_USE_LLM_LOCATOR=1` for the run)
    - `--debug-resume-widget` (sets `AUTO_APPLY_DEBUG_RESUME_WIDGET=1` to emit a structured widget snapshot if upload isn't detected)
    - `--resume-wait-timeout-seconds N` (sets `AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS=N`)
  - Saved state & artifacts:
    - `--review-mode`: Fill forms and save state (`pre.json`, `pre-full.jpg`) without submitting; marks item as `pending_review`
    - `--audit-after-submit` / `--no-audit-after-submit`: Control post-submission screenshot capture (default: ON)
  - Logging: `--save-logs` writes structured JSON logs to `<logs-dir>/<timestamp>.log` (default `logs/`); override directory with `--logs-dir <path>`
  - Exit codes: `0` when every item submits, `3` when any item fails, `4` when job ID not found

- `auto-apply resume-job`
  - `id` (required): application item id from `data/queues/<profile>.json`
  - `--submit`: Auto-submit after prefilling (default: pause for review)
  - `--json`: machine‑readable output
  - Exit codes: `0` on success, `4` when the id is not found, `6` when saved state is missing/corrupt (`invalid_state`)

- `auto-apply replay-job`
  - `id` (required): application item id
  - Resets queue item to `in_progress` without opening browser (use when retrying from scratch)
  - `--json`: machine‑readable output
  - Exit codes: `0` on success, `4` when the id is not found

- `auto-apply cleanup-artifacts`
  - `--older-than <days>` (required): Delete artifacts older than specified days
  - `--profile <id>` (optional): Limit cleanup to specific profile
  - `--dry-run`: List matched files without deleting
  - `--json`: machine‑readable output
  - Exit codes: `0` success, `2` nothing matched, `5` invalid arguments

## Profiles (TOML)

Example (`profiles/michael_scott_parkin_iii.toml`):

```toml
id = "michael_scott_parkin_iii"
name = "Michael Scott Parkin III"
resume_path = "resumes/Michael_Parkin_Senior_Front_End_Developer_Resume_2025.pdf"
preferred_browser = "chromium"     # or: chrome | msedge
user_data_dir = "G:/.../data/browser_profiles/michael_scott_parkin_iii"

[defaults]
name = "Your Name"
email = "you@example.com"
phone = "+1-555-010-0000"
location = "City, ST"
portfolio_url = "https://…"
github_url = "https://github.com/…"
linkedin_url = "https://linkedin.com/in/…"

[keywords]
roles = ["Senior Frontend Engineer", "Staff Frontend Engineer"]
tech_stack = ["React", "Next.js", "TypeScript"]

[prompts]
cover_letter = "Tailored guidance for cover letters…"
```

Notes
- `preferred_browser` chooses the launch channel: `chrome`, `chromium`, `msedge` (Edge)
- `user_data_dir` enables persistent browser profiles per user
- `resume_path` can be relative to repo or absolute

## Environment Variables (.env)

The CLI auto‑loads `.env` if present. Important variables:

LLM & API
- `LLM_PROVIDER` (e.g., `openrouter` | `google`)
- `LLM_MODEL` (model id for your provider)
- `OPENROUTER_API_KEY` | `GOOGLE_API_KEY`
- `LLM_TEMPERATURE` (default `0.0`)
- `LLM_TIMEOUT_SECONDS` (default `30`)
- `LLM_REFERER`, `LLM_USER_AGENT` (optional branding for some providers)

Networking
- `PROXY_URL` or `HTTP_PROXY` / `HTTPS_PROXY`
- `USER_AGENT` (override UA string if needed)
- `ALLOWED_DOMAINS` (comma‑separated; default `google.*,jobs.lever.co`)
- `AUTO_APPLY_BROWSER_MODE` (`auto` | `off` | `disabled` | `http`) — force legacy HTTP discovery when not `auto`

Diagnostics & Artifacts
- `AUTO_APPLY_DIAGNOSTICS` (default `0`) — turn on all capture
- `AUTO_APPLY_CAPTURE_VIDEO` (default `0`)
- `AUTO_APPLY_CAPTURE_HAR` (default `0`)
- `AUTO_APPLY_ARTIFACTS_DIR` (default `data/artifacts`)

Resume Upload Feature Flags
- `AUTO_APPLY_USE_LLM_LOCATOR` (default `0`) — allow LLM to find the resume input
- `AUTO_APPLY_DEBUG_RESUME_WIDGET` (default `0`) — emit a structured snapshot if not detected
- `AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS` (default `25`)

Stealth / Anti‑Detection (applied to process environment before browser launch)
- `BROWSER_LOCALE` (default `en-US`)
- `BROWSER_TIMEZONE` (default `America/Los_Angeles`)
- `BROWSER_VIEWPORT_WIDTH` (default `1280`)
- `BROWSER_VIEWPORT_HEIGHT` (default `800`)
- `AUTO_APPLY_DISABLE_DEFAULT_EXTENSIONS` (default `1`) — prefer a clean browser

General Behavior
- `DWELL_SECONDS` (default `0.8`) — small delays between actions
- `JITTER_SECONDS` (default `0.4`) — randomized delay variance
- `MAX_TABS` (default `3`) — safety cap
- `RETRIES` (default `2`)
- `DISCOVERY_WINDOW_HOURS` (default `24`)
- `DISCOVERY_CAP` (default `10`)
- `AUTO_APPLY_PROFILES_DIR` — override `profiles/` location

Tip: all of the above can be set inline per‑run, or placed in `.env`.

## How It Works (High‑Level)

- `discover` parses Google results and filters `jobs.lever.co` links, then enqueues items in `data/queues/<profile>.json`.
- `apply` launches a Browser‑Use session, navigates to the company’s Lever form, and:
  - Ensures navigation landed on `/apply` (closes stray `about:blank` tabs)
  - Fills gating fields (e.g., location) when needed
  - Uploads the resume via CDP (`DOM.setFileInputFiles`) with fallbacks
  - Completes basic contact fields and submits
- Structured logs (JSON via `structlog`) are printed to stderr; artifacts can be saved per profile under `data/artifacts/<profile>/` when diagnostics are enabled.

## Artifacts & Logs

### Structured Logs
- Events like `apply.start`, `form.wait.*`, `resume_upload.*`, `review_mode.artifacts_captured` emitted in JSON
- Use `--save-logs` to persist logs to timestamped `.jsonl` files for analysis

### Artifact Files
Saved to `data/artifacts/<profile>/<item_id>/`:

**Pre-Submission** (review mode or captcha):
- `pre.json`: SavedState v1 schema (form selectors + filled values)
- `pre-full.jpg`: Full-page screenshot before submission

**Post-Submission** (successful applications):
- `post-full.jpg`: Full-page screenshot of confirmation page (disable with `--no-audit-after-submit`)
- `confirmation.json`: Confirmation text, ID, and capture timestamp

**Diagnostics** (when `AUTO_APPLY_DIAGNOSTICS=1`):
- Video/HAR recordings (enable with `AUTO_APPLY_CAPTURE_VIDEO=1` / `AUTO_APPLY_CAPTURE_HAR=1`)
- Resume widget snapshot (enable with `AUTO_APPLY_DEBUG_RESUME_WIDGET=1`)

**Retention**: Manual only—use `auto-apply cleanup-artifacts --older-than <days>` to delete old files

## Troubleshooting

- “Unexpected UTF‑8 BOM” while loading queues
  - Fixed: queue loader now tolerates BOM (`utf-8-sig`). If you still hit issues, re‑save `data/queues/<profile>.json` as UTF‑8.
- “Expected elements did not render in time” or URL shows `about:blank`
  - The app now verifies navigation and refocuses the active tab; closing stray tabs is best‑effort. Re‑run with `--debug-resume-widget` if the resume upload is flaky.
- Reset queue state
  - Edit `data/queues/<profile>.json` to remove failed items or set their status back to `"NEW"`, or simply delete the file to start fresh. The loader will recreate it on next discovery.

## Development

Common tasks
- Lint: `ruff check .`
- Test: `pytest`
- Run from source: `auto-apply --help`

Structure
- Source: `src/job_ai_auto_apply_ui/`
- Tests: `tests/`
- Queues: `data/queues/<profile>.json`
- Artifacts: `data/artifacts/` (namespaced by profile)

## Ethics & Use

Use this project responsibly. Respect site terms of service, robots rules, and rate limits. Obtain consent where required and avoid abusive automation behavior.

