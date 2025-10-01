# Data Model: Lever Auto‑Apply Assistant

Date: 2025-10-01

## Entities

### Profile
- id: string (slug)
- name: string
- resume_path: string (file path)
- defaults: object (key/value)
- keywords: list[string]
- prompts: object
- user_data_dir: string|null
- preferred_browser: string (e.g., chromium) | null

### ApplicationItem
- id: string (ulid)
- url: string
- company: string
- title: string
- status: enum { new, in_progress, captcha_blocked, submitted, failed }
- discovered_at: datetime
- last_updated_at: datetime
- reason: object { code: string, message: string } | null
- artifacts: Artifacts
- hash: string (sha256 of url|company|title)

### AnswerCache
- id: string (ulid)
- profile_id: string (ref Profile)
- key: string (normalized question key)
- value: string
- type: enum { generic, long_form }
- scope: enum { profile, company, posting } (default profile for generic)
- company_id: string | null
- posting_id: string | null
- updated_at: datetime

### Artifacts
- dom_snapshot_path: string | null
- screenshot_path: string | null
- video_path: string | null
- har_path: string | null
- confirmation_text: string | null
- confirmation_id: string | null

### Config
- dwell_seconds: float (default 0.8)
- jitter_seconds: float (default 0.4)
- max_tabs: int (default 3)
- retries: int (default 2)
- discovery_window_hours: int (default 24)
- discovery_cap: int (default 10)
- proxy: object { scheme, host, port, username?, password? } | null
- user_agent: string | null
- allowed_domains: list[string]
- output_mode: enum { human, json }
- encryption_enabled: bool (default false)
- retention_days: int (0 = keep until manual cleanup)

## Relationships
- Profile 1..* ApplicationItem (by queue ownership)
- Profile 1..* AnswerCache (scope profile)
- ApplicationItem 1..1 Artifacts

## Validation Rules
- hash uniqueness per profile queue (prevents duplicates)
- status transitions: new → in_progress → submitted|failed|captcha_blocked; captcha_blocked → in_progress → submitted|failed
- required fields on submission: url, company, title, confirmation_text or confirmation_id
