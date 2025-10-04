# Job-AI-Auto-Apply-UI Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-01

## Active Technologies
- Python 3.11 + browser-use 0.7.x (CDP-first), Playwright (browsers), httpx, pydantic, structlog (001-as-a-job)

## Project Structure
```
src/
tests/
```

## Commands
- `cd src; pytest`
- `ruff check .`
- CLI summary:
  - `discover --profile <name> [--window <hours>] [--cap <int>] [--json]`
  - `apply --profile <name> [--auto|--supervised] [--json] [--llm-provider <name>] [--llm-model <model>]`
  - Apply diagnostics: `--use-llm-locator` / `--no-use-llm-locator`, `--debug-resume-widget`,
    `--resume-wait-timeout-seconds <int>`
  - `resume-job <id> [--json]`

## Code Style
Python 3.11: Follow standard conventions

## Recent Changes
- 001-as-a-job: Added Python 3.11 + browser-use 0.7.x (CDP-first), Playwright (browsers), httpx, pydantic, structlog
- 001-as-a-job: Apply CLI exposes LLM overrides and resume diagnostics flags; supervised remains default mode.
- 001-as-a-job: Lever agent now emits Step1 deterministic form plans and captures DOM/screenshot artifacts when post-submit
  CAPTCHAs block progress (`captcha.capture.artifacts`).

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
