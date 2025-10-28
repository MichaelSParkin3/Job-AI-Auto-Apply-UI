# Implementation Plan: Web UI Dashboard for Job-AI-Auto-Apply

**Branch**: `003-web-ui` | **Date**: 2025-10-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-web-ui/spec.md`

**Note**: This plan is filled in by the `/speckit.plan` command for the Web UI feature.

## Summary

Build a local web application (localhost-based) that provides a visual dashboard interface for the Job-AI-Auto-Apply automation tool. The web UI coexists with the existing CLI, enabling users to discover jobs via configurable modals, manage application profiles through editable forms, monitor application progress with real-time logs, and configure environment settings through settings pages. Core workflows include sidebar-based navigation with profile selection, job queue filtering/search, detailed job information display with extracted metadata, single and bulk job application with contextual options panels featuring quick-start + advanced toggle design, and artifact gallery viewing for screenshots and logs.

### UI Design Reference

**⚠️ ROUGH DRAFT - EVERYTHING SUBJECT TO CHANGE:**

The following images in `reference_files/ui-design/` are **rough sketches only** meant to provide general layout and information architecture direction. **EVERYTHING shown is subject to change**, including but not limited to:

- Page layout and structure
- Component organization and grouping
- Navigation flow and menu placement
- Form field ordering and grouping
- Visual hierarchy and spacing
- Sidebar vs. different navigation approaches
- Modal vs. slide-out vs. inline options panels
- Color scheme, typography, fonts
- Component styling and appearance
- Button placement and labeling
- Section titles and naming

**Reference Images** (Layout Direction Only):
- `job-application-details-page.png`: Rough concept for job detail page structure
- `edit-profile-page.png`: Rough concept for profile editing form layout
- `env-settings-page.png`: Rough concept for settings/environment variables layout

**Final Implementation Note**: These are conceptual sketches, not design specifications. The implementation will follow:
- Specification requirements (62 FRs) and acceptance scenarios (17 scenarios)
- shadcn/ui component library patterns and conventions
- Modern web UI best practices and accessibility standards
- Developer feedback during implementation
- Any deviations from these rough sketches will be documented in implementation choices

**Do not treat these images as binding specifications** - they are idea seeds only.

## Technical Context

**Language/Version (Frontend)**: TypeScript/JavaScript with Node.js LTS (18+)
**Language/Version (Backend)**: Python 3.11+ (leveraging existing CLI infrastructure)
**Primary Dependencies (Frontend)**: React 18+, shadcn/ui, TypeScript, Vite/Next.js
**Primary Dependencies (Backend)**: Flask or FastAPI (wraps existing auto-apply CLI), file I/O
**Storage**: File-based (TOML profiles, JSON queue files, .env settings, artifacts in filesystem)
**Testing (Frontend)**: Vitest/Jest, React Testing Library
**Testing (Backend)**: pytest (consistent with existing CLI tests)
**Target Platform**: Desktop (localhost:3000), modern browsers (Chrome, Firefox, Safari, Edge)
**Project Type**: Web application (frontend + backend wrapper)
**Performance Goals**: Dashboard <2s initial load; queue refresh <3s; options modals <1s interactive; artifact load <5s
**Constraints**: Single-user local app; no multi-tenancy; file polling every 2s (not WebSockets); responsive 1280x720+
**Scale/Scope**: Single profile active per session; support queues with 500+ jobs; 6 main pages (Dashboard, Job Detail, Profile, Settings, Artifacts, Logs)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Library-First Architecture
- ✅ **PASS**: Web UI backend will be a standalone service/library wrapping CLI
- ✅ **PASS**: Clear contract between frontend and backend via REST/JSON APIs
- ✅ **PASS**: File system utilities isolated in dedicated modules

### Principle II: CLI/Text I/O Interface
- ✅ **PASS**: Backend exposes REST API with JSON request/response
- ✅ **PASS**: All API endpoints support machine consumption (JSON)
- ✅ **PASS**: Existing CLI already has `--json` flag compliance
- ✅ **PASS**: No interactive prompts in API; all configuration via UI or request bodies

### Principle III: Test-First (TDD)
- ✅ **PASS**: Contract tests for all API endpoints required (phase 1)
- ✅ **PASS**: Unit tests for backend services (pytest)
- ✅ **PASS**: React component tests with React Testing Library (frontend)
- ✅ **PASS**: Integration tests for critical user flows (Cypress/Playwright)

### Principle IV: Contract & Integration Testing Discipline
- ✅ **PASS**: API contracts will have explicit OpenAPI/Swagger schema
- ✅ **PASS**: Contract tests guard all REST endpoints
- ✅ **PASS**: Integration tests cover job discovery, apply, profile edit, settings update workflows

### Principle V: Observability, Versioning, and Simplicity
- ✅ **PASS**: Backend logs structured events (JSON with severity levels)
- ✅ **PASS**: Frontend logs via console (React dev tools integration)
- ✅ **PASS**: API versioning via `/api/v1/` prefix (initial release v1.0)
- ✅ **PASS**: Simplicity through file-based state (no database complexity)
- ✅ **PASS**: Minimize dependencies (shadcn/ui as minimal UI layer)

### Security & Performance Standards
- ✅ **PASS**: No secrets in frontend code; API keys via backend env vars only
- ✅ **PASS**: Performance targets documented (dashboard <2s, queue refresh <3s, options <1s)
- ✅ **PASS**: Artifact files served with correct MIME types; lazy loading for large files

### Coding Standards
- ✅ **PASS**: Frontend: TypeScript with strict types, Prettier + ESLint, JSDoc for public functions
- ✅ **PASS**: Backend: Python with type hints, Ruff linter, Google-style docstrings
- ✅ **PASS**: Line length soft limit 100 characters
- ✅ **PASS**: Error handling: no swallowed exceptions; exit codes for CLI; HTTP status codes for API

**Constitution Check Result**: ✅ **PASS** - Feature aligns with all Core Principles and Quality Gates

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

**Structure Decision**: Web application (Option 2) with frontend (TypeScript/React) + backend (Python Flask/FastAPI) separation.

```text
web_ui/
├── backend/
│   ├── src/
│   │   ├── app.py                 # Flask/FastAPI app initialization
│   │   ├── models/                # Data models (Profile, Job, etc.)
│   │   │   ├── __init__.py
│   │   │   ├── application.py     # ApplicationItem, JobDetails, Artifacts
│   │   │   └── config.py          # RunConfiguration, Settings
│   │   ├── services/              # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── queue_service.py   # Queue file I/O, status updates
│   │   │   ├── profile_service.py # Profile TOML read/write
│   │   │   ├── cli_service.py     # CLI subprocess wrapper (discover, apply)
│   │   │   ├── artifact_service.py # Artifact file serving
│   │   │   └── settings_service.py # .env file management
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py          # Flask/FastAPI routes
│   │   │   ├── v1/
│   │   │   │   ├── profiles.py    # Profile endpoints
│   │   │   │   ├── jobs.py        # Job queue endpoints
│   │   │   │   ├── discover.py    # Discovery endpoints
│   │   │   │   ├── apply.py       # Application endpoints
│   │   │   │   ├── artifacts.py   # Artifact serving endpoints
│   │   │   │   └── settings.py    # Settings endpoints
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logging.py         # Structured logging
│   │       └── file_ops.py        # File I/O utilities
│   ├── tests/
│   │   ├── contract/
│   │   │   └── test_api_contracts.py # OpenAPI contract tests
│   │   ├── integration/
│   │   │   └── test_workflows.py  # Job discovery, apply, profile edit
│   │   └── unit/
│   │       ├── test_queue_service.py
│   │       ├── test_profile_service.py
│   │       └── test_cli_service.py
│   ├── requirements.txt
│   └── wsgi.py                     # Production server entry point
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx               # React app entry point
│   │   ├── App.tsx                # Root component
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── JobDetail.tsx
│   │   │   ├── ProfileEdit.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── Artifacts.tsx
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── JobQueue.tsx
│   │   │   ├── DiscoveryModal.tsx
│   │   │   ├── ApplyPanel.tsx
│   │   │   ├── ProfileForm.tsx
│   │   │   └── SettingsForm.tsx
│   │   ├── services/
│   │   │   ├── api.ts             # API client (fetch wrapper)
│   │   │   ├── storage.ts         # Local storage for options persistence
│   │   │   └── polling.ts         # Queue file polling logic
│   │   ├── types/
│   │   │   ├── index.ts           # TypeScript interfaces
│   │   │   └── api.ts             # API response types
│   │   ├── styles/
│   │   │   └── globals.css        # Global + shadcn/ui overrides
│   │   └── hooks/
│   │       ├── useQueue.ts        # Queue state + polling
│   │       └── useProfile.ts      # Profile state + switching
│   ├── public/
│   │   └── index.html
│   ├── tests/
│   │   ├── components/            # React component tests
│   │   ├── integration/           # E2E tests (Cypress/Playwright)
│   │   └── unit/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts (or next.config.js)
│   └── .eslintrc.json
│
└── README.md                       # Setup and run instructions

tests/ (shared integration tests)
├── e2e/
│   └── workflows.spec.ts           # Cypress/Playwright full workflows
```

**Rationale**: Separation of frontend/backend enables parallel development, independent deployment, and clear API boundaries. Frontend uses React + shadcn/ui for rapid UI delivery. Backend wraps existing CLI with REST API for loose coupling.

## Complexity Tracking

> **No Constitution Check violations. All principles and quality gates satisfied.**

No additional complexity justification needed - architecture aligns with constitutional requirements.

---

## Phase 0: Outline & Research

### Research Tasks

Since all technical context is specified in the plan and no NEEDS CLARIFICATION markers exist, Phase 0 focuses on:

1. **Frontend Framework Decision**: React vs Next.js vs Remix comparison for local app
   - Decision: **React 18 + Vite** for simplicity and rapid development
   - Rationale: Vite provides fast HMR; React sufficient for single-page dashboard; no SSR needed for localhost
   - Alternatives: Next.js rejected (overkill for local app); Remix rejected (unnecessary complexity)

2. **Backend Framework Decision**: Flask vs FastAPI
   - Decision: **FastAPI** for async support and automatic OpenAPI schema
   - Rationale: Async enables non-blocking subprocess calls; automatic schema generation for contract tests
   - Alternatives: Flask acceptable but lacks native async; Flask-RESTX adds boilerplate

3. **File Polling Strategy**: 2-second interval vs websockets
   - Decision: **File polling every 2 seconds** (as specified in constraints)
   - Rationale: Simplicity for local app; file I/O observable in logs; no WebSocket complexity
   - Alternatives: WebSockets rejected (adds server-side complexity for single-user app)

4. **Options Persistence**: LocalStorage vs file-based
   - Decision: **Frontend LocalStorage for UI state** + **File-based per-profile JSON** for RunConfiguration
   - Rationale: LocalStorage fast for UI responsiveness; file-based for durability across browser sessions
   - Alternatives: Database rejected (violates file-based assumption); cookies rejected (size limit)

5. **API Authentication**: None vs Token vs Session
   - Decision: **No authentication** (single-user localhost app)
   - Rationale: Local machine; no multi-user scenario; all data in user's file system
   - Alternatives: JWT rejected (unnecessary); OAuth rejected (out of scope)

**Output**: All research complete; technical decisions documented above. Proceed to Phase 1.

---

## Phase 1: Design & Contracts

### 1. Data Model (data-model.md)

Will be generated in phase 1 and include:
- **Profile Entity**: TOML-backed, editable via web UI
- **ApplicationItem (Job)**: Queue entry with lifecycle states (NEW → IN_PROGRESS → SUBMITTED/FAILED/CAPTCHA_BLOCKED)
- **JobDetails**: Extracted posting information
- **Artifacts**: Screenshot and log file references
- **RunConfiguration**: User-selected discover/apply options, persisted per profile
- **Settings**: .env file key-value pairs

### 2. API Contracts

REST API endpoints organized by resource:

**Profiles** (`/api/v1/profiles/`)
- `GET /` - List available profiles
- `GET /{id}` - Get profile details
- `PUT /{id}` - Update profile TOML
- `GET /{id}/queue` - Get profile's job queue
- `POST /{id}/switch` - Switch active profile

**Jobs** (`/api/v1/jobs/`)
- `GET /?profile={id}` - List jobs with filtering/search
- `GET /{job_id}` - Get job detail with artifacts
- `PUT /{job_id}/status` - Update job status (manual reset)
- `DELETE /{job_id}` - Remove from queue

**Discovery** (`/api/v1/discover/`)
- `POST /execute` - Start discovery with options (search_window, job_cap, custom_query)
- `GET /status` - Get discovery progress
- `GET /last-options/{profile_id}` - Retrieve saved options

**Apply** (`/api/v1/apply/`)
- `POST /single` - Apply to single job with options (mode, review_mode, llm_overrides, resume_diagnostics)
- `POST /bulk` - Apply to waiting jobs with batch options
- `GET /status/{job_id}` - Get application progress
- `GET /logs/{job_id}` - Stream real-time logs

**Artifacts** (`/api/v1/artifacts/`)
- `GET /{profile_id}/{job_id}/` - List available artifact files
- `GET /{profile_id}/{job_id}/{file}` - Serve artifact (screenshot, log, etc.)

**Settings** (`/api/v1/settings/`)
- `GET /` - Get all .env settings with descriptions
- `GET /{key}` - Get single setting value
- `PUT /` - Update multiple settings
- `DELETE /{key}` - Remove setting (revert to default)
- `POST /reset` - Reset all to defaults

### 3. Testing Strategy

**Contract Tests** (Backend):
- Validate all API endpoints exist with correct HTTP methods
- Validate request/response schema matches OpenAPI spec
- Validate error responses (400, 404, 500 with proper JSON)

**Unit Tests**:
- Backend services: queue_service, profile_service, cli_service, artifact_service, settings_service
- Frontend components: Sidebar, JobQueue, DiscoveryModal, ApplyPanel, etc.

**Integration Tests**:
- Discovery workflow: modal → execute → progress → refresh queue
- Apply workflow: job detail → apply panel → real-time logs → submission
- Profile edit: form validation → save → persistence check
- Settings update: UI modification → .env file write → verification

### 4. Quickstart (quickstart.md)

Will document:
- Frontend setup: `npm install` in web_ui/frontend/, `npm run dev`
- Backend setup: `pip install -r requirements.txt` in web_ui/backend/, `python app.py`
- CORS configuration (frontend localhost:5173 → backend localhost:5000)
- Environment variables (.env template with required keys)
- Sample profiles and queues for testing
- Development workflow (running tests, building for production)

### 5. Agent Context Update

Will run `.specify/scripts/bash/update-agent-context.sh` to update Claude Code context with:
- Web UI project structure
- Technology stack (React, FastAPI, TypeScript, Python)
- File paths for key modules
- Testing approach (pytest + Jest/Vitest)
- API schema and contract locations

---

## Timeline & Dependencies

**Phase 0 Complete**: ✅ Research finalized

**Phase 1 Deliverables** (generate via `/speckit.plan`):
- [ ] research.md - Research findings (this section)
- [ ] data-model.md - Entity definitions with validation rules
- [ ] contracts/ - OpenAPI schema and contract test fixtures
- [ ] quickstart.md - Setup and development guide
- [ ] Updated agent context file

**Phase 2** (via `/speckit.tasks`):
- Generate detailed task breakdown (T001-T0XX) with dependencies
- Map requirements (FR-001 through FR-049) to implementation tasks
- Risk assessment and mitigation strategies

---
