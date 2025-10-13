# Tasks: Lever Auto‑Apply Assistant (Google Sourcing + Lever Forms)

**Input**: Design documents from `/workspace/Job-AI-Auto-Apply-UI/specs/001-as-a-job/`
**Prerequisites**: `/workspace/Job-AI-Auto-Apply-UI/specs/001-as-a-job/plan.md` (required), `/workspace/Job-AI-Auto-Apply-UI/specs/001-as-a-job/research.md`, `/workspace/Job-AI-Auto-Apply-UI/specs/001-as-a-job/data-model.md`, `/workspace/Job-AI-Auto-Apply-UI/specs/001-as-a-job/contracts/`, `/workspace/Job-AI-Auto-Apply-UI/specs/001-as-a-job/quickstart.md`

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
   → quickstart.md: Extract E2E scenarios → integration tests
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness
```

## Phase 3.1: Setup
- [X] T001 Initialize Python project tooling and deps
  - Create/ensure `pyproject.toml` with: pytest, pytest-asyncio, httpx, pydantic, structlog, browser-use, playwright
  - Run `playwright install chromium`
  - Add basic `.env.example` keys for LLM provider
  - Files: `pyproject.toml`, `.env.example`
- [X] T002 [P] Configure linting and formatting
  - Add Ruff config and Black (or Ruff formatter); enable docstring checks per constitution
  - Files: `pyproject.toml`, `ruff.toml`
- [X] T003 [P] Create `profiles/` and a starter profile file
  - Example TOML/JSON with id, resume_path, defaults, keywords, prompts
  - Files: `profiles/front_end.toml`

## Phase 3.2: Tests First (TDD)
- [X] T004 [P] Contract test: discover (JSON shape, exit codes)
  - File: `tests/contract/test_discover_contract.py`
  - Based on: `contracts/cli-contracts.md`
- [X] T005 [P] Contract test: apply (event stream, exit codes)
  - File: `tests/contract/test_apply_contract.py`
  - Based on: `contracts/cli-contracts.md`
- [X] T006 [P] Contract test: resume-job (JSON shape)
  - File: `tests/contract/test_resume_contract.py`
  - Based on: `contracts/cli-contracts.md`
- [X] T007 [P] Integration test: discovery URL build + time filter
  - File: `tests/integration/test_discovery_build.py`
  - Based on: `reference_files/patterns-google-lever.md` (tbs param)
- [X] T008 [P] Integration test: Lever details extraction to JobDetails
  - File: `tests/integration/test_lever_details_extract.py`
  - Use static HTML fixtures; assert fields populated per `data-model.md`
- [X] T009 [P] Integration test: form fill selectors exist (static fixture)
  - File: `tests/integration/test_lever_form_selectors.py`
  - Based on: `reference_files/patterns-google-lever.md`

## Phase 3.3: Core Implementation
- [X] T010 Implement profile_manager loader
  - File: `src/job_ai_auto_apply_ui/profile_manager.py`
  - Load profile file; validate fields; expose dataclass/model
- [X] T011 [P] Implement application_queue storage
  - File: `src/job_ai_auto_apply_ui/application_queue.py`
  - CRUD ApplicationItem; enforce hash de-dup; status transitions; artifact links
- [X] T012 Implement job_discovery (URL build + fetch results)
  - File: `src/job_ai_auto_apply_ui/job_discovery.py`
  - Build Google URL with `tbs`; capture source_query/source_rank; enqueue items
- [X] T013 Implement details extraction
  - File: `src/job_ai_auto_apply_ui/job_discovery.py`
  - Open posting; extract JobDetails; save excerpt/text and apply_url
- [X] T014 Implement browser_agent.lever
  - File: `src/job_ai_auto_apply_ui/browser_agent/lever.py`
  - Headful session; resume upload; contact/links; dynamic cards; hCaptcha detect/persist; submit
- [X] T015 Implement prompt_builder
  - File: `src/job_ai_auto_apply_ui/llm/prompt_builder.py`
  - Compose prompts from Profile + JobDetails; emit JSON answers; integrate AnswerCache
- [X] T016 Implement orchestrator wiring
  - File: `src/job_ai_auto_apply_ui/orchestrator.py`
  - Wire discover/apply/resume-job to modules; honor `--json`; exit codes

## Phase 3.4: Integration
- [X] T017 Logging & step timeline events
  - Files: cross-cutting (`src/job_ai_auto_apply_ui/*`)
  - Structured logs; per-step events; attach artifacts on failure
- [X] T018 Diagnostics toggles (video/HAR) and allowed_domains safety
  - Files: `src/job_ai_auto_apply_ui/browser_agent/lever.py`
- [X] T019 Confirmation capture and attach to ApplicationItem.artifacts
  - Files: `src/job_ai_auto_apply_ui/browser_agent/lever.py`, `src/job_ai_auto_apply_ui/application_queue.py`

## Phase 3.5: Polish
- [ ] T020 [P] Unit tests for profile_manager and queue
  - Files: `tests/unit/test_profile_manager.py`, `tests/unit/test_queue.py`
- [X] T021 [P] Update quickstart and docs
  - File: `specs/001-as-a-job/quickstart.md`, `AGENTS.md`
- [X] T022 [P] Static JSON Schemas for CLI outputs
  - Files: `specs/001-as-a-job/contracts/schemas/*.json`
- [X] T023 Final pass: docstrings per constitution + run linters

## Phase 3.6: LLM Wiring
- [X] T024 LLM config and env keys
  - Files: `.env.example`, `src/job_ai_auto_apply_ui/config.py`, `src/job_ai_auto_apply_ui/llm/__init__.py`
  - Add env vars: `LLM_PROVIDER` (openrouter|google), `LLM_MODEL`, `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`,
    `LLM_TEMPERATURE` (default 0.0 for tests), `LLM_TIMEOUT_SECONDS` (default 30)
- [X] T025 OpenRouter client wrapper
  - File: `src/job_ai_auto_apply_ui/llm/openrouter_client.py`
  - Implement chat completion call with retries/backoff and error mapping; optional headers
    (Referer/User-Agent) as required by provider guidelines
- [X] T026 Provider selection + CLI override
  - Files: `src/job_ai_auto_apply_ui/orchestrator.py`, `src/job_ai_auto_apply_ui/config.py`, `src/job_ai_auto_apply_ui/llm/prompt_builder.py`
  - Add `--llm-provider` and `--llm-model` flags; plumb through to prompt builder
- [X] T027 [P] Tests for LLM wrappers and prompt_builder
  - Files: `tests/unit/test_llm_openrouter.py`, `tests/unit/test_prompt_builder.py`
  - Mock network; assert deterministic outputs and retry/backoff behavior
- [X] T028 [P] Docs and samples
  - Files: `specs/001-as-a-job/quickstart.md`, `AGENTS.md`, `.env.example`
  - Document key setup, provider choice, and test defaults (temperature=0.0)

## Dependencies
- Setup (T001–T003) before tests and implementation
- Contract & integration tests (T004–T009) before core implementation (T010–T016)
- `application_queue.py` (T011) before orchestrator wiring (T016)
- `job_discovery.py` details extraction (T013) after URL build (T012)
- Browser agent (T014) before confirmation capture (T019)
- LLM wiring: T024 before T025; T025 before T026; T026 before T027; T028 after T026
- Step1 fixture (T032) before new Step1 tests (T033–T037)
- Step1 tests (T033–T037) before deterministic core updates (T038–T042)
- Core Step1 updates (T038–T042) before CAPTCHA/telemetry integration (T043)
- Implementation (T038–T043) before documentation polish (T044–T045)

## Parallel Example
```
# Launch independent contract tests in parallel:
task start T004 --repo /workspace/Job-AI-Auto-Apply-UI
task start T005 --repo /workspace/Job-AI-Auto-Apply-UI
task start T006 --repo /workspace/Job-AI-Auto-Apply-UI

# Launch independent integration selector checks:
task start T007 --repo /workspace/Job-AI-Auto-Apply-UI
task start T009 --repo /workspace/Job-AI-Auto-Apply-UI

# Launch new Step1 deterministic tests together once the fixture exists:
task start T033 --repo /workspace/Job-AI-Auto-Apply-UI
task start T034 --repo /workspace/Job-AI-Auto-Apply-UI
task start T035 --repo /workspace/Job-AI-Auto-Apply-UI
task start T036 --repo /workspace/Job-AI-Auto-Apply-UI
task start T037 --repo /workspace/Job-AI-Auto-Apply-UI

# LLM tests can run in parallel once wrappers are in place:
task start T027 --repo /workspace/Job-AI-Auto-Apply-UI
```
## Reconciliation Tasks
- [X] RT001 Update CLI documentation to match implemented flags
  - Description: Reflect new apply command toggles (`--llm-provider`, `--llm-model`, `--use-llm-locator`/`--no-use-llm-locator`, `--debug-resume-widget`, `--resume-wait-timeout-seconds`) and remove the undocumented `--discovery-only` reference.
  - Acceptance Criteria: spec.md FR-030 describes actual modes; cli-contracts.md lists current flags and exit codes; quickstart.md includes guidance for the new options; contract tests cover parser acceptance for these flags.
  - Files: `specs/001-as-a-job/spec.md`, `specs/001-as-a-job/contracts/cli-contracts.md`, `specs/001-as-a-job/quickstart.md`, `tests/contract/test_apply_contract.py`.
  - Tests First: Extend contract test to assert argparse accepts the documented flags before editing docs.
- [X] RT002 Align JobDetails normalization expectations with current model behavior
  - Description: Update data-model.md (and related spec sections) to note that `ApplicationItem.details` may be null until extraction completes and that work_model/employment_type values are stored as free-form strings with suggested normalization.
  - Acceptance Criteria: data-model.md reflects optional details and string-based enums; spec acceptance/test narratives reference the updated normalization approach; plan references remain valid.
  - Files: `specs/001-as-a-job/data-model.md`, `specs/001-as-a-job/spec.md`, `specs/001-as-a-job/plan.md`.
  - Tests First: Add or update unit test coverage in `tests/unit/test_queue.py` to confirm serialization when details is null before updating docs.
- [X] RT003 Emit confirmation identifiers in apply event stream when available
  - Description: Update orchestrator.iter_apply_events to include `confirmation_id` alongside `confirmation_text` when artifacts supply it so that the runtime matches the documented sample and schema.
  - Acceptance Criteria: `submitted` events contain both confirmation text and id when present; contract test asserts the field; schema remains satisfied.
  - Files: `src/job_ai_auto_apply_ui/orchestrator.py`, `tests/contract/test_apply_contract.py`.
  - Tests First: Enhance the apply contract test to expect the `confirmation_id` field before modifying the implementation.

## Phase 3.7: Stabilization (Tests + Runtime)
- [X] T029 [P] Unblock contract tests by isolating CLI parser from heavy imports
  - Description: Ensure `pytest tests/contract -q` does not import `browser_agent/lever.py`.
  - Actions: Move heavy imports inside command handlers or behind a feature flag (e.g., `AUTO_APPLY_ENABLE_BROWSER=1`); provide safe fallbacks/mocks for `LeverBrowserOptions` in CLI parse-only paths.
  - Files: `src/job_ai_auto_apply_ui/orchestrator.py`, `src/job_ai_auto_apply_ui/job_discovery.py`, `tests/contract/test_apply_contract.py` (adjust to assert no browser import on parse).
  - Acceptance: Running `pytest tests/contract -q` succeeds on a fresh env even if `browser_agent/lever.py` has syntax errors; contract tests continue to validate new flags and event schema.

- [X] T030 [P] Strengthen queue serialization tests for `details=None`
  - Description: Add explicit fixtures and assertions for `ApplicationItem.details is None` and enum/string fields; cover round‑trip JSON and status transitions.
  - Files: `tests/unit/test_queue.py`, `src/job_ai_auto_apply_ui/application_queue.py` (only if parsing adjustments required).
  - Acceptance: `pytest tests/unit/test_queue.py -q` passes; failure messages clearly indicate schema mismatches.

- [X] T031 Fix runtime SyntaxError in `browser_agent/lever.py` and satisfy Ruff
  - Description: Remove stray escaped newlines and incomplete blocks around resume upload re‑check; refactor long lines/import order per Ruff.
  - Files: `src/job_ai_auto_apply_ui/browser_agent/lever.py`.
  - Acceptance: `python -m job_ai_auto_apply_ui.orchestrator --help` imports without error; `auto-apply apply ...` starts; `pytest -q` runs collection phase without SyntaxError; `ruff check .` passes for `browser_agent/lever.py`.

