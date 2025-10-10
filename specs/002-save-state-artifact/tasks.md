# Tasks: Saved Form State & Audit Artifacts

**Input**: Design documents from 'G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\002-save-state-artifact'
**Prerequisites**: 'G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\002-save-state-artifact\plan.md' (required), 'G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\002-save-state-artifact\research.md', 'G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\002-save-state-artifact\data-model.md', 'G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\002-save-state-artifact\contracts', 'G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\002-save-state-artifact\quickstart.md'

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
   → Integration: logging & artifacts pipeline
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
- [X] T001 Ensure artifacts root and queues directories exist at runtime
  - Code: use Settings.artifacts_path(profile) and Path('data/queues').mkdir(parents=True, exist_ok=True) where needed
  - Files: src/job_ai_auto_apply_ui/config.py, src/job_ai_auto_apply_ui/orchestrator.py
- [X] T002 [P] Add test fixtures for saved state and artifacts
  - Files: tests/fixtures/pre_state_sample.json, tests/fixtures/lever_form.html (reuse), tests/fixtures/lever_posting.html (reuse)

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
- [X] T003 [P] Contract test: CLI saved-state, resume, replay, cleanup
  - File: tests/contract/test_cli_saved_state_contract.py
  - Based on: G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\002-save-state-artifact\contracts\cli-contracts.md
  - Assert: flags (--review-mode, --audit-after-submit/--no-audit-after-submit, resume-job --submit, cleanup-artifacts) parse; JSON events include saved_for_review, captcha_blocked, submitted(confirmation_id, screenshot_after_path); exit codes per spec
- [X] T004 [P] Integration test: review-mode persists pre.json + pre-full.jpg and sets pending_review
  - File: tests/integration/test_review_mode_artifacts.py
  - Arrange: temp artifacts dir; stub BrowserSession/Page to bypass network; simulate LeverFormPlan + values
  - Assert: data/artifacts/<profile>/<item_id> contains pre.json, pre-full.jpg; queue item status == 'pending_review'
- [X] T005 [P] Integration test: resume-job prefill + pause; --submit triggers submit path
  - File: tests/integration/test_resume_job_prefill.py
  - Arrange: existing pre.json; run 'auto-apply resume-job <id>' with and without --submit
  - Assert: without --submit → paused payload; with --submit → submitted event with confirmation fields
- [X] T006 [P] Integration test: captcha-blocked persists pre artifacts and sets captcha_blocked
  - File: tests/integration/test_captcha_blocked_artifacts.py
  - Arrange: simulate captcha detected; ensure pre.json + pre-full.jpg written; queue item status == 'captcha_blocked'
- [X] T007 [P] Integration test: cleanup-artifacts deletes only targeted files
  - File: tests/integration/test_cleanup_artifacts.py
  - Arrange: create artifacts across profiles and dates; run 'auto-apply cleanup-artifacts --profile X --older-than 30 --dry-run' then without --dry-run
  - Assert: JSON reports matched files in dry-run; only eligible paths removed; queues intact

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T008 Extend ApplicationStatus with 'pending_review' and transitions
  - File: src/job_ai_auto_apply_ui/application_queue.py
  - Add: PENDING_REVIEW enum; allow IN_PROGRESS → {SUBMITTED, FAILED, CAPTCHA_BLOCKED, PENDING_REVIEW}; PENDING_REVIEW → {IN_PROGRESS, SUBMITTED, FAILED}
- [ ] T009 Extend Artifacts with saved-state and audit fields
  - File: src/job_ai_auto_apply_ui/application_queue.py
  - Add fields: form_state_path, screenshot_before_path, screenshot_after_path; include in to_dict/from_dict
- [ ] T010 [P] Add SavedState v1 model + read/write helpers
  - File: src/job_ai_auto_apply_ui/saved_state.py (new)
  - Structure: version, captured_at, profile_id, item_id, url, apply_url; plan selectors; values; labels(optional)
  - Helpers: write_pre_state(path, payload), read_pre_state(path) returning dict
- [ ] T011 Implement review-mode flags and behavior in apply path
  - File: src/job_ai_auto_apply_ui/orchestrator.py
  - Parser: add --review-mode and --audit-after-submit/--no-audit-after-submit to 'apply' subcommand
  - Events: when --review-mode, emit saved_for_review with form_state_path + screenshot_before_path and set queue to PENDING_REVIEW
- [ ] T012 Implement resume-job semantics and --submit flag
  - File: src/job_ai_auto_apply_ui/orchestrator.py
  - Parser: add --submit to 'resume-job'
  - Behavior: open browser, apply pre.json, pause by default; when --submit, follow submit flow and capture confirmation
- [ ] T013 Implement replay-job command
  - File: src/job_ai_auto_apply_ui/orchestrator.py
  - Behavior: reset queue item to IN_PROGRESS; do not open browser; JSON output includes id + status
- [ ] T014 Implement cleanup-artifacts command
  - File: src/job_ai_auto_apply_ui/orchestrator.py
  - Flags: --profile <id>, --older-than <days> (REQUIRED), --dry-run, --json; exit codes per contract (0 success, 2 nothing matched, 5 invalid args)
- [ ] T015 Capture pre.json + pre-full.jpg and optional post-full.jpg in browser agent
  - File: src/job_ai_auto_apply_ui/browser_agent/lever.py
  - Add helpers: capture_pre_artifacts(session,page,profile,item,plan,values) → (pre_json_path, pre_screenshot_path); capture_post_screenshot(...) → post_screenshot_path
  - When captcha detected: return Reason('captcha_blocked', ...) after persisting pre artifacts
- [ ] T016 Wire JSON events for saved_for_review, captcha_blocked, submitted(confirmation_id, screenshot_after_path)
  - Files: src/job_ai_auto_apply_ui/orchestrator.py, src/job_ai_auto_apply_ui/browser_agent/lever.py
  - Ensure queue.mark_captcha and queue.mark_submitted attach artifacts with new fields

## Phase 3.4: Integration
- [ ] T017 Structured logging for new flows
  - Files: src/job_ai_auto_apply_ui/telemetry.py, src/job_ai_auto_apply_ui/orchestrator.py
  - Emit: apply.review_mode.start, apply.review_mode.saved, apply.captcha.detected, cleanup.preview, cleanup.apply
- [ ] T018 Ensure Settings.artifacts_root honored everywhere and per-profile namespacing
  - Files: src/job_ai_auto_apply_ui/config.py, src/job_ai_auto_apply_ui/browser_agent/lever.py, src/job_ai_auto_apply_ui/orchestrator.py
  - Use Settings.artifacts_path(profile.id) for all paths under data/artifacts/<profile>/...

## Phase 3.5: Polish
- [ ] T019 [P] Unit tests: queue transitions incl. PENDING_REVIEW and CAPTCHA_BLOCKED
  - File: tests/unit/test_queue_transitions.py
  - Assert: invalid transitions rejected; new transitions accepted; serialization round-trip includes new artifact fields
- [ ] T020 [P] Unit tests: saved_state read/write helpers
  - File: tests/unit/test_saved_state.py
  - Assert: read_pre_state/write_pre_state produce expected JSON shape and tolerate optional labels
- [ ] T021 [P] Update docs per accepted behavior
  - Files: G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\002-save-state-artifact\contracts\cli-contracts.md, G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI\specs\002-save-state-artifact\quickstart.md
  - Reflect: final flags, exit codes, event fields
- [ ] T022 [P] Ruff/format pass and minor refactors
  - Command: ruff check .

## Additional Coverage (appendix)
- [ ] T023 [P] Integration test: success path captures post-full.jpg and confirmation.json
  - File: tests/integration/test_submit_artifacts_success.py
  - Arrange: stub browser agent/session; After submitted event, assert `post-full.jpg` and `confirmation.json` exist under `data/artifacts/<profile>/<item_id>/`
- [ ] T024 [P] Integration test: replay-job resets to IN_PROGRESS without browser
  - File: tests/integration/test_replay_job.py
  - Arrange: existing queue item; run `auto-apply replay-job <id>`; assert status `in_progress`; verify no browser session initiated (stubbed)
- [ ] T025 Contract test: resume-job invalid_state exit code 6 + JSON error
  - File: tests/contract/test_resume_invalid_state.py
  - Arrange: queue contains id but missing/corrupt `pre.json`; assert exit `6` and error JSON payload
- [ ] T026 [P] Documentation updates: naming + cleanup semantics
  - Files: specs/002-save-state-artifact/spec.md, specs/002-save-state-artifact/plan.md, specs/002-save-state-artifact/contracts/cli-contracts.md
  - Ensure identifiers use snake_case in backticks; cleanup requires `--older-than`; no default TTL; add invalid_state in resume-job

## Dependencies
- Tests (T003–T007) before Core (T008–T016)
- Models (T008–T010) before Services/CLI (T011–T016)
- CLI changes (T011–T014) touch the same file → sequential (no [P])
- Browser agent work (T015–T016) can proceed after models; may run parallel to T011–T014
- Integration (T017–T018) after Core; Polish (T019–T022) last

## Parallel Example
```
# Launch independent contract/integration tests in parallel:
task start T003 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI
task start T004 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI
task start T005 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI
task start T006 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI
task start T007 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI

# Once models are ready, work on saved state helpers in parallel:
task start T010 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI
task start T015 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI

# Polish unit tests can run together:
task start T019 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI
task start T020 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI
task start T021 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI
task start T022 --repo G:\Github_Repos\Job-AI-Auto-Apply-UI\Job-AI-Auto-Apply-UI
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing (TDD)
- Use `cd src; pytest -q` to run tests quickly; `ruff check .` for lint
