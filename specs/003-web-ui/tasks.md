# Tasks: Web UI Dashboard for Job-AI-Auto-Apply

**Feature**: 003-web-ui | **Created**: 2025-10-28 | **Status**: Ready for Implementation

**Specification**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Data Model**: [data-model.md](data-model.md) | **API Contracts**: [contracts/api-contracts.md](contracts/api-contracts.md)

---

## Overview

Phase 2 implementation tasks for building the Web UI Dashboard. This document organizes all work into:
- **Phase 1 (Setup)**: Project initialization and configuration
- **Phase 2 (Foundational)**: Blocking prerequisites all features depend on
- **Phase 3-8 (User Stories)**: One phase per major feature in priority order
- **Phase 9 (Polish)**: Cross-cutting concerns and optimizations

**Total Tasks**: 87 tasks across 9 phases | **Parallel Opportunities**: 47 tasks marked [P]

**Recommended MVP Scope**: Complete Phase 1 + Phase 2 + Phase 3 (Dashboard & Profile Switching) for first release (27 tasks)

---

## Dependencies & Execution Strategy

### User Story Completion Order

```
Phase 1: Setup (2 tasks)
    ↓
Phase 2: Foundational (15 tasks - must complete before any user stories)
    ├─→ Phase 3: Dashboard & Profile Switching [US1] (12 tasks)
    ├─→ Phase 4: Job Queue Display [US2] (11 tasks) [can start after Phase 2]
    ├─→ Phase 5: Job Details & Artifacts [US3] (14 tasks) [depends on US2]
    ├─→ Phase 6: Discovery Workflow [US4] (12 tasks) [independent, needs Phase 2]
    ├─→ Phase 7: Application Control [US5] (13 tasks) [depends on US3]
    ├─→ Phase 8: Profile & Settings Management [US6] (10 tasks) [independent, needs Phase 2]
    └─→ Phase 9: Polish & Integration (2 tasks)
```

### Parallel Execution Within Phases

Within each user story phase, the following tasks can run in parallel:
- **Different files**: Frontend and backend components for same feature [P]
- **Different services**: Independent services (e.g., artifact_service, settings_service) [P]
- **Tests**: All unit tests [P]
- **Different pages**: Different UI pages [P]

Within same file: Sequential (no [P] marker)

---

## Phase 1: Setup (2 tasks)

**Objective**: Initialize project structure and development environment

### T001: Create project structure and configuration files [P]

**Story**: Setup | **Files**: `web_ui/backend/`, `web_ui/frontend/`

Create the directory structure and configuration files for both backend and frontend:

**Backend**:
- `web_ui/backend/requirements.txt` - Python dependencies (fastapi, uvicorn, pydantic, python-dotenv)
- `web_ui/backend/.env.example` - Environment template
- `web_ui/backend/src/__init__.py` - Package marker
- `web_ui/backend/src/app.py` - FastAPI app initialization (stub, will be filled in Phase 2)
- `web_ui/backend/src/models/__init__.py`
- `web_ui/backend/src/services/__init__.py`
- `web_ui/backend/src/api/__init__.py`
- `web_ui/backend/src/utils/__init__.py`
- `web_ui/backend/tests/__init__.py`

**Frontend**:
- `web_ui/frontend/package.json` - React 18, TypeScript, Vite, shadcn/ui, axios
- `web_ui/frontend/tsconfig.json` - TypeScript config (strict mode)
- `web_ui/frontend/vite.config.ts` - Vite configuration
- `web_ui/frontend/.eslintrc.json` - ESLint config
- `web_ui/frontend/src/main.tsx` - React entry point
- `web_ui/frontend/src/types/index.ts` - TypeScript interfaces (empty, will fill)
- `web_ui/frontend/src/services/api.ts` - API client stub
- `web_ui/frontend/src/hooks/__init__.ts` - Marker

**Acceptance**: All directories exist, all files created with correct syntax

---

### T002: Initialize Git and commit setup [P]

**Story**: Setup | **Files**: `.gitignore`

- Update `.gitignore` to exclude `node_modules/`, `.venv/`, `__pycache__/`, `.env`, `dist/`, `build/`
- Create initial commit with project structure message

**Acceptance**: `git log` shows setup commit; `git status` is clean

---

## Phase 2: Foundational (15 tasks)

**Objective**: Build core infrastructure that all user stories depend on

**Blocking**: These tasks must complete before any user story implementation begins

**Test-First Discipline**: For all Phase 2 tasks (T003-T017):
1. **Write tests first** (contract/unit/integration)
2. **Then implement** the feature to make tests pass
3. **Verify** all tests pass before task completion
4. **Coverage target**: 95%+ code coverage on backend models and services
5. **Frontend**: Write component tests before implementing component logic

This ensures foundational services are reliable and well-tested before user stories depend on them.

### T003: Implement backend app initialization with CORS [P]

**Story**: Foundational | **Files**: `web_ui/backend/src/app.py`

Create FastAPI application with:
- Uvicorn app initialization
- CORS middleware configured for `http://localhost:5173` (frontend)
- Root health check endpoint `/health` returning `{"status": "ok"}`
- API v1 route group `/api/v1/`
- Global exception handling for 400/404/500 responses
- Structured JSON logging configuration
- Environment loading from `.env`

**Acceptance**:
- `python src/app.py` starts without errors
- `curl http://localhost:5000/health` returns `{"status":"ok"}`
- CORS headers present in responses

---

### T004: Implement backend models - Profile, ApplicationItem, JobDetails, Artifacts, RunConfiguration, Settings [P]

**Story**: Foundational | **Files**: `web_ui/backend/src/models/application.py`, `web_ui/backend/src/models/config.py`

Create Pydantic models matching data-model.md:

**application.py**:
- `ApplicationStatus` enum (NEW, IN_PROGRESS, SUBMITTED, FAILED, CAPTCHA_BLOCKED)
- `JobDetails` model (location, work_model, employment_type, department, compensation, posting_text, tech_tags, apply_url, posting_date, etc.)
- `Artifacts` model (screenshot_path, dom_snapshot_path, video_path, har_path, confirmation_text, confirmation_id, paths, capture_timestamp)
- `FailureReason` model (code, message)
- `ApplicationItem` model (id, url, company, title, status, details, artifacts, reason, date_discovered, date_applied, source_query, source_rank, hash)
- `Profile` model (id, name, email, phone, location, resume_path, preferred_browser, user_data_dir, defaults, keywords, experience, prompts)

**config.py**:
- `RunConfiguration` model (profile_id, operation_type, search_window, job_cap, custom_query, mode, review_mode, llm_provider_override, llm_model_override, use_llm_locator, debug_resume_widget, resume_wait_timeout, audit_after_submit, save_logs, logs_dir, max_concurrent, stop_on_failure, last_updated)
- `Setting` model (key, value, description, category, input_type, default_value, options, min, max, is_secret, required)
- Model validation (required fields, pattern matching, enums)

**Acceptance**:
- All models instantiate correctly with sample data
- Validation errors for invalid data
- JSON serialization works

---

### T005: Implement backend FileOps utility for TOML/JSON/env file I/O [P]

**Story**: Foundational | **Files**: `web_ui/backend/src/utils/file_ops.py`

Create file operations utilities:
- `load_toml(path)` → dict
- `save_toml(path, data)` → None (with atomic write)
- `load_json(path, utf8_sig=True)` → dict/list
- `save_json(path, data)` → None
- `load_env(path)` → dict of env vars
- `save_env(path, updates)` → None (preserves non-updated values)
- `ensure_dir(path)` → None
- Error handling for missing files, permission errors, malformed content

**Acceptance**:
- Can load/save TOML profiles
- Can load/save JSON queue files (handles UTF-8 BOM)
- Can load/save .env files (preserves comments and structure)
- **Atomic Writes**: All `save_*` functions use atomic write pattern:
  - Write to temporary file in same directory
  - Verify write success (fsync)
  - Atomic rename (platform-aware: os.replace for Windows, os.rename for POSIX)
  - On failure, rollback without corrupting original
- **Corruption Prevention Tests**:
  - Test: Simulate write failure during save → original file unchanged
  - Test: Simulate process crash during write → file recoverable from temp
  - Test: Verify atomic rename on all platforms (Windows/Linux/macOS)

---

### T006: Implement backend ProfileService for profile CRUD [P]

**Story**: Foundational | **Files**: `web_ui/backend/src/services/profile_service.py`

Create profile service:
- `list_profiles()` → List[Profile]
- `get_profile(profile_id)` → Profile
- `update_profile(profile_id, data)` → Profile (saves to TOML)
- `get_active_profile()` → Optional[str] (from memory or env)
- `set_active_profile(profile_id)` → None
- Validation of required fields before save
- Error handling for missing profiles

Uses FileOps to read/write profile TOML files from `profiles/` directory

**Acceptance**:
- Can list all profiles from `profiles/` directory
- Can load and edit profile
- Can save profile to TOML file
- Validation works

---

### T007: Implement backend QueueService for queue file I/O and status management [P]

**Story**: Foundational | **Files**: `web_ui/backend/src/services/queue_service.py`

Create queue service:
- `load_queue(profile_id)` → List[ApplicationItem]
- `save_queue(profile_id, items)` → None
- `update_item_status(profile_id, job_id, status)` → ApplicationItem
- `remove_item(profile_id, job_id)` → None
- `enqueue_job(profile_id, item)` → ApplicationItem (with deduplication hash check)
- `get_job(profile_id, job_id)` → ApplicationItem
- `get_status_counts(profile_id)` → dict with counts per status
- Error handling for missing files, invalid status transitions

Uses FileOps to read/write queue JSON files from `data/queues/` directory

**Acceptance**:
- Can load queue for a profile
- Can update job status
- Can add new jobs
- Hash-based deduplication prevents duplicates

---

### T008: Implement backend SettingsService for .env file management [P]

**Story**: Foundational | **Files**: `web_ui/backend/src/services/settings_service.py`

Create settings service:
- `get_all_settings()` → List[Setting] (all available settings with descriptions)
- `get_setting(key)` → Setting
- `update_settings(updates)` → List[str] (updated keys)
- `reset_setting(key)` → None
- `reset_all()` → None
- Settings catalog with descriptions, types, categories, default values, input types
- Mask sensitive values (API keys) in responses
- Validation of setting values (numeric ranges, enum values, etc.)

Uses FileOps to read/write `.env` file

**Acceptance**:
- Can load all settings with descriptions
- Can update settings and write to .env
- Can reset settings to defaults
- Sensitive values masked in API responses

---

### T009: Implement backend ArtifactService for file serving [P]

**Story**: Foundational | **Files**: `web_ui/backend/src/services/artifact_service.py`

Create artifact service:
- `list_artifacts(profile_id, job_id)` → List[dict] with name, type, size_bytes, created_at
- `get_artifact_file(profile_id, job_id, filename)` → bytes (file content)
- `get_artifact_metadata(profile_id, job_id)` → dict with all artifact info
- Validate file paths to prevent directory traversal attacks
- Correct MIME type handling
- Graceful handling of missing files

**Acceptance**:
- Can list artifacts for a job
- Can retrieve artifact files
- MIME types correct for file types
- Security: cannot access files outside artifact directory

---

### T010: Implement backend APIClient for CLI integration [P]

**Story**: Foundational | **Files**: `web_ui/backend/src/services/cli_service.py`

Create CLI integration service:
- `execute_discover(profile_id, search_window, job_cap, custom_query)` → Async generator yielding JSON events
- `execute_apply_single(profile_id, job_id, options)` → Async generator yielding log events
- `execute_apply_bulk(profile_id, options)` → Async generator yielding progress events
- Subprocess execution with timeout handling
- JSON parsing of CLI output
- Error handling for failed CLI calls
- Stream results to caller (generator pattern for real-time updates)

Uses existing `auto-apply` CLI commands

**Acceptance**:
- Can execute discovery command
- Can execute apply command
- Streaming works (logs returned in real-time)
- Errors handled gracefully

---

### T011: Implement backend API routes module with error handling [P]

**Story**: Foundational | **Files**: `web_ui/backend/src/api/routes.py`

Create base API structure:
- Route registration for all v1 endpoint groups
- Dependency injection setup (FastAPI Depends for services)
- Global request/response middleware
- Error response formatting
- Request validation using Pydantic models
- Status code documentation

Stub in all route files (will implement in user story phases):
- `web_ui/backend/src/api/v1/profiles.py`
- `web_ui/backend/src/api/v1/jobs.py`
- `web_ui/backend/src/api/v1/discover.py`
- `web_ui/backend/src/api/v1/apply.py`
- `web_ui/backend/src/api/v1/artifacts.py`
- `web_ui/backend/src/api/v1/settings.py`

**Acceptance**:
- API app starts and routes are registered
- Error responses have correct format
- Pydantic validation works

---

### T012: Initialize frontend React app with TypeScript and Vite [P]

**Story**: Foundational | **Files**: `web_ui/frontend/src/main.tsx`, `web_ui/frontend/src/App.tsx`, `web_ui/frontend/public/index.html`

Create React app:
- `main.tsx`: React root render with React.StrictMode
- `App.tsx`: Root component with router setup (React Router v6)
- `public/index.html`: HTML template
- Basic layout structure (prepare for sidebar)
- Vite dev server configuration
- Hot Module Reloading setup
- Install dependencies: `npm install`

**Acceptance**:
- `npm run dev` starts Vite dev server
- App accessible at `http://localhost:5173`
- React DevTools work
- HMR works (edit App.tsx and see changes instantly)

---

### T013: Create frontend type definitions (TypeScript interfaces) [P]

**Story**: Foundational | **Files**: `web_ui/frontend/src/types/index.ts`, `web_ui/frontend/src/types/api.ts`

Define all TypeScript interfaces matching backend models:

**types/index.ts**:
- `Profile` interface
- `ApplicationItem` interface
- `JobDetails` interface
- `Artifacts` interface
- `ApplicationStatus` type
- `RunConfiguration` interface
- `Setting` interface

**types/api.ts**:
- Request/response interfaces for each API endpoint
- Pagination types
- Error response type
- Success response wrappers

**Acceptance**:
- All types compile without errors
- Types match backend Pydantic models
- `npm run typecheck` passes

---

### T014: Create frontend API client service [P]

**Story**: Foundational | **Files**: `web_ui/frontend/src/services/api.ts`

Implement HTTP client:
- Base fetch wrapper with error handling
- Request/response interceptors
- Automatic JSON encoding/decoding
- Error response parsing
- Retry logic for transient failures (3 retries with backoff)
- Timeout handling
- URL base configuration from environment

Methods for each API endpoint group (stubs that return typed responses):
- Profiles: `listProfiles()`, `getProfile()`, `updateProfile()`, `switchProfile()`
- Jobs: `listJobs()`, `getJob()`, `updateJobStatus()`, `deleteJob()`
- Discovery: `executeDiscover()`, `getDiscoveryStatus()`, `getLastDiscoveryOptions()`
- Apply: `applySingle()`, `applyBulk()`, `getApplyStatus()`, `getApplyLogs()`
- Artifacts: `listArtifacts()`, `getArtifact()`
- Settings: `getSettings()`, `getSetting()`, `updateSettings()`, `resetSetting()`, `resetAllSettings()`

**Acceptance**:
- Can instantiate API client
- Methods have correct signatures
- Error handling works
- Timeout handling works

---

### T015: Create frontend local storage service [P]

**Story**: Foundational | **Files**: `web_ui/frontend/src/services/storage.ts`

Implement browser storage utilities:
- `getUIState(key)` → any
- `setUIState(key, value)` → void
- `getRunOptions(profileId, operationType)` → RunConfiguration
- `setRunOptions(profileId, operationType, options)` → void
- `getActiveProfile()` → string | null
- `setActiveProfile(profileId)` → void
- JSON serialization/deserialization
- Error handling for quota exceeded
- Clear methods for debugging

**Acceptance**:
- Can store/retrieve UI state
- Persists across page refresh
- Handles complex objects (RunConfiguration)

---

### T016: Create frontend hooks for queue polling [P]

**Story**: Foundational | **Files**: `web_ui/frontend/src/hooks/useQueue.ts`

Implement custom hook for queue management:
- `useQueue(profileId)` hook
- State: `items`, `counts`, `isLoading`, `error`, `lastUpdated`
- Poll queue every 2 seconds via API
- Auto-poll while component mounted
- Manual refresh trigger
- Filtering by status
- Filtering by search query
- Error handling
- Clear polling on unmount

**Acceptance**:
- Hook manages queue state
- 2-second polling works
- Component unmount clears polling
- Filtering works

---

### T017: Create frontend hooks for profile management [P]

**Story**: Foundational | **Files**: `web_ui/frontend/src/hooks/useProfile.ts`

Implement custom hook for profile switching:
- `useProfile()` hook
- State: `profiles`, `activeProfile`, `profileData`, `isLoading`, `error`
- Load profiles list on mount
- Switch active profile and update API
- Load profile details
- Cache profile list (update every 30s or on demand)
- Error handling

**Acceptance**:
- Hook manages profile state
- Can switch profiles
- Profile data loads
- Caching works

---

## Phase 3: Dashboard & Profile Switching [US1] (12 tasks)

**User Story 1**: Dashboard home page with profile selection, job status counts, and navigation

**Story Goal**: Users can view dashboard, select a profile, see job queue organized by status, and navigate to other pages

**Independent Test Criteria**:
- Dashboard loads with default profile (or first profile)
- Profile dropdown shows all available profiles
- Switching profiles updates queue and counts
- Status counts match queue items (NEW, IN_PROGRESS, SUBMITTED, FAILED, CAPTCHA_BLOCKED)
- Navigation links to other pages work

### T018: Create backend Profiles API endpoints [P]

**Story**: US1 | **Files**: `web_ui/backend/src/api/v1/profiles.py`

Implement REST endpoints:
- `GET /api/v1/profiles/` - List all profiles with queue counts
- `GET /api/v1/profiles/{id}` - Get profile details
- `PUT /api/v1/profiles/{id}` - Update profile
- `POST /api/v1/profiles/{id}/switch` - Set active profile
- HTTP status codes and error handling
- Request/response validation with Pydantic models

Uses ProfileService and QueueService

**Acceptance**:
- All endpoints return correct JSON
- Status codes correct (200, 404, 400)
- Queue counts accurate

---

### T019: Create Sidebar component with profile dropdown and navigation [P]

**Story**: US1 | **Files**: `web_ui/frontend/src/components/Sidebar.tsx`

Implement UI:
- Logo/branding header
- Profile dropdown (uses useProfile hook)
- Status count badges (uses useQueue hook):
  - Jobs Waiting (NEW count)
  - In Progress (IN_PROGRESS count)
  - Captcha Blocked (CAPTCHA_BLOCKED count)
  - Submitted (SUBMITTED count)
  - Skipped (FAILED count)
- Navigation links:
  - Dashboard
  - Discover Jobs
  - Profiles
  - Settings
  - Artifacts
- Active page indicator
- Responsive on 1280x720+
- Keyboard navigation support (Tab, Enter)
- ARIA labels for accessibility

Uses shadcn/ui components (Select, Badge, Navigation)

**Acceptance**:
- Sidebar renders on all pages
- Profile dropdown works
- Status counts update on queue refresh
- Navigation links work
- Keyboard accessible

---

### T020: Create Dashboard page shell [P]

**Story**: US1 | **Files**: `web_ui/frontend/src/pages/Dashboard.tsx`

Implement page layout:
- Page title "Job Dashboard"
- Action buttons:
  - "Discover Jobs" (opens modal in US4)
  - "Apply to Waiting Jobs" (opens panel in US5)
- Job queue display area (JobQueue component)
- Last updated timestamp
- Responsive layout
- Error handling

**Acceptance**:
- Page renders without errors
- Action buttons visible
- Queue component integrates

---

### T021: Create JobQueue component with filtering and search [P]

**Story**: US1 | **Files**: `web_ui/frontend/src/components/JobQueue.tsx`

Implement job list UI:
- Status filter tabs (All, Waiting, In Progress, Submitted, etc.)
- Search input (filters by title or company)
- Job list with:
  - Clickable job title → navigates to detail page
  - Company name
  - Date discovered
  - Status badge with color
- Pagination or virtual scrolling for 500+ jobs
- Empty state message
- Loading state
- Error state
- Last updated timestamp

Uses useQueue hook for state and filtering

**Acceptance**:
- List renders with sample queue data
- Filtering by status works
- Search works
- Pagination works for large queues
- Clicking job navigates to detail page

---

### T022: Create App router structure with React Router [P]

**Story**: US1 | **Files**: `web_ui/frontend/src/App.tsx`

Set up routing:
- BrowserRouter wrapper
- Routes for main pages:
  - `/` → Dashboard
  - `/job/:jobId` → JobDetail
  - `/profiles` → ProfileEdit
  - `/settings` → Settings
  - `/artifacts` → Artifacts
- Layout wrapper with Sidebar
- 404 page
- Route error boundary

**Acceptance**:
- All routes accessible
- Sidebar present on all pages
- Navigation between pages works

---

### T023: Create TopBar/Header component for page titles [P]

**Story**: US1 | **Files**: `web_ui/frontend/src/components/TopBar.tsx`

Implement page header:
- Current page title
- Last updated timestamp
- Breadcrumb navigation (optional)
- User quick actions (settings icon, etc.)
- Responsive on 1280x720+

**Acceptance**:
- Header renders on all pages
- Page title updates based on route
- Last updated time displays

---

### T024: Implement profile persistence in local storage [P]

**Story**: US1 | **Files**: `web_ui/frontend/src/hooks/useProfile.ts` (enhance)

Enhance useProfile hook:
- Save active profile ID to localStorage on switch
- Restore active profile on app load
- Fall back to first profile if saved one is deleted
- Update storage when switching

**Acceptance**:
- Profile persists across page reload
- Falls back correctly if profile deleted
- Storage reads/writes work

---

### T025: Create loading and error UI components [P]

**Story**: US1 | **Files**: `web_ui/frontend/src/components/LoadingSpinner.tsx`, `web_ui/frontend/src/components/ErrorMessage.tsx`

Implement reusable components:
- LoadingSpinner: animated spinner with optional message
- ErrorMessage: error display with retry button option
- ErrorBoundary: catches React errors
- Network error handling with retry

Uses shadcn/ui components (Alert, Spinner)

**Acceptance**:
- Components render correctly
- Error messages display with context
- Retry triggers handler

---

### T026: Implement API client error handling and retry logic [P]

**Story**: US1 | **Files**: `web_ui/frontend/src/services/api.ts` (enhance)

Enhance API client:
- HTTP error mapping (400, 404, 500)
- User-friendly error messages
- Exponential backoff retry (3 attempts, 1s/2s/4s delays)
- Timeout handling (15s default)
- Network error detection
- Error logging to console

**Acceptance**:
- Failed API calls retry automatically
- User sees error message on permanent failure
- Timeout handling works

---

### T027: Set up ESLint and Prettier for frontend code quality [P]

**Story**: US1 | **Files**: `web_ui/frontend/.eslintrc.json`, `web_ui/frontend/.prettierrc`

Configure tooling:
- ESLint with React/TypeScript plugins
- Prettier for formatting
- Pre-commit hooks (optional)
- CI check for linting

**Acceptance**:
- `npm run lint` works
- `npm run format` works
- No linting errors in existing code

---

### T028: Set up Ruff and Black for backend code quality [P]

**Story**: US1 | **Files**: `web_ui/backend/setup.cfg` or `pyproject.toml`

Configure Python tooling:
- Ruff linter configuration (line length 100)
- Black formatter configuration
- Type checking with mypy
- Pre-commit hooks (optional)

**Acceptance**:
- `ruff check .` works
- `black .` works
- `mypy .` works
- No errors in existing code

---

## Phase 4: Job Queue Display [US2] (11 tasks)

**User Story 2**: Display and filter jobs in queue by status, search, and pagination

**Story Goal**: Users can view all jobs in active profile's queue organized by status with filtering and search

**Independent Test Criteria**:
- Queue displays all jobs from active profile
- Status filtering works (show only jobs with selected status)
- Search works (filter by title or company name)
- Pagination or virtual scrolling handles 500+ jobs
- Job list updates when status changes via API polling
- Sorting by date discovered works

### T029: Create backend Jobs API endpoints [P]

**Story**: US2 | **Files**: `web_ui/backend/src/api/v1/jobs.py`

Implement REST endpoints:
- `GET /api/v1/jobs/?profile=<id>` - List jobs with optional filtering by status/search
- `GET /api/v1/jobs/{job_id}` - Get job detail
- `PUT /api/v1/jobs/{job_id}/status` - Update job status
- `DELETE /api/v1/jobs/{job_id}` - Remove job from queue
- Query parameters: status, search, skip, limit
- Pagination support (default 50, max 500)
- Sorting options
- HTTP status codes

Uses QueueService

**Acceptance**:
- All endpoints work
- Filtering by status works
- Search works
- Pagination works

---

### T030: Implement JobQueue component enhancements with sorting and pagination [P]

**Story**: US2 | **Files**: `web_ui/frontend/src/components/JobQueue.tsx` (enhance)

Enhance component:
- Column sorting (by title, company, date, status)
- Pagination controls (prev, next, page number input)
- Results count display
- Sort direction indicator
- Selected filter/sort persistence in URL params
- Keyboard shortcuts for pagination (arrows)
- Lazy loading of job details on scroll

**Acceptance**:
- Sorting works on all columns
- Pagination navigates correctly
- Filters persist in URL
- Large queues remain responsive

---

### T031: Create unit test for QueueService [P]

**Story**: US2 | **Files**: `web_ui/backend/tests/unit/test_queue_service.py`

Write unit tests:
- Load queue from JSON file
- Parse ApplicationItem correctly
- Status transitions valid
- Deduplication by hash
- Update job status
- Remove job from queue
- Get status counts

Uses pytest fixtures for sample queue data

**Acceptance**:
- All tests pass
- Coverage >= 80%
- Tests are clear and maintainable

---

### T032: Create component test for JobQueue [P]

**Story**: US2 | **Files**: `web_ui/frontend/tests/components/test_JobQueue.tsx`

Write React component tests:
- Renders job list
- Filters by status
- Searches by title/company
- Pagination works
- Clicking job navigates
- Loading state
- Error state

Uses React Testing Library

**Acceptance**:
- All tests pass
- Coverage >= 80%
- Tests follow RTL best practices

---

### T033: Create unit test for Jobs API endpoint [P]

**Story**: US2 | **Files**: `web_ui/backend/tests/contract/test_api_contracts.py`

Write contract tests:
- GET /api/v1/jobs/ returns correct schema
- Filtering by status works
- Search parameter works
- Pagination parameters work
- Status codes correct (200, 404, 400)

Uses pytest and fastapi.testclient

**Acceptance**:
- All tests pass
- Tests validate request/response schema
- Error cases tested

---

### T034: Implement virtual scrolling for large job queues [P]

**Story**: US2 | **Files**: `web_ui/frontend/src/components/JobQueue.tsx` (enhance)

Optimize for performance:
- Virtual scrolling for 500+ jobs (using react-window or similar)
- Only render visible rows
- Smooth scrolling
- Scroll position restoration

**Acceptance**:
- 500-job queue renders smoothly
- Scrolling performance good (60 FPS)
- Accessibility maintained (ARIA live region)

---

### T035: Add keyboard navigation to job list [P]

**Story**: US2 | **Files**: `web_ui/frontend/src/components/JobQueue.tsx` (enhance)

Implement keyboard support:
- Arrow keys navigate jobs
- Enter opens selected job
- Tab through filters
- Escape closes selections
- Screen reader announcements

**Acceptance**:
- All keyboard shortcuts work
- Accessibility tested with screen reader

---

### T036: Implement refresh functionality for queue [P]

**Story**: US2 | **Files**: `web_ui/frontend/src/hooks/useQueue.ts` (enhance)

Add manual refresh:
- Refresh button in UI
- Manual refresh function
- Loading indicator during refresh
- Preserve scroll position
- Deduplicate rapid refreshes

**Acceptance**:
- Manual refresh fetches latest queue
- Loading state shows during fetch
- Queue updates in UI

---

### T037: Create queue data validation utility [P]

**Story**: US2 | **Files**: `web_ui/frontend/src/utils/validation.ts`

Implement validation:
- Validate ApplicationItem data
- Validate status enum
- Validate required fields
- Warn on unexpected fields
- Type guard functions

**Acceptance**:
- Validation catches invalid data
- Type guards work with TypeScript

---

### T038: Implement responsive design for queue on tablet/mobile [P]

**Story**: US2 | **Files**: `web_ui/frontend/src/components/JobQueue.tsx` (enhance)

Make responsive:
- Adjust column visibility on smaller screens
- Stack layout on mobile
- Touch-friendly pagination
- Mobile-optimized search
- Swipe gestures (optional)

Note: Minimum 1280x720, but responsive above that

**Acceptance**:
- Works at 1280x720 (minimum)
- Works at 1920x1080 (standard desktop)
- Works at tablet sizes (768x1024)
- Layout adapts gracefully

---

### T039: Add accessibility features to job queue [P]

**Story**: US2 | **Files**: `web_ui/frontend/src/components/JobQueue.tsx` (enhance)

Enhance accessibility:
- ARIA labels on all interactive elements
- ARIA live region for queue updates
- Role attributes correct
- Color contrast >= AA (WCAG 2.1)
- Semantic HTML (table, thead, tbody, th, tr, td)
- Skip links (optional)

**Acceptance**:
- axe-core audit passes
- Keyboard navigation works
- Screen reader friendly

---

## Phase 5: Job Details & Artifacts [US3] (14 tasks)

**User Story 3**: Display job details page with extracted job information, artifacts, and status

**Story Goal**: Users can click on a job from the queue to view full details, including extracted metadata, artifacts, and current application status

**Independent Test Criteria**:
- Job detail page loads with correct job data
- All extracted job details display (location, work model, employment type, etc.)
- Missing fields handled gracefully ("Not available")
- Full job posting text expandable/collapsible
- Artifacts (screenshots) display in gallery
- Real-time logs display during application
- Application status with timestamp shows
- Confirmation details show when submitted

### T040: Create backend Jobs detail endpoint implementation [P]

**Story**: US3 | **Files**: `web_ui/backend/src/api/v1/jobs.py` (enhance)

Enhance GET /{job_id} endpoint:
- Return complete ApplicationItem with all details
- Include artifacts metadata
- Include extracted JobDetails
- Include failure reason if applicable
- Null field handling for missing details
- Performance optimization (no N+1 queries)

**Acceptance**:
- Endpoint returns full job data
- Performance acceptable (<1s response)
- Null fields handled

---

### T041: Create JobDetail page component [P]

**Story**: US3 | **Files**: `web_ui/frontend/src/pages/JobDetail.tsx`

Implement page:
- Page layout with job header
- Load job data on mount (useEffect)
- Display basic info (title, company, date discovered, profile)
- Current status with visual indicator
- Timeline of status changes (if available)
- Action buttons (apply, resume, reapply, view artifacts)
- Error handling (job not found)
- Back navigation

Uses useQueue hook or separate useJob hook

**Acceptance**:
- Page loads with job data
- All sections render
- Navigation works
- Error states handled

---

### T042: Create JobDetailsSection component for extracted metadata [P]

**Story**: US3 | **Files**: `web_ui/frontend/src/components/JobDetailsSection.tsx`

Implement details display:
- Location field
- Work model (remote/hybrid/onsite)
- Employment type
- Department
- Compensation (salary range, bonus, equity)
- Tech tags (skills)
- Source query and rank
- Posting date
- "Not available" placeholder for missing fields
- Responsive layout

Uses shadcn/ui components (Card, Badge, etc.)

**Acceptance**:
- All fields display correctly
- Missing fields show "Not available"
- Layout responsive
- Readable typography

---

### T043: Create JobPostingSection component with expandable full text [P]

**Story**: US3 | **Files**: `web_ui/frontend/src/components/JobPostingSection.tsx`

Implement expandable posting:
- Job posting excerpt (first 200 chars)
- "Read More" button to expand
- Full job posting text in expandable section
- Collapse/expand animation
- Copy to clipboard button (optional)
- Responsive layout

Uses shadcn/ui Collapsible component

**Acceptance**:
- Excerpt displays initially
- Click "Read More" to expand
- Full text visible when expanded
- Collapse works
- Mobile-friendly

---

### T044: Create ArtifactsGallery component for screenshots and logs [P]

**Story**: US3 | **Files**: `web_ui/frontend/src/components/ArtifactsGallery.tsx`

Implement artifact display:
- List of available artifacts (screenshots, logs, etc.)
- Gallery view for images
- Log file viewer (text display)
- File download links
- "Not available" message if no artifacts
- Image lightbox for full size viewing (optional)
- Lazy loading for large files

**Acceptance**:
- Artifacts list renders
- Can view each artifact
- Download links work
- Missing artifacts handled gracefully

---

### T045: Create LogViewer component for real-time application logs [P]

**Story**: US3 | **Files**: `web_ui/frontend/src/components/LogViewer.tsx`

Implement log display:
- Real-time log display (during application)
- Auto-scroll to bottom
- Timestamp and log level display
- Color-coded log levels (info, warning, error)
- Search/filter logs
- Clear logs button
- Copy logs button
- Responsive width
- Monospace font

**Acceptance**:
- Logs display during application
- Auto-scroll works
- Filtering works
- Readable layout

---

### T046: Implement log streaming from backend [P]

**Story**: US3 | **Files**: `web_ui/backend/src/api/v1/apply.py` (initial), `web_ui/frontend/src/services/api.ts` (enhance)

Create streaming endpoint:
- `GET /api/v1/apply/logs/{job_id}` endpoint
- Server-Sent Events (SSE) for streaming logs
- OR JSON Lines format (newline-delimited JSON)
- Real-time event delivery
- Error handling for closed connections
- Backpressure handling

Frontend API client:
- `streamApplyLogs(jobId)` returns AsyncIterable or EventSource
- Handles disconnections
- Reconnect logic
- Timeout handling

**Acceptance**:
- Logs stream in real-time
- No buffering
- Disconnects handled
- Frontend receives logs

---

### T047: Create unit test for artifact file serving [P]

**Story**: US3 | **Files**: `web_ui/backend/tests/unit/test_artifact_service.py`

Write tests:
- List artifacts for job
- Retrieve artifact file
- Correct MIME types
- Missing file handling
- Path traversal attack prevention
- File size calculation

**Acceptance**:
- All tests pass
- Coverage >= 80%
- Security tests included

---

### T048: Create component test for JobDetail [P]

**Story**: US3 | **Files**: `web_ui/frontend/tests/components/test_JobDetail.tsx`

Write tests:
- Renders job data
- Expands/collapses posting text
- Artifacts display
- Log viewer renders
- Action buttons present
- Missing data handled
- Loading state

**Acceptance**:
- All tests pass
- Coverage >= 80%
- Tests realistic scenarios

---

### T049: Implement status change detection and real-time updates [P]

**Story**: US3 | **Files**: `web_ui/frontend/src/components/JobDetail.tsx` (enhance)

Add polling/subscription:
- Detect when job status changes (via API polling)
- Update UI immediately
- Show status change notification
- Update detail page without full refresh

**Acceptance**:
- Status changes detected
- UI updates immediately
- No full page refresh needed

---

### T050: Add confirmation details display [P]

**Story**: US3 | **Files**: `web_ui/frontend/src/components/JobDetail.tsx` (enhance)

Display submission confirmation:
- Confirmation text (success message)
- Confirmation ID (application reference number)
- Timestamp of submission
- Format nicely
- Copy ID button (optional)

**Acceptance**:
- Confirmation details display
- Readable format
- Copy functionality works

---

### T051: Implement lazy loading for artifact images [P]

**Story**: US3 | **Files**: `web_ui/frontend/src/components/ArtifactsGallery.tsx` (enhance)

Optimize performance:
- Lazy load images on scroll into view
- Placeholder images during load
- Native lazy loading (HTML loading="lazy")
- Fallback for older browsers
- Progressive image loading (low-res → high-res)

**Acceptance**:
- Large artifact images load efficiently
- Performance acceptable (<5s)
- Placeholders show during load

---

### T052: Add accessibility features to job detail page [P]

**Story**: US3 | **Files**: `web_ui/frontend/src/pages/JobDetail.tsx` (enhance)

Enhance accessibility:
- Proper heading hierarchy (h1, h2, h3)
- ARIA labels for interactive elements
- ARIA live region for status updates
- Color contrast >= AA
- Semantic HTML
- Skip links (optional)
- Keyboard navigation for all components

**Acceptance**:
- axe-core audit passes
- Keyboard navigation works
- Screen reader friendly

---

### T053: Create error boundary for JobDetail page [P]

**Story**: US3 | **Files**: `web_ui/frontend/src/pages/JobDetail.tsx` (enhance)

Add error handling:
- ErrorBoundary wrapper
- Graceful fallback UI
- Error logging
- Retry button
- Return to dashboard link

**Acceptance**:
- Component errors don't break app
- User sees helpful error message
- Retry works

---

## Phase 6: Discovery Workflow [US4] (12 tasks)

**User Story 4**: Job discovery with configuration modal, real-time progress, and queue refresh

**Story Goal**: Users can discover jobs with configurable search window and job cap, see real-time progress, and have results automatically added to queue

**Independent Test Criteria**:
- Discovery modal opens with last-used options pre-populated
- Search window and job cap can be configured
- Discovery executes with selected parameters
- Real-time progress displays in modal (discovering, count, status messages)
- Results summary shows when complete
- Queue updates with newly discovered jobs
- Status counts in sidebar update
- Last-used options persist per profile

### T054: Create backend Discovery API endpoints [P]

**Story**: US4 | **Files**: `web_ui/backend/src/api/v1/discover.py`

Implement endpoints:
- `POST /api/v1/discover/execute` - Start discovery with options
- `GET /api/v1/discover/status` - Get discovery progress
- `GET /api/v1/discover/last-options/{profile_id}` - Get last-used options
- Request/response validation with Pydantic models
- Async discovery execution
- Progress streaming to client
- Error handling for failed discovery

Uses CLIService for discover command execution and QueueService for job enqueueing

**Acceptance**:
- All endpoints work correctly
- Progress updates stream in real-time
- Last-used options persist

---

### T055: Create DiscoveryModal component [P]

**Story**: US4 | **Files**: `web_ui/frontend/src/components/DiscoveryModal.tsx`

Implement modal UI:
- Modal dialog (shadcn/ui Dialog)
- Load last-used options on open
- Quick-start section:
  - Search window dropdown (1h, 12h, 24h, 7d, 2w, custom)
  - Job cap numeric input (default 10)
  - Profile selector (pre-filled)
- Advanced Options collapsible section:
  - Custom search query text input
  - Browser mode selector
- Discover and Cancel buttons
- Discovery in progress state:
  - Progress bar (% complete)
  - Job count found
  - Status messages
- Results summary:
  - Total jobs found
  - Close and View Queue buttons

**Acceptance**:
- Modal opens on "Discover Jobs" button click
- Options pre-populated from storage
- Discovery can be executed
- Progress shows
- Results display

---

### T056: Implement RunConfiguration persistence service [P]

**Story**: US4 | **Files**: `web_ui/backend/src/services/run_config_service.py`

Create service:
- `save_run_config(profile_id, config)` → None
- `load_run_config(profile_id)` → RunConfiguration
- Load from `data/run-config/<profile>.json`
- Save to file with atomic write
- Return defaults if file doesn't exist
- Validation of operation_type

Uses FileOps utilities

**Acceptance**:
- Can save and load RunConfiguration
- Persists to JSON file
- Validation works

---

### T057: Integrate RunConfiguration service into backend [P]

**Story**: US4 | **Files**: `web_ui/backend/src/api/v1/discover.py` (enhance)

Wire up persistence:
- Load last-used options when GET /last-options called
- Save options when POST /execute called
- Endpoint returns saved options

**Acceptance**:
- Last-used options endpoint works
- Options saved on discovery execute
- Options pre-populate in next modal open

---

### T058: Implement discovery progress streaming [P]

**Story**: US4 | **Files**: `web_ui/backend/src/api/v1/discover.py` (enhance), `web_ui/frontend/src/components/DiscoveryModal.tsx` (enhance)

Create real-time progress:
- Server streams progress events (SSE or polling)
- Events include: discovered count, status message, progress %
- Frontend DiscoveryModal receives updates
- Display updates in modal
- Handle discovery completion

**Acceptance**:
- Progress updates visible in modal
- No delay between discovery and update display
- Completion detected

---

### T059: Create unit test for RunConfigurationService [P]

**Story**: US4 | **Files**: `web_ui/backend/tests/unit/test_run_config_service.py`

Write tests:
- Save and load RunConfiguration
- Defaults when file doesn't exist
- Validation of operation_type
- File I/O

**Acceptance**:
- All tests pass
- Coverage >= 80%

---

### T060: Create component test for DiscoveryModal [P]

**Story**: US4 | **Files**: `web_ui/frontend/tests/components/test_DiscoveryModal.tsx`

Write tests:
- Modal opens/closes
- Options pre-populate from storage
- Discovery executes with correct parameters
- Progress updates display
- Results summary displays
- Buttons work (Discover, Cancel, Close, View Queue)

**Acceptance**:
- All tests pass
- Coverage >= 80%

---

### T061: Implement queue refresh after discovery [P]

**Story**: US4 | **Files**: `web_ui/frontend/src/components/DiscoveryModal.tsx` (enhance), `web_ui/frontend/src/hooks/useQueue.ts` (enhance)

Auto-refresh queue:
- When discovery completes, refresh queue automatically
- Update job counts in sidebar
- Navigate to queue view (optional)
- Show success notification

**Acceptance**:
- Queue updates after discovery
- New jobs visible immediately
- Counts update

---

### T062: Add error handling to discovery workflow [P]

**Story**: US4 | **Files**: `web_ui/frontend/src/components/DiscoveryModal.tsx` (enhance)

Handle errors:
- Discovery execution errors
- Network errors
- Display error message in modal
- Allow retry
- Log errors

**Acceptance**:
- Errors display user-friendly message
- Retry works
- Error doesn't break modal

---

### T063: Implement form validation for discovery options [P]

**Story**: US4 | **Files**: `web_ui/frontend/src/components/DiscoveryModal.tsx` (enhance)

Add validation:
- Job cap: positive integer, <= 1000
- Search window: valid value
- Custom query: optional
- Real-time validation feedback
- Prevent submit with invalid data

**Acceptance**:
- Invalid data rejected
- User sees error messages
- Submit disabled until valid

---

### T064: Create contract tests for Discovery API [P]

**Story**: US4 | **Files**: `web_ui/backend/tests/contract/test_api_contracts.py` (enhance)

Write tests:
- POST /api/v1/discover/execute schema
- GET /api/v1/discover/status schema
- GET /api/v1/discover/last-options/{profile_id} schema
- Request validation
- Response validation
- Error responses (400, 404, 500)

**Acceptance**:
- All tests pass
- Schema validation comprehensive

---

### T065: Add accessibility features to discovery modal [P]

**Story**: US4 | **Files**: `web_ui/frontend/src/components/DiscoveryModal.tsx` (enhance)

Enhance accessibility:
- Proper heading hierarchy
- ARIA labels on all fields
- ARIA live region for progress/status
- Focus management
- Keyboard navigation (Tab, Escape to close)
- Color contrast >= AA
- Semantic HTML for form

**Acceptance**:
- axe-core audit passes
- Keyboard navigation works
- Screen reader friendly

---

## Phase 7: Application Control [US5] (13 tasks)

**User Story 5**: Single and bulk job application with configurable options, real-time supervision, and status updates

**Story Goal**: Users can apply to single or multiple jobs with configurable options (mode, review mode, LLM settings, resume diagnostics), see real-time progress, and view results

**Independent Test Criteria**:
- Single job apply panel opens with last-used options pre-populated
- Advanced options toggle shows/hides additional settings
- Bulk apply panel opens with different options (mode, max concurrent, stop on failure)
- Job-specific options (resume diagnostics) not in bulk mode
- Apply executes with selected options
- Real-time logs stream during application
- Browser window visible during supervised application
- Application status updates
- Errors displayed with user-friendly messages
- Options persist per profile

### T066: Create backend Apply API endpoints [P]

**Story**: US5 | **Files**: `web_ui/backend/src/api/v1/apply.py`

Implement endpoints:
- `POST /api/v1/apply/single` - Apply to single job
- `POST /api/v1/apply/bulk` - Apply to waiting jobs
- `GET /api/v1/apply/status/{job_id}` - Get application status
- `GET /api/v1/apply/logs/{job_id}` - Stream logs
- Request/response validation
- Async execution
- Log streaming (SSE or polling)
- Error handling

Uses CLIService for apply execution and QueueService for status updates

**Acceptance**:
- All endpoints work
- Logs stream correctly
- Status updates accurate

---

### T067: Create ApplyPanel component for single job application [P]

**Story**: US5 | **Files**: `web_ui/frontend/src/components/ApplyPanel.tsx`

Implement panel UI:
- Panel dialog (shadcn/ui Dialog or Drawer)
- Load last-used options on open
- Quick-start section:
  - Mode selector dropdown (Supervised/Auto, default Supervised)
  - Review mode checkbox (fill without submitting)
- Advanced Options collapsible section:
  - LLM provider override dropdown
  - LLM model override text input
  - Resume diagnostics toggles:
    - Use LLM locator checkbox
    - Debug resume widget checkbox
    - Resume wait timeout numeric input
  - Audit after submit checkbox
  - Save logs checkbox with logs directory path
- Apply and Cancel buttons
- After apply:
  - Show real-time logs from LogViewer
  - Update status
  - Show confirmation if submitted

**Acceptance**:
- Panel opens on "Apply Now" button
- Options pre-populated from storage
- Advanced options toggle works
- Apply executes
- Logs display during application

---

### T068: Create BulkApplyPanel component for bulk application [P]

**Story**: US5 | **Files**: `web_ui/frontend/src/components/BulkApplyPanel.tsx`

Implement panel UI:
- Panel dialog (shadcn/ui Dialog or Drawer)
- Load last-used options on open
- Common options section:
  - Mode selector (Supervised/Auto)
  - Max concurrent numeric input (default from MAX_TABS)
  - Stop on first failure checkbox
  - Review mode checkbox
- Advanced Options collapsible section:
  - LLM overrides (provider, model)
  - Save logs toggle with directory path
- Note: Job-specific options NOT included (resume diagnostics, etc.)
- Apply and Cancel buttons
- Progress display during bulk apply:
  - Jobs queued count
  - Jobs completed count
  - Progress bar
  - Current job being applied

**Acceptance**:
- Panel opens on "Apply to Waiting" button
- Options correctly configured for bulk mode
- Job-specific options hidden
- Progress displays during execution

---

### T069: Create progress display for bulk application [P]

**Story**: US5 | **Files**: `web_ui/frontend/src/components/BulkApplyProgress.tsx`

Implement progress UI:
- Progress bar showing % complete
- Job counts (completed / total)
- Current job being applied (title, company)
- Stop/pause button
- Expandable log view
- Results summary on completion

**Acceptance**:
- Progress displays during bulk apply
- Updates in real-time
- Results show on completion

---

### T070: Implement supervised mode browser window handling [P]

**Story**: US5 | **Files**: `web_ui/backend/src/services/cli_service.py` (enhance), `web_ui/frontend/src/components/ApplyPanel.tsx` (enhance)

Handle browser visibility:
- Backend: Execute CLI with headful mode (default)
- Backend: Stream browser window focus info
- Frontend: Display notification that browser is visible
- Frontend: Show "browser window is open" indicator
- Frontend: Allow user to bring browser to front (if possible)
- Supervised mode: window must be visible (user can see/interact)

**Acceptance**:
- Browser window visible during supervised mode
- User can see form filling
- User can interact if needed

---

### T071: Create unit test for ApplySingle endpoint [P]

**Story**: US5 | **Files**: `web_ui/backend/tests/unit/test_apply_service.py`

Write tests:
- Single job apply execution
- Options parsing and validation
- Status update to IN_PROGRESS
- Log streaming setup

**Acceptance**:
- All tests pass
- Coverage >= 80%

---

### T072: Create component test for ApplyPanel [P]

**Story**: US5 | **Files**: `web_ui/frontend/tests/components/test_ApplyPanel.tsx`

Write tests:
- Panel opens/closes
- Options pre-populate
- Advanced options toggle
- Apply executes with correct parameters
- Logs display
- Status updates

**Acceptance**:
- All tests pass
- Coverage >= 80%

---

### T073: Create component test for BulkApplyPanel [P]

**Story**: US5 | **Files**: `web_ui/frontend/tests/components/test_BulkApplyPanel.tsx`

Write tests:
- Panel opens/closes
- Bulk-specific options displayed
- Job-specific options hidden
- Apply executes
- Progress displays
- Results show on completion

**Acceptance**:
- All tests pass
- Coverage >= 80%

---

### T074: Implement error handling for application execution [P]

**Story**: US5 | **Files**: `web_ui/frontend/src/components/ApplyPanel.tsx` (enhance)

Handle errors:
- Execution errors
- Network errors
- Browser automation errors (selectors not found, etc.)
- Display error message with context
- Allow retry
- Update job status to FAILED

**Acceptance**:
- Errors display user-friendly message
- Job status updates correctly
- Retry possible

---

### T075: Implement captcha detection and status update [P]

**Story**: US5 | **Files**: `web_ui/backend/src/services/cli_service.py` (enhance), `web_ui/frontend/src/components/ApplyPanel.tsx` (enhance)

Handle captcha:
- Backend: CLI detects CAPTCHA, updates job status to CAPTCHA_BLOCKED
- Frontend: Display "Resume Job" button when status is CAPTCHA_BLOCKED
- Frontend: Allow user to manually solve captcha and resume
- Update job status back to IN_PROGRESS when resumed

**Acceptance**:
- CAPTCHA detection works
- Status updates to CAPTCHA_BLOCKED
- Resume button appears
- Resume functionality works

---

### T076: Implement stop/pause application functionality [P]

**Story**: US5 | **Files**: `web_ui/frontend/src/components/ApplyPanel.tsx` (enhance)

Add stop button:
- Stop button during application
- Kills browser automation process
- Updates job status to appropriate state (FAILED if incomplete)
- Closes browser window
- Shows stopped message

**Acceptance**:
- Stop button works
- Process killed properly
- Status updates correctly

---

### T077: Create contract tests for Apply API [P]

**Story**: US5 | **Files**: `web_ui/backend/tests/contract/test_api_contracts.py` (enhance)

Write tests:
- POST /api/v1/apply/single schema
- POST /api/v1/apply/bulk schema
- GET /api/v1/apply/status/{job_id} schema
- GET /api/v1/apply/logs/{job_id} streaming
- Request validation
- Response validation
- Error responses (400, 404, 500)

**Acceptance**:
- All tests pass
- Schema validation comprehensive

---

### T078: Add accessibility features to apply panels [P]

**Story**: US5 | **Files**: `web_ui/frontend/src/components/ApplyPanel.tsx`, `web_ui/frontend/src/components/BulkApplyPanel.tsx` (enhance)

Enhance accessibility:
- Proper form labeling
- ARIA labels on all fields
- ARIA live region for status updates
- Focus management
- Keyboard navigation (Tab, Escape to close)
- Color contrast >= AA
- Semantic HTML for form
- Error messages associated with fields (aria-describedby)

**Acceptance**:
- axe-core audit passes
- Keyboard navigation works
- Screen reader friendly

---

## Phase 8: Profile & Settings Management [US6] (10 tasks)

**User Story 6**: Edit profile configuration and application settings with validation and persistence

**Story Goal**: Users can edit profile TOML fields and .env settings through web UI with validation and automatic persistence

**Independent Test Criteria**:
- Profile page displays editable form with all profile fields
- Can add/remove experience entries dynamically
- Required fields validated before save
- Save persists to TOML file
- Settings page displays all settings organized by category
- Settings changes persist to .env file
- Sensitive fields (API keys) masked in UI
- Reset to defaults works

### T079: Create backend Profile update endpoint implementation [P]

**Story**: US6 | **Files**: `web_ui/backend/src/api/v1/profiles.py` (enhance)

Enhance PUT endpoint:
- Accept Profile update request
- Validate required fields
- Save to TOML file
- Return updated profile
- Error handling for invalid data or write failures

**Acceptance**:
- Endpoint validates and saves profile
- Validation errors clear
- TOML file updated correctly

---

### T080: Create backend Settings endpoints [P]

**Story**: US6 | **Files**: `web_ui/backend/src/api/v1/settings.py`

Implement endpoints:
- `GET /api/v1/settings/` - Get all settings with descriptions
- `GET /api/v1/settings/{key}` - Get single setting
- `PUT /api/v1/settings/` - Update multiple settings
- `DELETE /api/v1/settings/{key}` - Reset single setting
- `POST /api/v1/settings/reset` - Reset all settings
- Settings catalog with descriptions, types, categories
- Mask sensitive values in responses
- Validation of values
- Save to .env file

Uses SettingsService

**Acceptance**:
- All endpoints work
- Sensitive values masked
- .env file updated correctly

---

### T081: Create ProfileEdit page component [P]

**Story**: US6 | **Files**: `web_ui/frontend/src/pages/ProfileEdit.tsx`

Implement page:
- Edit profile form (ProfileForm component)
- Save and Cancel buttons
- Success/error messages
- Back navigation
- Unsaved changes warning (optional)

**Acceptance**:
- Page displays profile form
- Can edit and save
- Messages display
- Navigation works

---

### T082: Create ProfileForm component [P]

**Story**: US6 | **Files**: `web_ui/frontend/src/components/ProfileForm.tsx`

Implement form:
- Profile ID (read-only)
- Name, email, phone, location
- Resume path (with file picker button)
- Preferred browser dropdown
- User data directory
- Defaults section (name, email, phone, location, URLs)
- Keywords section (roles, tech stack)
- Experience section:
  - Add/remove experience entries
  - Each entry: company, role, dates, highlights, tech_stack, metrics
- Form validation
- Error messages
- Save and Cancel buttons

Uses shadcn/ui components (Form, Input, Button, etc.)

**Acceptance**:
- Form displays all fields
- Can edit fields
- Can add/remove experience
- Validation works
- Save/Cancel work

---

### T083: Create Settings page component [P]

**Story**: US6 | **Files**: `web_ui/frontend/src/pages/Settings.tsx`

Implement page:
- Settings form (SettingsForm component)
- Save and Revert buttons
- Modified indicator
- Reset All button with confirmation
- Organized by category (collapsible sections)

**Acceptance**:
- Page displays settings form
- Can edit and save
- Revert works
- Reset All works

---

### T084: Create SettingsForm component [P]

**Story**: US6 | **Files**: `web_ui/frontend/src/components/SettingsForm.tsx`

Implement form:
- Collapsible sections by category:
  - LLM & Provider
  - Resume Upload
  - General Behavior
  - Stealth & Anti-Detection
  - Diagnostics
- Each setting:
  - Key name and description
  - Input field (text, number, checkbox, dropdown, password)
  - Current value
- API key fields as password inputs (masked) with show/hide toggle
- Form validation (numeric ranges, enum values, etc.)
- Modified indicator (show which settings changed)
- Save, Revert, Reset All buttons

Uses shadcn/ui components

**Acceptance**:
- All settings display
- Can edit all field types
- API keys masked
- Validation works
- Save/Revert work

---

### T085: Create unit test for SettingsService [P]

**Story**: US6 | **Files**: `web_ui/backend/tests/unit/test_settings_service.py`

Write tests:
- Load all settings with defaults
- Get single setting
- Update settings
- Reset settings
- Sensitive value masking
- Validation of values
- .env file I/O

**Acceptance**:
- All tests pass
- Coverage >= 80%

---

### T086: Create component test for ProfileForm and SettingsForm [P]

**Story**: US6 | **Files**: `web_ui/frontend/tests/components/test_ProfileForm.tsx`, `test_SettingsForm.tsx`

Write tests:
- Forms render with data
- Can edit fields
- Validation works
- Submit sends correct data
- Add/remove works (ProfileForm)
- Show/hide password works (SettingsForm)
- Reset works (SettingsForm)

**Acceptance**:
- All tests pass
- Coverage >= 80%

---

### T087: Create contract tests for Profile and Settings API [P]

**Story**: US6 | **Files**: `web_ui/backend/tests/contract/test_api_contracts.py` (enhance)

Write tests:
- PUT /api/v1/profiles/{id} schema
- GET /api/v1/settings/ schema
- GET /api/v1/settings/{key} schema
- PUT /api/v1/settings/ schema
- DELETE /api/v1/settings/{key} schema
- POST /api/v1/settings/reset schema
- Request validation
- Response validation
- Error responses (400, 404, 500)

**Acceptance**:
- All tests pass
- Schema validation comprehensive

---

### T088: Add accessibility features to profile and settings forms [P]

**Story**: US6 | **Files**: `web_ui/frontend/src/components/ProfileForm.tsx`, `web_ui/frontend/src/components/SettingsForm.tsx` (enhance)

Enhance accessibility:
- Proper form labeling (label elements)
- ARIA labels on all inputs
- ARIA live region for validation errors
- Focus management after save
- Keyboard navigation (Tab order)
- Color contrast >= AA
- Semantic HTML for form
- Error messages associated with fields (aria-describedby)
- Required field indicators

**Acceptance**:
- axe-core audit passes
- Keyboard navigation works
- Screen reader friendly

---

## Phase 9: Polish & Integration (2 tasks)

**Objective**: Cross-cutting concerns, optimizations, and E2E testing

### T089: Create integration test for complete job discovery → apply workflow [P]

**Story**: Polish | **Files**: `web_ui/backend/tests/integration/test_workflows.py`, `tests/e2e/workflows.spec.ts` (or Cypress)

Write integration tests:
- End-to-end: Discover jobs → Apply to job → View results
- Backend: Verify CLI integration, file I/O, queue updates
- Frontend: User workflow from dashboard → discover → queue → detail → apply → status update
- Both: Verify data flows correctly through API

Uses pytest (backend), Playwright or Cypress (frontend)

**Acceptance**:
- Complete workflow works end-to-end
- Data persists correctly
- Real-time updates work

---

### T090: Performance optimization and monitoring [P]

**Story**: Polish | **Files**: Various optimizations across codebase

Implement comprehensive performance optimization and monitoring:

**Frontend Optimizations**:
- Code splitting: Lazy load components per route (React.lazy + Suspense)
- Bundle analysis: Use `vite-plugin-visualizer` to identify large dependencies
- Asset loading: Enable Vite minification, CSS minification, gzip compression
- Image optimization: Use WebP with JPEG fallback, responsive images

**Backend Optimizations**:
- Queue pagination: Load 50 items per page (virtual scrolling on frontend)
- Profile caching: Cache in-memory, invalidate on write
- Settings caching: 60-second TTL for .env reads
- API response compression: Enable gzip on all JSON responses

**Performance Metrics & Monitoring**:
- **Telemetry Library**: Integrate web-vitals (frontend) + prometheus (backend)
- **Metrics Collection**:
  - Frontend: Core Web Vitals (LCP, FID, CLS), custom timing marks
  - Backend: Request latency histograms, queue operation timings
- **Real-Time Dashboard**: `/metrics` endpoint showing current performance stats
- **Logging Integration**: Store performance events alongside application logs

**Performance Targets** (concrete):
- Dashboard <2s initial load (LCP)
- Queue refresh <3s (API response time)
- Options modals <1s interactive (TTI)
- Artifact load <5s (image decoding + display)
- Frontend bundle <500KB (gzipped)
- Backend response time p99 <1s (excluding discovery/apply operations)

**Acceptance**:
- All performance targets met (verified with performance tests)
- Bundle size < 500KB (gzipped) verified with vite-plugin-visualizer
- Telemetry: web-vitals on frontend, prometheus on backend collecting and exposing metrics
- `/api/v1/metrics/` endpoint returns current performance stats
- Performance monitoring logs stored alongside application events
- Load test passes: 100 concurrent users, 50 jobs per queue, <3s response time p95

---

### T091: Accessibility audit and WCAG 2.1 Level AA compliance [P]

**Story**: Polish | **Files**: Various frontend components, tests

Conduct comprehensive accessibility audit and ensure WCAG 2.1 Level AA compliance across all pages:

**Audit Scope**:
- Run axe-core automated accessibility tests on all pages
- Manual keyboard navigation testing (Tab, Enter, Escape)
- Screen reader testing (VoiceOver on macOS, NVDA on Windows, JAWS where available)
- Color contrast verification (WCAG AA: 4.5:1 for text, 3:1 for UI components)
- Focus indicators visibility and clarity
- Form label associations and error messages

**Fixes Required**:
- Accessible headings hierarchy (h1 → h2 → h3, no skipped levels)
- ARIA labels for dynamic content and status updates
- Button and link text clarity (no "click here", meaningful labels)
- Form validation messages tied to form controls
- Modal focus management (trap focus inside modal)
- Image alt text (descriptive, not "image of")
- Loading states announced to screen readers

**Testing Implementation**:
- Frontend: axe-core integration tests (jest-axe)
- Automated: Run in CI/CD pipeline (fail on errors)
- Manual: Checklist for edge cases (videos, animations, complex interactions)
- Documentation: Accessibility statement added to dashboard

**Acceptance**:
- Automated tests: 0 axe-core errors, 0 warnings on all pages
- Manual testing: Keyboard navigation successful on all features
- Screen reader testing: All content readable and functional
- Color contrast: All text/UI elements pass WCAG AA (4.5:1 or 3:1)
- Focus management: Clear visible focus indicators on all interactive elements
- Documentation: Accessibility statement and WCAG compliance notes in footer

---

---

## Summary

**Total Tasks**: 91 | **Parallel Opportunities**: ~50 tasks marked [P]

### Tasks by Phase

| Phase | Name | Tasks | Duration |
|-------|------|-------|----------|
| 1 | Setup | 2 | 1 day |
| 2 | Foundational | 15 | 3 days |
| 3 | Dashboard & Profile Switching [US1] | 12 | 2 days |
| 4 | Job Queue Display [US2] | 11 | 2 days |
| 5 | Job Details & Artifacts [US3] | 14 | 3 days |
| 6 | Discovery Workflow [US4] | 12 | 2 days |
| 7 | Application Control [US5] | 13 | 3 days |
| 8 | Profile & Settings [US6] | 10 | 2 days |
| 9 | Polish & Integration | 2 | 2 days |
| **Total** | | **91** | **~22 days** |

### MVP Scope (Recommended First Release)

**Phases 1-3**: Minimum 27 tasks for functional MVP
- Users can see dashboard with job queue
- Switch between profiles
- View job details
- Foundation for all features

### Key Parallel Opportunities

Within each phase, these can run in parallel [P]:
- Frontend and backend for same feature (different files)
- Different services (artifact, settings, CLI, etc.)
- Different pages (Dashboard, JobDetail, ProfileEdit, Settings)
- All unit tests
- Contract tests and implementation tests (tests run against stubbed API)

### Implementation Order

**Recommended Execution**:
1. Complete Phase 1-2 sequentially (blockers for everything)
2. Implement Phases 3-8 in priority order, but:
   - Phase 3 before Phase 4
   - Phase 4 before Phase 5
   - Phases 4, 6, 8 can run in parallel after Phase 2
   - Phase 7 depends on Phase 5
3. Phase 9 at end

### Testing Strategy

- **Unit Tests [TDD]**: Write tests before implementation (Phases 2-8)
- **Component Tests**: React component behavior (Phases 3-8)
- **Contract Tests**: API endpoint validation (Phases 2, 6, 7, 8)
- **Integration Tests**: End-to-end workflows (Phase 9)

Each phase should have at least 3-5 test tasks alongside implementation

---

## How to Use This Document

1. **Start with Phase 1**: Set up project structure (1 day)
2. **Then Phase 2**: Build foundational services and models (3 days) - DON'T SKIP
3. **Then choose Phase 3 or 4**: Begin user story work
4. **Within each phase**:
   - Tasks marked [P] can be split among team members
   - Same-file tasks must be sequential (one at a time)
   - Use the task file path to understand where code goes
   - Use the acceptance criteria to know when task is complete
5. **Testing**: Each task should have corresponding test task in same phase

---

**Generated**: 2025-10-28 | **Feature**: 003-web-ui | **Specification**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

🤖 Generated with Claude Code | [spec template](../../.specify/templates/tasks-template.md)
