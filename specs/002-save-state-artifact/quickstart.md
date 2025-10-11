# Quickstart: Saved Form State & Audit Artifacts

## Usage Examples

### 1. Apply in review mode (save state, skip submit)
```bash
auto-apply apply --profile my --review-mode
```
- Fills form and captures `pre.json` + `pre-full.jpg`
- Sets status to `pending_review`
- Does NOT submit the form

### 2. Resume a saved application
```bash
# Prefill + pause (default)
auto-apply resume-job 01HXYZ...

# Auto-submit after prefill
auto-apply resume-job 01HXYZ... --submit
```

### 3. Retry from scratch (no prefill)
```bash
auto-apply replay-job 01HXYZ...
```
- Resets status to `in_progress`
- Does NOT open browser or prefill

### 4. Apply to single specific job
```bash
# Retry single job with full browser workflow (auto-resets status if needed)
auto-apply apply --profile my --id 01HXYZ... --review-mode
```
- Auto-resets status if FAILED/CAPTCHA_BLOCKED/SUBMITTED
- Opens browser and fills form from scratch
- Combines replay-job reset + apply execution
- Works with all apply flags (--review-mode, --supervised, etc.)

### 5. Control screenshots
```bash
# Default: post-full.jpg captured on success
auto-apply apply --profile my

# Disable post-submission screenshot
auto-apply apply --profile my --no-audit-after-submit
```

### 6. Cleanup artifacts
```bash
# Delete artifacts older than 30 days
auto-apply cleanup-artifacts --older-than 30

# Specific profile
auto-apply cleanup-artifacts --profile my --older-than 30

# Dry-run (lists matches without deleting)
auto-apply cleanup-artifacts --older-than 30 --dry-run
```

## Artifact Files

All artifacts are saved to `data/artifacts/<profile>/<item_id>/`:
- `pre.json` - Saved form state (captured in review-mode or when captcha detected)
- `pre-full.jpg` - Screenshot before submission
- `post-full.jpg` - Screenshot after successful submission

## Acceptance Validation
- ✅ Resume-job opens posting, pre-fills fields, and pauses; with `--submit`, submission succeeds
- ✅ Review mode produces `pre.json` + `pre-full.jpg` and sets status to `pending_review`
- ✅ Captcha-blocked runs persist pre artifacts and set status to `captcha_blocked`
- ✅ Cleanup removes only targeted artifacts; queue files remain untouched

## Important Notes
- Artifacts are unredacted and saved locally
- `--older-than` is REQUIRED for cleanup (no default TTL)
- All identifiers use `snake_case` in code and artifacts
