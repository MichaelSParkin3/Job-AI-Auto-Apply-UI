# QA Audit Report: Lever Auto-Apply Assistant

## Summary
- Reviewed 27 tasks claimed complete in `specs/001-as-a-job/tasks.md`; 15 remain `[X]` and 12 are now marked `[ERROR]`. 【F:specs/001-as-a-job/tasks.md†L32-L124】
- Global test run fails during collection because the package path is not configured, blocking contract coverage. 【687b86†L1-L33】

## Documents Read (Manifest)
- specs/001-as-a-job/contracts/cli-contracts.md — 1,211 bytes (2025-10-01 22:03:02 UTC) 【a3d91a†L1-L10】
- specs/001-as-a-job/contracts/schemas/apply-event.schema.json — 2,300 bytes (2025-10-01 22:03:02 UTC) 【a3d91a†L1-L10】
- specs/001-as-a-job/contracts/schemas/discover.schema.json — 843 bytes (2025-10-01 22:03:02 UTC) 【a3d91a†L1-L10】
- specs/001-as-a-job/contracts/schemas/resume-job.schema.json — 442 bytes (2025-10-02 02:22:20 UTC) 【a3d91a†L1-L10】
- specs/001-as-a-job/data-model.md — 2,756 bytes (2025-10-01 22:03:02 UTC) 【a3d91a†L1-L10】
- specs/001-as-a-job/plan.md — 10,102 bytes (2025-10-02 02:22:20 UTC) 【a3d91a†L1-L10】
- specs/001-as-a-job/quickstart.md — 833 bytes (2025-10-01 22:03:02 UTC) 【a3d91a†L1-L10】
- specs/001-as-a-job/research.md — 2,051 bytes (2025-10-01 22:03:02 UTC) 【a3d91a†L1-L10】
- specs/001-as-a-job/spec.md — 13,078 bytes (2025-10-02 02:22:20 UTC) 【a3d91a†L1-L10】
- specs/001-as-a-job/tasks.md — 7,570 bytes (2025-10-02 02:27:51 UTC) 【a3d91a†L1-L10】
- Constitution `.specify/memory/constitution.md` — 8,267 bytes (2025-10-01 22:03:02 UTC) 【ba58dd†L1-L2】

## Test Results
- `pytest -q` → **FAILED** (package `job_ai_auto_apply_ui` not importable, six collection errors). 【687b86†L1-L33】
- `PYTHONPATH=src pytest tests/unit/test_job_discovery.py -q` → **PASSED** (4 tests). 【f73a25†L1-L1】
- `PYTHONPATH=src pytest tests/unit/test_browser_agent_lever.py -q` → **PASSED** (1 test). 【618df4†L1-L1】

## Findings
### T002 Configure linting and formatting — [ERROR]
- Requirement: add Ruff configuration and docstring checks. 【F:specs/001-as-a-job/tasks.md†L38-L40】
- Repository lacks any `ruff.toml` and `pyproject.toml` does not define a `[tool.ruff]` section, so lint gates are absent. 【1ed457†L1-L2】【F:pyproject.toml†L1-L21】
- **Recommendation:** add Ruff configuration (either `ruff.toml` or `[tool.ruff]` in `pyproject.toml`) enabling docstring checks, and commit formatter settings.

### T003 Create `profiles/` starter profile — [ERROR]
- Task expects `profiles/front_end.toml`. 【F:specs/001-as-a-job/tasks.md†L41-L43】
- Only `profiles/michael_scott_parkin_iii.toml` exists; the required starter file is missing. 【69d744†L1-L2】
- **Recommendation:** add `profiles/front_end.toml` with the documented fields or update tasks/docs to match the actual profile asset.

### T004 Contract test: discover — [ERROR]
- Contract test is required. 【F:specs/001-as-a-job/tasks.md†L46-L48】
- `pytest -q` cannot import `job_ai_auto_apply_ui` because `tests/conftest.py` adds only the repo root, not `src`, breaking every contract test. 【687b86†L1-L33】【F:tests/conftest.py†L8-L11】
- **Recommendation:** adjust test configuration (e.g., insert `PROJECT_ROOT / "src"` into `sys.path` or add packaging metadata) so contract tests import the package and exercise the CLI.

### T005 Contract test: apply — [ERROR]
- Same import failure blocks the apply contract test from running. 【F:specs/001-as-a-job/tasks.md†L49-L51】【687b86†L1-L33】
- **Recommendation:** fix module import path and rerun the contract suite; ensure streaming events validate against the schema.

### T006 Contract test: resume-job — [ERROR]
- Resume CLI contract test also fails to import the package. 【F:specs/001-as-a-job/tasks.md†L52-L54】【687b86†L1-L33】
- **Recommendation:** resolve packaging path and re-run contract tests to verify schema compliance.

### T007 Integration test: discovery URL — [ERROR]
- Task requires `tests/integration/test_discovery_build.py`. 【F:specs/001-as-a-job/tasks.md†L55-L57】
- `tests/integration/` directory is absent, so the test was never created. 【6a1b58†L1-L2】
- **Recommendation:** add the integration test exercising query construction and time filtering per the spec.

### T008 Integration test: Lever details extraction — [ERROR]
- Task calls for `tests/integration/test_lever_details_extract.py`. 【F:specs/001-as-a-job/tasks.md†L58-L60】
- No integration tests exist, leaving JobDetails extraction unverified. 【6a1b58†L1-L2】
- **Recommendation:** implement the fixture-driven integration test and ensure it passes.

### T009 Integration test: form selectors — [ERROR]
- Form selector integration test is missing. 【F:specs/001-as-a-job/tasks.md†L61-L63】【6a1b58†L1-L2】
- **Recommendation:** add the static form selector test to guard against selector drift.

### T018 Diagnostics toggles & allowed domains — [ERROR]
- Task expects diagnostic toggles (video/HAR) and domain safety handling. 【F:specs/001-as-a-job/tasks.md†L92-L94】
- `browser_agent/lever.py` only analyzes forms; there is no logic for diagnostics toggles or allowed domain enforcement. 【F:src/job_ai_auto_apply_ui/browser_agent/lever.py†L1-L118】
- **Recommendation:** implement configuration-driven toggles for video/HAR capture and enforce allowed domains within the browser agent per the spec.

### T023 Docstring pass + linters — [ERROR]
- Constitution mandates Google-style docstrings on public interfaces. 【F:.specify/memory/constitution.md†L59-L107】
- Functions like `cmd_discover` lack the required `Args`/`Returns` sections, so the documented linting pass never occurred. 【F:src/job_ai_auto_apply_ui/orchestrator.py†L23-L73】
- **Recommendation:** update public docstrings to Google style, re-run linters with docstring checks enabled, and capture the results in tooling output.

### T025 OpenRouter client wrapper — [ERROR]
- Task requires `src/job_ai_auto_apply_ui/llm/openrouter_client.py`. 【F:specs/001-as-a-job/tasks.md†L111-L114】
- The `llm` package contains only `__init__.py` and `prompt_builder.py`; the wrapper module is missing. 【1a7d59†L1-L2】
- **Recommendation:** add the OpenRouter client implementation with retries/backoff and integrate it with config wiring.

### T027 Tests for LLM wrappers & prompt builder — [ERROR]
- Task specifies unit tests `tests/unit/test_llm_openrouter.py` and `tests/unit/test_prompt_builder.py`. 【F:specs/001-as-a-job/tasks.md†L118-L120】
- The `tests/unit` directory holds only browser and discovery tests; LLM tests are absent. 【4fdeb7†L1-L2】
- **Recommendation:** create the missing unit tests, covering cache reuse, prompt assembly, and client retry behaviour.

## Successes Worth Preserving
- Core discovery and browser-agent unit tests pass once `PYTHONPATH` includes `src`, indicating the underlying implementations work when import paths are corrected. 【f73a25†L1-L1】【618df4†L1-L1】
- JSON schemas for CLI outputs are present and referenced by contract tests. 【F:specs/001-as-a-job/contracts/schemas/discover.schema.json†L1-L29】【F:specs/001-as-a-job/contracts/cli-contracts.md†L1-L29】

## Risk Assessment
- Contract coverage is effectively zero until the package path issue is resolved, risking regressions in CLI behaviour. 【687b86†L1-L33】
- Missing integration tests leave Google discovery parsing and Lever selector extraction unguarded against site changes. 【6a1b58†L1-L2】
- LLM integration lacks both client implementation and tests, so any real prompt/answer flow would fail at runtime. 【1a7d59†L1-L2】【4fdeb7†L1-L2】

## Appendix: Interface Observations
- Current pytest bootstrap inserts the repository root but not `src`, preventing `job_ai_auto_apply_ui` from being imported. 【F:tests/conftest.py†L8-L11】
- CLI help/contracts reference `front_end` profile, yet the repository only ships `michael_scott_parkin_iii.toml`; align docs or assets. 【F:tests/contract/test_discover_contract.py†L36-L60】【69d744†L1-L2】
