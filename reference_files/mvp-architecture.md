# MVP Architecture: Lever Auto-Apply Assistant

## Project Goals
- Automate discovery of fresh Lever-hosted job postings relevant to the user.
- Manage multiple application profiles so each career track (for example front end developer or music producer) has dedicated resume files, preferences, and prompts.
- Generate form-ready responses grounded in the profile-specific resume and job history file, augmented with scraped job details.
- Drive a browser session end-to-end via `browser-use`, including resume upload and submission attempts, while running entirely on the local machine.
- Persist application state so partially completed forms (for example blocked by CAPTCHA) can be resumed manually.

## High-Level Flow
1. **Profile Selection** - Let the user choose which profile will drive the current automation run, loading its resume, demographic info, and search presets.
2. **Job Sourcing** - Launch a `browser-use` session in non-headless mode, navigate to Google, and issue a query such as `site:jobs.lever.co "front end developer" "US remote"` filtered to the last 24 hours. Capture the top N results (configurable per profile) and open them in background tabs for analysis.
3. **Qualification** - Optionally filter postings by keywords, location, or company name before queueing them for automation.
4. **Application Session** - For each queued posting, open the Lever application page with `browser-use`, ingest form schema, and request structured answers from the LLM using resume and job description context.
5. **Form Fill and Upload** - Populate fields, attach the resume PDF tied to the active profile, and advance through multi-step flows while logging each action. Highlighted elements from `browser-use` aid form targeting.
6. **Completion Handling** - If submission succeeds, mark the job as completed. If a CAPTCHA or unsupported widget appears, snapshot state and flag for manual follow-up.

## Core Components
| Component | Responsibilities | Tech Choices |
|-----------|-----------------|--------------|
| `profile_manager` | Loads profile metadata, resume paths, search keywords, and form defaults; provides CLI to add or switch profiles. | Local TOML or YAML files per profile backed by `pydantic` models. |
| `profile_context` | Maintains the canonical resume and job history file for the active profile, exposing structured data (skills, experience bullets) for prompt templating. | Plaintext or Markdown resume parsed to JSON via `pydantic` models. |
| `job_discovery` | Drives Google search flow using profile keywords, extracts Lever posting links, normalizes metadata (title, company, posted time). | `browser-use` multi-tab navigation, configurable throttling. |
| `application_queue` | Stores posting URLs with status transitions (`new`, `in_progress`, `captcha_blocked`, `submitted`, `failed`) scoped per profile. | Local SQLite file or JSON store under `data/state`. |
| `prompt_builder` | Crafts OpenRouter LLM prompts that blend job description snippets with structured resume context and Lever-specific instructions. | OpenRouter REST API, reusable prompt templates, retry and backoff wrapper. |
| `browser_agent` | Encapsulates `browser-use` session lifecycle, human-like navigation, form detection helpers, captcha heuristics, file upload interactions, and BrowserProfile tuning. | `browser-use` (Playwright under the hood), custom command library for common Lever widgets. |
| `state_recorder` | Captures DOM snapshots, filled field values, and runtime logs to support resume-after-captcha flow. | Disk-backed JSON or LiteFS snapshots, zipped asset per job. |
| `orchestrator` | High-level controller or CLI that pulls the next job for the active profile, coordinates LLM calls, triggers the browser agent, and updates statuses. | Typer or Click CLI, async event loop orchestrating tasks. |
| `audit_logger` | Centralized structured logging for actions, timestamps, errors, and compliance auditing. | `structlog` or `loguru`, optional JSON log sink. |

## LLM Orchestration
- Use OpenRouter or Google API models (for example `gpt-4.1-mini`, `gemini-2.5-pro`, `claude-3.5-sonnet`) selectable via configuration and overrideable per profile.
- Prompt template structure:
  - System prompt: "You are an assistant drafting concise, relevant answers for job application forms hosted on Lever. Use only the provided resume context."
  - Resume context: sanitized JSON representation plus key bullet highlights from the selected profile.
  - Job context: scraped company name, position title, location, employment type, compensation hints, and trimmed job description paragraphs.
  - Task instructions: guidance for tone (professional yet brief), field-specific notes (for example salary expectations, eligibility questions), and expected output schema (JSON, yes/no, multi-choice labels).
- Implement deterministic parsing for multi-choice or boolean fields by requesting explicit JSON outputs. Cache LLM responses per question to avoid redundant calls when retrying forms.
- Allow an optional human-in-the-loop checkpoint that surfaces generated answers before final submission when the job application is flagged for review.

## Browser-use Configuration and Stealth Practices
- Instantiate `BrowserProfile(headless=False, wait_between_actions=0.8)` (values configurable per profile) to keep the browser visible and pacing human-like. Add slight random jitter (for example +/-0.4 seconds) before each action.
- Persist a profile-specific `user_data_dir` to retain cookies when helpful, or set it to `None` for ephemeral sessions. Provide CLI flags to toggle behavior.
- Override automation fingerprints when running locally: set `ignore_default_args=['--enable-automation']` and inject a modern Chrome user agent. Confirm that `navigator.webdriver` is unset before form fill steps.
- Support optional proxy settings (`ProxySettings(server="http://ip:port"...)`) to rotate traffic when users want additional obfuscation, but default to direct local access.
- Leverage Browser Use's element highlighting (default behavior) to confirm the agent is acting on the intended fields; store screenshots for debugging when actions fail or time out.

## Browser Automation Practices
- Keep navigation throttled: respect configurable minimum dwell times on each page and avoid queueing more than a few parallel tabs per profile run.
- Encapsulate Lever-specific selectors (for example `input[name="name"]`, dynamic file upload buttons) in helper functions for easier maintenance.
- Detect page structure changes by validating key elements (job title header, apply form container) before continuing, and abort gracefully if mismatched.
- Capture confirmation text or screenshots after submission and attach them to the job history entry.
- Always honor Lever and Google terms of service; monitor request volume, insert throttling, and surface rate-limit configuration to the user.

## CAPTCHA and Session Recovery
- Monitor for common CAPTCHA cues (iframes from reCAPTCHA, hCaptcha). When detected:
  - Serialize current form values, active tab URL, and step index to the state store.
  - Persist a DOM snapshot and screenshot to assist manual completion.
  - Transition job status to `captcha_blocked` and notify via CLI output or log.
- Provide a CLI command `resume-job <job_id>` that reloads the saved state, reopens the page, and repopulates fields up to the CAPTCHA step so the user only needs to solve the challenge.

## Data and Security Considerations
- Store the resume file, profile metadata, queues, and generated structured profile data locally under `data/`; encrypt at rest if sensitive data is present (for example using the `cryptography` package with a user-supplied key).
- Keep OpenRouter or Google API keys in environment variables or a `.env` file managed by `python-dotenv`; never hardcode secrets.
- Redact personal identifiers from logs by default; allow opt-in verbose logging for debugging when required.
- Add consent prompts before the first run reminding the user to verify compliance with employer portals and to review submissions before sending.

## Coding and Testing Standards
- Adopt Google-style docstrings for every public module, class, and function so comments double as generated documentation. Include `Args`, `Returns`, `Raises`, and `Examples` sections where relevant.
- Prefer inline comments only when intent is non-obvious; keep logic self-documenting and surface higher-level explanations through docstrings.
- Enforce type hints across the codebase and validate them with `mypy` or a comparable static checker before merging.
- Require tests alongside each new feature or bug fix. Cover business logic with unit tests, prompt serialization with component tests, and browser automation with Playwright-driven integration suites.
- Use `pytest` with markers (for example `@pytest.mark.e2e`) so long-running browser scenarios can be isolated; wire the suite into the CLI via `python -m pytest`.
- Maintain deterministic fixtures that load profile and resume data from the local `data/` tree, and store test artifacts (screenshots, DOM snapshots) under `data/state/test_runs/` to avoid polluting production records.

## Configuration Layout
```
project/
  config/
    settings.example.toml   # API keys, throttling, model choices, resume path
    profiles/
      front_end.toml        # Profile-specific resume path, search keywords, defaults
      music_producer.toml
  data/
    resume/                 # Canonical resume plus machine-readable JSON cache per profile
    state/                  # Saved sessions, captcha snapshots, logs, queue storage
  src/
    __init__.py
    orchestrator.py
    profile_manager.py
    job_discovery.py
    application_queue.py
    browser_agent/
      __init__.py
      lever.py
    llm/
      __init__.py
      openrouter_client.py
      prompt_builder.py
```

## Implementation Roadmap
- **Phase 0 - Environment Setup**
  - Create a Python 3.11 virtual environment, add `browser-use`, `playwright`, `httpx`, `pydantic`, `python-dotenv`, `sqlmodel`, and `structlog` to `pyproject.toml`.
  - Configure Playwright browsers (`playwright install chromium`).
  - Establish configuration schema, profile directory structure, and load resume files; create placeholder `.env.example` with the OpenRouter key.

- **Phase 1 - Profile and Discovery Foundation**
  - Implement `profile_manager` with commands to add, list, and activate profiles.
  - Build `job_discovery` to run Google queries using profile title and location keywords, pacing searches via `wait_between_actions` and result throttling.
  - Normalize metadata (title, company) and enqueue to the local `application_queue`.

- **Phase 2 - Form Automation Core**
  - Build `browser_agent.lever` helpers for detecting steps, mapping fields, and uploading files in non-headless mode with hardened BrowserProfile defaults.
  - Integrate the LLM prompt builder; ensure JSON responses map to form fields with validation hooks and include job description excerpts.
  - Implement the resume upload workflow and submission detection; log success or failure outcomes.

- **Phase 3 - Resilience and Recovery**
  - Add CAPTCHA detection, state snapshotting, and the `resume-job` CLI flow.
  - Harden error handling (timeouts, navigation failures) with automatic retries and detailed logs tied to the active profile.
  - Introduce a human-in-the-loop review mode to show auto-filled answers before the final submit when desired.

- **Phase 4 - Hardening and Observability**
  - Add structured logging, metrics hooks, and optional notifications (email or Slack) for blocked jobs.
  - Document configuration and usage in the README, including legal considerations and manual override steps.
  - Write integration tests with mock Lever forms to validate selector mappings without hitting production systems.

