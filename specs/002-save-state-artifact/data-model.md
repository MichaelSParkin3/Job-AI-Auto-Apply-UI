# Data Model: Saved Form State & Artifacts

## Entities

### ApplicationStatus (extended)
- new
- in_progress
- captcha_blocked
- pending_review  ← NEW
- submitted
- failed

Valid transitions:
- in_progress → {submitted, failed, captcha_blocked, pending_review}
- pending_review → {in_progress, submitted, failed}

### Artifacts (extended)
Fields:
- form_state_path: string | null  ← NEW
- screenshot_before_path: string | null  ← NEW (pre-full.jpg)
- screenshot_after_path: string | null  ← NEW (post-full.jpg)
- confirmation_text: string | null
- confirmation_id: string | null
- (BC fields retained): dom_snapshot_path, screenshot_path, video_path, har_path

### Saved State v1 (pre.json)
Top-level:
- version: "v1"
- captured_at: ISO8601 timestamp
- profile_id: string
- item_id: string
- url: string
- apply_url: string

Plan:
- resume_input: selector
- contact_fields: map[name] → selector
- link_fields: map[name] → selector
- dynamic_questions: list of { field_name, field_type, selector, options? }
- eeo_fields: list of { name, selector, field_type, options? }
- submit_button: selector
- captcha_selector: selector | null

Values:
- contacts: { name, email, phone, location, location_hidden }
- links: map[name] → value
- dynamic_questions: list of { field_name, selector, value | values[] }
- eeo: list of { name, selector, value }
- resume: { storage_id_len: int, filename: string, confirmed_attached: bool }

Labels (optional):
- nearby label/placeholder texts to assist selector drift recovery

### Artifact Storage Layout
- data/artifacts/<profile>/<item_id>/
  - pre.json
  - pre-full.jpg
  - post-full.jpg (optional)
  - confirmation.json (on submit)

