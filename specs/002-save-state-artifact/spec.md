# Feature Specification: Saved Form State & Audit Artifacts for Job Applications

**Feature Branch**: 002-save-state-artifact  
**Created**: 2025-10-09  
**Status**: Planned  
**Input**: User description: "G:Github_ReposJob-AI-Auto-Apply-UIJob-AI-Auto-Apply-UIspecs002-save-state-artifact"

## Execution Flow (main)
`
1. Parse user description from Input
   → Identify need to persist filled application form data and screenshots for later review or resume.
2. Extract key concepts from description
   → Actors: job seeker (operator). Actions: discover, apply, save state, resume with prefill, replay. Data: form state, screenshots, confirmation.
3. For each unclear aspect:
   → Multi‑page forms: out of scope (Lever single‑page). Post‑submit screenshot default: ON by default but can be disabled. Resume behavior: pause for review by default; --submit to send.
4. Fill User Scenarios & Testing section
   → Define captcha‑blocked, review‑mode, success, and replay scenarios with measurable outcomes.
5. Generate Functional Requirements
   → Each requirement testable: commands, statuses, artifacts, toggles.
6. Identify Key Entities (if data involved)
   → Application Item, Artifacts, Form State, Queue.
7. Run Review Checklist
   → No [NEEDS CLARIFICATION] remain for v1 scope.
8. Return: SUCCESS (spec ready for planning)
`

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👤 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something, mark it
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

### Session 2025-10-10
- Q: What is the default retention policy for saved artifacts (pre.json, pre-full.jpg, post-full.jpg, confirmation.json)? → A: Keep until a manual cleanup command is run (no automatic deletion by default).
- Q: What should the cleanup command be named? → A: cleanup-artifacts.
- Q: Should saved artifacts include unredacted content by default? → A: Yes, unredacted by default (local-only storage in v1).
- Q: Default resume-job behavior after prefill? → A: Pause for manual review by default; --submit to send.
## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a job seeker running the CLI, I want the system to save the fully filled application form and a full‑page screenshot before submission, so that I can resume after a captcha or review my entries and submit later.

### Acceptance Scenarios
1. **Given** a filled form and a blocking captcha, **When** the apply run attempts to submit, **Then** the system saves a pre‑submit form state (selectors + values) and a full‑page screenshot, marks the item as captcha‑blocked, and the operator can later use resume-job <id> to reopen the posting with fields prefilled.
2. **Given** the operator runs apply in review mode, **When** the form is filled and validated, **Then** the system saves pre‑submit state and screenshot and skips submission, marking the item as pending review for later resume-job.
3. **Given** a successful submission, **When** the confirmation page is shown, **Then** the system records confirmation details and captures a post‑submit full‑page screenshot by default (toggleable), and artifacts are available per item.
4. **Given** an item needs to be retried from scratch, **When** the operator runs replay-job <id>, **Then** the item is reset to in‑progress without opening the browser or pre‑filling.
5. **Given** artifacts exist for multiple items, **When** the operator invokes the cleanup-artifacts command with a chosen scope, **Then** only targeted artifacts are removed and non‑targeted data (queue files, logs) remain intact.
6. **Given** a saved form state for an item, **When** the operator runs resume-job <id> without --submit, **Then** the browser opens with fields prefilled and the CLI pauses for manual review; with --submit, the form is submitted and confirmation artifacts are captured.
7. **Given** an application id exists but the saved state is missing or corrupted, **When** the operator runs resume-job <id>, **Then** the command exits with code 6 (invalid_state) and emits JSON: `{ "id": "<id>", "status": "invalid_state", "error": "pre.json missing or invalid" }`.

### Edge Cases
- Saved state missing or corrupted → clearly surfaced error and guidance to re‑run apply.
- Form structure changed since capture → prefill best‑effort; operator can edit before submit.
- No confirmation page is present → fall back to confirmation text on the page area or final URL.
- Multi‑page forms → out of scope for v1 (Lever forms assumed single‑page).

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: Provide a review mode that fills the form and saves pre‑submit artifacts, then skips submission.
- **FR-002**: On `captcha_blocked` attempts, save pre‑submit form state and a full‑page screenshot and mark the item appropriately.
- **FR-003**: On every attempt (success or failure), save pre‑submit artifacts (form state + full‑page screenshot) before any submit action.
- **FR-004**: On successful submission, save confirmation details and a post‑submit full‑page screenshot by default; allow disabling via a flag/setting.
- **FR-005**: Introduce `resume-job <id>` to reopen a posting, apply the saved state to prefill fields, and pause for manual review by default; allow `--submit` to proceed.
- **FR-006**: Introduce `replay-job <id>` to reset the queue item to `in_progress` without opening a browser or applying state.
- **FR-007**: Persist artifacts per item under a concrete folder: `data/artifacts/<profile>/<item_id>/` containing `pre.json`, `pre-full.jpg`, `post-full.jpg` (optional), and `confirmation.json` (on submit).
- **FR-008**: Expose operator controls to enable/disable post‑submit screenshot capture (default ON).
- **FR-009**: Update queue item status to include `pending_review` alongside existing states; define valid transitions for resume/replay flows.
- **FR-010**: Provide a `cleanup-artifacts` command that REQUIRES `--older-than <days>`; flags: `--profile <id>`, `--older-than <days>`, `--dry-run`, `--json`. Running without `--older-than` returns exit code 5 (invalid args). No default TTL and no automatic deletion.
- **FR-011**: Saved artifacts are unredacted by default; v1 performs no masking. A one-time stderr warning is shown when capturing artifacts.

### Key Entities *(include if feature involves data)*
- **Application Item**: A single job application attempt, with status and metadata.
- **Artifacts**: Paths to saved files per item (pre.json, screenshots, confirmation data).
- **Form State**: The captured mapping of selectors and values needed to prefill forms later.
- **Queue**: Persistent list of items per profile with statuses and references to artifacts.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain for v1 scope
- [x] Requirements are testable and unambiguous  
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified (single‑page Lever forms)

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked/resolved
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---


