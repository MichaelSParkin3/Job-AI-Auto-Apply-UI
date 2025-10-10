# Quickstart: Saved Form State & Audit Artifacts

1. Apply in review mode (save state, skip submit):
   - `auto-apply apply --profile my --review-mode`
2. Resume a saved application (prefill + pause by default):
   - `auto-apply resume-job 01HXYZ...`
   - Auto-submit after prefill:
     - `auto-apply resume-job 01HXYZ... --submit`
3. Retry from scratch (no prefill):
   - `auto-apply replay-job 01HXYZ...`
4. Control screenshots:
   - Default: post-full.jpg captured on success
   - Disable: `auto-apply apply --no-audit-after-submit`
5. Cleanup artifacts (explicit days required):
   - Delete artifacts older than 30 days:
     - `auto-apply cleanup-artifacts --older-than 30`
   - Specific profile and days:
     - `auto-apply cleanup-artifacts --profile my --older-than 30`
   - Dry-run first (lists matches without deleting):
     - `auto-apply cleanup-artifacts --older-than 30 --dry-run`

Acceptance validation
- Resume-job opens the target posting, pre-fills fields, and pauses; with `--submit`, submission succeeds and confirmation artifacts appear.
- Review mode produces pre.json + pre-full.jpg and sets status to pending_review.
- Captcha-blocked runs persist pre artifacts and set status to captcha_blocked.
- Cleanup removes only targeted artifacts; queue files remain untouched.

Note: Artifacts are unredacted and saved locally. A one-time warning is shown when capturing artifacts.
