# Research: Web UI Dashboard for Job-AI-Auto-Apply

**Date**: 2025-10-28 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Overview

Phase 0 research identified and evaluated critical technical decisions for the Web UI feature. All decisions have been validated against the project constitution and constraints. This document summarizes research findings, rationale, and alternatives considered.

---

## Technical Decisions

### 1. Frontend Framework Decision

**Context**: Choose a frontend framework for a single-page dashboard application running on localhost (http://localhost:3000) with modern browser targets.

**Decision**: **React 18 + Vite**

**Rationale**:
- **Vite's Fast HMR**: Hot module reloading enables rapid development feedback
- **React Sufficient**: React 18 is sufficient for a single-page dashboard; no need for SSR
- **No Localhost Complexity**: Server-side rendering (SSR) provides no value for localhost-only app
- **Component Reusability**: React + shadcn/ui enables rapid UI component composition
- **Lightweight Build**: Vite produces smaller bundle sizes than Next.js for SPA workflows
- **Developer Experience**: React's ecosystem and tooling are well-established

**Alternatives Considered**:
- **Next.js**: Rejected (unnecessary complexity for SPA; SSR/SSG not needed for localhost)
- **Remix**: Rejected (adds server-side routing complexity; overkill for single-page dashboard)
- **Vue 3**: Considered (similar lightweight option; rejected due to team familiarity with React)
- **Svelte**: Rejected (smaller ecosystem; shadcn/ui uses React)

**Compatibility**: React 18+ with TypeScript provides type safety; ESLint + Prettier for code quality.

---

### 2. Backend Framework Decision

**Context**: Wrap existing CLI tool with REST API that exposes job discovery, application, profile management, and settings configuration.

**Decision**: **FastAPI**

**Rationale**:
- **Native Async Support**: FastAPI's async/await enables non-blocking subprocess calls for CLI integration (discovered jobs, application progress)
- **Automatic OpenAPI Schema**: FastAPI auto-generates OpenAPI 3.0 schema for contract testing and API documentation
- **Type Hints**: Python 3.11+ type hints provide static type checking (mypy) and IDE autocomplete
- **Performance**: FastAPI is among the fastest Python web frameworks (comparable to Go/Node in benchmarks)
- **Minimal Boilerplate**: Less ceremony than Flask-RESTX; decorator-based routing is clean
- **Contract Testing**: Auto-generated schema supports pydantic models for request/response validation

**Alternatives Considered**:
- **Flask**: Acceptable but lacks native async support; Flask-RESTX adds boilerplate; requires custom OpenAPI setup
- **Django REST Framework**: Rejected (too heavy for a wrapper service; designed for larger monoliths)
- **Starlette**: Rejected (lower-level; FastAPI builds on Starlette with better ergonomics)

**Compatibility**: FastAPI requires Python 3.11+; aligns with existing CLI Python 3.11+ requirement.

---

### 3. File Polling Strategy

**Context**: Keep frontend and backend in sync with queue file changes when jobs are discovered or status updates via CLI.

**Decision**: **File polling every 2 seconds**

**Rationale**:
- **Specified in Constraints**: Plan explicitly states "file polling every 2s (not WebSockets)"
- **Simplicity**: No WebSocket infrastructure complexity for single-user localhost app
- **Observability**: File I/O is observable in logs; easier to debug state changes
- **CLI Integration**: Existing CLI writes to queue files on disk; polling aligns with current architecture
- **Sufficient Latency**: 2-second refresh meets success criteria (FM-001: queue refreshes within 3 seconds)
- **No Server Complexity**: No need to track client subscriptions or broadcast messages

**Alternatives Considered**:
- **WebSockets**: Rejected (adds bidirectional communication complexity; server must track active clients for single-user app)
- **Server-Sent Events (SSE)**: Rejected (similar complexity to WebSockets for this use case)
- **1-second polling**: Rejected (higher CPU/disk I/O; 2-second trade-off balances responsiveness and resource usage)

**Implementation**: Frontend `polling.ts` service implements 2-second interval check of queue file via API endpoint.

---

### 4. Options Persistence Strategy

**Context**: User-selected discover and apply options (search window, job cap, mode, LLM settings, etc.) should persist across browser sessions for convenience.

**Decision**: **Frontend LocalStorage for UI state** + **File-based per-profile JSON for RunConfiguration**

**Rationale**:
- **UI State (LocalStorage)**: Form field selections, expanded/collapsed sections, tab state stored in browser localStorage
  - Fast access without network round-trip
  - No server overhead for read-heavy UI state
  - Survives browser refresh within same session

- **Persistent Config (File-based JSON)**: RunConfiguration entity persisted to `data/run-config/<profile>.json`
  - Survives browser close/restart cycles
  - Mirrors file-based architecture (TOML profiles, JSON queues)
  - Respects single-machine constraint (no database needed)
  - Enables CLI tools to read last-used options if desired in future

**Alternatives Considered**:
- **Database (SQLite, PostgreSQL)**: Rejected (violates file-based storage assumption; adds unnecessary complexity for localhost app)
- **Cookies Only**: Rejected (size limit ~4KB; insufficient for storing complex option objects)
- **Server Session State**: Rejected (server not responsible for UI preferences; violates stateless API design)
- **Hybrid Approach**: Accepted (LocalStorage for immediate UX; JSON for durability is the chosen approach)

**Implementation**: Frontend `storage.ts` service provides `saveUIState()` (localStorage) and `saveRunConfig()` (API POST to backend); backend persists to disk.

---

### 5. API Authentication Strategy

**Context**: Determine whether API endpoints require authentication/authorization.

**Decision**: **No authentication** (single-user localhost app)

**Rationale**:
- **Deployment Model**: Application runs on localhost; not exposed to network
- **Single User**: Only the machine owner has access to the web UI
- **File-Based Data**: All data lives in the user's home directory (`data/`, `profiles/`)
- **Trust Boundary**: Frontend and backend run on same machine under same user context
- **Complexity**: Authentication adds overhead with no security benefit for localhost

**Alternatives Considered**:
- **JWT Tokens**: Rejected (unnecessary complexity; no multi-user scenario)
- **Session Cookies**: Rejected (same as JWT; adds session tracking overhead)
- **API Keys**: Rejected (not needed; frontend and backend trust each other)
- **OAuth/SAML**: Rejected (completely out of scope for localhost app)

**Implementation**: No authentication middleware; all API endpoints accessible. CORS configured to allow localhost:5173 → localhost:5000.

---

## Constitution Alignment

All five research decisions align with the project constitution:

- **Principle I (Library-First)**: Backend is a standalone service wrapping CLI with clear REST API contract
- **Principle II (CLI/Text I/O)**: API exposes JSON request/response; frontend consumes structured data
- **Principle III (Test-First)**: Contract tests validate FastAPI OpenAPI schema; unit tests for React components
- **Principle IV (Contract/Integration)**: OpenAPI schema + pydantic models enable contract testing
- **Principle V (Observability/Versioning)**: Structured logging in backend; /api/v1/ versioning prefix

---

## Performance & Constraints Alignment

All decisions support the stated performance targets and constraints:

| Constraint | Decision Support |
|-----------|-----------------|
| Dashboard <2s initial load | React + Vite produces small SPA bundles; file polling aligns with queue refresh timing |
| Queue refresh <3s | 2-second polling interval meets requirement |
| Options modals <1s interactive | LocalStorage provides instant UI updates; FastAPI responds quickly to reads |
| 500+ job queue support | React with pagination/virtual scrolling; no WebSocket scalability concerns |
| No database | File-based RunConfiguration and LocalStorage both satisfy |
| Localhost single-user | No authentication needed; polling sufficient for single client |

---

## Phase 0 Completion Status

✅ **All 5 research tasks complete**

Research findings documented. All technical decisions validated against constraints, constitution, and performance targets. Proceed to Phase 1 (Design & Contracts).

---
