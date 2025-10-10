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
- Behavior: reset queue item to in_progress without opening a browser.
- Flags: `--json`

### cleanup-artifacts (NEW)
- Default scope: older than N days (prompt for N).
- Flags: `--profile <id>`, `--older-than <days>`, `--dry-run`, `--json`

## JSON Events (apply/resume flows)
- start: `{ "event": "start", "profile": "<id>" }`
- item: `{ "event": "item", "id": "<item_id>", "status": "in_progress" }`
- saved_for_review: `{ "event": "saved_for_review", "id": "<item_id>", "form_state_path": "...", "screenshot_before_path": "..." }`
- captcha_blocked: `{ "event": "captcha_blocked", "id": "<item_id>", "form_state_path": "...", "screenshot_before_path": "..." }`
- submitted: `{ "event": "submitted", "id": "<item_id>", "confirmation_text": "...", "confirmation_id": "?", "screenshot_after_path": "..." }`
- failed: `{ "event": "failed", "id": "<item_id>", "reason": { "code": "...", "message": "..." } }`
- end: `{ "event": "end", "summary": { "submitted": n, "failed": m } }`

## Exit Codes
- apply: `0` when all succeed; `3` when any fail
- resume-job: `0` on success; `4` when id not found
- replay-job: `0` on success; `4` when id not found
- cleanup-artifacts: `0` on success; `2` when nothing matched; `5` on invalid args

