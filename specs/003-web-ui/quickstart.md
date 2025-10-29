# Quickstart: Web UI Dashboard for Job-AI-Auto-Apply

**Version**: 1.0 | **Date**: 2025-10-28

## Overview

This guide walks you through setting up and running the Web UI dashboard for the Job-AI-Auto-Apply automation tool. The Web UI consists of:

- **Frontend**: React 18 + TypeScript + Vite + shadcn/ui running on `localhost:5173`
- **Backend**: FastAPI (Python) wrapping the existing CLI, running on `localhost:5000`

The two services run independently and communicate via REST API.

---

## Prerequisites

Before starting, ensure you have:

### System Requirements
- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend)
- **npm 9+** (comes with Node.js)
- **Virtual environment support** (venv or similar)

### Existing Setup
- Job-AI-Auto-Apply CLI already installed and working
- At least one profile configured in `profiles/` directory
- Resume file in place and referenced in profile
- Required environment variables (.env) prepared

### Verify Prerequisites

```bash
# Check Python version
python --version  # Should be 3.11 or higher

# Check Node.js and npm
node --version   # Should be 18 or higher
npm --version    # Should be 9 or higher

# Verify existing CLI works
auto-apply --help
```

---

## Quick Start (5 minutes)

### 1. Backend Setup

```bash
# Navigate to backend directory
cd web_ui/backend

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# On Unix/macOS:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys and settings
# At minimum, set:
# - LLM_PROVIDER (openrouter or google)
# - LLM_MODEL (model identifier)
# - OPENROUTER_API_KEY or GOOGLE_API_KEY

# Start backend server
python src/app.py
```

Backend will start on `http://localhost:5000`

**Expected Output**:
```
INFO:     Uvicorn running on http://127.0.0.1:5000 (Press CTRL+C to quit)
INFO:     Application startup complete
```

### 2. Frontend Setup (in a new terminal)

```bash
# Navigate to frontend directory
cd web_ui/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will start on `http://localhost:5173`

**Expected Output**:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
```

### 3. Access the Dashboard

Open your browser and navigate to:

```
http://localhost:5173
```

You should see the dashboard with:
- Sidebar with profile selector
- Job queue list (if you've run discovery before)
- Navigation to Discover, Profiles, Settings, Artifacts pages

---

## Detailed Setup

### Backend Setup (Detailed)

#### Step 1: Navigate to Backend

```bash
cd web_ui/backend
```

#### Step 2: Create Virtual Environment

```bash
python -m venv .venv

# Activate it
# Unix/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Verify activation (should show (.venv) prefix in terminal)
```

#### Step 3: Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
```

#### Step 4: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env file with your settings
# Required:
# - LLM_PROVIDER=openrouter (or google)
# - LLM_MODEL=openrouter/gpt-4-turbo (or Google model)
# - OPENROUTER_API_KEY=sk-xxxxx (if using OpenRouter)
# - GOOGLE_API_KEY=xxxxx (if using Google)

# Optional but recommended:
# - AUTO_APPLY_PROFILES_DIR=../../../profiles (path to CLI profiles)
# - AUTO_APPLY_ARTIFACTS_DIR=../../data/artifacts (for diagnostics)
# - AUTO_APPLY_DIAGNOSTICS=1 (for testing, capture screenshots)
```

#### Step 5: Start Backend

```bash
python src/app.py
```

The server will:
- Load FastAPI application
- Initialize services (queue, profile, CLI wrapper)
- Start listening on `http://localhost:5000`

**Verify it's working**:
```bash
# In another terminal
curl http://localhost:5000/api/v1/profiles/
```

Should return JSON array of profiles (may be empty).

---

### Frontend Setup (Detailed)

#### Step 1: Navigate to Frontend

```bash
cd web_ui/frontend
```

#### Step 2: Install Dependencies

```bash
npm install

# Verify installation
npm list react
```

#### Step 3: Start Development Server

```bash
npm run dev
```

The server will:
- Start Vite development server
- Enable Hot Module Reloading (HMR)
- Display local and network URLs

#### Step 4: Access Dashboard

Open browser to `http://localhost:5173`

If you see a connection error:
- Verify backend is running on `http://localhost:5000`
- Check CORS configuration in backend
- Check browser console for detailed error

---

## Environment Variables

### Backend (.env)

**LLM Configuration**:
```env
LLM_PROVIDER=openrouter
LLM_MODEL=openrouter/gpt-4-turbo
OPENROUTER_API_KEY=sk-xxxxx
LLM_TEMPERATURE=0.0
LLM_TIMEOUT_SECONDS=30
```

**Behavior Settings**:
```env
DWELL_SECONDS=0.8
JITTER_SECONDS=0.4
MAX_TABS=3
RETRIES=2
DISCOVERY_WINDOW_HOURS=24
DISCOVERY_CAP=10
```

**Resume Upload**:
```env
AUTO_APPLY_USE_LLM_LOCATOR=0
AUTO_APPLY_DEBUG_RESUME_WIDGET=0
AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS=25
```

**Diagnostics**:
```env
AUTO_APPLY_DIAGNOSTICS=0
AUTO_APPLY_CAPTURE_VIDEO=0
AUTO_APPLY_CAPTURE_HAR=0
AUTO_APPLY_ARTIFACTS_DIR=data/artifacts
```

**Paths** (relative to backend directory):
```env
AUTO_APPLY_PROFILES_DIR=../../../profiles
AUTO_APPLY_QUEUES_DIR=../../data/queues
```

### Frontend (.env)

(Created automatically by Vite if needed)

```env
VITE_API_BASE_URL=http://localhost:5000
```

---

## Sample Workflow

### 1. Discover Jobs

```
1. Open http://localhost:5173
2. Select profile from sidebar dropdown
3. Click "Discover Jobs" button
4. In modal:
   - Set Search Window: "24h"
   - Set Job Cap: "10"
   - Click "Discover" button
5. Watch progress indicator
6. Jobs appear in queue as they're discovered
```

### 2. View Job Details

```
1. Click a job from the queue
2. Job detail page shows:
   - Title, Company, Location
   - Work model, Employment type
   - Full job posting (expandable)
   - Extracted metadata
3. Click "Apply Now" to proceed
```

### 3. Apply to Job

```
1. Click "Apply Now" button
2. In modal/panel:
   - Mode: "Supervised" (default)
   - Advanced options: (collapsed by default)
3. Click "Apply" button
4. Watch real-time logs
5. Browser automation runs with supervision
6. Status updates to "Submitted" or "Failed"
7. Artifacts available (screenshots, logs)
```

### 4. Manage Settings

```
1. Click "Settings" in sidebar
2. Edit environment variables:
   - LLM provider and model
   - Timeout settings
   - Diagnostic flags
3. Click "Save Changes"
4. Settings persisted to .env
5. Changes apply to next operation
```

### 5. View Artifacts

```
1. Navigate to Artifacts page
2. Select profile and date range
3. View screenshots and logs
4. Download if needed
```

---

## Testing

### Backend Tests

```bash
cd web_ui/backend

# Run all tests
pytest

# Run specific test suite
pytest tests/contract/      # Contract tests
pytest tests/integration/   # Integration tests
pytest tests/unit/          # Unit tests

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src
```

### Frontend Tests

```bash
cd web_ui/frontend

# Run unit tests
npm test

# Run with coverage
npm test -- --coverage

# Run E2E tests (Cypress)
npm run test:e2e
```

### Integration Testing

```bash
# Test backend API directly
curl http://localhost:5000/api/v1/profiles/

# Test with profile ID
curl http://localhost:5000/api/v1/profiles/your_profile_id

# Test job queue
curl 'http://localhost:5000/api/v1/jobs/?profile=your_profile_id'
```

---

## Development Workflow

### Hot Reload

Both frontend and backend support auto-reload on file changes:

**Frontend (Vite HMR)**:
- Edit `.tsx`, `.ts`, `.css` files
- Browser automatically refreshes
- Component state may be preserved

**Backend (FastAPI reload)**:
- Backend runs with `--reload` flag
- Edit `.py` files
- Server automatically restarts
- Logs show reload confirmation

### Debugging

**Frontend**:
- Use browser DevTools (F12)
- React DevTools extension recommended
- Network tab shows API requests
- Console shows TypeScript errors

**Backend**:
- Check stdout for logs
- Enable debug logging: `import logging; logging.basicConfig(level=logging.DEBUG)`
- Use FastAPI `/docs` endpoint at `http://localhost:5000/docs` for interactive API testing

### Code Quality

**Frontend**:
```bash
cd web_ui/frontend

# Lint
npm run lint

# Type check
npm run typecheck

# Format
npm run format
```

**Backend**:
```bash
cd web_ui/backend

# Lint
ruff check .

# Type check
mypy src

# Format
black .
```

---

## Troubleshooting

### Backend Won't Start

**Error: "Address already in use"**
```bash
# Port 5000 is taken. Find and kill the process:
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows

# Or change port in src/app.py
```

**Error: "ModuleNotFoundError: No module named 'fastapi'"**
```bash
# Virtual environment not activated or dependencies not installed
source .venv/bin/activate  # Activate venv
pip install -r requirements.txt
```

**Error: "Could not find profile directory"**
```bash
# Check AUTO_APPLY_PROFILES_DIR in .env
# Should point to absolute or relative path to profiles/
# Default: ../../../profiles (relative to web_ui/backend/)
```

### Frontend Won't Connect to Backend

**Error: "CORS policy violation" or "Failed to fetch"**
```bash
# Backend not running. Check:
1. Backend is running on http://localhost:5000
2. Try: curl http://localhost:5000/api/v1/profiles/
3. Check CORS configuration in src/app.py

# If backend is on different host, update:
# web_ui/frontend/.env
VITE_API_BASE_URL=http://localhost:5000
```

**Error: "Connection refused"**
```bash
# Verify ports are correct
# Frontend: http://localhost:5173
# Backend: http://localhost:5000

# Check firewall settings
# Try from different terminal: curl http://localhost:5000/api/v1/profiles/
```

### Profile Not Found

**Error: "Profile 'my_profile' not found"**
```bash
# Check profile files exist
ls profiles/my_profile.toml

# Verify AUTO_APPLY_PROFILES_DIR in backend .env points to correct location
# List profiles via API
curl http://localhost:5000/api/v1/profiles/ | jq

# Create test profile if needed
# Copy example: cp profiles/example.toml profiles/test.toml
# Edit with your details
```

### Application Crashes

**Check Logs**:
```bash
# Backend: look at stdout/stderr where you ran python src/app.py
# Frontend: check browser console (F12 > Console tab)

# Enable verbose logging
# Backend: set LOG_LEVEL=DEBUG in .env
# Frontend: npm run dev -- --debug
```

---

## Next Steps

### 1. Discover Jobs

Run your first discovery to populate the queue:

```bash
# Via CLI (if preferred):
auto-apply discover --profile your_profile_id --window 24h --cap 5

# Or via Web UI:
# Open dashboard → Click "Discover Jobs" → Configure options → Click "Discover"
```

### 2. Test Application

Apply to a test job to verify the system works end-to-end:

```bash
# Via Web UI (recommended for first test):
# Open dashboard → Select job → Click "Apply Now" → Configure → Click "Apply"
# Watch real-time logs and browser automation

# Or via CLI:
# auto-apply apply --profile your_profile_id --id <job_id> --supervised
```

### 3. Configure Settings

Customize LLM settings and behavior:

```
1. Open Web UI Settings page
2. Configure LLM provider and model
3. Adjust timeouts and behavior flags
4. Save and verify in next discovery/apply run
```

### 4. Monitor Artifacts

Check captured artifacts after applications:

```
1. Open Artifacts page
2. Select profile
3. View screenshots and logs
4. Download if needed for debugging
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Browser (localhost:5173)           │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │     React Components (TypeScript)             │  │
│  │  - Dashboard, JobDetail, ProfileEdit, etc.    │  │
│  │                                               │  │
│  │  ┌────────────────────────────────────────┐  │  │
│  │  │  API Client (api.ts)                   │  │  │
│  │  │  - fetch wrapper, error handling       │  │  │
│  │  │  - Auto-polling for queue updates      │  │  │
│  │  └────────────────────────────────────────┘  │  │
│  │                                               │  │
│  │  ┌────────────────────────────────────────┐  │  │
│  │  │  Storage (localStorage, state)          │  │  │
│  │  │  - UI state, cached options             │  │  │
│  │  └────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
              │
         REST API (JSON)
              │
              ↓
┌─────────────────────────────────────────────────────┐
│          FastAPI Server (localhost:5000)            │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │     FastAPI Routes (v1/)                     │  │
│  │  - /profiles/, /jobs/, /discover/, /apply/   │  │
│  │  - /artifacts/, /settings/                   │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │     Services Layer                           │  │
│  │  - profile_service: Load/save TOML           │  │
│  │  - queue_service: Manage ApplicationItems    │  │
│  │  - cli_service: Execute CLI (subprocess)     │  │
│  │  - artifact_service: Serve files             │  │
│  │  - settings_service: Manage .env             │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │     File Storage                             │  │
│  │  - profiles/*.toml                           │  │
│  │  - data/queues/<profile>.json                │  │
│  │  - data/run-config/<profile>.json            │  │
│  │  - data/artifacts/<profile>/*                │  │
│  │  - .env (settings)                           │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │     CLI Integration                          │  │
│  │  - Wraps auto-apply CLI commands             │  │
│  │  - Streams JSON output                       │  │
│  │  - Captures exit codes                       │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Performance Notes

### Initial Load
- First visit may take 2-3 seconds (Vite downloads dependencies)
- Subsequent reloads are instant (cached)

### Queue Refresh
- Polls every 2 seconds
- Shows up to 50 jobs per page (pagination)
- Scrolling loads more (virtual scrolling)

### Application Progress
- Logs update every 0.5-1 second
- Real-time supervision visible in browser
- Large queues (500+ jobs) remain responsive

### File Operations
- Profile saves complete within 1 second
- Settings updates within 1-2 seconds
- Artifacts load within 5 seconds

---

## Support & Debugging

### Enable Debug Logging

**Backend**:
```python
# In src/app.py, uncomment or add:
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

**Frontend**:
```typescript
// In src/services/api.ts or components, add:
console.debug('API request:', { url, method, body });
console.debug('API response:', data);
```

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Profile not found" | Verify profile TOML exists in `profiles/` |
| Queue is empty | Run discovery first via CLI or UI |
| Logs not updating | Check backend is running, connection is active |
| Settings not saving | Check .env file permissions, path exists |
| Artifacts not visible | Enable diagnostics flag in settings |
| Slow page load | Check for large artifacts, clear browser cache |

---

## Additional Resources

- **Backend API Docs**: http://localhost:5000/docs (Swagger UI)
- **Spec Documentation**: `specs/003-web-ui/`
  - `spec.md` - Feature requirements
  - `plan.md` - Implementation plan
  - `data-model.md` - Data structures
  - `contracts/api-contracts.md` - API endpoints
- **Existing CLI Docs**: See main project README
- **Code Structure**: `web_ui/` directory organization

---
