# Implementation Plan: Lever Auto‑Apply Assistant (Google Sourcing + Lever Forms)

**Branch**: `001-as-a-job` | **Date**: 2025-10-01 | **Spec**: G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\001-as-a-job\spec.md
**Input**: Feature specification from `/specs/001-as-a-job/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Automate discovery of fresh Lever postings via Google (site:jobs.lever.co, last 24h),
normalize queue items, auto-fill Lever forms using profile-driven data and
LLM-backed answers, and submit with default supervised mode (auto-fill then pause
at final submit). Provide resumable state, artifacts (screenshots/DOM), step timeline,
and rate/stealth controls. Default discovery cap 10.

## Technical Context
**Language/Version**: Python 3.11  
**Primary Dependencies**: browser-use 0.7.x (CDP-first), Playwright (browsers), httpx, pydantic, structlog  
**Storage**: Local `data/` tree; JSON/SQLite for queue and cache  
**Testing**: pytest + pytest-asyncio; browser-use hooks; optional video/HAR in diagnostics  
**Target Platform**: Local desktop (Windows/macOS/Linux) using Chromium headful by default  
**Project Type**: single  
**Performance Goals**: Typical Lever flow completes in 2–5 minutes under default pacing  
**Constraints**: Respect allowed domains and pacing; supervised default; privacy redaction on logs  
**Scale/Scope**: 3–10 new postings per 24h; default cap 10

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Library‑First Architecture: Plan splits modules (profile_manager, job_discovery, application_queue, browser_agent, llm, orchestrator). PASS
- CLI/Text I/O: Expose commands with stdout/stderr and `--json` outputs. PASS
- Test‑First (TDD): Contract/integration tests defined before code. PASS
- Contract & Integration Testing: Contracts for CLI/JSON I/O; integration tests for Lever flows. PASS
- Observability/Versioning/Simplicity: Structured logs, SemVer for contracts, YAGNI. PASS

## Project Structure

### Documentation (this feature)
```
specs/001-as-a-job/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
└── job_ai_auto_apply_ui/
    ├── __init__.py
    ├── application_queue.py
    ├── browser_agent/
    │   ├── __init__.py
    │   └── lever.py
    ├── config.py
    ├── job_discovery.py
    ├── llm/
    │   ├── __init__.py
    │   └── prompt_builder.py
    ├── orchestrator.py
    ├── profile_manager.py
    └── telemetry.py

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Single-project repository with `src/job_ai_auto_apply_ui` as the primary
library package and `tests/` for contract/integration/unit suites; no additional services introduced.

## Core Implementation Outline
Follow these steps in order; each step cites the spec or reference to consult while implementing.

1) Profile management (`src/job_ai_auto_apply_ui/profile_manager.py`)
- Purpose: Load active profile (resume_path, defaults, keywords, prompts, user_data_dir, preferred_browser).
- References: data-model.md → Profile; spec.md → FR-003; quickstart.md step 1.

2) Queue + persistence (`src/job_ai_auto_apply_ui/application_queue.py`)
- Purpose: Create/read/update ApplicationItem; enforce hash de-dup; manage statuses and artifacts; tolerate `details=None` until extraction populates metadata.
- References: data-model.md → ApplicationItem, Artifacts; spec.md → FR-002, FR-006, FR-013.

3) Discovery (`src/job_ai_auto_apply_ui/job_discovery.py`)
- Purpose: Build Google URL with `tbs` time filter; collect Lever links; capture source_query and source_rank.
- References: reference_files/patterns-google-lever.md → Google; spec.md → FR-001, FR-018, FR-032, FR-028.

4) Details extraction (`src/job_ai_auto_apply_ui/job_discovery.py`)
- Purpose: For each posting, fetch and normalize JobDetails (title, location, department, work_model, employment_type, excerpt/text, apply_url) while allowing free-form values when canonical enums are unavailable.
- References: data-model.md → JobDetails; reference_files/patterns-google-lever.md → Posting page selectors; spec.md → new acceptance bullets 10–11.

5) Browser agent for Lever (`src/job_ai_auto_apply_ui/browser_agent/lever.py`)
- Purpose: Headful session; resume upload; contact+links; dynamic cards; submit; hCaptcha detection and persistence on block.
- References: reference_files/patterns-google-lever.md → Form selectors; spec.md → FR-004, FR-011, FR-012, FR-026, FR-027, FR-030.
- Operational notes: browser-user-0.7.X-changes.md → hooks/event bus; browser-use-testing-tips.md → allowed_domains, artifacts.

6) Prompt builder (`src/job_ai_auto_apply_ui/llm/prompt_builder.py`)
- Purpose: Build JSON answers for long-form questions from Profile + JobDetails + posting_excerpt; respect AnswerCache rules.
- References: reference_files/mvp-architecture.md → LLM Orchestration; spec.md → FR-033; data-model.md → AnswerCache.

7) Orchestrator CLI (`src/job_ai_auto_apply_ui/orchestrator.py`)
- Purpose: Wire `discover`, `apply`, `resume-job` to library calls; honor `--json` and exit codes; supervised default.
- References: contracts/cli-contracts.md; spec.md → FR-014, FR-019, FR-030.

8) Observability & artifacts (cross-cutting)
- Purpose: Structured logs; step timeline events; artifact capture on failure; attach confirmations on success.
- References: spec.md → FR-005, FR-026, FR-027; browser-use-testing-tips.md.

## Phase 0: Outline & Research
1. Extract unknowns from Technical Context:
   - Proxy configuration options; supported browsers
   - Deterministic JSON mapping for Lever widgets; answer cache scoping (documented)
   - Diagnostics artifacts (video/HAR) toggle and storage

2. Generate and dispatch research agents (lightweight tasks):
   - Best practices for browser-use 0.7.x hooks and step timelines
   - Playwright file uploads for Lever; safe selectors
   - JSON schema for field mappings and confirmation capture

3. Consolidate findings in `research.md` (decision/rationale/alternatives)

**Output**: research.md with critical unknowns resolved

## Phase 1: Design & Contracts
1. Extract entities to `data-model.md` (Profile, ApplicationItem, AnswerCache, Artifacts, Config).
2. Generate CLI contracts (text I/O + `--json`):
   - `discover --profile <name> [--window 24h] [--cap 10]` → JSON queue items
   - `apply --profile <name> [--auto|--supervised]` → JSON status stream
   - `resume-job <id>` → JSON result
3. Contract tests: one test per command asserting schema and exit codes.
4. Extract test scenarios to `quickstart.md` (E2E steps for a mock Lever page).
5. Update agent file incrementally:
   - Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType codex`

Selectors reference
- Use selectors and URL patterns from `reference_files/patterns-google-lever.md` for Google discovery, Lever details, and form flows.

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent file

## Phase 2: Task Planning Approach
- Generate tasks from design docs: contracts → tests, entities → models, scenarios → integration tests.
- TDD ordering; mark [P] where independent files allow parallelism.
- Estimated 25–30 tasks in tasks.md created by /tasks command (not created here).

## Phase 3+: Future Implementation
- Phase 3: /tasks generates tasks.md
- Phase 4: Implement to make tests pass
- Phase 5: Validate via quickstart and integration suites

## Complexity Tracking
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v1.1.0 - See `.specify/memory/constitution.md`*
