# REST API Contracts: Web UI Dashboard

**Version**: v1 | **Date**: 2025-10-28 | **Base URL**: `http://localhost:5000/api/v1`

## Overview

This document specifies all REST API endpoints for the Web UI dashboard backend. All requests and responses use JSON format. The API follows RESTful conventions with standard HTTP methods and status codes.

**CORS Configuration**: Frontend (localhost:5173) is allowed to call backend (localhost:5000).

**Error Format**: All error responses include JSON body with `error` and `message` fields.

```json
{
  "error": "error_code",
  "message": "Human-readable error description"
}
```

---

## Profiles API (`/api/v1/profiles/`)

### GET /api/v1/profiles/

List all available profiles.

**Request**: None

**Response** (200 OK):
```json
{
  "profiles": [
    {
      "id": "john_doe",
      "name": "John Doe",
      "email": "john@example.com",
      "location": "São Paulo, Brazil",
      "resume_path": "resumes/john_resume.pdf",
      "preferred_browser": "chrome",
      "queue_count": 145,
      "queue_counts": {
        "NEW": 45,
        "IN_PROGRESS": 2,
        "SUBMITTED": 98,
        "FAILED": 0,
        "CAPTCHA_BLOCKED": 0
      }
    }
  ]
}
```

**Status Codes**:
- **200**: Success
- **500**: Server error (profile directory not accessible)

---

### GET /api/v1/profiles/{id}

Get profile details.

**Request Path Parameters**:
- `id` (string, required): Profile identifier

**Response** (200 OK):
```json
{
  "id": "john_doe",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+55-11-98765-4321",
  "location": "São Paulo, Brazil",
  "resume_path": "resumes/john_resume.pdf",
  "preferred_browser": "chrome",
  "user_data_dir": "/home/user/.browser-data/john_doe",
  "defaults": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+55-11-98765-4321",
    "location": "São Paulo, Brazil"
  },
  "keywords": {
    "roles": ["Senior Engineer", "Staff Engineer"],
    "tech_stack": ["React", "TypeScript", "Node.js"]
  },
  "experience": [
    {
      "company": "TechCorp",
      "role": "Senior Frontend Engineer",
      "dates": "2020-01-01 – 2024-10-28",
      "highlights": ["Led React migration", "40% performance improvement"],
      "tech_stack": ["React", "TypeScript", "WebGL"],
      "metrics": {"impact": "40% faster", "team_size": "5"}
    }
  ],
  "prompts": {
    "cover_letter": "Select 2-3 most relevant experiences..."
  }
}
```

**Status Codes**:
- **200**: Success
- **404**: Profile not found
- **500**: Server error

---

### PUT /api/v1/profiles/{id}

Update profile (TOML file).

**Request Path Parameters**:
- `id` (string, required): Profile identifier

**Request Body**: Profile object (same schema as GET response)

**Response** (200 OK):
```json
{
  "id": "john_doe",
  "name": "John Doe Updated",
  "email": "john.updated@example.com",
  "message": "Profile saved successfully"
}
```

**Status Codes**:
- **200**: Success (profile saved)
- **400**: Validation error (invalid field values)
- **404**: Profile not found
- **500**: Server error (file write failed)

---

### GET /api/v1/profiles/{id}/queue

Get profile's job queue.

**Request Path Parameters**:
- `id` (string, required): Profile identifier

**Query Parameters**:
- `status` (optional): Filter by status (NEW, IN_PROGRESS, SUBMITTED, FAILED, CAPTCHA_BLOCKED)
- `search` (optional): Search by company or title
- `skip` (optional): Pagination offset (default 0)
- `limit` (optional): Page size (default 50, max 500)

**Response** (200 OK):
```json
{
  "profile_id": "john_doe",
  "total": 145,
  "items": [
    {
      "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
      "url": "https://jobs.lever.co/example/123456",
      "company": "Innovative Inc.",
      "title": "Senior Frontend Engineer",
      "status": "NEW",
      "date_discovered": "2025-10-28T10:30:00Z",
      "date_applied": null,
      "source_query": "React TypeScript jobs remote",
      "source_rank": 3,
      "details": {
        "location": "Remote",
        "work_model": "Remote",
        "employment_type": "Full-time",
        "department": "Engineering",
        "compensation": {
          "min": 120000,
          "max": 180000,
          "currency": "USD"
        },
        "posting_text": "We are looking for...",
        "tech_tags": ["React", "TypeScript"],
        "apply_url": "https://jobs.lever.co/example/123456/apply",
        "posting_date": "2025-10-20T00:00:00Z"
      },
      "artifacts": null
    }
  ]
}
```

**Status Codes**:
- **200**: Success
- **404**: Profile not found
- **500**: Server error

---

### POST /api/v1/profiles/{id}/switch

Set active profile (affects subsequent discover/apply operations).

**Request Path Parameters**:
- `id` (string, required): Profile identifier to activate

**Request Body**: Empty or `{}`

**Response** (200 OK):
```json
{
  "active_profile": "john_doe",
  "message": "Profile switched successfully"
}
```

**Status Codes**:
- **200**: Success
- **404**: Profile not found
- **500**: Server error

---

## Jobs API (`/api/v1/jobs/`)

### GET /api/v1/jobs/

List jobs in active profile's queue.

**Query Parameters**:
- `profile` (string, required): Profile ID to list jobs for
- `status` (optional): Filter by status
- `search` (optional): Search by company/title
- `skip` (optional): Pagination offset (default 0)
- `limit` (optional): Page size (default 50, max 500)

**Response** (200 OK):
```json
{
  "profile_id": "john_doe",
  "total": 145,
  "items": [
    {
      "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
      "url": "https://jobs.lever.co/example/123456",
      "company": "Innovative Inc.",
      "title": "Senior Frontend Engineer",
      "status": "NEW",
      "date_discovered": "2025-10-28T10:30:00Z"
    }
  ]
}
```

**Status Codes**:
- **200**: Success
- **400**: Missing required profile parameter
- **404**: Profile not found
- **500**: Server error

---

### GET /api/v1/jobs/{job_id}

Get full job details (with artifacts).

**Request Path Parameters**:
- `job_id` (string, required): ULID of job

**Query Parameters**:
- `profile` (string, required): Profile ID containing the job

**Response** (200 OK):
```json
{
  "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "url": "https://jobs.lever.co/example/123456",
  "company": "Innovative Inc.",
  "title": "Senior Frontend Engineer",
  "status": "NEW",
  "date_discovered": "2025-10-28T10:30:00Z",
  "date_applied": null,
  "source_query": "React TypeScript",
  "source_rank": 3,
  "details": {
    "location": "Remote",
    "work_model": "Remote",
    "employment_type": "Full-time",
    "department": "Engineering",
    "compensation": {
      "min": 120000,
      "max": 180000,
      "currency": "USD"
    },
    "posting_text": "Full job description...",
    "tech_tags": ["React", "TypeScript"],
    "apply_url": "https://jobs.lever.co/example/123456/apply",
    "posting_date": "2025-10-20T00:00:00Z"
  },
  "artifacts": {
    "screenshot_path": "data/artifacts/john_doe/01ARZ3NDEKTSV4RRFFQ69G5FAV_screenshot.png",
    "confirmation_text": "Your application has been received",
    "confirmation_id": "APP-12345"
  }
}
```

**Status Codes**:
- **200**: Success
- **400**: Missing required profile parameter
- **404**: Job not found
- **500**: Server error

---

### PUT /api/v1/jobs/{job_id}/status

Manually update job status (e.g., reset from FAILED to NEW).

**Request Path Parameters**:
- `job_id` (string, required): ULID of job

**Request Body**:
```json
{
  "profile": "john_doe",
  "status": "NEW"
}
```

**Response** (200 OK):
```json
{
  "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "status": "NEW",
  "message": "Job status updated"
}
```

**Status Codes**:
- **200**: Success
- **400**: Invalid status value
- **404**: Job not found
- **500**: Server error

---

### DELETE /api/v1/jobs/{job_id}

Remove job from queue.

**Request Path Parameters**:
- `job_id` (string, required): ULID of job

**Query Parameters**:
- `profile` (string, required): Profile ID containing the job

**Response** (204 No Content):
Empty body

**Status Codes**:
- **204**: Success (job deleted)
- **400**: Missing required profile parameter
- **404**: Job not found
- **500**: Server error

---

## Discovery API (`/api/v1/discover/`)

### POST /api/v1/discover/execute

Start job discovery with user-selected options.

**Request Body**:
```json
{
  "profile": "john_doe",
  "search_window": "24h",
  "job_cap": 10,
  "custom_query": "React remote"
}
```

**Response** (202 Accepted):
```json
{
  "discovery_id": "disc-12345",
  "status": "running",
  "message": "Discovery started"
}
```

**Status Codes**:
- **202**: Discovery accepted and started
- **400**: Validation error (missing required fields)
- **404**: Profile not found
- **500**: Server error

---

### GET /api/v1/discover/status

Get discovery progress.

**Query Parameters**:
- `discovery_id` (string, optional): Specific discovery session ID
- `profile` (string, required): Profile ID

**Response** (200 OK):
```json
{
  "discovery_id": "disc-12345",
  "status": "running",
  "discovered_count": 8,
  "total_to_discover": 10,
  "progress_percent": 80,
  "elapsed_seconds": 15,
  "message": "Discovering jobs..."
}
```

**Status Codes**:
- **200**: Success
- **404**: Discovery session not found
- **500**: Server error

---

### GET /api/v1/discover/last-options/{profile_id}

Retrieve last-used discovery options for a profile.

**Request Path Parameters**:
- `profile_id` (string, required): Profile ID

**Response** (200 OK):
```json
{
  "profile_id": "john_doe",
  "operation_type": "discover",
  "search_window": "24h",
  "job_cap": 10,
  "custom_query": "React remote",
  "last_updated": "2025-10-28T10:30:00Z"
}
```

**Status Codes**:
- **200**: Success (returns last-used options or defaults)
- **404**: Profile not found
- **500**: Server error

---

## Apply API (`/api/v1/apply/`)

### POST /api/v1/apply/single

Apply to a single job with user-selected options.

**Request Body**:
```json
{
  "profile": "john_doe",
  "job_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "mode": "supervised",
  "review_mode": false,
  "llm_provider_override": null,
  "llm_model_override": null,
  "use_llm_locator": false,
  "debug_resume_widget": false,
  "resume_wait_timeout": 25
}
```

**Response** (202 Accepted):
```json
{
  "job_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "status": "IN_PROGRESS",
  "message": "Application started"
}
```

**Status Codes**:
- **202**: Application accepted and started
- **400**: Validation error
- **404**: Job or profile not found
- **500**: Server error

---

### POST /api/v1/apply/bulk

Apply to multiple jobs (all waiting jobs or filtered set) with batch options.

**Request Body**:
```json
{
  "profile": "john_doe",
  "mode": "supervised",
  "max_concurrent": 1,
  "stop_on_failure": false,
  "llm_provider_override": null,
  "llm_model_override": null,
  "save_logs": true,
  "logs_dir": "data/logs"
}
```

**Response** (202 Accepted):
```json
{
  "batch_id": "batch-12345",
  "status": "running",
  "jobs_count": 45,
  "message": "Bulk application started"
}
```

**Status Codes**:
- **202**: Bulk application accepted and started
- **400**: Validation error
- **404**: Profile not found
- **500**: Server error

---

### GET /api/v1/apply/status/{job_id}

Get application progress for a job.

**Request Path Parameters**:
- `job_id` (string, required): ULID of job

**Query Parameters**:
- `profile` (string, required): Profile ID

**Response** (200 OK):
```json
{
  "job_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "status": "IN_PROGRESS",
  "progress": {
    "step": "analyzing_form",
    "step_description": "Analyzing job application form",
    "elapsed_seconds": 8
  }
}
```

**Status Codes**:
- **200**: Success
- **404**: Job not found
- **500**: Server error

---

### GET /api/v1/apply/logs/{job_id}

Stream real-time application logs.

**Request Path Parameters**:
- `job_id` (string, required): ULID of job

**Query Parameters**:
- `profile` (string, required): Profile ID

**Response** (200 OK - Server-Sent Events or JSON Lines):
```
data: {"timestamp": "2025-10-28T10:30:00Z", "event": "apply.start", "message": "Starting application"}
data: {"timestamp": "2025-10-28T10:30:01Z", "event": "form.analyze", "message": "Analyzing form fields"}
data: {"timestamp": "2025-10-28T10:30:05Z", "event": "form.fill", "message": "Filling contact info"}
data: {"timestamp": "2025-10-28T10:30:08Z", "event": "submit", "message": "Submitting application"}
```

**Status Codes**:
- **200**: Success (streaming response)
- **404**: Job not found
- **500**: Server error

---

## Artifacts API (`/api/v1/artifacts/`)

### GET /api/v1/artifacts/{profile_id}/{job_id}/

List available artifact files for a job.

**Request Path Parameters**:
- `profile_id` (string, required): Profile ID
- `job_id` (string, required): Job ID

**Response** (200 OK):
```json
{
  "profile_id": "john_doe",
  "job_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "artifacts": [
    {
      "name": "01ARZ3NDEKTSV4RRFFQ69G5FAV_screenshot.png",
      "type": "image/png",
      "size_bytes": 245120,
      "created_at": "2025-10-28T10:35:00Z"
    },
    {
      "name": "01ARZ3NDEKTSV4RRFFQ69G5FAV_logs.txt",
      "type": "text/plain",
      "size_bytes": 12480,
      "created_at": "2025-10-28T10:35:00Z"
    }
  ]
}
```

**Status Codes**:
- **200**: Success (may be empty list if no artifacts)
- **404**: Profile or job not found
- **500**: Server error

---

### GET /api/v1/artifacts/{profile_id}/{job_id}/{file}

Serve artifact file (screenshot, log, etc.).

**Request Path Parameters**:
- `profile_id` (string, required): Profile ID
- `job_id` (string, required): Job ID
- `file` (string, required): Artifact filename

**Response** (200 OK):
Binary file content with appropriate `Content-Type` header

**Status Codes**:
- **200**: Success
- **404**: File not found
- **500**: Server error

---

## Settings API (`/api/v1/settings/`)

### GET /api/v1/settings/

Get all settings with descriptions.

**Query Parameters**:
- `category` (optional): Filter by category (llm, behavior, resume_upload, stealth, networking, diagnostics)

**Response** (200 OK):
```json
{
  "settings": [
    {
      "key": "LLM_PROVIDER",
      "value": "openrouter",
      "description": "LLM provider to use (openrouter or google)",
      "category": "llm",
      "input_type": "dropdown",
      "options": ["openrouter", "google"],
      "is_secret": false
    },
    {
      "key": "OPENROUTER_API_KEY",
      "value": "***masked***",
      "description": "OpenRouter API key for LLM requests",
      "category": "llm",
      "input_type": "password",
      "is_secret": true
    },
    {
      "key": "DWELL_SECONDS",
      "value": 0.8,
      "description": "Delay between browser actions in seconds",
      "category": "behavior",
      "input_type": "number",
      "is_secret": false
    }
  ]
}
```

**Status Codes**:
- **200**: Success
- **500**: Server error

---

### GET /api/v1/settings/{key}

Get a single setting value.

**Request Path Parameters**:
- `key` (string, required): Setting key (e.g., LLM_PROVIDER)

**Response** (200 OK):
```json
{
  "key": "LLM_PROVIDER",
  "value": "openrouter",
  "description": "LLM provider to use",
  "category": "llm",
  "input_type": "dropdown",
  "options": ["openrouter", "google"],
  "is_secret": false
}
```

**Status Codes**:
- **200**: Success
- **404**: Setting not found
- **500**: Server error

---

### PUT /api/v1/settings/

Update multiple settings.

**Request Body**:
```json
{
  "LLM_PROVIDER": "google",
  "LLM_TEMPERATURE": 0.5,
  "DWELL_SECONDS": 1.0
}
```

**Response** (200 OK):
```json
{
  "updated": ["LLM_PROVIDER", "LLM_TEMPERATURE", "DWELL_SECONDS"],
  "message": "Settings updated and saved to .env"
}
```

**Status Codes**:
- **200**: Success
- **400**: Validation error (invalid value for setting)
- **500**: Server error (file write failed)

---

### DELETE /api/v1/settings/{key}

Remove setting (revert to default).

**Request Path Parameters**:
- `key` (string, required): Setting key to reset

**Response** (200 OK):
```json
{
  "key": "LLM_TEMPERATURE",
  "message": "Setting reset to default value"
}
```

**Status Codes**:
- **200**: Success
- **404**: Setting not found
- **500**: Server error

---

### POST /api/v1/settings/reset

Reset all settings to defaults.

**Request Body**: Empty or `{}`

**Response** (200 OK):
```json
{
  "reset_count": 18,
  "message": "All settings reset to defaults"
}
```

**Status Codes**:
- **200**: Success
- **500**: Server error

---

## Response Patterns

### Paginated List Response

All list endpoints use consistent pagination:

```json
{
  "total": 145,
  "skip": 0,
  "limit": 50,
  "items": [...]
}
```

### Error Response

All error responses follow this pattern:

```json
{
  "error": "not_found",
  "message": "Profile 'unknown_profile' not found"
}
```

### Standard HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET/PUT/DELETE |
| 202 | Accepted | Long-running operation (discover, apply) accepted |
| 204 | No Content | Successful DELETE with no response body |
| 400 | Bad Request | Validation error or missing required parameter |
| 404 | Not Found | Resource (profile, job, setting) not found |
| 500 | Internal Server Error | Unexpected error; details in response body |

---

## Schema Files

Detailed JSON Schema definitions for all request/response bodies are in the `schemas/` directory:

- `profiles.schema.json` - Profile entity and endpoints
- `jobs.schema.json` - ApplicationItem and job endpoints
- `discover.schema.json` - Discovery options and responses
- `apply.schema.json` - Apply options and responses
- `artifacts.schema.json` - Artifact file metadata
- `settings.schema.json` - Settings entity and endpoints

---

## Implementation Notes

- All timestamps are ISO 8601 format with timezone
- All array indices are zero-based
- File paths are relative to project root or absolute
- API is stateless (no session tracking)
- CORS headers allow frontend localhost:5173
- Content-Type: application/json for all JSON responses
- Streaming responses (logs) use Server-Sent Events or JSON Lines format

---
