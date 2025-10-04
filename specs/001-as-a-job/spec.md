# Feature Specification: Lever Auto‑Apply Assistant (Google Sourcing + Lever Forms)

**Feature Branch**: `001-as-a-job`  
**Created**: 2025-10-01  
**Status**: Draft  
**Input**: User description distilled from conversation (see triggering /specify message)

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies  
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## Clarifications

### Session 2025-10-01
- Q: What should be the default operating mode when the assistant runs with no flags? → A: Auto‑fill then pause at final submit.
- Q: What is the default discovery cap per run (max new postings to queue)? → A: 10 max; fewer if available.
- Q: What’s the default scope for reusing LLM-generated answers (Answer Cache)? → A: Per profile for generic fields; long-form/job-specific not reused by default.
- Q: What is the default retention period for artifacts under data/ (logs, DOM snapshots, screenshots)? → A: Keep until manual cleanup.

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a job seeker, I want an assistant that discovers fresh Lever-hosted postings and
auto-fills/auto-submits my applications using a selected profile (resume, defaults,
prompts), so that I save time while keeping control and traceability.

### Acceptance Scenarios
1. Given a selected profile, when I run a discovery + apply session, then the system
   gathers Google results filtered to `site:jobs.lever.co` from the last 24h and
   creates a normalized application queue without duplicates.
2. Given a queue item, when an application form is accessible without portal login,
   then the assistant auto-fills fields from the profile and cached answers and
   attempts submission, capturing confirmation details.
3. Given a posting that enforces SSO, when the assistant detects a login wall, then
   it pauses and marks the item for manual handoff with a resume path to return and
   auto-replay from the saved step.
4. Given configured rate-limit and stealth settings, when running a session, then
   dwell time, action jitter, and tab concurrency adhere to configured bounds and
   the assistant stays within allowed domains for safety.
5. Given a submission attempt, when the posting is closed or the link is dead,
   then the assistant marks the item failed with reason and stores a screenshot and
   DOM snapshot as artifacts.
6. Given an in-progress application, when a CAPTCHA is encountered, then the system
   serializes progress (values, URL, step index), stores DOM/screen snapshots, marks
   `captcha_blocked`, and provides a resume path to continue after manual solve.
7. Given a previously applied or duplicate posting, when it is rediscovered, then
   the system de-dupes by URL/company/title hash and updates status accordingly.
8. Given an interruption (crash or user stop), when I relaunch the assistant, then
   it resumes from the most recent saved step with consistent state.
9. Given observability is enabled, when a step completes, then a step-level record
   with timestamps and optional screenshots is available for auditing.
10. Given discovery or when opening the application form, when job posting details
    are extracted, then normalized JobDetails fields are persisted on the
    ApplicationItem and raw artifacts are saved for auditing.
11. Given prompts are generated for long-form answers or cover letters, when the
    assistant prepares the prompt, then it MUST include JobDetails (title, company,
    location, employment_type, and posting_excerpt) alongside resume context.

### Edge Cases
- CAPTCHAs/bot gates block form interactions. Progress is serialized; status set
  to `captcha_blocked`; operator receives a resume path for manual solve + replay.
- Dead links/closed roles detected by key-element validation cause early abort with
  clear log and screenshot.
- Unsupported/dynamic widgets or upload quirks trigger graceful failure: store field
  values, screenshots, and status with reason; item remains in queue for retry.
- Already-applied or duplicate postings are skipped or marked with the correct
  terminal status and rationale.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST discover postings via Google results filtered to
  `site:jobs.lever.co` limited to last 24h.
- **FR-002**: System MUST normalize discovered links into queue items with fields:
  url, company, title, discovered_at, source, and a stable de-dup hash.
- **FR-003**: System MUST support a selectable profile (resume path, defaults,
  keywords, prompts) used to populate forms.
- **FR-004**: System MUST auto-fill Lever application forms using deterministic
  JSON field mappings and helper selectors for common widgets.
- **FR-004a**: The runtime MUST emit a Step1-compliant form plan containing
  `meta`, `widgets.resume`, `fields[]`, and `submit` entries with selector
  precedence, alternates, and a `requiresLocationGate` flag so that downstream
  automation can reason about location gating and resume upload signals.
- **FR-005**: System MUST capture submission confirmations (text, IDs, or emails)
  and attach them to the queue item.
- **FR-006**: System MUST maintain statuses: `new`, `in_progress`, `captcha_blocked`,
  `submitted`, `failed` (with reason code and message).
- **FR-007**: System MUST persist resumable state (current URL, step index, stored
  values, artifacts) to allow recovery after interruptions.
- **FR-008**: System MUST store structured logs, DOM snapshots, and screenshots
  under `data/` and associate them to queue items.
- **FR-009**: System MUST enforce configurable rate/stealth controls: min dwell,
  action jitter, max parallel tabs, retry/backoff, optional proxy, and UA override.
- **FR-010**: System MUST avoid interactive prompts during unattended runs and
  provide a non-interactive mode toggle.
- **FR-011**: System MUST provide a manual handoff path when SSO is required and
  resume automatically after user completes the step.
- **FR-012**: System MUST validate key elements before fill to detect content drift
  and abort with a clear log when validation fails.
- **FR-012a**: When a post-submit CAPTCHA remains visible, the assistant MUST log
  the blocking state, capture DOM + screenshot artifacts, and return
  `captcha_blocked` for manual follow-up.
- **FR-013**: System MUST de-duplicate new discoveries against existing items by
  hash of URL/company/title and update status appropriately.
- **FR-014**: System MUST produce human-readable logs and optional `--json` outputs
  for automation pipelines.
- **FR-016**: System MUST allow users to review and edit answers before submission
  when operating in supervised mode.
- **FR-017**: System MUST provide clear failure reasons and retry guidance per item.
- **FR-018**: System MUST allow configuration of the discovery time window (default
  24h) and search query tuning (keywords, locations).
- **FR-019**: System MUST expose deterministic exit codes and structured error
  messages for operational troubleshooting.
- **FR-020**: System MUST capture and attach the final application URL and timestamp
  to submitted items.
- **FR-030**: Default mode MUST auto-fill forms and pause at the final submit step
  for one-click user approval. Operators MAY pass `--auto` to submit without
  pausing or `--supervised` to opt-in explicitly. Apply runs MUST honor documented
  toggles for LLM selection (`--llm-provider`, `--llm-model`) and resume upload
  handling (`--use-llm-locator` / `--no-use-llm-locator`,
  `--debug-resume-widget`, `--resume-wait-timeout-seconds`).
- **FR-032**: System MUST cap discovery at a configurable maximum of 10 items per
  run by default; queue size may be smaller when fewer matching postings exist.
- **FR-033**: AnswerCache MUST reuse answers per profile for generic fields (e.g.,
  contact info, eligibility, links). Long-form or job/company-specific answers are
  NOT reused by default and require fresh generation or explicit opt-in.
- **FR-034**: Artifact retention defaults to indefinite (no automatic deletion).
  Users MAY configure `retention_days` to enable automatic pruning.

*Clarifications required:*
- **FR-021**: System MUST source Google results via an in-browser public search
  (no external Search API required), limited to a configurable time window (default
  24h).
- **FR-022**: System MUST enforce default pacing limits unless overridden: minimum
  dwell per page 0.8s with ±0.4s jitter; maximum parallel tabs 3; retries with
  exponential backoff up to 2 attempts per failing step.
- **FR-024**: System MUST allow optional HTTP/HTTPS/SOCKS5 proxy configuration at
  the profile or session level, including host/port and basic auth.
- **FR-025**: System MUST run on a modern Chromium-based desktop browser in visible
  (non-headless) mode by default and support persisted user profiles (optional
  `user_data_dir`) for cookie reuse.
- **FR-026**: System MUST store artifacts (screenshots and DOM snapshots) for
  failures, and MAY store video/HAR traces when diagnostics mode is enabled.
- **FR-027**: System MUST record a step-level timeline (start/end timestamps and
  action summaries) accessible from logs for auditability.
- **FR-028**: System MUST gate navigation to allowed domains during discovery and
  application (e.g., `google.*`, `jobs.lever.co`, company subpaths) to keep runs
  deterministic and safe.
- **FR-029**: System MUST provide a supervised mode that previews generated long-
  form answers for human approval before final submission.

### Key Entities *(include if feature involves data)*
- **Profile**: Selected configuration for applying (resume path, defaults, keywords,
  prompts); may include a `user_data_dir` for cookie reuse and a preferred browser.
- **ApplicationItem**: A discovered posting to process. Fields: id, url, company,
  title, status, discovered_at, last_updated_at, reason, artifacts, hash, and
  optional `details` populated after extraction completes.
- **AnswerCache**: Q/A pairs used to fill forms (question key → prepared answer),
  seeded from resume/job description; reused across retries. Entries carry `type`
  = {generic | long_form}, `scope` default `profile` for generic, and may include
  optional `company_id`/`posting_id` when scoping is narrower.
- **Artifacts**: File references for DOM snapshots, screenshots, optional video/HAR,
  confirmation data, and structured logs associated with an ApplicationItem.
- **Config**: Rate/stealth settings (dwell, jitter, tabs, retry/backoff), allowed
  domains, discovery window, optional proxy, output modes (human/JSON), and
  `discovery_cap` (default 10), plus `retention_days` (0 means keep until manual
  cleanup).

### Non-Functional Requirements
- The assistant SHOULD complete typical Lever applications within 2–5 minutes per
  posting under default pacing and network conditions.
- Logs MUST be human-readable by default and optionally emitted as structured JSON.
- Personally identifiable information in logs MUST be redacted by default.
- Default artifact retention is indefinite; users MAY set a retention window to
  enable automatic pruning.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous  
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [ ] User description parsed
- [ ] Key concepts extracted
- [ ] Ambiguities marked
- [ ] User scenarios defined
- [ ] Requirements generated
- [ ] Entities identified
- [ ] Review checklist passed

---
