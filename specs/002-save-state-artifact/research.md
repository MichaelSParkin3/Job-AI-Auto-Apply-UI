# Research: Saved Form State & Audit Artifacts

## Decisions
- Capture pre-submit artifacts for all outcomes (captcha, review, success):
  - pre.json (selectors + values)
  - pre-full.jpg (full-page screenshot before submit)
- Successful submissions:
  - confirmation.json (confirmation text/id + final URL)
  - post-full.jpg captured by default (toggleable)
- Resume semantics:
  - resume-job opens, pre-fills, pauses by default; `--submit` to send
  - replay-job resets item to in_progress without opening a browser
- Retention policy:
  - Manual cleanup only by default; no automatic deletion
  - Default cleanup scope when no flags provided: older than N days (prompt for N)
- Privacy:
  - Unredacted artifacts (local-only storage) in v1
- Scope:
  - Lever forms assumed single-page (v1)

## Rationale
- Pre-submit artifacts enable auditability and reliable resume/replay.
- Post-submit screenshot provides visual confirmation beyond textual confirmation.
- Keeping resume-job as an interactive checkpoint reduces mis-submits; `--submit` provides automation when desired.
- Manual cleanup avoids accidental data loss and fits local-only storage.
- Unredacted storage aligns with local, operator-controlled usage; avoids complexity of masking.

## Alternatives Considered
- Capture on failures only → rejected (operators want to review successful submissions).
- Default redaction → rejected (adds complexity, value marginal for local-only usage).
- Automatic retention expiration → rejected (risk of removing needed audit data).
- Single resume-job behavior (auto-submit) → rejected (less safe by default).

## Open Questions (Deferred)
- Optional export of artifacts bundle (zip) for sharing.
- Configurable JPEG quality and max width.

