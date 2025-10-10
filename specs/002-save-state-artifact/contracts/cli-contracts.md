# CLI Contracts: Saved State, Replay, Cleanup

## Commands

### apply (existing)
- Flags (additive):
  - `--review-mode` (save pre artifacts, skip submit)
  - `--audit-after-submit` / `--no-audit-after-submit` (post-full.jpg)

### resume-job <id> (NEW semantics)
- Behavior: open browser, apply saved state, pause by default; `--submit` to send.
- Flags: `--submit`, `--json`

### replay-job <id> (NEW)
- Behavior: reset queue item to `in_progress` without opening a browser.
- Flags: `--json`

### cleanup-artifacts (NEW)
- Flags: `--profile <id>`, `--older-than <days>` (REQUIRED), `--dry-run`, `--json`
- Behavior:
  - Running without `--older-than` returns exit code `5` (invalid args).
  - With `--older-than` and `--dry-run`, prints JSON listing matched files and returns `0`.
  - With `--older-than` (no `--dry-run`), deletes matched files and returns `0`; returns `2` when nothing matched.

## JSON Events (apply/resume flows)
- start: `{ "event": "start", "profile": "<id>" }`
- item: `{ "event": "item", "id": "<item_id>", "status": "in_progress" }`
- saved_for_review: `{ "event": "saved_for_review", "id": "<item_id>", "form_state_path": "...", "screenshot_before_path": "..." }`
- captcha_blocked: `{ "event": "captcha_blocked", "id": "<item_id>", "reason": { "code": "captcha_blocked", "message": "..." }, "form_state_path": "...", "screenshot_before_path": "..." }`
- submitted: `{ "event": "submitted", "id": "<item_id>", "confirmation_text": "...", "confirmation_id": "?", "screenshot_after_path": "..." }`
- failed: `{ "event": "failed", "id": "<item_id>", "reason": { "code": "...", "message": "..." } }`
- end: `{ "event": "end", "summary": { "submitted": n, "failed": m } }`

## Internal Log Events
These structured log events are emitted for telemetry (not part of JSON stream):
- `apply.review_mode.start` - When review-mode begins
- `review_mode.artifacts_captured` - Pre-artifacts saved successfully
- `review_mode.artifacts_failed` - Pre-artifact capture failed
- `captcha.blocking_visible` - hCaptcha detected and blocking
- `captcha.artifacts_captured` - Captcha pre-artifacts saved
- `captcha.artifacts_failed` - Captcha artifact capture failed
- `cleanup.preview` - Dry-run preview (before listing files)
- `cleanup.apply` - Actual deletion (before removing files)
- `cleanup.complete` - Cleanup operation finished

## Exit Codes
- apply: `0` when all succeed; `3` when any fail
- resume-job: `0` on success; `4` when id not found; `6` when saved state is missing/corrupt (`invalid_state`)
- replay-job: `0` on success; `4` when id not found
- cleanup-artifacts: `0` on success; `2` when nothing matched; `5` on invalid args (e.g., missing `--older-than`)

### Error JSON (resume invalid state)
```
{ "id": "01HXYZ...", "status": "invalid_state", "error": "pre.json missing or invalid" }
```
