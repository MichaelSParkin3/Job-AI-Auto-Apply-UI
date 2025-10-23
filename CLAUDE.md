# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Job-AI-Auto-Apply-UI** is a supervised CLI tool that discovers Lever job postings via Google search and auto-fills application forms using Browser-Use (CDP-first) and Playwright. The system emphasizes resumable workflows, structured logging, and reliable resume uploads.

**Key Characteristics:**
- Python 3.11 with async/await patterns
- Browser automation via browser-use 0.7.x (CDP-based) and Playwright
- Profile-driven configuration with TOML files
- Persistent queue system with state management
- LLM integration for dynamic question answering (OpenRouter/Google)
- Structured event logging with JSON output modes

## Commands

### Virtual Environment

This project uses a virtual environment located at `.venv/` (gitignored). The venv uses **Python 3.13.7**.

**Activate the venv:**
```bash
# Windows
.venv\Scripts\activate

# Unix/macOS
source .venv/bin/activate
```

**After activation, install dependencies:**
```bash
pip install -e .
```

**Important**: Always activate the venv before running tests or CLI commands to ensure Python 3.11+ compatibility (required by browser-use).

### Development
```bash
# Install (editable mode)
pip install -e .

# Lint
ruff check .

# Test
pytest                    # All tests
pytest tests/contract     # Contract tests only
pytest tests/integration  # Integration tests
pytest tests/unit         # Unit tests
```

### CLI Usage
```bash
# Discover postings
auto-apply discover --profile <id> --window 24h --cap 10

# Apply to queued jobs (supervised mode is default)
auto-apply apply --profile <id> --supervised

# Apply to single specific job (auto-resets status if needed)
auto-apply apply --profile <id> --id <job_id> --review-mode

# Resume a blocked job
auto-apply resume-job <application_id>

# Enable diagnostics for resume upload
auto-apply apply --profile <id> --use-llm-locator --debug-resume-widget --resume-wait-timeout-seconds 30
```

## Architecture

### Core Modules

**orchestrator.py** — CLI entry point and command handlers
- Builds argparse parser with discover/apply/resume-job subcommands
- Lazy-loads browser runtime to avoid import overhead in contract tests
- Streams apply events as JSON or human-readable output
- Entry point: `auto-apply` command maps to `orchestrator:main`

**profile_manager.py** — Profile loading and validation
- Loads TOML profiles from `profiles/` directory (override via `AUTO_APPLY_PROFILES_DIR`)
- Profile dataclass: id, name, resume_path, defaults, keywords, prompts, user_data_dir, preferred_browser, experience
- Validates required fields (id, resume_path) and coerces mappings
- experience field: optional array of work history objects (company, role, dates, highlights, tech_stack, metrics) for structured portfolio representation in LLM prompts

**application_queue.py** — Persistent queue management
- Stores ApplicationItem records in `data/queues/<profile>.json`
- ApplicationItem fields: id (ULID), url, company, title, status, details (JobDetails), artifacts, hash
- Status enum: NEW → IN_PROGRESS → SUBMITTED|FAILED|CAPTCHA_BLOCKED
- Hash-based deduplication per profile (sha256 of url|company|title)
- UTF-8-sig encoding tolerance for BOM handling

**job_discovery.py** — Google search and Lever posting extraction
- Builds Google search URL with `tbs` parameter for time filtering (e.g., `qdr:h24`)
- Parses results for `jobs.lever.co` links; captures source_query and source_rank
- Optional browser-based extraction for JobDetails (title, location, department, work_model, employment_type, excerpt, apply_url)
- JobDetails fields are nullable until extraction completes

**browser_agent/lever.py** — Form automation and submission
- LeverApplyAgent: orchestrates form filling workflow
- LeverBrowserOptions: diagnostics, allowed_domains, stealth settings
- LeverFormPlan: selectors for resume input, contact fields, link fields, dynamic questions, EEO fields, submit button
- Resume upload via CDP `DOM.setFileInputFiles` with fallback detection
- CAPTCHA detection (hCaptcha) transitions status to CAPTCHA_BLOCKED
- Confirmation capture: extracts text and ID from success pages

**llm/** — LLM client and prompt building
- openrouter_client.py: OpenRouter API wrapper with retry/backoff
- prompt_builder.py: Constructs JSON prompts from Profile + JobDetails + AnswerCache
- LLMConfig loaded from settings; supports provider/model overrides via CLI

**config.py** — Environment-based configuration
- Settings dataclass loads from environment variables
- Key settings: dwell_seconds, jitter_seconds, max_tabs, retries, allowed_domains, diagnostics flags, LLM keys
- Artifacts path resolution with profile namespacing

**telemetry.py** — Structured logging
- Uses structlog for JSON event logging
- Timeline binding: log_event() and bind_timeline() for step tracking
- Events: discover.start, apply.start, item.submitted, item.failed, etc.

### Data Flow

1. **Discovery Flow**
   - User runs `auto-apply discover --profile <id>`
   - orchestrator loads profile, calls job_discovery.discover_jobs()
   - Google search → parse Lever links → optional browser extraction → enqueue ApplicationItems
   - Queue stored in `data/queues/<profile>.json`

2. **Apply Flow**
   - User runs `auto-apply apply --profile <id>`
   - orchestrator.iter_apply_events() streams events
   - For each pending item: launch browser → analyze form → fill fields → upload resume → submit
   - On success: mark SUBMITTED with Artifacts (confirmation_text, confirmation_id, paths)
   - On failure: mark FAILED with Reason (code, message)
   - CAPTCHA detected: mark CAPTCHA_BLOCKED for manual intervention

3. **Resume Flow**
   - `auto-apply resume-job <id>` searches all profile queues
   - Sets status to IN_PROGRESS and returns resume payload

### Key Patterns

**Lazy Imports for Browser Runtime**
- orchestrator.py uses `_load_browser_runtime()` to defer browser-use imports
- Allows contract tests to run without loading heavy browser dependencies
- Pattern: `global _BROWSER_RUNTIME; if _BROWSER_RUNTIME is None: from browser_use...`

**Status Transitions**
- ApplicationStatus enum enforces valid transitions
- NEW → IN_PROGRESS: when apply starts
- IN_PROGRESS → SUBMITTED: on successful submit
- IN_PROGRESS → FAILED: on error
- IN_PROGRESS → CAPTCHA_BLOCKED: when CAPTCHA detected
- CAPTCHA_BLOCKED → IN_PROGRESS: when resumed

**Hash-Based Deduplication**
- ApplicationItem.hash = sha256(url|company|title)
- ApplicationQueue.enqueue() skips items with existing hashes

**Artifacts Capture**
- Artifacts dataclass: dom_snapshot_path, screenshot_path, video_path, har_path, confirmation_text, confirmation_id
- Stored per profile: `data/artifacts/<profile>/`
- Enable via `AUTO_APPLY_DIAGNOSTICS=1` or specific flags

**CLI Contract Compliance**
- discover: JSON output with items array; exit codes 0/2/1
- apply: JSON event stream (start/item/submitted/failed/end); exit codes 0/3/4/1 (4 when job ID not found)
- resume-job: JSON status payload; exit codes 0/4/6/1
- Schemas in `specs/001-as-a-job/contracts/schemas/`

## Configuration

### Profile TOML Structure
```toml
id = "profile_id"
name = "Full Name"
resume_path = "resumes/resume.pdf"
preferred_browser = "chrome"  # or "chromium", "msedge"
user_data_dir = "path/to/browser/profile"

[defaults]
name = "Full Name"
email = "email@example.com"
phone = "+1-555-010-0000"
location = "City, ST"
portfolio_url = "https://..."
github_url = "https://github.com/..."
linkedin_url = "https://linkedin.com/in/..."

[keywords]
roles = ["Frontend Engineer", "Staff Engineer"]
tech_stack = ["React", "TypeScript", "Next.js"]

[[experience]]
company = "Company Name"
role = "Position Title"
dates = "Start – End"
highlights = [
    "Achievement with metrics",
    "Another achievement with impact"
]
tech_stack = ["React", "TypeScript"]
metrics = {key_metric = "value", another_metric = "value"}

[[experience]]
company = "Another Company"
role = "Previous Role"
dates = "Start – End"
highlights = ["Achievement 1", "Achievement 2"]
tech_stack = ["JavaScript", "HTML/CSS"]
metrics = {metric_1 = "10%", metric_2 = "500k"}

[prompts]
cover_letter = """Select 2-3 most relevant experiences based on job requirements.
If role emphasizes [topic] → highlight [company] [specific metric].
Structure: 1) Job mission, 2) 2-3 achievements with metrics, 3) Enthusiasm."""

resume_summary = """Craft 1-2 sentences from all experiences, don't default to one."""

key_accomplishments = """Vary company sources, include specific metrics."""

experience_selection = """When answering behavioral questions, match question to best company:
- [Topic 1] → [Company] [metric]
- [Topic 2] → [Company] [metric]
Distribute across portfolio."""
```

**Key Notes:**
- `[[experience]]` section provides structured work history. Multiple entries enable LLM to intelligently select relevant examples per job instead of over-relying on a single company
- Each experience should include: company name, role title, dates, 2-3 highlights with metrics, tech stack, and key metrics object
- `[prompts]` contains dynamic AI guidance (not static templates) that instructs the LLM when to use each company's achievements based on job characteristics

### Environment Variables (.env)

**LLM Configuration**
- `LLM_PROVIDER`: openrouter | google
- `LLM_MODEL`: Model identifier for provider
- `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`: API credentials
- `LLM_TEMPERATURE`: Default 0.0 (deterministic)
- `LLM_TIMEOUT_SECONDS`: Default 30

**Diagnostics**
- `AUTO_APPLY_DIAGNOSTICS=1`: Enable all capture
- `AUTO_APPLY_CAPTURE_VIDEO=1`: Record video
- `AUTO_APPLY_CAPTURE_HAR=1`: Record network traffic
- `AUTO_APPLY_ARTIFACTS_DIR`: Default `data/artifacts`

**Resume Upload Tuning**
- `AUTO_APPLY_USE_LLM_LOCATOR=1`: Enable LLM-powered element finding
- `AUTO_APPLY_DEBUG_RESUME_WIDGET=1`: Emit structured snapshot on upload failure
- `AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS`: Default 25

**Stealth Settings**
- `BROWSER_LOCALE`: Default `en-US`
- `BROWSER_TIMEZONE`: Default `America/Los_Angeles`
- `BROWSER_VIEWPORT_WIDTH`, `BROWSER_VIEWPORT_HEIGHT`: Default 1280x800
- `AUTO_APPLY_DISABLE_DEFAULT_EXTENSIONS=1`: Clean browser launch

**Networking**
- `ALLOWED_DOMAINS`: Comma-separated; default `google.*,jobs.lever.co`
- `PROXY_URL` or `HTTP_PROXY`/`HTTPS_PROXY`
- `USER_AGENT`: Override UA string

**General Behavior**
- `DWELL_SECONDS`: Default 0.8 (delay between actions)
- `JITTER_SECONDS`: Default 0.4 (randomized variance)
- `MAX_TABS`: Default 3
- `RETRIES`: Default 2
- `DISCOVERY_WINDOW_HOURS`: Default 24
- `DISCOVERY_CAP`: Default 10

## Important Conventions

### Testing Strategy
- **Contract tests** (`tests/contract/`): CLI argument parsing, JSON output schema, exit codes
- **Integration tests** (`tests/integration/`): Discovery URL building, Lever selector validation, details extraction with static HTML fixtures
- **Unit tests** (`tests/unit/`): Profile loading, queue operations, LLM client mocking

### Code Style
- **Linting**: Ruff configured in pyproject.toml
- **Line length**: 100 characters
- **Docstrings**: Required per constitution (D202, D203, D213, D413 ignored)
- **Imports**: Sorted by Ruff (I rule)
- **Per-file ignores**: E501 allowed in browser_agent/lever.py, job_discovery.py due to long selector strings

### File Organization
- **Queue files**: `data/queues/<profile>.json` (one per profile)
- **Artifacts**: `data/artifacts/<profile>/` (namespaced per profile)
- **Profiles**: `profiles/*.toml` (one per user identity)
- **Specs**: `specs/001-as-a-job/` (plan, contracts, data model, tasks)
- **Reference docs**: `reference_files/` (patterns, architecture, testing tips)

### Browser Session Management
- **Headful by default**: Enables CAPTCHA solving and visual inspection
- **User data dir**: Persistent browser profiles for session reuse
- **Channel resolution**: `preferred_browser` maps to Playwright channel (chrome/chromium/msedge)
- **Keep alive**: Session persists between form steps
- **Artifacts**: Video/HAR recording controlled by diagnostics flags

### Error Handling
- **Reason object**: Failed items store Reason(code, message)
- **Graceful degradation**: JobDetails fields nullable; normalization best-effort
- **UTF-8 BOM tolerance**: Queue loader uses utf-8-sig encoding
- **Domain enforcement**: ensure_allowed_domain() validates URLs against allow-list

## Specs and Documentation

**Primary specs location**: `specs/001-as-a-job/`
- `plan.md`: Implementation plan with phases and constitution checks
- `tasks.md`: Detailed task breakdown with dependencies (T001-T031, RT001-RT003)
- `data-model.md`: Entity definitions (Profile, ApplicationItem, JobDetails, Artifacts, AnswerCache)
- `spec.md`: Feature requirements (FR-001 through FR-033)
- `contracts/cli-contracts.md`: CLI input/output contracts and exit codes
- `quickstart.md`: End-to-end usage examples

**Reference files**: `reference_files/`
- Browser-use API changes, testing tips, Lever/Google patterns

## Integration Points

### Browser-Use (0.7.x)
- BrowserSession: Playwright wrapper with CDP access
- allowed_domains: Enforces URL allow-list
- Session lifecycle: start() → execute → stop()
- Hooks: Not currently used (could be added for step logging)
- **Documentation**: https://docs.browser-use.com/ (examples: https://docs.browser-use.com/examples/templates/playwright-integration)

### Playwright
- File upload: `DOM.setFileInputFiles` via CDP for resume uploads
- Browser channels: chrome, chromium, msedge
- User data dir: Persistent profiles for cookies/auth

### LLM Providers
- OpenRouter: Via openrouter_client.py (supports multiple models)
- Google: Via direct API (Gemini models)
- Provider selection: CLI overrides (`--llm-provider`, `--llm-model`) or environment

### Queue Storage
- JSON files in `data/queues/` (one per profile)
- In-memory ApplicationQueue manages reads/writes
- Atomic updates per operation (enqueue, mark_submitted, mark_failed, resume)

## Development Workflow

1. **Profile Creation**: Copy example TOML to `profiles/<id>.toml`, fill required fields
2. **Environment Setup**: Copy `.env.example` to `.env`, add API keys
3. **Discovery**: Run `auto-apply discover --profile <id>` to populate queue
4. **Testing Apply**: Run `auto-apply apply --profile <id> --supervised` to fill forms with supervision
5. **Resume Debugging**: Add `--debug-resume-widget --use-llm-locator` if upload fails
6. **Queue Management**: Edit `data/queues/<profile>.json` to reset statuses or remove items

## Common Tasks

### Adding a New Profile
1. Create `profiles/<id>.toml` with required fields
2. Place resume in `resumes/` or absolute path
3. Configure defaults, keywords, and prompts sections
4. Optional: Set user_data_dir and preferred_browser

### Debugging Resume Upload
1. Enable diagnostics: `AUTO_APPLY_USE_LLM_LOCATOR=1 AUTO_APPLY_DEBUG_RESUME_WIDGET=1`
2. Increase timeout: `AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS=30`
3. Check artifacts: `data/artifacts/<profile>/` for snapshots
4. Review logs for `resume_upload.*` events

### Extending Browser Agent
1. Add selectors to LeverFormPlan in `browser_agent/lever.py`
2. Update analyze_form() to extract new field types
3. Implement filling logic in execute_in_browser()
4. Add integration test with static HTML fixture

### Adding LLM Provider
1. Create client module in `llm/` (follow openrouter_client.py pattern)
2. Update LLMConfig in `llm/__init__.py`
3. Wire provider selection in orchestrator.py
4. Add API key to .env.example and config.py
5. Document in README.md environment variables section

## Troubleshooting

**"Unexpected UTF-8 BOM"**
- Fixed: Queue loader uses `utf-8-sig` encoding
- Manual fix: Re-save queue JSON as UTF-8 without BOM

**"Expected elements did not render in time"**
- Check URL landed on correct page (not about:blank)
- Enable resume debugging flags
- Verify allowed_domains includes target site

**CAPTCHA Blocked**
- Status transitions to CAPTCHA_BLOCKED automatically
- Resume with `auto-apply resume-job <id>` after manual solve
- Headful mode allows visual inspection and intervention

**Resume Upload Fails**
- Enable `--use-llm-locator` for LLM-assisted element finding
- Use `--debug-resume-widget` to capture widget structure
- Increase `--resume-wait-timeout-seconds` if site is slow
- Check artifacts for DOM snapshot and screenshot

**Queue Corruption**
- Delete `data/queues/<profile>.json` to reset
- Re-run discover to rebuild queue
- Backup queue files before major operations

## Notes for Claude

- Lazy import pattern in orchestrator.py prevents heavy browser imports during CLI parsing
- Contract tests must run without browser_agent imports (use global runtime loaders)
- ApplicationItem.details can be null until extraction completes
- JobDetails work_model and employment_type are free-form strings with suggested normalization
- Profile resume_path is relative to repo root or absolute
- Queue hash prevents duplicates but allows re-enqueueing if manually removed
- Browser sessions are ephemeral per item (fresh launch each time)
- Artifacts are namespaced per profile in subdirectories
- CLI exit codes follow contract: 0 success, 2 no results, 3 partial failure, 4 not found, 1 fatal error
