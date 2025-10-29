# Data Model: Web UI Dashboard for Job-AI-Auto-Apply

**Date**: 2025-10-28 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Overview

The Web UI data model extends the existing CLI data structures with new entities for managing user-selected options and runtime configuration. This document defines all entities, their attributes, validation rules, and relationships.

---

## Entities

### 1. Profile

**Purpose**: Represents a job seeker identity with associated application history and configuration.

**Storage**: TOML file in `profiles/<id>.toml` (existing CLI entity)

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | Unique profile identifier (referenced in queue files and URLs) |
| name | string | Yes | Full name of job seeker |
| email | string | Yes | Primary email address |
| phone | string | No | Phone number (E.164 format preferred) |
| location | string | No | City, State or region |
| resume_path | string | Yes | Path to resume PDF (relative or absolute) |
| preferred_browser | string | No | chrome, chromium, or msedge (Playwright channel) |
| user_data_dir | string | No | Path to persistent browser profile (cookies, auth state) |
| defaults | object | No | Default form values (name, email, phone, location, URLs) |
| keywords | object | No | Job search preferences (roles, tech_stack) |
| experience | array | No | Array of work history objects with company, role, dates, highlights, tech_stack, metrics |
| prompts | object | No | LLM prompt templates for cover letters, experience selection, etc. |

**Validation Rules**:
- `id`: non-empty, alphanumeric + underscore only, unique per profile directory
- `name`: non-empty, max 200 characters
- `email`: valid email format
- `phone`: if present, must be valid format (E.164 or common formats)
- `resume_path`: file must exist and be readable
- `preferred_browser`: if present, must be one of: chrome, chromium, msedge
- `defaults.email`: must match email field (if provided)
- `experience[].company`: non-empty string
- `experience[].role`: non-empty string

**Relationships**:
- Profile owns one ApplicationQueue (stored in `data/queues/<profile>.json`)
- Profile owns one RunConfiguration (stored in `data/run-config/<profile>.json`)
- Profile has zero or more Settings overrides (in .env, globally scoped but profile context available)

---

### 2. ApplicationItem (Job in Queue)

**Purpose**: Represents a discovered job posting and its application lifecycle.

**Storage**: JSON array in `data/queues/<profile>.json` (existing CLI entity)

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | Yes | ULID (unique, sortable timestamp-based ID) |
| url | string | Yes | Full URL to job posting on jobs.lever.co |
| company | string | Yes | Company name extracted from posting |
| title | string | Yes | Job title extracted from posting |
| status | enum | Yes | NEW, IN_PROGRESS, SUBMITTED, FAILED, CAPTCHA_BLOCKED |
| details | object | No | JobDetails object (null until extraction completes) |
| artifacts | object | No | Artifacts object with file paths and metadata |
| reason | object | No | Failure reason (code, message) if status is FAILED |
| date_discovered | datetime | Yes | ISO 8601 timestamp when job was discovered |
| date_applied | datetime | No | ISO 8601 timestamp when application was submitted |
| source_query | string | No | Google search query that found this job |
| source_rank | integer | No | Rank in search results (1-based) |
| hash | string | Yes | SHA256(url + company + title) for deduplication |

**Status Transitions**:
```
NEW → IN_PROGRESS → SUBMITTED (success)
NEW → IN_PROGRESS → FAILED (error)
NEW → IN_PROGRESS → CAPTCHA_BLOCKED (CAPTCHA detected)
CAPTCHA_BLOCKED → IN_PROGRESS (resumed by user)
```

**Validation Rules**:
- `id`: ULID format (128-bit unique identifier)
- `url`: must be valid HTTPS URL on jobs.lever.co domain
- `company`: non-empty, max 200 characters
- `title`: non-empty, max 500 characters
- `status`: must be one of enum values
- `date_discovered`: valid ISO 8601 datetime
- `date_applied`: valid ISO 8601 datetime if present
- `hash`: 64-character hexadecimal SHA256 hash
- `source_rank`: positive integer if present

**Relationships**:
- ApplicationItem belongs to one Profile (via queue file location)
- ApplicationItem has optional associated JobDetails
- ApplicationItem has optional associated Artifacts
- ApplicationItem has optional failure Reason

---

### 3. JobDetails

**Purpose**: Extracted information from job posting (displayed on detail page).

**Storage**: Nested object within ApplicationItem.details

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| location | string | No | Job location (e.g., "São Paulo, Portugal" or "Remote") |
| work_model | string | No | Work arrangement (Remote, On-site, Hybrid) |
| employment_type | string | No | Type of employment (Full-time, Part-time, Contract, Temporary) |
| department | string | No | Department or team (e.g., "Engineering", "Sales") |
| compensation | object | No | Salary/benefits information (min, max, currency, bonus, equity) |
| posting_text | string | No | Full job description/posting body |
| tech_tags | array | No | Technology keywords extracted from posting (e.g., ["React", "TypeScript"]) |
| apply_url | string | No | Direct URL to apply form (may differ from main posting URL) |
| posting_date | datetime | No | Date when job was posted |
| company_description | string | No | Brief company overview if available |
| qualifications | array | No | Required qualifications extracted from posting |

**Extraction Status**:
- All fields are nullable until extraction completes
- Extraction may be partial (some fields present, others null)
- Normalization is best-effort (free-form strings preferred over fixed enums)

**Validation Rules**:
- `location`: if present, non-empty string
- `work_model`: if present, one of suggested values: Remote, On-site, Hybrid (free-form accepted)
- `employment_type`: if present, one of suggested values: Full-time, Part-time, Contract, Temporary (free-form accepted)
- `department`: if present, non-empty string
- `posting_date`: valid ISO 8601 datetime if present
- `apply_url`: valid HTTPS URL if present
- `tech_tags`: array of non-empty strings
- `compensation.min`: numeric if present
- `compensation.max`: numeric if present; must be >= min if both present

**Relationships**:
- JobDetails belongs to one ApplicationItem
- JobDetails is nullable (not extracted until optional browser extraction completes)

---

### 4. Artifacts

**Purpose**: Captured files and data from the application process.

**Storage**: Nested object within ApplicationItem.artifacts; files stored in `data/artifacts/<profile>/`

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| screenshot_path | string | No | Path to pre-submit form screenshot |
| dom_snapshot_path | string | No | Path to DOM HTML snapshot at submission |
| video_path | string | No | Path to browser recording (if diagnostics enabled) |
| har_path | string | No | Path to HAR (HTTP Archive) network recording |
| confirmation_text | string | No | Text extracted from submission confirmation page |
| confirmation_id | string | No | Application ID or confirmation number from posting |
| paths | array | No | Additional artifact file paths (logs, etc.) |
| capture_timestamp | datetime | No | ISO 8601 timestamp when artifacts were captured |

**Artifact File Organization**:
```
data/artifacts/
└── <profile_id>/
    ├── <job_id>_screenshot.png
    ├── <job_id>_dom.html
    ├── <job_id>_recording.webm
    ├── <job_id>_network.har
    ├── <job_id>_confirmation.txt
    └── <job_id>_logs.txt
```

**Validation Rules**:
- `screenshot_path`: if present, file must exist and be readable PNG
- `dom_snapshot_path`: if present, file must exist and be readable HTML
- `video_path`: if present, file must exist and be readable WebM/MP4
- `har_path`: if present, file must exist and be valid JSON HAR
- `confirmation_text`: if present, non-empty string
- `confirmation_id`: if present, non-empty string
- `paths`: array of valid file paths
- `capture_timestamp`: valid ISO 8601 datetime if present

**Relationships**:
- Artifacts belongs to one ApplicationItem
- Artifacts is optional (may be empty or null if no diagnostics captured)

---

### 5. RunConfiguration (NEW for Web UI)

**Purpose**: User-selected options for discover or apply operations, persisted per profile for convenience.

**Storage**: JSON file in `data/run-config/<profile>.json`

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| profile_id | string | Yes | Reference to profile being configured |
| operation_type | enum | Yes | discover, apply_single, apply_bulk |
| search_window | string | No | Time filter for job discovery (e.g., "24h", "7d", "30d") |
| job_cap | integer | No | Maximum number of jobs to discover in one session |
| custom_query | string | No | Custom search query to append to default discovery |
| mode | enum | No | supervised (default), auto (run without supervision) |
| review_mode | boolean | No | Pause after form analysis before submitting (supervised mode only) |
| llm_provider_override | string | No | Override default LLM provider (openrouter, google, etc.) |
| llm_model_override | string | No | Override default LLM model (e.g., gpt-4-turbo, claude-3-opus) |
| use_llm_locator | boolean | No | Enable LLM-powered element finding for form fields |
| debug_resume_widget | boolean | No | Capture DOM snapshots on resume upload failures |
| resume_wait_timeout | integer | No | Timeout in seconds for resume upload detection |
| audit_after_submit | boolean | No | Pause after form submission for visual confirmation |
| save_logs | boolean | No | Save detailed execution logs to file |
| logs_dir | string | No | Directory to save logs (relative or absolute path) |
| max_concurrent | integer | No | Maximum concurrent applications in bulk mode |
| stop_on_failure | boolean | No | Stop bulk apply if any application fails |
| last_updated | datetime | Yes | ISO 8601 timestamp of last configuration change |

**Operation Type Details**:

**discover**:
- `search_window`: Required
- `job_cap`: Required
- `custom_query`: Optional
- Other fields ignored

**apply_single**:
- `mode`: Default "supervised"
- `review_mode`: Optional
- `llm_provider_override`, `llm_model_override`: Optional
- `use_llm_locator`, `debug_resume_widget`, `resume_wait_timeout`: Optional
- `audit_after_submit`: Optional
- `save_logs`, `logs_dir`: Optional
- Bulk-specific fields ignored (max_concurrent, stop_on_failure)

**apply_bulk**:
- `mode`: Default "supervised"
- `max_concurrent`: Optional, default 1
- `stop_on_failure`: Optional, default false
- `llm_provider_override`, `llm_model_override`: Optional (applies to all jobs)
- `save_logs`, `logs_dir`: Optional
- Job-specific options (review_mode, debug_resume_widget) not used in bulk

**Validation Rules**:
- `profile_id`: must reference existing profile
- `operation_type`: must be one of enum values
- `search_window`: if operation_type is "discover", must be non-empty
- `job_cap`: if operation_type is "discover", must be positive integer
- `max_concurrent`: if operation_type is "apply_bulk", must be positive integer (1-10)
- `mode`: if present, must be one of: supervised, auto
- `llm_provider_override`: if present, must be valid provider identifier
- `llm_model_override`: if present, must be valid model identifier
- `resume_wait_timeout`: if present, must be positive integer (seconds)
- `logs_dir`: if present, directory must exist or be creatable
- `last_updated`: valid ISO 8601 datetime

**Relationships**:
- RunConfiguration belongs to one Profile
- One RunConfiguration per profile (identified by profile_id)
- Referenced by discovery and apply API endpoints to restore last-used options

---

### 6. Settings / Environment

**Purpose**: Application configuration persisted to .env file.

**Storage**: `web_ui/backend/.env` file (or environment variables)

**Fields**:

| Field | Type | Category | Required | Description |
|-------|------|----------|----------|-------------|
| LLM_PROVIDER | string | llm | Yes | LLM provider: openrouter, google |
| LLM_MODEL | string | llm | Yes | Model identifier for chosen provider |
| OPENROUTER_API_KEY | string | llm | No | OpenRouter API key (if provider is openrouter) |
| GOOGLE_API_KEY | string | llm | No | Google API key (if provider is google) |
| LLM_TEMPERATURE | float | llm | No | LLM temperature (0.0-1.0, default 0.0) |
| LLM_TIMEOUT_SECONDS | integer | llm | No | API timeout in seconds (default 30) |
| DWELL_SECONDS | float | behavior | No | Delay between browser actions (default 0.8) |
| JITTER_SECONDS | float | behavior | No | Random variance in delays (default 0.4) |
| MAX_TABS | integer | behavior | No | Maximum concurrent browser tabs (default 3) |
| RETRIES | integer | behavior | No | Max retries on transient failures (default 2) |
| DISCOVERY_WINDOW_HOURS | integer | behavior | No | Default discovery time window (default 24) |
| DISCOVERY_CAP | integer | behavior | No | Default max jobs to discover (default 10) |
| AUTO_APPLY_USE_LLM_LOCATOR | boolean | resume_upload | No | Enable LLM element finding |
| AUTO_APPLY_DEBUG_RESUME_WIDGET | boolean | resume_upload | No | Capture widget snapshots on failure |
| AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS | integer | resume_upload | No | Resume upload timeout (default 25) |
| BROWSER_LOCALE | string | stealth | No | Browser locale (default en-US) |
| BROWSER_TIMEZONE | string | stealth | No | Browser timezone (default America/Los_Angeles) |
| BROWSER_VIEWPORT_WIDTH | integer | stealth | No | Viewport width in pixels (default 1280) |
| BROWSER_VIEWPORT_HEIGHT | integer | stealth | No | Viewport height in pixels (default 800) |
| AUTO_APPLY_DISABLE_DEFAULT_EXTENSIONS | boolean | stealth | No | Launch browser without extensions |
| ALLOWED_DOMAINS | string | networking | No | Comma-separated domain allowlist (default google.*,jobs.lever.co) |
| USER_AGENT | string | networking | No | Custom browser user agent string |
| PROXY_URL | string | networking | No | HTTP/HTTPS proxy URL |
| AUTO_APPLY_DIAGNOSTICS | boolean | diagnostics | No | Enable all artifact capture |
| AUTO_APPLY_CAPTURE_VIDEO | boolean | diagnostics | No | Record browser video |
| AUTO_APPLY_CAPTURE_HAR | boolean | diagnostics | No | Record network traffic (HAR) |
| AUTO_APPLY_ARTIFACTS_DIR | string | diagnostics | No | Directory for artifacts (default data/artifacts) |

**Input Types by Field**:

| Input Type | Fields | UI Component |
|-----------|--------|--------------|
| text | LLM_PROVIDER, LLM_MODEL, BROWSER_LOCALE, BROWSER_TIMEZONE, USER_AGENT, ALLOWED_DOMAINS | Text input |
| password | OPENROUTER_API_KEY, GOOGLE_API_KEY, PROXY_URL | Password input (masked) |
| number | LLM_TEMPERATURE, DWELL_SECONDS, JITTER_SECONDS, MAX_TABS, RETRIES, DISCOVERY_WINDOW_HOURS, DISCOVERY_CAP, BROWSER_VIEWPORT_WIDTH, BROWSER_VIEWPORT_HEIGHT, AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS | Number input with spinner |
| checkbox | LLM_TIMEOUT_SECONDS, AUTO_APPLY_USE_LLM_LOCATOR, AUTO_APPLY_DEBUG_RESUME_WIDGET, AUTO_APPLY_DISABLE_DEFAULT_EXTENSIONS, AUTO_APPLY_DIAGNOSTICS, AUTO_APPLY_CAPTURE_VIDEO, AUTO_APPLY_CAPTURE_HAR | Toggle checkbox |
| dropdown | LLM_PROVIDER | Select dropdown (openrouter, google) |
| directory | AUTO_APPLY_ARTIFACTS_DIR | Directory picker |

**Validation Rules**:
- API keys: non-empty if provider is active; must be valid format
- Numeric fields: must be within reasonable ranges
- LLM_TEMPERATURE: must be between 0.0 and 1.0 (inclusive)
- DWELL_SECONDS, JITTER_SECONDS: must be non-negative floats
- MAX_TABS, RETRIES, timeouts: must be positive integers
- ALLOWED_DOMAINS: comma-separated list of domain patterns
- Directory fields: must be creatable or must exist and be writable

**UI Presentation**:
- API keys marked as `is_secret: true` (masked in UI, never logged)
- Grouped by category (LLM, Behavior, Resume Upload, Stealth, Networking, Diagnostics)
- Descriptions provided for each setting
- Reset to defaults button available
- Save changes button with confirmation

**Relationships**:
- Settings apply globally to all profiles
- Profile context available when editing (settings shown in Profile Settings page)
- No direct relationship to Profile entity (global scope)

---

## Data Relationships

```
Profile (1)
  │
  ├─→ (1) ApplicationQueue [ApplicationItem array in data/queues/<profile>.json]
  │   │
  │   └─→ (1..n) ApplicationItem
  │       ├─→ (0..1) JobDetails
  │       └─→ (0..1) Artifacts
  │
  └─→ (1) RunConfiguration [data/run-config/<profile>.json]
      ├─ operation_type: discover
      ├─ operation_type: apply_single
      └─ operation_type: apply_bulk

Settings (global)
  ├─ LLM configuration
  ├─ Browser settings
  ├─ Behavior settings
  ├─ Resume upload settings
  ├─ Diagnostics flags
  └─ Network configuration
```

---

## Data Flow Examples

### Discovery Workflow
1. User opens Dashboard, selects Profile
2. Clicks "Discover Jobs" button → DiscoveryModal opens with last RunConfiguration (search_window, job_cap, custom_query)
3. User modifies options if needed, clicks "Discover"
4. Frontend saves RunConfiguration to `data/run-config/<profile>.json` via API
5. Backend executes CLI discover command with options
6. Discovered jobs enqueued as ApplicationItems in `data/queues/<profile>.json`
7. Frontend polls queue every 2 seconds, displays updated ApplicationItems

### Application Workflow
1. User clicks job in queue → navigates to JobDetail page
2. JobDetails extracted and displayed (location, work model, employment type, etc.)
3. User clicks "Apply Now" → ApplyPanel opens with last RunConfiguration (mode, review_mode, llm options)
4. User modifies options if needed, clicks "Apply"
5. Frontend saves RunConfiguration, backend launches browser
6. ApplicationItem.status transitions: NEW → IN_PROGRESS
7. After completion: IN_PROGRESS → SUBMITTED (with Artifacts) or FAILED
8. Real-time logs streamed to UI every 2 seconds

---

## Storage Locations Summary

| Entity | Storage Location | Format | Scope |
|--------|------------------|--------|-------|
| Profile | `profiles/<id>.toml` | TOML | Per-profile |
| ApplicationItem | `data/queues/<profile>.json` | JSON array | Per-profile |
| JobDetails | Nested in ApplicationItem | JSON object | Per-job |
| Artifacts | Files in `data/artifacts/<profile>/` + metadata in ApplicationItem | Files + JSON | Per-job |
| RunConfiguration | `data/run-config/<profile>.json` | JSON object | Per-profile |
| Settings | `.env` or `web_ui/backend/.env` | Key=value pairs | Global |

---

## Implementation Notes

- All file storage uses UTF-8 encoding (UTF-8-sig for queue files to handle BOM)
- Timestamps in ISO 8601 format with timezone information
- Nullable fields indicate optional extraction or incomplete data
- Validation occurs at API layer (pydantic models for FastAPI)
- Frontend type definitions mirror backend pydantic models via TypeScript
- No circular references in entity relationships

---
