# Feature Specification: Web UI Dashboard for Job-AI-Auto-Apply

**Feature Branch**: `003-web-ui`
**Created**: 2025-10-28
**Status**: Draft
**Input**: Build a web UI for job management, profile editing, and settings configuration with shadcn-style components using a sidebar layout

---

## Executive Summary

Build a local web application that provides a visual dashboard interface for the Job-AI-Auto-Apply automation tool. The web UI coexists with the existing CLI, allowing users to discover jobs, manage application profiles, monitor application progress with real-time log viewing, and configure environment settings through an intuitive graphical interface. The application runs as a localhost service with a sidebar-based navigation structure.

---

## User Scenarios & Testing

### Primary User Story

**Job Discovery and Application Management**

Sarah, a job seeker using the automation tool, visits the web dashboard (http://localhost:3000). She selects her profile from a dropdown in the sidebar and sees the queue of discovered jobs organized by status (Waiting: 142 items, In Progress, Submitted: 256). She clicks on "Senior Frontend Engineer - Innovative Inc." to view full job details.

The detail page displays comprehensive information: title, company, location (Portugal Remote), work model (remote), employment type (permanent full time), department (Engineering), and the date discovered. She can read the full job posting text by expanding the "Read More" section to understand the role requirements. She can see a pre-submit screenshot artifact showing the form that will be filled, and notes the source search query that found this job. She verifies the direct apply URL and job status before proceeding.

When she clicks "Apply Now," the system launches a supervised browser session and displays real-time logs on the detail page showing form-filling progress. She watches the browser automation complete the application and receives confirmation. The job status updates to "Submitted" with confirmation details.

### Acceptance Scenarios

1. **Given** user is on dashboard home, **When** user selects a profile from sidebar dropdown, **Then** queue displays jobs filtered for that profile with counts by status

2. **Given** job is in queue, **When** user clicks job title from sidebar list, **Then** detail page displays full job information including company, title, location, work type, department, employment type, and current application status

3. **Given** user is on job detail page with extracted job details, **When** user expands the full job posting text, **Then** the complete job description is displayed in an expanded section

4. **Given** user is on job detail page, **When** some job details are unavailable/null (e.g., posting_date, compensation), **Then** those fields are either hidden or displayed as "Not available"

5. **Given** user is on job detail page, **When** job is currently applying (in supervised mode), **Then** real-time application logs are displayed and updated as the browser automation progresses

6. **Given** user is on job detail page, **When** application has completed, **Then** pre-submit screenshot artifact is displayed showing the form that was filled

7. **Given** user is on profile edit page, **When** user modifies profile fields and clicks "Save Changes", **Then** changes persist to the TOML profile file and user sees confirmation message

8. **Given** user is on settings page, **When** user modifies an environment variable and clicks "Save Changes", **Then** the setting is persisted and applied to subsequent operations

9. **Given** job is captcha-blocked, **When** user clicks "Resume Job" button, **Then** the job transitions from blocked status and can be reapplied

10. **Given** user is on job detail page for a submitted job, **When** user clicks "View Artifacts", **Then** screenshots and logs are displayed in a gallery view

11. **Given** user is on dashboard, **When** user clicks "Discover Jobs" button, **Then** discovery configuration modal opens with last-used options pre-populated (search window, job cap, custom query if previously set)

12. **Given** discovery modal is open, **When** user selects search window "7d", sets job cap to 20, and clicks "Discover", **Then** discovery executes with those parameters and displays real-time progress in modal

13. **Given** discovery is in progress, **When** discovery completes, **Then** modal displays results summary (jobs found count) with "Close" or "View Queue" buttons

14. **Given** user is on job detail page for a waiting job, **When** user clicks "Apply Now" button, **Then** single job apply options panel opens showing mode (default: Supervised) and review mode checkbox with "Advanced Options" collapsible section

15. **Given** single job apply panel is open, **When** user expands "Advanced Options" and enables "Debug Resume Widget" with timeout set to 30 seconds, **Then** options are saved for this profile

16. **Given** user clicks "Apply to Waiting Jobs" on dashboard, **When** bulk apply panel opens, **Then** panel shows mode selector and max concurrent input, and Advanced Options only shows batch-relevant settings (not resume diagnostics)

17. **Given** user has previously configured apply options (mode, resume diagnostics), **When** user opens apply panel again, **Then** last-used advanced options are pre-populated

### Edge Cases

- What happens when a user switches profiles while an application is actively running? (The sidebar should show the profile's queue, and the user can view active jobs; previous profile's browser window continues independently)
- How does the system handle large artifact files (screenshots) loading on the detail page? (Progressive loading / lazy loading with placeholders)
- What happens if the TOML profile file becomes corrupted while the UI is open? (Graceful error message with option to reload or revert)
- How are concurrent applications from multiple profiles managed? (Each profile has independent browser session; UI shows aggregated stats across all profiles)

---

## Requirements

### Functional Requirements

#### Dashboard & Navigation

- **FR-001**: System MUST display a persistent sidebar on every page with application logo, profile selector dropdown, and navigation links for main pages
- **FR-002**: Sidebar MUST display job status categories (Jobs Waiting, In Progress, Captcha Blocked, Submitted, Skipped) with count badges showing number of jobs in each status
- **FR-003**: System MUST allow users to switch between different application profiles via dropdown selector in sidebar; queue and profile data must update on switch
- **FR-004**: System MUST persist user's last selected profile in local storage so dashboard reopens with same profile

#### Job Queue & Listing

- **FR-005**: System MUST display all jobs in the active profile's queue organized by status, with clickable titles that navigate to job detail page
- **FR-006**: Job list items MUST show: job title, company name, date discovered, and current status with visual indicator (color or badge)
- **FR-007**: System MUST support filtering jobs by status (All, Waiting, In Progress, Submitted, Skipped, Captcha Blocked)
- **FR-008**: Users MUST be able to search jobs by keyword (title or company name) with real-time filtering of the queue list

#### Job Application Details Page

- **FR-009**: Detail page MUST display comprehensive job information: title, company, date discovered, and profile used for application
- **FR-009A**: Detail page MUST display extracted job details section with all available information from the queue file's `details` object, including: location, work model (remote/hybrid/onsite), employment type, department, posting date, compensation, tech tags, source query, source rank, direct apply URL, job posting excerpt, full job posting text, extraction timestamp, and job status (open/closed)
- **FR-009B**: Detail page MUST gracefully handle missing or null fields by either hiding the field or displaying "Not available" placeholder
- **FR-009C**: Full job posting text MUST be displayed in an expandable/collapsible section or "Read More" expandable format to prevent overwhelming the page with lengthy content
- **FR-010**: Detail page MUST show current application status with clear visual indicator and timestamp of status change
- **FR-011**: System MUST display pre-submit screenshot artifact on detail page if available (showing the form before submission)
- **FR-012**: System MUST display real-time application logs on the detail page when a job is actively being applied (in supervised mode), updating as the browser automation progresses
- **FR-013**: System MUST show confirmation details (confirmation text and ID) on detail page when application is successfully submitted
- **FR-014**: Detail page MUST provide action buttons contextual to job status: "Apply Now" (for waiting jobs), "Resume" (for captcha-blocked), "Reapply" (for failed/submitted), "View Artifacts" (when available)

#### Application Control & Execution

- **FR-015**: Job detail page MUST provide "Apply Now" button for single job application that opens application options panel when clicked
- **FR-015A**: Single job apply panel MUST display quick-start options section: mode selector (dropdown: Supervised/Auto, default Supervised), review mode checkbox (fill form without submitting)
- **FR-015B**: Single job apply panel MUST provide "Advanced Options" collapsible section containing: LLM provider override dropdown, LLM model override text input, resume upload diagnostics toggles (use LLM locator checkbox, debug resume widget checkbox, resume wait timeout numeric input), audit after submit toggle checkbox, save logs checkbox with logs directory path input
- **FR-015C**: Apply option panel MUST save last-used advanced options per profile and pre-populate those options on next open
- **FR-015D**: Dashboard MUST provide "Apply to Waiting Jobs" bulk action button that opens bulk application options panel
- **FR-015E**: Bulk apply panel MUST display common options section: mode selector (Supervised/Auto), max concurrent applications numeric input (default from MAX_TABS setting), stop on first failure checkbox, review mode checkbox
- **FR-015F**: Bulk apply panel MUST provide "Advanced Options" collapsible section with batch-relevant settings: LLM overrides, save logs toggle; job-specific options (resume diagnostics) MUST NOT appear in bulk mode
- **FR-015G**: Both single and bulk apply panels MUST provide "Apply" action button to launch browser automation and "Cancel" button to close without action
- **FR-015H**: After apply action starts, system MUST close options panel and display real-time progress on detail page (for single job) or dashboard progress widget (for bulk apply)
- **FR-016**: System MUST display active browser window to user during supervised application (browser window is visible, not hidden)
- **FR-017**: Users MUST be able to pause/stop active application by closing the browser window or clicking a "Stop" button
- **FR-018**: System MUST handle and display application errors with user-friendly error messages and failure reasons on the detail page
- **FR-019**: For captcha-blocked jobs, system MUST show "Resume Job" button after user manually solves captcha in the browser

#### Profile Management Page

- **FR-020**: Profile page MUST display editable form for profile configuration: ID, name, resume path (with file browser), preferred browser, user data directory
- **FR-021**: Profile page MUST display editable sections for: Defaults (name, email, phone, location, URLs), Keywords (roles, tech stack), and Experience (company, role, dates, highlights, tech stack, metrics)
- **FR-022**: Profile page MUST support adding/removing experience entries dynamically with "Add Experience" button
- **FR-023**: System MUST validate required fields (ID, name, resume path) before saving and show validation errors inline
- **FR-024**: Profile page MUST provide "Save Changes" and "Cancel" buttons; Save persists changes to TOML profile file
- **FR-025**: System MUST show confirmation message after successful profile save with option to return to dashboard

#### Settings / Configuration Page

- **FR-026**: Settings page MUST display all environment variables organized in collapsible sections: LLM & Provider, Resume Upload, General Behavior, Stealth & Anti-Detection, Diagnostics
- **FR-027**: Each setting MUST display: configuration key name, current value, description, and input field (text, number, checkbox, or dropdown as appropriate)
- **FR-028**: Settings page MUST provide "Save Changes" and "Revert to Default" buttons
- **FR-029**: System MUST persist setting changes to .env file
- **FR-030**: System MUST show which settings have been modified (visual indicator) before save
- **FR-031**: System MUST provide "Reset All to Defaults" button with confirmation dialog
- **FR-032**: Settings page MUST display API key fields as password inputs (masked) with show/hide toggle

#### Job Discovery & Configuration

- **FR-033**: Dashboard MUST provide "Discover Jobs" button that opens a discovery configuration modal dialog
- **FR-033A**: Discovery modal MUST display quick-start section with common options: search window dropdown (1h, 12h, 24h, 7d, 2w, custom input), job cap numeric input (default 10), and profile selector (pre-filled with active profile)
- **FR-033B**: Discovery modal MUST provide "Advanced Options" collapsible section containing: custom search query override text input, browser mode selector
- **FR-033C**: Discovery modal MUST save last-used options per profile and pre-populate those options on next open
- **FR-033D**: Discovery modal MUST provide "Discover" action button to execute discovery with selected options and "Cancel" button to close without action
- **FR-034**: System MUST execute discovery command with user-selected options and display real-time progress indicator (discovering, job count found, status messages) within modal
- **FR-035**: Discovery modal MUST display results summary showing total jobs found, any errors encountered, with "Close" or "View Queue" action buttons
- **FR-036**: After discovery completes successfully, system MUST refresh queue display with newly discovered jobs and update status counts in sidebar

#### Artifacts & Visualization

- **FR-037**: System MUST serve artifact files (screenshots, logs) from the file system and display them appropriately (images in gallery, text logs in viewer)
- **FR-038**: Detail page MUST show "View Artifacts" button/link when artifacts are available for a job
- **FR-039**: Artifact viewer MUST support navigating between multiple artifact types (screenshots, logs)
- **FR-040**: Artifact viewer MUST handle missing or deleted artifact files gracefully with informative message

#### Real-time Status Updates

- **FR-041**: System MUST poll the queue file every 2 seconds to detect status changes from CLI operations and update UI accordingly
- **FR-042**: When active job status changes, system MUST update job list and detail page without requiring manual refresh
- **FR-043**: System MUST display when data was last updated (timestamp) on the dashboard

#### Error Handling & Feedback

- **FR-044**: System MUST display user-friendly error messages for all failures (failed profile save, failed setting update, missing required fields)
- **FR-045**: System MUST provide clear distinction between warnings (e.g., missing artifacts) and errors (failed operations)
- **FR-046**: All forms MUST show inline validation feedback when fields are invalid (color change, error text below field)

#### Responsive Design & Accessibility

- **FR-047**: UI MUST be responsive and usable on desktop screens (1280x720 minimum resolution)
- **FR-048**: All interactive elements MUST be keyboard navigable and have appropriate ARIA labels
- **FR-049**: System MUST use semantic HTML and sufficient color contrast for accessibility

---

## Key Entities

### Profile
Represents a job seeker identity with associated application history and configuration
- **Attributes**: id, name, email, phone, location, resume path, preferred browser, experience history, custom prompts
- **Relationships**: owns ApplicationQueue, has multiple Experience entries

### ApplicationItem (Job in Queue)
Represents a discovered job posting and its application lifecycle
- **Attributes**: id (ULID), url, company, title, status, date discovered, application status, artifacts, failure reason
- **Relationships**: belongs to one Profile, has associated JobDetails, generates Artifacts

### JobDetails
Extracted information from job posting
- **Attributes**: location, work model, employment type, department, compensation, posting text, tech tags, application URL, posting date
- **Relationships**: belongs to one ApplicationItem

### Artifacts
Captured files and data from application process
- **Attributes**: screenshot paths, form state, logs, confirmation text/ID
- **Relationships**: belongs to one ApplicationItem

### RunConfiguration
User-selected options for discover or apply operations, persisted per profile
- **Attributes**: profile_id, operation_type (discover/apply_single/apply_bulk), search_window, job_cap, mode (supervised/auto), review_mode, llm_provider_override, llm_model_override, use_llm_locator, debug_resume_widget, resume_wait_timeout, audit_after_submit, save_logs, logs_dir, max_concurrent, stop_on_failure, custom_query, last_updated
- **Relationships**: belongs to one Profile

### Settings / Environment
Application configuration persisted to .env file
- **Attributes**: LLM provider, API keys, behavior settings, stealth settings, diagnostics flags
- **Relationships**: applies globally to all operations

---

## Success Criteria

### User Experience Metrics

- **UX-001**: Users can navigate from dashboard to job detail page and view full information within 2 clicks
- **UX-002**: Users can create or edit a profile using the web UI in under 5 minutes (vs manual TOML editing)
- **UX-003**: Users can configure all environment settings through web UI without needing to manually edit .env file
- **UX-004**: 95% of form validation errors are caught before save attempt, preventing invalid profile saves
- **UX-005**: Users can execute discover or apply actions with default options in under 3 clicks (click action button → click confirm in modal/panel)
- **UX-006**: Advanced options are accessible but do not clutter the primary workflow for users who don't need them (collapsible sections used)
- **UX-007**: Last-used options persisted per profile reduce repetitive configuration by 80% (users don't need to reset options for repeated actions)

### Functionality Metrics

- **FM-001**: Job queue display refreshes within 3 seconds of CLI job discovery or status change
- **FM-002**: Real-time application logs display updates with latency under 2 seconds during supervised application
- **FM-003**: All artifact types (screenshots, logs) load and display within 5 seconds on detail page
- **FM-004**: Profile and settings save operations complete within 3 seconds with user confirmation
- **FM-005**: All extracted job details (location, work model, employment type, department, etc.) load and display within 2 seconds of navigating to detail page
- **FM-006**: Discovery and apply option modals/panels render and become interactive within 1 second of user triggering action
- **FM-007**: Option changes (toggling checkboxes, changing dropdown selections, text input) respond immediately without lag (< 100ms latency)

### Reliability Metrics

- **RM-001**: UI remains responsive when managing queue with 500+ jobs (pagination or virtual scrolling)
- **RM-002**: Switching profiles completes without errors and displays correct profile's queue
- **RM-003**: Recovery from lost connection to CLI subprocess (display error message and allow retry)

### Accessibility Metrics

- **AM-001**: All pages pass WCAG 2.1 Level AA color contrast requirements
- **AM-002**: All form fields have associated labels and error messages
- **AM-003**: Keyboard navigation works on all pages (Tab, Enter, Escape for modals)

### Adoption Metrics

- **AD-001**: Users prefer web UI over CLI for profile management (qualitative feedback)
- **AD-002**: Supervised mode browser visibility enables users to solve captchas without additional tools
- **AD-003**: Real-time log viewing reduces support questions about application progress

---

## Assumptions

### Deployment & Infrastructure

- Web UI runs on localhost (single-machine desktop application)
- Backend can spawn CLI processes and capture their JSON output
- File system access available to read/write profiles, queue files, and artifacts
- Node.js or equivalent JavaScript runtime available for running the frontend
- No user authentication/login required (single-user local app)

### Browser Automation Integration

- CLI subprocess output (JSON events, exit codes) available to backend via stdout/stderr
- Queue JSON files readable by backend in real-time (file polling)
- TOML profile files editable as text files via backend
- Browser windows launched by CLI remain visible to user (supervised mode default)
- Artifacts currently limited to screenshots and logs (video capture not supported in initial release)
- Artifacts saved to predictable file paths per CLI documentation

### Data & State

- One profile active at a time per browser session
- Queue state sourced from `data/queues/{profile}.json` file
- Profile configuration sourced from `profiles/{id}.toml` file
- Settings sourced from `.env` file in repo root
- Artifacts located in `data/artifacts/{profile}/{job_id}/` directories

### User Workflow

- Users have existing profiles configured as TOML files
- Users have resumed Python environment with `auto-apply` CLI available
- Supervised mode is default (user can see browser window during application)
- Users will manually solve captchas when prompted
- Logs are primarily for visibility/debugging, not critical operational decisions

### Run-Time Options & Configuration

- Users need flexibility to override default CLI behavior per run without editing .env or settings files
- Most users will use default options 80% of the time; advanced options serve power users and troubleshooting
- Last-used options persisted per profile enable rapid repeated operations with same configuration
- Bulk apply operations typically run with simpler option sets than single job diagnostics (no job-specific resume diagnostics in bulk mode)
- Options map directly to CLI flags and arguments; UI layer does not add custom business logic

### Browser Compatibility

- Modern desktop browsers (Chrome, Firefox, Safari, Edge)
- Minimum 1280x720 screen resolution
- JavaScript enabled

---

## Constraints

### Technical Scope

- Web UI is complementary to CLI, not replacement (both coexist)
- No cloud deployment or multi-user features in this release
- No database required (file-based state only)
- Profile editing focused on common fields (not all TOML flexibility initially)
- Option modals/panels designed for desktop interaction (dropdown menus, checkboxes, expandable sections)
- Run-time options map directly to CLI flags (no custom UI-only business logic)

### Performance Targets

- Dashboard loads in under 2 seconds from cache
- Queue file polling every 2 seconds (not real-time sockets)
- Artifact loading lazy/progressive for large files

### Out of Scope

- Multi-user support or authentication
- Cloud deployment or SaaS hosting
- Mobile app or tablet optimization
- Advanced profile templating or duplication
- Job posting content search/indexing

---

## Dependencies & Related Features

### Dependencies

- **001-as-a-job**: Depends on existing CLI, queue structure, and profile format established in initial feature
- **002-save-state-artifact**: Depends on artifact capture and storage patterns for displaying screenshots/logs

### Future Integrations

- Could integrate with advanced profile cloning/templates
- Could add job search result browsing (vs just queue management)
- Could expand to multi-profile comparison or analytics
- Could add scheduled job discovery automation

---

## Review & Acceptance Checklist

### Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities addressed in clarification phase
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---
