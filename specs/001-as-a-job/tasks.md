# Tasks: Lever Auto‑Apply Assistant (Google Sourcing + Lever Forms)

**Input**: Design documents from `G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\001-as-a-job\`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/ , quickstart.md

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
  - File: `src/profile_manager.py`
  - Load profile file; validate fields; expose dataclass/model
- [X] T011 [P] Implement application_queue storage
  - File: `src/application_queue.py`
  - CRUD ApplicationItem; enforce hash de-dup; status transitions; artifact links
- [X] T012 Implement job_discovery (URL build + fetch results)
  - File: `src/job_discovery.py`
  - Build Google URL with `tbs`; capture source_query/source_rank; enqueue items
- [X] T013 Implement details extraction
  - File: `src/job_discovery.py`
  - Open posting; extract JobDetails; save excerpt/text and apply_url
- [X] T014 Implement browser_agent.lever
  - File: `src/browser_agent/lever.py`
  - Headful session; resume upload; contact/links; dynamic cards; hCaptcha detect/persist; submit
- [X] T015 Implement prompt_builder
  - File: `src/llm/prompt_builder.py`
  - Compose prompts from Profile + JobDetails; emit JSON answers; integrate AnswerCache
- [X] T016 Implement orchestrator wiring
  - File: `src/orchestrator.py`
  - Wire discover/apply/resume-job to modules; honor `--json`; exit codes

## Phase 3.4: Integration
- [ ] T017 Logging & step timeline events
  - Files: cross-cutting (`src/*`)
  - Structured logs; per-step events; attach artifacts on failure
- [ ] T018 Diagnostics toggles (video/HAR) and allowed_domains safety
  - Files: `src/browser_agent/lever.py`
- [ ] T019 Confirmation capture and attach to ApplicationItem.artifacts
  - Files: `src/browser_agent/lever.py`, `src/application_queue.py`

## Phase 3.5: Polish
- [ ] T020 [P] Unit tests for profile_manager and queue
  - Files: `tests/unit/test_profile_manager.py`, `tests/unit/test_queue.py`
- [ ] T021 [P] Update quickstart and docs
  - File: `specs/001-as-a-job/quickstart.md`, `AGENTS.md`
- [ ] T022 [P] Static JSON Schemas for CLI outputs
  - Files: `specs/001-as-a-job/contracts/schemas/*.json`
- [ ] T023 Final pass: docstrings per constitution + run linters

## Phase 3.6: LLM Wiring
- [ ] T024 LLM config and env keys
  - Files: `.env.example`, `src/config.py`, `src/llm/__init__.py`
  - Add env vars: `LLM_PROVIDER` (openrouter|google), `LLM_MODEL`, `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`,
    `LLM_TEMPERATURE` (default 0.0 for tests), `LLM_TIMEOUT_SECONDS` (default 30)
- [ ] T025 OpenRouter client wrapper
  - File: `src/llm/openrouter_client.py`
  - Implement chat completion call with retries/backoff and error mapping; optional headers
    (Referer/User-Agent) as required by provider guidelines
- [ ] T026 Provider selection + CLI override
  - Files: `src/orchestrator.py`, `src/config.py`, `src/llm/prompt_builder.py`
  - Add `--llm-provider` and `--llm-model` flags; plumb through to prompt builder
- [ ] T027 [P] Tests for LLM wrappers and prompt_builder
  - Files: `tests/unit/test_llm_openrouter.py`, `tests/unit/test_prompt_builder.py`
  - Mock network; assert deterministic outputs and retry/backoff behavior
- [ ] T028 [P] Docs and samples
  - Files: `specs/001-as-a-job/quickstart.md`, `AGENTS.md`, `.env.example`
  - Document key setup, provider choice, and test defaults (temperature=0.0)

## Dependencies
- Setup (T001–T003) before tests and implementation
- Contract & integration tests (T004–T009) before core implementation (T010–T016)
- `application_queue.py` (T011) before orchestrator wiring (T016)
- `job_discovery.py` details extraction (T013) after URL build (T012)
- Browser agent (T014) before confirmation capture (T019)
- LLM wiring: T024 before T025; T025 before T026; T026 before T027; T028 after T026

## Parallel Example
```
# Launch independent contract tests in parallel:
/specs/001-as-a-job> Task: "T004 Contract test discover"
/specs/001-as-a-job> Task: "T005 Contract test apply"
/specs/001-as-a-job> Task: "T006 Contract test resume-job"

# Launch independent integration selector checks:
/specs/001-as-a-job> Task: "T007 Discovery URL build"
/specs/001-as-a-job> Task: "T009 Lever form selectors"

# LLM tests can run in parallel once wrappers are in place:
/specs/001-as-a-job> Task: "T027 Tests for LLM wrappers and prompt_builder"
```
