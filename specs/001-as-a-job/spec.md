# Feature Specification: Lever Auto-Apply CLI

**Feature Branch**: `001-as-a-job`
**Created**: 2025-10-01
**Status**: Current
**Input**: Runtime behaviour from `auto-apply` CLI, queue persistence, and automated tests

## Execution Flow (main)
```
1. Operator selects a profile and runs an `auto-apply` subcommand.
   → `discover` builds a Google query, parses Lever-hosted results, and enqueues new ApplicationItems.
2. Queue persistence stores ApplicationItems with status/metadata per profile.
   → JSON files under `data/queues/<profile>.json` deduplicate by URL/company/title hash.
3. `apply` streams ApplicationQueue.pending() items through the browser agent.
   → Each item launches a Browser-Use session, fills the Lever form, and records submitted/failed events.
4. `resume-job` lifts an item back to `in_progress` so operators can re-run `apply` from the queue.
5. Structured logs and optional JSON output describe discoveries, apply events, and resume status.
```
Implementation references: [`src/job_ai_auto_apply_ui/orchestrator.py#L77-L366`](../src/job_ai_auto_apply_ui/orchestrator.py#L77-L366), [`src/job_ai_auto_apply_ui/application_queue.py#L1-L460`](../src/job_ai_auto_apply_ui/application_queue.py#L1-L460), [`src/job_ai_auto_apply_ui/job_discovery.py#L277-L520`](../src/job_ai_auto_apply_ui/job_discovery.py#L277-L520).

---

## ⚡ Quick Guidelines
- ✅ Deliver a reliable CLI for job seekers automating Lever applications with supervised defaults.
- ❌ Do not document unsupported flags or behaviours (e.g., no `--discovery-only` toggle).
- 👥 Primary persona: an operator maintaining TOML profiles and running discovery/apply sessions locally.

### Section Requirements
- Cover each CLI command (discover, apply, resume-job) and how they interact with the queue and browser agent.
- Document configuration levers exposed via environment variables and CLI flags.
- Capture success/exit-code contracts validated by automated tests.

### For AI Generation
When extending this feature:
1. Treat CLI contracts and JSON schemas as the source of truth; add tests before expanding outputs.
2. Mark new flags or behaviours in both spec and README alongside parser updates.
3. Keep queue semantics (status transitions, dedupe hash, artifact handling) backward compatible or document migrations.
4. Validate browser automation changes with contract tests that stub `iter_apply_events`.

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a job seeker running the CLI, I want to discover Lever postings and stream supervised apply runs for my chosen profile so that I can submit consistent applications quickly.

- **Preconditions**
  - A TOML profile exists in `profiles/<id>.toml` with resume path, defaults, keywords, and prompts (`Profile.from_mapping`).[`src/job_ai_auto_apply_ui/profile_manager.py#L17-L86`](../src/job_ai_auto_apply_ui/profile_manager.py#L17-L86)
  - Queue storage is writable under `data/queues/<profile>.json`; existing items deserialize with optional JobDetails (`ApplicationQueue.__init__`).[`src/job_ai_auto_apply_ui/application_queue.py#L200-L244`](../src/job_ai_auto_apply_ui/application_queue.py#L200-L244)

- **Happy Path Steps**
  1. Run `auto-apply discover --profile <id> --window 24h --cap 10` to construct a Google search URL, parse Lever hits (browser or HTTP fallback), and enqueue unique ApplicationItems while emitting either human-readable text or JSON depending on `--json` (`cmd_discover`, `discover_jobs`).[`src/job_ai_auto_apply_ui/orchestrator.py#L77-L131`](../src/job_ai_auto_apply_ui/orchestrator.py#L77-L131)[`src/job_ai_auto_apply_ui/job_discovery.py#L277-L520`](../src/job_ai_auto_apply_ui/job_discovery.py#L277-L520)
  2. Run `auto-apply apply --profile <id>` in supervised mode by default (unless `--auto` is passed) to iterate `ApplicationQueue.pending()`, resume items into `in_progress`, drive Browser-Use to execute the Lever form plan, and stream `start`/`item`/`submitted`/`failed`/`end` events (`iter_apply_events`).[`src/job_ai_auto_apply_ui/orchestrator.py#L252-L366`](../src/job_ai_auto_apply_ui/orchestrator.py#L252-L366)
  3. Inspect terminal output or `--json` streams for confirmation text with optional IDs. Submitted items are marked with attached artifacts; failures record reason codes via `ApplicationQueue.mark_submitted/mark_failed`.[`src/job_ai_auto_apply_ui/orchestrator.py#L338-L365`](../src/job_ai_auto_apply_ui/orchestrator.py#L338-L365)[`src/job_ai_auto_apply_ui/application_queue.py#L312-L371`](../src/job_ai_auto_apply_ui/application_queue.py#L312-L371)

- **Inputs**
  - CLI flags: `--profile` (required), `--window`, `--cap`, `--json`, `--auto`, `--supervised`, `--llm-provider`, `--llm-model`, `--use-llm-locator` / `--no-use-llm-locator`, `--debug-resume-widget`, `--resume-wait-timeout-seconds`, `--save-logs`, `--logs-dir` (`build_parser`).[`src/job_ai_auto_apply_ui/orchestrator.py#L520-L565`](../src/job_ai_auto_apply_ui/orchestrator.py#L520-L565)
  - Environment overrides loaded via `Settings` (timing, diagnostics, browser stealth, LLM defaults).[`src/job_ai_auto_apply_ui/config.py#L34-L138`](../src/job_ai_auto_apply_ui/config.py#L34-L138)

- **Outputs**
  - Queue JSON persisted with updated statuses/artifacts per item (`ApplicationQueue._persist`).[`src/job_ai_auto_apply_ui/application_queue.py#L372-L381`](../src/job_ai_auto_apply_ui/application_queue.py#L372-L381)
  - CLI exit codes: `discover` returns `0` when items found or `2` when empty; `apply` returns `0` when no failures else `3`; `resume-job` returns `0` on success or `4` if not found (`cmd_*` handlers, tests).[`src/job_ai_auto_apply_ui/orchestrator.py#L130-L131`](../src/job_ai_auto_apply_ui/orchestrator.py#L130-L131)[`src/job_ai_auto_apply_ui/orchestrator.py#L218-L219`](../src/job_ai_auto_apply_ui/orchestrator.py#L218-L219)[`src/job_ai_auto_apply_ui/orchestrator.py#L223-L249`](../src/job_ai_auto_apply_ui/orchestrator.py#L223-L249)[`tests/contract/test_cli_contracts.py#L48-L132`](../tests/contract/test_cli_contracts.py#L48-L132)
  - JSON event stream adheres to `apply-event.schema.json` when `--json` is set (contract tests stubbing `iter_apply_events`).[`tests/contract/test_cli_contracts.py#L135-L175`](../tests/contract/test_cli_contracts.py#L135-L175)

- **Acceptance Criteria**
  1. Discovery emits schema-compliant payloads and exit code `2` when no new items; queue file is untouched when nothing enqueued.[`src/job_ai_auto_apply_ui/orchestrator.py#L107-L131`](../src/job_ai_auto_apply_ui/orchestrator.py#L107-L131)[`tests/contract/test_cli_contracts.py#L48-L79`](../tests/contract/test_cli_contracts.py#L48-L79)
  2. Apply streams events (human + JSON modes) reflecting queue state transitions and returns `3` if any item fails (`cmd_apply`, `iter_apply_events`, tests).[`src/job_ai_auto_apply_ui/orchestrator.py#L134-L220`](../src/job_ai_auto_apply_ui/orchestrator.py#L134-L220)[`tests/contract/test_cli_contracts.py#L81-L175`](../tests/contract/test_cli_contracts.py#L81-L175)
  3. Resume-job sets the item back to `in_progress` (or reports not found) and emits matching JSON (`resume_job`, `cmd_resume`).[`src/job_ai_auto_apply_ui/orchestrator.py#L509-L548`](../src/job_ai_auto_apply_ui/orchestrator.py#L509-L548)[`tests/contract/test_cli_contracts.py#L110-L132`](../tests/contract/test_cli_contracts.py#L110-L132)

- **Implementation Links**
  - CLI orchestrator and streaming: [`src/job_ai_auto_apply_ui/orchestrator.py`](../src/job_ai_auto_apply_ui/orchestrator.py)
  - Discovery pipeline: [`src/job_ai_auto_apply_ui/job_discovery.py`](../src/job_ai_auto_apply_ui/job_discovery.py)
  - Queue persistence: [`src/job_ai_auto_apply_ui/application_queue.py`](../src/job_ai_auto_apply_ui/application_queue.py)

- **Validation Links**
  - CLI contract smoke tests: [`tests/contract/test_cli_contracts.py`](../tests/contract/test_cli_contracts.py)
  - Discovery unit coverage (query building, browser mode): [`tests/unit/test_job_discovery.py`](../tests/unit/test_job_discovery.py)

### Acceptance Scenarios
1. **Given** a valid profile and empty queue, **when** `auto-apply discover --profile <id> --json` runs with no matching postings, **then** exit code `2` and an empty `items` array are returned while no browser modules load.[`tests/contract/test_cli_contracts.py#L48-L79`](../tests/contract/test_cli_contracts.py#L48-L79)
2. **Given** an ApplicationQueue with pending items, **when** `auto-apply apply --profile <id>` runs without `--json`, **then** human-readable progress and summary print to stdout and exit code `0` is returned if no failures occur.[`src/job_ai_auto_apply_ui/orchestrator.py#L187-L220`](../src/job_ai_auto_apply_ui/orchestrator.py#L187-L220)[`tests/contract/test_cli_contracts.py#L81-L108`](../tests/contract/test_cli_contracts.py#L81-L108)
3. **Given** a queue item identifier, **when** `auto-apply resume-job <id> --json` finds the item, **then** the payload reports `status: "in_progress"` with `resumed_from_step: 0` and exit code `0`.[`src/job_ai_auto_apply_ui/orchestrator.py#L509-L548`](../src/job_ai_auto_apply_ui/orchestrator.py#L509-L548)[`tests/contract/test_cli_contracts.py#L110-L132`](../tests/contract/test_cli_contracts.py#L110-L132)

### Edge Cases
- Duplicate discoveries are skipped via hash checks while preserving original queue entries.[`src/job_ai_auto_apply_ui/application_queue.py#L244-L308`](../src/job_ai_auto_apply_ui/application_queue.py#L244-L308)
- Invalid or non-HTTP Google result links are ignored with logged reasons (`discover_jobs`).[`src/job_ai_auto_apply_ui/job_discovery.py#L314-L345`](../src/job_ai_auto_apply_ui/job_discovery.py#L314-L345)
- `AUTO_APPLY_BROWSER_MODE` set to `off|disabled|http` forces HTTP-only discovery, bypassing Browser-Use dependencies.[`src/job_ai_auto_apply_ui/job_discovery.py#L295-L312`](../src/job_ai_auto_apply_ui/job_discovery.py#L295-L312)[`tests/unit/test_job_discovery.py#L118-L151`](../tests/unit/test_job_discovery.py#L118-L151)
- Resume-job returns exit code `4` with a `not_found` payload when the queue lacks the requested ID.[`src/job_ai_auto_apply_ui/orchestrator.py#L233-L242`](../src/job_ai_auto_apply_ui/orchestrator.py#L233-L242)

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: The CLI MUST expose `discover`, `apply`, and `resume-job` subcommands with the flag set documented above (including logging and LLM overrides).[`src/job_ai_auto_apply_ui/orchestrator.py#L520-L565`](../src/job_ai_auto_apply_ui/orchestrator.py#L520-L565)
- **FR-002**: Discovery MUST construct Google search queries limited to six unique profile terms and map the window to Google `tbs` filters before parsing Lever results.[`src/job_ai_auto_apply_ui/job_discovery.py#L277-L340`](../src/job_ai_auto_apply_ui/job_discovery.py#L277-L340)[`tests/unit/test_job_discovery.py#L34-L79`](../tests/unit/test_job_discovery.py#L34-L79)
- **FR-003**: Discovery MUST enqueue only unique ApplicationItems per profile, persisting queue files and returning schema-compliant payloads.[`src/job_ai_auto_apply_ui/application_queue.py#L244-L308`](../src/job_ai_auto_apply_ui/application_queue.py#L244-L308)[`tests/contract/test_cli_contracts.py#L48-L79`](../tests/contract/test_cli_contracts.py#L48-L79)
- **FR-004**: Apply MUST default to supervised mode, stream structured events (human or JSON), and update queue statuses/artifacts for submitted and failed items.[`src/job_ai_auto_apply_ui/orchestrator.py#L134-L366`](../src/job_ai_auto_apply_ui/orchestrator.py#L134-L366)
- **FR-005**: Apply MUST honour resume upload toggles (`--use-llm-locator`, `--no-use-llm-locator`, `--debug-resume-widget`, `--resume-wait-timeout-seconds`) by mutating environment variables for downstream helpers.[`src/job_ai_auto_apply_ui/orchestrator.py#L148-L157`](../src/job_ai_auto_apply_ui/orchestrator.py#L148-L157)
- **FR-006**: Apply MUST support optional LLM overrides (`--llm-provider`, `--llm-model`) and emit the effective configuration for telemetry.[`src/job_ai_auto_apply_ui/orchestrator.py#L159-L184`](../src/job_ai_auto_apply_ui/orchestrator.py#L159-L184)
- **FR-007**: Apply MUST optionally save structured logs when `--save-logs` is provided, using `--logs-dir` as the target directory.[`src/job_ai_auto_apply_ui/orchestrator.py#L169-L178`](../src/job_ai_auto_apply_ui/orchestrator.py#L169-L178)
- **FR-008**: Resume-job MUST locate items across all queue files, transition them to `in_progress`, and report `not_found` otherwise.[`src/job_ai_auto_apply_ui/orchestrator.py#L509-L548`](../src/job_ai_auto_apply_ui/orchestrator.py#L509-L548)
- **FR-009**: Settings MUST expose dwell/jitter, retries, discovery cap/window, diagnostics toggles, and stealth environment knobs via environment variables.[`src/job_ai_auto_apply_ui/config.py#L34-L138`](../src/job_ai_auto_apply_ui/config.py#L34-L138)
- **FR-010**: Browser-based discovery MUST operate when `AUTO_APPLY_BROWSER_MODE` is `auto`, falling back gracefully when disabled and ensuring sessions are started/stopped.[`src/job_ai_auto_apply_ui/job_discovery.py#L332-L520`](../src/job_ai_auto_apply_ui/job_discovery.py#L332-L520)[`tests/unit/test_job_discovery.py#L118-L151`](../tests/unit/test_job_discovery.py#L118-L151)

### Key Entities *(include if feature involves data)*
- **Profile**: User configuration (id, name, resume, defaults, keywords, prompts, optional browser prefs).[`src/job_ai_auto_apply_ui/profile_manager.py#L17-L86`](../src/job_ai_auto_apply_ui/profile_manager.py#L17-L86)
- **ApplicationItem & ApplicationQueue**: Queue element with status, timestamps, optional JobDetails/artifacts/reason plus hash-based dedupe persisted to JSON per profile.[`src/job_ai_auto_apply_ui/application_queue.py#L27-L381`](../src/job_ai_auto_apply_ui/application_queue.py#L27-L381)
- **JobDetails**: Optional normalized metadata captured during discovery (location, department, posting text, apply URL).[`src/job_ai_auto_apply_ui/application_queue.py#L102-L174`](../src/job_ai_auto_apply_ui/application_queue.py#L102-L174)
- **Artifacts**: Optional DOM/screenshot/video/HAR and confirmation metadata attached after apply runs.[`src/job_ai_auto_apply_ui/application_queue.py#L54-L100`](../src/job_ai_auto_apply_ui/application_queue.py#L54-L100)
- **LeverFormPlan & Browser Options**: Form selectors, dynamic questions, and browser session configuration used by the apply agent.[`src/job_ai_auto_apply_ui/browser_agent/lever.py#L18-L147`](../src/job_ai_auto_apply_ui/browser_agent/lever.py#L18-L147)

### Non-Functional Requirements
- CLI output MUST remain copy/paste friendly and structured logs MUST emit via `structlog` with optional file capture.[`src/job_ai_auto_apply_ui/orchestrator.py#L169-L220`](../src/job_ai_auto_apply_ui/orchestrator.py#L169-L220)
- JSON contracts MUST stay aligned with schemas stored in `specs/001-as-a-job/contracts/schemas/` and validated by contract tests.[`tests/contract/test_cli_contracts.py#L48-L175`](../tests/contract/test_cli_contracts.py#L48-L175)
- Browser sessions MUST apply locale/timezone stealth settings before navigation to reduce detection risk.[`src/job_ai_auto_apply_ui/browser_agent/lever.py#L99-L134`](../src/job_ai_auto_apply_ui/browser_agent/lever.py#L99-L134)

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details leak beyond what users must know
- [x] Focused on user value and operational outcomes
- [x] Written for non-technical stakeholders coordinating CLI usage
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No clarification markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable via exit codes/events
- [x] Scope is clearly bounded around Lever CLI workflows
- [x] Dependencies and assumptions identified (profiles, env vars, browser availability)

---

## Execution Status
*Updated by maintainers during documentation refresh*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities resolved
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---
