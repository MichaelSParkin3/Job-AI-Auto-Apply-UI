# Web UI Implementation Plan: FastAPI + shadcn/ui for Job-AI-Auto-Apply

**Document Version:** 1.0
**Created:** 2025-11-03
**Branch:** `web-ui-minimal`
**Focus:** Discover & Apply commands with flag selection, comprehensive testing

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Path Configuration & CLI Integration](#path-configuration--cli-integration)
4. [Backend Implementation (FastAPI)](#backend-implementation-fastapi)
5. [Frontend Implementation (React + shadcn)](#frontend-implementation-react--shadcn)
6. [Testing Strategy](#testing-strategy)
7. [Implementation Phases](#implementation-phases)
8. [Development Workflow](#development-workflow)
9. [Acceptance Criteria](#acceptance-criteria)

---

## Architecture Overview

### System Design

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React + Vite + shadcn/ui)                    │
│  - Command Launcher (discover/apply with flags)         │
│  - Queue Table Viewer                                   │
│  - Real-time Apply Progress                             │
│  Port: 5173 (dev) / served by FastAPI (prod)           │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ HTTP REST API + WebSockets
                 │
┌────────────────▼────────────────────────────────────────┐
│  Backend (FastAPI)                                      │
│  - REST API: /api/discover, /api/apply                  │
│  - WebSocket: /ws/apply for real-time streaming        │
│  - Imports existing orchestrator.py directly           │
│  Port: 8000                                             │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ Direct Python imports (no subprocess!)
                 │
┌────────────────▼────────────────────────────────────────┐
│  Existing CLI Code (ZERO CHANGES NEEDED)               │
│  - orchestrator.py (discover/apply/resume-job)         │
│  - application_queue.py (ApplicationQueue)             │
│  - profile_manager.py (load_profile, list_profiles)    │
│  - config.py (Settings singleton)                      │
│  Uses paths:                                            │
│  - data/queues/ (via config.QUEUES_DIR)                │
│  - profiles/ (via config.PROFILES_DIR)                 │
└─────────────────────────────────────────────────────────┘
```

### Key Principles

1. **No CLI Code Changes**: Backend imports existing modules directly
2. **Path Consistency**: Both CLI and web UI use same `config.py` paths
3. **Async-First**: FastAPI + existing async orchestrator code
4. **Real-time Streaming**: WebSocket for apply progress (not subprocess polling)
5. **Type Safety**: Pydantic models + TypeScript generated from OpenAPI
6. **Comprehensive Testing**: Backend unit/integration, frontend component/E2E

---

## Directory Structure

```
Job-AI-Auto-Apply-UI/
├── data/
│   └── queues/                          # ← Queue storage (unchanged)
│       └── michael_scott_parkin_iii.json
├── profiles/                            # ← Profile TOML files (unchanged)
│   └── michael_scott_parkin_iii.toml
├── src/
│   └── job_ai_auto_apply_ui/           # ← Existing CLI code (NO CHANGES)
│       ├── orchestrator.py
│       ├── application_queue.py
│       ├── profile_manager.py
│       ├── config.py
│       └── ...
├── web_ui/                              # ← NEW: Web UI code
│   ├── backend/                         # FastAPI backend
│   │   ├── __init__.py
│   │   ├── app.py                       # FastAPI app + startup
│   │   ├── config.py                    # Web-specific config (ports, CORS)
│   │   ├── dependencies.py              # Shared dependencies (settings injection)
│   │   ├── models/                      # Pydantic response models
│   │   │   ├── __init__.py
│   │   │   ├── queue.py                 # QueueItemResponse, QueueListResponse
│   │   │   ├── profile.py               # ProfileResponse, ProfileListResponse
│   │   │   ├── command.py               # DiscoverRequest, ApplyRequest
│   │   │   └── events.py                # ApplyEventResponse (WebSocket)
│   │   └── routes/                      # API route handlers
│   │       ├── __init__.py
│   │       ├── profiles.py              # GET /api/profiles
│   │       ├── queues.py                # GET /api/queues/{profile_id}
│   │       ├── discover.py              # POST /api/discover
│   │       ├── apply.py                 # POST /api/apply (returns task ID)
│   │       └── websockets.py            # WS /ws/apply/{task_id}
│   ├── frontend/                        # React + Vite + shadcn
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── ui/                  # shadcn primitives (button, input, etc.)
│   │   │   │   ├── CommandLauncher.tsx  # Main component for discover/apply
│   │   │   │   ├── DiscoverForm.tsx     # Discover command form
│   │   │   │   ├── ApplyForm.tsx        # Apply command form
│   │   │   │   ├── ApplyProgress.tsx    # Real-time apply progress
│   │   │   │   ├── QueueTable.tsx       # Queue viewer (future)
│   │   │   │   └── ProfileSelector.tsx  # Profile dropdown
│   │   │   ├── lib/
│   │   │   │   ├── api.ts               # Axios client + typed endpoints
│   │   │   │   ├── websocket.ts         # WebSocket manager
│   │   │   │   └── utils.ts             # shadcn helpers
│   │   │   ├── types/                   # TypeScript types (generated from OpenAPI)
│   │   │   │   └── api.ts
│   │   │   ├── App.tsx                  # Main app layout
│   │   │   └── main.tsx                 # Entry point
│   │   ├── tests/                       # Frontend tests
│   │   │   ├── components/              # Component tests (Vitest + Testing Library)
│   │   │   └── e2e/                     # E2E tests (Playwright)
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.js
│   │   ├── tsconfig.json
│   │   └── playwright.config.ts
│   └── tests/                           # Backend tests
│       ├── __init__.py
│       ├── test_routes_profiles.py
│       ├── test_routes_queues.py
│       ├── test_routes_discover.py
│       ├── test_routes_apply.py
│       ├── test_websockets.py
│       └── conftest.py                  # Pytest fixtures
├── developer_tasks/
│   └── dev_docs/
│       └── web_ui_implementation_plan.md  # ← THIS DOCUMENT
├── pyproject.toml                       # Add fastapi, uvicorn
├── package.json                         # Root package.json for scripts
└── README.md                            # Update with web UI instructions
```

---

## Path Configuration & CLI Integration

### Problem Statement

**Challenge**: Ensure web UI and CLI use identical paths for:
- Queue storage: `data/queues/`
- Profile storage: `profiles/`
- Artifacts: `data/artifacts/`

**Solution**: Both import `config.py` singleton, which resolves paths relative to project root.

### Current Path Resolution (in CLI)

**`src/job_ai_auto_apply_ui/config.py`**:
```python
from pathlib import Path
import os

# Project root is 2 levels up from this file
PROJECT_ROOT = Path(__file__).parent.parent.parent

class Settings:
    def __init__(self):
        self.profiles_dir = os.getenv(
            "AUTO_APPLY_PROFILES_DIR",
            str(PROJECT_ROOT / "profiles")
        )
        self.queues_dir = os.getenv(
            "AUTO_APPLY_QUEUES_DIR",
            str(PROJECT_ROOT / "data" / "queues")
        )
        self.artifacts_dir = os.getenv(
            "AUTO_APPLY_ARTIFACTS_DIR",
            str(PROJECT_ROOT / "data" / "artifacts")
        )

settings = Settings()  # Singleton instance
```

**Current behavior**:
- CLI imports `from job_ai_auto_apply_ui.config import settings`
- Paths resolve to absolute paths based on `PROJECT_ROOT`

### Backend Integration (FastAPI)

**`web_ui/backend/app.py`**:
```python
from job_ai_auto_apply_ui.config import settings  # ← Same singleton!

@app.on_event("startup")
async def startup_event():
    logger.info(f"Profiles directory: {settings.profiles_dir}")
    logger.info(f"Queues directory: {settings.queues_dir}")
    logger.info(f"Artifacts directory: {settings.artifacts_dir}")

    # Validate directories exist
    Path(settings.profiles_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.queues_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.artifacts_dir).mkdir(parents=True, exist_ok=True)
```

**Key points**:
1. Backend imports **same `config.py`** as CLI
2. No environment variable changes needed
3. Works in both dev (from repo root) and production (installed package)

### Testing Path Configuration

**Test: Verify CLI and Web UI use same paths**

```python
# web_ui/tests/test_path_consistency.py

from pathlib import Path
from job_ai_auto_apply_ui.config import settings

def test_paths_resolve_correctly():
    """Ensure paths point to expected locations."""
    assert Path(settings.profiles_dir).name == "profiles"
    assert Path(settings.queues_dir).name == "queues"
    assert (Path(settings.queues_dir).parent / "artifacts").exists()

def test_queue_file_accessible():
    """Ensure actual queue file can be read."""
    queue_path = Path(settings.queues_dir) / "michael_scott_parkin_iii.json"
    assert queue_path.exists(), f"Queue file not found: {queue_path}"

    import json
    with open(queue_path) as f:
        data = json.load(f)
    assert "items" in data
```

---

## Backend Implementation (FastAPI)

### Phase 1: App Scaffolding

**File: `web_ui/backend/app.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from job_ai_auto_apply_ui.config import settings
from .routes import profiles, queues, discover, apply, websockets

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting FastAPI server")
    logger.info(f"Profiles: {settings.profiles_dir}")
    logger.info(f"Queues: {settings.queues_dir}")
    yield
    logger.info("Shutting down FastAPI server")

app = FastAPI(
    title="Job Auto Apply Web UI",
    version="0.1.0",
    lifespan=lifespan
)

# CORS for development (Vite runs on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(profiles.router, prefix="/api", tags=["profiles"])
app.include_router(queues.router, prefix="/api", tags=["queues"])
app.include_router(discover.router, prefix="/api", tags=["discover"])
app.include_router(apply.router, prefix="/api", tags=["apply"])
app.include_router(websockets.router, prefix="/ws", tags=["websockets"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}

def main():
    """Entry point for auto-apply-web command."""
    import uvicorn
    uvicorn.run(
        "web_ui.backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

**Update `pyproject.toml`**:
```toml
[project.scripts]
auto-apply = "job_ai_auto_apply_ui.orchestrator:main"
auto-apply-web = "web_ui.backend.app:main"  # ← NEW
```

---

### Phase 2: Route Implementation

#### 2.1 Profiles Route

**File: `web_ui/backend/routes/profiles.py`**

```python
from fastapi import APIRouter, HTTPException
from typing import List
from pathlib import Path

from job_ai_auto_apply_ui.profile_manager import list_profiles, load_profile
from ..models.profile import ProfileResponse, ProfileListResponse

router = APIRouter()

@router.get("/profiles", response_model=ProfileListResponse)
async def get_profiles():
    """List all available profiles from profiles/ directory."""
    try:
        profile_ids = list_profiles()  # Returns list of profile IDs
        profiles = []

        for profile_id in profile_ids:
            try:
                profile = load_profile(profile_id)
                profiles.append(ProfileResponse(
                    id=profile.id,
                    name=profile.name,
                    resume_path=profile.resume_path,
                    preferred_browser=profile.preferred_browser,
                    has_experience=len(profile.experience or []) > 0
                ))
            except Exception as e:
                # Skip invalid profiles, log error
                logger.warning(f"Failed to load profile {profile_id}: {e}")

        return ProfileListResponse(profiles=profiles, count=len(profiles))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str):
    """Get details for a specific profile."""
    try:
        profile = load_profile(profile_id)
        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            resume_path=profile.resume_path,
            preferred_browser=profile.preferred_browser,
            has_experience=len(profile.experience or []) > 0
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**File: `web_ui/backend/models/profile.py`**

```python
from pydantic import BaseModel
from typing import List, Optional

class ProfileResponse(BaseModel):
    id: str
    name: str
    resume_path: str
    preferred_browser: Optional[str] = None
    has_experience: bool = False

class ProfileListResponse(BaseModel):
    profiles: List[ProfileResponse]
    count: int
```

---

#### 2.2 Discover Route

**File: `web_ui/backend/routes/discover.py`**

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
import structlog
from datetime import datetime

from job_ai_auto_apply_ui.orchestrator import handle_discover
from job_ai_auto_apply_ui.profile_manager import load_profile

router = APIRouter()
logger = structlog.get_logger()

class DiscoverRequest(BaseModel):
    """Request model for discover command."""
    profile_id: str = Field(..., description="Profile identifier")
    window: str = Field(default="24h", description="Time window (24h, 7d, 1w, etc.)")
    cap: int = Field(default=10, ge=1, le=100, description="Max jobs to discover")

class DiscoverResponse(BaseModel):
    """Response model for discover command."""
    success: bool
    items_discovered: int
    message: str
    profile_id: str

async def run_discover_task(request: DiscoverRequest):
    """Background task to run discover command."""
    logger.info("discover.start", profile_id=request.profile_id, window=request.window, cap=request.cap)

    try:
        profile = load_profile(request.profile_id)
        result = await handle_discover(
            profile=profile,
            window=request.window,
            cap=request.cap,
            json_output=True  # Get structured result
        )
        logger.info("discover.complete", profile_id=request.profile_id, count=result.get("count", 0))
        return result
    except Exception as e:
        logger.error("discover.failed", profile_id=request.profile_id, error=str(e))
        raise

@router.post("/discover", response_model=DiscoverResponse)
async def discover(request: DiscoverRequest, background_tasks: BackgroundTasks):
    """
    Trigger discover command to find new job postings.

    This endpoint returns immediately and runs discovery in background.
    Poll /api/queues/{profile_id} to see new items.
    """
    try:
        # Validate profile exists
        profile = load_profile(request.profile_id)

        # Run in background (FastAPI BackgroundTasks)
        # NOTE: For long-running tasks, consider Celery or similar
        background_tasks.add_task(run_discover_task, request)

        return DiscoverResponse(
            success=True,
            items_discovered=0,  # Will be updated in background
            message=f"Discover started for profile '{request.profile_id}' (window: {request.window}, cap: {request.cap})",
            profile_id=request.profile_id
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{request.profile_id}' not found")
    except Exception as e:
        logger.error("discover.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

**Testing Discover Route**:

```python
# web_ui/tests/test_routes_discover.py

import pytest
from httpx import AsyncClient
from web_ui.backend.app import app

@pytest.mark.asyncio
async def test_discover_with_valid_profile(async_client: AsyncClient):
    """Test discover endpoint with valid profile."""
    response = await async_client.post(
        "/api/discover",
        json={
            "profile_id": "michael_scott_parkin_iii",
            "window": "24h",
            "cap": 5
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["profile_id"] == "michael_scott_parkin_iii"
    assert "Discover started" in data["message"]

@pytest.mark.asyncio
async def test_discover_with_invalid_profile(async_client: AsyncClient):
    """Test discover endpoint with non-existent profile."""
    response = await async_client.post(
        "/api/discover",
        json={
            "profile_id": "nonexistent_profile",
            "window": "24h",
            "cap": 10
        }
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_discover_validation(async_client: AsyncClient):
    """Test discover request validation."""
    # Cap too high
    response = await async_client.post(
        "/api/discover",
        json={"profile_id": "test", "cap": 200}
    )
    assert response.status_code == 422  # Validation error
```

---

#### 2.3 Apply Route (with WebSocket streaming)

**File: `web_ui/backend/routes/apply.py`**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime
import structlog

router = APIRouter()
logger = structlog.get_logger()

# In-memory task storage (use Redis/DB for production)
active_tasks = {}

class ApplyRequest(BaseModel):
    """Request model for apply command."""
    profile_id: str
    job_id: Optional[str] = None  # If None, apply to all pending
    supervised: bool = True
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    use_llm_locator: bool = False
    debug_resume_widget: bool = False
    resume_wait_timeout_seconds: Optional[int] = None
    review_mode: bool = False

class ApplyResponse(BaseModel):
    """Response model for apply command start."""
    task_id: str
    message: str
    websocket_url: str

@router.post("/apply", response_model=ApplyResponse)
async def apply(request: ApplyRequest):
    """
    Start apply command and return WebSocket URL for progress.

    Client should immediately connect to /ws/apply/{task_id} to receive events.
    """
    try:
        task_id = str(uuid.uuid4())

        # Store task config
        active_tasks[task_id] = {
            "request": request,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }

        logger.info("apply.task.created", task_id=task_id, profile_id=request.profile_id)

        return ApplyResponse(
            task_id=task_id,
            message=f"Apply task created for profile '{request.profile_id}'",
            websocket_url=f"/ws/apply/{task_id}"
        )
    except Exception as e:
        logger.error("apply.error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

**File: `web_ui/backend/routes/websockets.py`**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import AsyncIterator
import structlog
from pathlib import Path

from job_ai_auto_apply_ui.orchestrator import iter_apply_events
from job_ai_auto_apply_ui.profile_manager import load_profile
from .apply import active_tasks

router = APIRouter()
logger = structlog.get_logger()

@router.websocket("/apply/{task_id}")
async def websocket_apply(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time apply progress.

    Events stream format (JSON):
    {"type": "apply.start", "profile_id": "...", "timestamp": "..."}
    {"type": "item.start", "item_id": "...", "company": "...", "title": "..."}
    {"type": "item.submitted", "item_id": "...", "confirmation_id": "..."}
    {"type": "item.failed", "item_id": "...", "reason": {...}}
    {"type": "apply.end", "submitted": 5, "failed": 1}
    """
    await websocket.accept()

    try:
        # Get task config
        if task_id not in active_tasks:
            await websocket.send_json({
                "type": "error",
                "message": f"Task {task_id} not found"
            })
            await websocket.close()
            return

        task = active_tasks[task_id]
        request = task["request"]

        # Load profile
        profile = load_profile(request.profile_id)

        # Stream apply events
        logger.info("websocket.apply.start", task_id=task_id, profile_id=request.profile_id)

        async for event in iter_apply_events(
            profile=profile,
            mode="supervised" if request.supervised else "auto",
            job_id=request.job_id,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
            use_llm_locator=request.use_llm_locator,
            debug_resume_widget=request.debug_resume_widget,
            resume_wait_timeout_seconds=request.resume_wait_timeout_seconds,
            review_mode=request.review_mode
        ):
            # Forward event to WebSocket client
            await websocket.send_json(event)

        # Cleanup task
        active_tasks[task_id]["status"] = "completed"
        logger.info("websocket.apply.complete", task_id=task_id)

    except WebSocketDisconnect:
        logger.info("websocket.disconnected", task_id=task_id)
    except Exception as e:
        logger.error("websocket.error", task_id=task_id, error=str(e))
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
```

**Testing WebSocket**:

```python
# web_ui/tests/test_websockets.py

import pytest
from fastapi.testclient import TestClient
from web_ui.backend.app import app

def test_websocket_apply_stream():
    """Test WebSocket apply event streaming."""
    client = TestClient(app)

    # Create task
    response = client.post("/api/apply", json={
        "profile_id": "michael_scott_parkin_iii",
        "supervised": True
    })
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    # Connect to WebSocket
    with client.websocket_connect(f"/ws/apply/{task_id}") as websocket:
        # Receive first event
        event = websocket.receive_json()
        assert event["type"] == "apply.start"
        assert event["profile_id"] == "michael_scott_parkin_iii"

        # Receive events until completion
        while True:
            event = websocket.receive_json()
            if event["type"] == "apply.end":
                assert "submitted" in event
                assert "failed" in event
                break
```

---

## Frontend Implementation (React + shadcn)

### Phase 1: Project Setup

**Initialize Vite + React + TypeScript**:

```bash
cd web_ui
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Install shadcn/ui**:

```bash
npx shadcn-ui@latest init

# Prompts:
# - TypeScript: Yes
# - Style: Default
# - Color: Slate
# - CSS variables: Yes
# - Tailwind config: Yes
# - Import alias: @/

# Install components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add input
npx shadcn-ui@latest add select
npx shadcn-ui@latest add label
npx shadcn-ui@latest add card
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add switch
npx shadcn-ui@latest add separator
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add progress
npx shadcn-ui@latest add scroll-area
```

**Install dependencies**:

```bash
npm install axios swr date-fns
npm install -D @types/node
```

**Update `vite.config.ts`**:

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

---

### Phase 2: API Client

**File: `frontend/src/lib/api.ts`**

```ts
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Type definitions (will be generated from OpenAPI later)
export interface Profile {
  id: string
  name: string
  resume_path: string
  preferred_browser?: string
  has_experience: boolean
}

export interface DiscoverRequest {
  profile_id: string
  window: string
  cap: number
}

export interface ApplyRequest {
  profile_id: string
  job_id?: string
  supervised: boolean
  llm_provider?: string
  llm_model?: string
  use_llm_locator: boolean
  debug_resume_widget: boolean
  resume_wait_timeout_seconds?: number
  review_mode: boolean
}

export interface ApplyResponse {
  task_id: string
  message: string
  websocket_url: string
}

// API methods
export const profilesApi = {
  list: () => api.get<{ profiles: Profile[]; count: number }>('/api/profiles'),
  get: (id: string) => api.get<Profile>(`/api/profiles/${id}`),
}

export const discoverApi = {
  start: (request: DiscoverRequest) =>
    api.post('/api/discover', request),
}

export const applyApi = {
  start: (request: ApplyRequest) =>
    api.post<ApplyResponse>('/api/apply', request),
}

export default api
```

**File: `frontend/src/lib/websocket.ts`**

```ts
export type ApplyEvent =
  | { type: 'apply.start'; profile_id: string; timestamp: string }
  | { type: 'item.start'; item_id: string; company: string; title: string }
  | { type: 'item.submitted'; item_id: string; confirmation_id: string }
  | { type: 'item.failed'; item_id: string; reason: { code: string; message: string } }
  | { type: 'apply.end'; submitted: number; failed: number }
  | { type: 'error'; message: string }

export class ApplyWebSocket {
  private ws: WebSocket | null = null
  private url: string

  constructor(taskId: string) {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
    this.url = `${wsUrl}/ws/apply/${taskId}`
  }

  connect(onEvent: (event: ApplyEvent) => void, onError?: (error: Event) => void) {
    this.ws = new WebSocket(this.url)

    this.ws.onmessage = (message) => {
      const event = JSON.parse(message.data) as ApplyEvent
      onEvent(event)
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      onError?.(error)
    }

    this.ws.onclose = () => {
      console.log('WebSocket closed')
    }
  }

  disconnect() {
    this.ws?.close()
  }
}
```

---

### Phase 3: Component Implementation

#### 3.1 Profile Selector

**File: `frontend/src/components/ProfileSelector.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { profilesApi, Profile } from '@/lib/api'

interface ProfileSelectorProps {
  value: string
  onChange: (profileId: string) => void
}

export function ProfileSelector({ value, onChange }: ProfileSelectorProps) {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchProfiles = async () => {
      try {
        const response = await profilesApi.list()
        setProfiles(response.data.profiles)

        // Auto-select first profile if none selected
        if (!value && response.data.profiles.length > 0) {
          onChange(response.data.profiles[0].id)
        }
      } catch (error) {
        console.error('Failed to load profiles:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchProfiles()
  }, [])

  return (
    <div className="space-y-2">
      <Label htmlFor="profile">Profile</Label>
      <Select value={value} onValueChange={onChange} disabled={loading}>
        <SelectTrigger id="profile">
          <SelectValue placeholder={loading ? "Loading..." : "Select a profile"} />
        </SelectTrigger>
        <SelectContent>
          {profiles.map((profile) => (
            <SelectItem key={profile.id} value={profile.id}>
              {profile.name} ({profile.id})
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
```

---

#### 3.2 Discover Form

**File: `frontend/src/components/DiscoverForm.tsx`**

```tsx
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { discoverApi } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'

interface DiscoverFormProps {
  profileId: string
}

export function DiscoverForm({ profileId }: DiscoverFormProps) {
  const [window, setWindow] = useState('24h')
  const [cap, setCap] = useState(10)
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!profileId) {
      toast({
        title: 'Error',
        description: 'Please select a profile first',
        variant: 'destructive',
      })
      return
    }

    setLoading(true)

    try {
      const response = await discoverApi.start({
        profile_id: profileId,
        window,
        cap,
      })

      toast({
        title: 'Discover Started',
        description: response.data.message,
      })
    } catch (error: any) {
      toast({
        title: 'Discover Failed',
        description: error.response?.data?.detail || error.message,
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Discover Jobs</CardTitle>
        <CardDescription>
          Search for new job postings and add them to your queue
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="window">Time Window</Label>
            <Select value={window} onValueChange={setWindow}>
              <SelectTrigger id="window">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="24h">Last 24 hours</SelectItem>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="1w">Last week</SelectItem>
                <SelectItem value="1m">Last month</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="cap">Maximum Jobs</Label>
            <Input
              id="cap"
              type="number"
              min={1}
              max={100}
              value={cap}
              onChange={(e) => setCap(parseInt(e.target.value))}
            />
          </div>

          <Button type="submit" disabled={loading || !profileId}>
            {loading ? 'Discovering...' : 'Run Discover'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
```

---

#### 3.3 Apply Form with Real-time Progress

**File: `frontend/src/components/ApplyForm.tsx`**

```tsx
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { applyApi } from '@/lib/api'
import { ApplyProgress } from './ApplyProgress'
import { useToast } from '@/components/ui/use-toast'

interface ApplyFormProps {
  profileId: string
}

export function ApplyForm({ profileId }: ApplyFormProps) {
  const [jobId, setJobId] = useState('')
  const [supervised, setSupervised] = useState(true)
  const [llmProvider, setLlmProvider] = useState<string>('')
  const [llmModel, setLlmModel] = useState('')
  const [useLlmLocator, setUseLlmLocator] = useState(false)
  const [debugResumeWidget, setDebugResumeWidget] = useState(false)
  const [resumeWaitTimeout, setResumeWaitTimeout] = useState<number | undefined>()
  const [reviewMode, setReviewMode] = useState(false)

  const [taskId, setTaskId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!profileId) {
      toast({
        title: 'Error',
        description: 'Please select a profile first',
        variant: 'destructive',
      })
      return
    }

    setLoading(true)

    try {
      const response = await applyApi.start({
        profile_id: profileId,
        job_id: jobId || undefined,
        supervised,
        llm_provider: llmProvider || undefined,
        llm_model: llmModel || undefined,
        use_llm_locator: useLlmLocator,
        debug_resume_widget: debugResumeWidget,
        resume_wait_timeout_seconds: resumeWaitTimeout,
        review_mode: reviewMode,
      })

      setTaskId(response.data.task_id)

      toast({
        title: 'Apply Started',
        description: response.data.message,
      })
    } catch (error: any) {
      toast({
        title: 'Apply Failed',
        description: error.response?.data?.detail || error.message,
        variant: 'destructive',
      })
      setLoading(false)
    }
  }

  const handleComplete = () => {
    setTaskId(null)
    setLoading(false)
  }

  if (taskId) {
    return <ApplyProgress taskId={taskId} onComplete={handleComplete} />
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Apply to Jobs</CardTitle>
        <CardDescription>
          Auto-fill and submit job applications from your queue
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Basic Options */}
          <div className="space-y-2">
            <Label htmlFor="job-id">
              Job ID (optional)
              <span className="text-sm text-muted-foreground ml-2">
                Leave empty to apply to all pending jobs
              </span>
            </Label>
            <Input
              id="job-id"
              placeholder="e.g., 0199a2f3ed7602cd3b34d33dbf11"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
            />
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="supervised"
              checked={supervised}
              onCheckedChange={setSupervised}
            />
            <Label htmlFor="supervised">Supervised Mode (pause before submit)</Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="review-mode"
              checked={reviewMode}
              onCheckedChange={setReviewMode}
            />
            <Label htmlFor="review-mode">Review Mode (capture artifacts only, no submit)</Label>
          </div>

          <Separator />

          {/* Advanced Options */}
          <details className="space-y-4">
            <summary className="cursor-pointer font-medium">Advanced Options</summary>

            <div className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="llm-provider">LLM Provider (override)</Label>
                <Select value={llmProvider} onValueChange={setLlmProvider}>
                  <SelectTrigger id="llm-provider">
                    <SelectValue placeholder="Default (from .env)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openrouter">OpenRouter</SelectItem>
                    <SelectItem value="google">Google</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="llm-model">LLM Model (override)</Label>
                <Input
                  id="llm-model"
                  placeholder="e.g., google/gemini-2.0-flash-exp:free"
                  value={llmModel}
                  onChange={(e) => setLlmModel(e.target.value)}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="use-llm-locator"
                  checked={useLlmLocator}
                  onCheckedChange={setUseLlmLocator}
                />
                <Label htmlFor="use-llm-locator">Use LLM Element Locator</Label>
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="debug-resume-widget"
                  checked={debugResumeWidget}
                  onCheckedChange={setDebugResumeWidget}
                />
                <Label htmlFor="debug-resume-widget">Debug Resume Widget</Label>
              </div>

              <div className="space-y-2">
                <Label htmlFor="resume-timeout">Resume Upload Timeout (seconds)</Label>
                <Input
                  id="resume-timeout"
                  type="number"
                  min={10}
                  max={120}
                  placeholder="Default: 25"
                  value={resumeWaitTimeout || ''}
                  onChange={(e) => setResumeWaitTimeout(e.target.value ? parseInt(e.target.value) : undefined)}
                />
              </div>
            </div>
          </details>

          <Button type="submit" disabled={loading || !profileId} className="w-full">
            {loading ? 'Starting...' : 'Run Apply'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
```

---

#### 3.4 Apply Progress (Real-time WebSocket)

**File: `frontend/src/components/ApplyProgress.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ApplyWebSocket, ApplyEvent } from '@/lib/websocket'

interface ApplyProgressProps {
  taskId: string
  onComplete: () => void
}

export function ApplyProgress({ taskId, onComplete }: ApplyProgressProps) {
  const [events, setEvents] = useState<ApplyEvent[]>([])
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState<'running' | 'completed' | 'error'>('running')

  useEffect(() => {
    const ws = new ApplyWebSocket(taskId)

    ws.connect(
      (event) => {
        setEvents((prev) => [...prev, event])

        if (event.type === 'apply.end') {
          setStatus('completed')
          setProgress(100)
          setTimeout(() => onComplete(), 3000)
        } else if (event.type === 'error') {
          setStatus('error')
        } else if (event.type === 'item.submitted' || event.type === 'item.failed') {
          // Increment progress (rough estimate)
          setProgress((prev) => Math.min(prev + 10, 95))
        }
      },
      (error) => {
        console.error('WebSocket error:', error)
        setStatus('error')
      }
    )

    return () => ws.disconnect()
  }, [taskId])

  const getEventBadge = (event: ApplyEvent) => {
    switch (event.type) {
      case 'apply.start':
        return <Badge variant="outline">Started</Badge>
      case 'item.start':
        return <Badge>Processing</Badge>
      case 'item.submitted':
        return <Badge variant="success">Submitted</Badge>
      case 'item.failed':
        return <Badge variant="destructive">Failed</Badge>
      case 'apply.end':
        return <Badge variant="success">Completed</Badge>
      case 'error':
        return <Badge variant="destructive">Error</Badge>
      default:
        return null
    }
  }

  const getEventMessage = (event: ApplyEvent) => {
    switch (event.type) {
      case 'apply.start':
        return `Started applying for profile: ${event.profile_id}`
      case 'item.start':
        return `Filling application: ${event.company} - ${event.title}`
      case 'item.submitted':
        return `Submitted! Confirmation: ${event.confirmation_id}`
      case 'item.failed':
        return `Failed: ${event.reason.message}`
      case 'apply.end':
        return `Completed: ${event.submitted} submitted, ${event.failed} failed`
      case 'error':
        return `Error: ${event.message}`
      default:
        return JSON.stringify(event)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Apply Progress</CardTitle>
        <CardDescription>Real-time application status</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>
          <Progress value={progress} />
        </div>

        <ScrollArea className="h-[400px] border rounded-md p-4">
          <div className="space-y-3">
            {events.map((event, index) => (
              <div key={index} className="flex items-start gap-3">
                {getEventBadge(event)}
                <span className="text-sm flex-1">{getEventMessage(event)}</span>
              </div>
            ))}
          </div>
        </ScrollArea>

        {status === 'completed' && (
          <p className="text-sm text-muted-foreground">
            Apply completed! Returning to form in 3 seconds...
          </p>
        )}
      </CardContent>
    </Card>
  )
}
```

---

#### 3.5 Main App Layout

**File: `frontend/src/App.tsx`**

```tsx
import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ProfileSelector } from '@/components/ProfileSelector'
import { DiscoverForm } from '@/components/DiscoverForm'
import { ApplyForm } from '@/components/ApplyForm'
import { Toaster } from '@/components/ui/toaster'

function App() {
  const [profileId, setProfileId] = useState('')

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <header className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Job Auto Apply</h1>
        <p className="text-muted-foreground">
          Discover and apply to jobs automatically
        </p>
      </header>

      <div className="mb-6">
        <ProfileSelector value={profileId} onChange={setProfileId} />
      </div>

      <Tabs defaultValue="discover" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="discover">Discover</TabsTrigger>
          <TabsTrigger value="apply">Apply</TabsTrigger>
        </TabsList>

        <TabsContent value="discover">
          <DiscoverForm profileId={profileId} />
        </TabsContent>

        <TabsContent value="apply">
          <ApplyForm profileId={profileId} />
        </TabsContent>
      </Tabs>

      <Toaster />
    </div>
  )
}

export default App
```

---

## Testing Strategy

### Backend Tests

**Test Structure**:
```
web_ui/tests/
├── conftest.py                 # Pytest fixtures
├── test_routes_profiles.py     # Profile endpoints
├── test_routes_discover.py     # Discover endpoint
├── test_routes_apply.py        # Apply endpoint
└── test_websockets.py          # WebSocket streaming
```

**File: `web_ui/tests/conftest.py`**

```python
import pytest
from httpx import AsyncClient
from web_ui.backend.app import app

@pytest.fixture
async def async_client():
    """Async HTTP client for testing FastAPI."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def test_profile_id():
    """Test profile ID that exists in profiles/ directory."""
    return "michael_scott_parkin_iii"
```

**Coverage Goals**:
- ✅ Profile listing and retrieval
- ✅ Discover endpoint validation and execution
- ✅ Apply endpoint task creation
- ✅ WebSocket event streaming
- ✅ Error handling (404, 422, 500)
- ✅ Path consistency (queues, profiles dirs)

---

### Frontend Tests

**Test Structure**:
```
web_ui/frontend/tests/
├── components/
│   ├── ProfileSelector.test.tsx
│   ├── DiscoverForm.test.tsx
│   ├── ApplyForm.test.tsx
│   └── ApplyProgress.test.tsx
└── e2e/
    ├── discover-flow.spec.ts
    └── apply-flow.spec.ts
```

**Install test dependencies**:

```bash
cd web_ui/frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom
npm install -D @playwright/test
```

**Component Test Example (`DiscoverForm.test.tsx`)**:

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { DiscoverForm } from '@/components/DiscoverForm'
import * as api from '@/lib/api'

vi.mock('@/lib/api')

describe('DiscoverForm', () => {
  it('renders form with default values', () => {
    render(<DiscoverForm profileId="test" />)

    expect(screen.getByLabelText(/time window/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/maximum jobs/i)).toHaveValue(10)
    expect(screen.getByRole('button', { name: /run discover/i })).toBeEnabled()
  })

  it('submits discover request with correct params', async () => {
    const mockStart = vi.spyOn(api.discoverApi, 'start').mockResolvedValue({
      data: { success: true, message: 'Started' }
    })

    render(<DiscoverForm profileId="test" />)

    fireEvent.change(screen.getByLabelText(/maximum jobs/i), { target: { value: '20' } })
    fireEvent.click(screen.getByRole('button', { name: /run discover/i }))

    await waitFor(() => {
      expect(mockStart).toHaveBeenCalledWith({
        profile_id: 'test',
        window: '24h',
        cap: 20,
      })
    })
  })

  it('shows error when profile not selected', async () => {
    render(<DiscoverForm profileId="" />)

    fireEvent.click(screen.getByRole('button', { name: /run discover/i }))

    await waitFor(() => {
      expect(screen.getByText(/please select a profile/i)).toBeInTheDocument()
    })
  })
})
```

**E2E Test Example (`discover-flow.spec.ts`)**:

```ts
import { test, expect } from '@playwright/test'

test.describe('Discover Flow', () => {
  test('complete discover workflow', async ({ page }) => {
    // Navigate to app
    await page.goto('http://localhost:5173')

    // Select profile
    await page.click('button[id="profile"]')
    await page.click('text=michael_scott_parkin_iii')

    // Navigate to discover tab
    await page.click('text=Discover')

    // Fill form
    await page.selectOption('select[id="window"]', '24h')
    await page.fill('input[id="cap"]', '5')

    // Submit
    await page.click('button:has-text("Run Discover")')

    // Verify toast notification
    await expect(page.locator('text=Discover Started')).toBeVisible()
  })
})
```

**Test Coverage Goals**:
- ✅ Component rendering
- ✅ Form validation
- ✅ API integration (mocked)
- ✅ User interactions (clicks, inputs)
- ✅ Error handling and toast notifications
- ✅ E2E flows (discover, apply)

---

## Implementation Phases

### Phase 1: Backend Foundation (Week 1)

**Tasks**:
1. Create `web_ui/backend/` structure
2. Implement FastAPI app with CORS
3. Add `/api/profiles` endpoints
4. Add `/api/discover` endpoint
5. Write backend tests (profiles, discover)
6. Update `pyproject.toml` with dependencies
7. Add `auto-apply-web` CLI command
8. Document backend API (README)

**Validation**:
- ✅ `auto-apply-web` starts server on port 8000
- ✅ `/health` endpoint returns 200
- ✅ `/api/profiles` returns valid profile list
- ✅ `/api/discover` starts background task
- ✅ All backend tests pass

---

### Phase 2: Apply + WebSocket (Week 2)

**Tasks**:
1. Implement `/api/apply` endpoint (task creation)
2. Implement `/ws/apply/{task_id}` WebSocket
3. Stream `iter_apply_events()` to WebSocket clients
4. Write WebSocket tests
5. Test with CLI apply command

**Validation**:
- ✅ POST `/api/apply` returns task ID
- ✅ WebSocket connects and streams events
- ✅ Events match CLI `--json` output format
- ✅ WebSocket closes on completion
- ✅ Error handling works (invalid profile, etc.)

---

### Phase 3: Frontend Setup (Week 3)

**Tasks**:
1. Initialize Vite + React + TypeScript
2. Install and configure shadcn/ui
3. Create API client (`lib/api.ts`, `lib/websocket.ts`)
4. Implement `ProfileSelector` component
5. Set up Vite proxy for `/api` and `/ws`

**Validation**:
- ✅ Frontend runs on port 5173
- ✅ Vite proxy forwards requests to backend
- ✅ ProfileSelector fetches and displays profiles
- ✅ No CORS errors

---

### Phase 4: Discover Form (Week 4)

**Tasks**:
1. Implement `DiscoverForm` component
2. Add form validation
3. Integrate with `/api/discover` endpoint
4. Add toast notifications
5. Write component tests
6. Write E2E test for discover flow

**Validation**:
- ✅ Form renders with default values
- ✅ Submitting triggers API call
- ✅ Toast shows success/error messages
- ✅ Component tests pass
- ✅ E2E test completes discover flow

---

### Phase 5: Apply Form + Progress (Week 5)

**Tasks**:
1. Implement `ApplyForm` component with all flags
2. Implement `ApplyProgress` component
3. Integrate WebSocket for real-time updates
4. Add progress bar and event log
5. Handle WebSocket errors and reconnection
6. Write component tests
7. Write E2E test for apply flow

**Validation**:
- ✅ Apply form shows all CLI flags
- ✅ Submitting creates task and opens WebSocket
- ✅ Progress updates in real-time
- ✅ Events display correctly
- ✅ Completion returns to form
- ✅ E2E test completes apply flow

---

### Phase 6: Polish & Documentation (Week 6)

**Tasks**:
1. Add loading states and error boundaries
2. Improve UI/UX (spacing, colors, responsiveness)
3. Add dark mode toggle
4. Update README with web UI instructions
5. Create developer documentation
6. Record demo video
7. Deploy to production (optional)

**Validation**:
- ✅ All features work end-to-end
- ✅ UI looks professional
- ✅ Documentation complete
- ✅ All tests pass (backend + frontend)

---

## Development Workflow

### Running Both Services

**Option 1: Separate Terminals**

```bash
# Terminal 1: Backend
source .venv/bin/activate
auto-apply-web

# Terminal 2: Frontend
cd web_ui/frontend
npm run dev
```

**Option 2: Concurrently (Root Package.json)**

```bash
# Install concurrently at root
npm init -y
npm install --save-dev concurrently

# Add scripts to package.json
{
  "scripts": {
    "dev:backend": "source .venv/bin/activate && auto-apply-web",
    "dev:frontend": "cd web_ui/frontend && npm run dev",
    "dev": "concurrently \"npm:dev:backend\" \"npm:dev:frontend\"",
    "test:backend": "pytest web_ui/tests -v",
    "test:frontend": "cd web_ui/frontend && npm test",
    "test": "npm run test:backend && npm run test:frontend"
  }
}

# Run both
npm run dev
```

---

### Testing Workflow

**Backend Tests**:
```bash
pytest web_ui/tests -v --cov=web_ui/backend
```

**Frontend Component Tests**:
```bash
cd web_ui/frontend
npm test
```

**Frontend E2E Tests**:
```bash
cd web_ui/frontend
npx playwright test
```

---

## Acceptance Criteria

### Backend

- [ ] FastAPI app starts with `auto-apply-web` command
- [ ] `/api/profiles` returns list of profiles from `profiles/` directory
- [ ] `/api/discover` triggers discover command with correct params
- [ ] `/api/apply` creates task and returns WebSocket URL
- [ ] WebSocket streams apply events in real-time
- [ ] All endpoints handle errors gracefully (404, 422, 500)
- [ ] Backend tests achieve >80% coverage
- [ ] Paths match CLI (`data/queues/`, `profiles/`)

### Frontend

- [ ] Profile selector populates from backend
- [ ] Discover form validates and submits
- [ ] Apply form shows all CLI flags
- [ ] Apply progress streams events via WebSocket
- [ ] Toast notifications for success/error
- [ ] UI is responsive (desktop and mobile)
- [ ] Component tests cover all interactions
- [ ] E2E tests validate complete workflows

### Integration

- [ ] Web UI and CLI use identical queue files
- [ ] Discover from web UI creates items visible in CLI
- [ ] Apply from web UI updates queue status correctly
- [ ] No code changes to existing CLI modules

---

## Next Steps

1. Review this plan and confirm approach
2. Create tasks in GitHub Issues or project board
3. Start Phase 1: Backend Foundation
4. Iterate with testing and feedback

---

**Questions? Concerns? Suggestions?**

This plan is comprehensive but flexible. If you'd like to adjust scope, technologies, or timeline, please let me know!
