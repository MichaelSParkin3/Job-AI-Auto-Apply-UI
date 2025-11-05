# Profile Management UI - Detailed Implementation Plan

**Version:** 1.0
**Date:** November 5, 2025
**Status:** Planning Phase
**Estimated Duration:** 10-14 days

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Profile Structure & Fields](#profile-structure--fields)
4. [Existing Codebase Analysis](#existing-codebase-analysis)
5. [Phase-by-Phase Implementation](#phase-by-phase-implementation)
6. [Files to Create/Modify](#files-to-createmodify)
7. [Technology Decisions](#technology-decisions)
8. [Gotchas & Considerations](#gotchas--considerations)
9. [Testing Strategy](#testing-strategy)
10. [Timeline](#timeline)

---

## Overview

Implement a structured, multi-step wizard UI for creating, editing, and managing profile TOML files through the web interface. Currently, profiles are managed manually as TOML files. This feature will provide a user-friendly form-based interface with validation, resume upload, and full CRUD operations.

### Goals

- ✅ Create new profiles via web UI
- ✅ Edit existing profiles
- ✅ Upload and manage resume PDFs
- ✅ Validate all required fields
- ✅ Support complex nested structures (experience array, keywords, prompts)
- ✅ Provide intuitive, step-by-step guidance
- ✅ Maintain data integrity with proper validation

### Success Criteria

- All profile fields accessible via UI
- Resume upload working with validation
- Form validation prevents invalid data
- Profiles saved correctly as TOML
- User can edit and save multiple times
- Clear error messages guide corrections

---

## Architecture

### High-Level Flow

```
App.tsx (add "Profiles" tab)
  ├── ProfilesPage
  │   ├── Mode: list | create | edit
  │   ├── ProfileList (list mode)
  │   │   ├── Display all profiles
  │   │   └── Actions: Edit, Delete, Duplicate
  │   └── ProfileForm (create/edit modes)
  │       ├── 7-step wizard
  │       ├── Navigation (back/next)
  │       └── Submit to backend
  │
Backend Routes
  ├── GET /api/profiles/{id}/detail
  ├── POST /api/profiles (create)
  ├── PUT /api/profiles/{id} (update)
  ├── DELETE /api/profiles/{id} (optional)
  └── POST /api/profiles/{id}/resume (upload)
```

### Wizard Steps

1. **Basic Information** - id, name, browser settings
2. **Resume & Search** - Resume upload, search query
3. **Contact Defaults** - Email, phone, location, URLs, EEO fields
4. **Keywords** - Roles, seniority, tech stack, domains
5. **Experience** - Work history array with nested fields
6. **Prompts** - LLM guidance text for various contexts
7. **Review & Save** - Summary before final submission

---

## Profile Structure & Fields

### Complete Field List

#### Required Fields
```
id: string              # Slug identifier, becomes TOML filename
name: string            # Display name
resume_path: string     # Path to resume PDF (relative or absolute)
```

#### Optional Basic Fields
```
preferred_browser: string | None    # chrome/chromium/msedge
user_data_dir: string | None        # Path to browser profile directory
search_query: string | None         # Custom Google search query
```

#### Defaults Section (Contact & EEO Information)
```
defaults: {
  current_company: string           # Current employer
  email: string                     # Contact email
  phone: string                     # Contact phone
  location: string                  # City, State format
  portfolio_url: string             # Portfolio website
  github_url: string                # GitHub profile URL
  linkedin_url: string              # LinkedIn profile URL
  work_authorization: string        # Authorization status
  work_authorized: string           # Boolean as string
  requires_visa_sponsorship: string # Boolean as string
  worked_at_company_before: string  # Boolean as string
  zip_code: string                  # Postal code
  eeo_gender: string                # Gender identity (EEO)
  eeo_race: string                  # Race/ethnicity (EEO)
  eeo_veteran_status: string        # Veteran status (EEO)
  eeo_disability_status: string     # Disability status (EEO)
  salary_expectation: string        # Salary range
  pronouns: string                  # Preferred pronouns
}
```

#### Keywords Section (Search Criteria)
```
keywords: {
  roles: list[string]       # Job titles to target
  seniority: list[string]   # Seniority levels (Junior, Senior, etc.)
  tech_stack: list[string]  # Technologies/languages
  domains: list[string]     # Industry domains
}
```

#### Experience Array (Work History)
```
experience: [
  {
    company: string           # Company name (required)
    role: string              # Job title (required)
    dates: string             # Date range (required)
    location: string | None   # Office location (optional)
    context: string | None    # Context/description (optional)
    highlights: list[string]  # Key achievements (2-3 items)
    tech_stack: list[string]  # Technologies used
    metrics: {
      key: string             # Metric name (e.g., "error_reduction")
      value: string           # Metric value (e.g., "45%")
    }
  }
]
```

#### Prompts Section (LLM Guidance)
```
prompts: {
  cover_letter: string              # Guidance for cover letters
  resume_summary: string            # Guidance for resume summaries
  key_accomplishments: string       # Guidance for achievements
  experience_selection: string      # Guidance for experience selection
  ai_tools_response: string | None  # Guidance for AI tools question
}
```

### Field Characteristics

| Field | Type | Required | Editable | Default | Notes |
|-------|------|----------|----------|---------|-------|
| id | string | Yes | No (pk) | - | Slug format, becomes filename |
| name | string | Yes | Yes | - | Display name for profile |
| resume_path | string | Yes | Yes | - | Validated on load |
| preferred_browser | string | No | Yes | None | Enum: chrome/chromium/msedge |
| user_data_dir | string | No | Yes | None | Path to browser profile |
| search_query | string | No | Yes | None | Custom Google search |
| defaults.* | string | No | Yes | "" | All contact fields |
| keywords.* | list[str] | No | Yes | [] | All keyword categories |
| experience | array | No | Yes | None | Complex nested structure |
| prompts.* | string | No | Yes | "" | Multi-line guidance text |

---

## Existing Codebase Analysis

### Backend Structure

**FastAPI Setup (`web_ui/backend/app.py`):**
- FastAPI app with CORS enabled
- Lifespan manager creates directories on startup
- Routes prefixed: `/api` for REST, `/ws` for WebSocket
- Health check endpoint: `GET /health`
- Runs on port 8000

**Configuration (`web_ui/backend/config.py`):**
- Settings dataclass loads from environment
- Key settings:
  - `AUTO_APPLY_PROFILES_DIR` → defaults to `./profiles`
  - `AUTO_APPLY_QUEUES_DIR` → defaults to `./data/queues`
  - `AUTO_APPLY_ARTIFACTS_DIR` → defaults to `./data/artifacts`

**Existing Routes (`web_ui/backend/routes/profiles.py`):**
```python
GET /api/profiles              # List profiles
GET /api/profiles/{profile_id} # Get profile summary
```

**Current ProfileResponse Model:**
```python
{
  'id': str,
  'name': str,
  'resume_path': str,
  'preferred_browser': str | None,
  'has_experience': bool
}
```

**Profile Manager (`src/job_ai_auto_apply_ui/profile_manager.py`):**
- `load_profile(profile_id: str, base_dir: Path = None) -> Profile` - Load TOML
- `profiles_root(base: Path = None) -> Path` - Get profiles directory
- `Profile.from_mapping(payload)` - Create from dict
- **NO SAVE FUNCTIONALITY** - Profiles are read-only via TOML

### Frontend Architecture

**Tech Stack:**
- React 19.1.1
- TypeScript 5.9.3
- Vite 7.1.7
- TailwindCSS 4.1.16
- Axios 1.13.1

**Components (`components/ui/`):**
- Custom shadcn/ui-inspired components
- No external component library (Radix, MUI)
- Styled with Tailwind utilities

**State Management:**
- React useState/useEffect only
- No Redux/Zustand
- Component-local state patterns

**HTTP Client (`lib/api.ts`):**
- Axios instance with base URL
- Type-safe request/response interfaces
- Organized by resource (profilesApi, discoverApi, etc.)

**Current Routing:**
- No router - single page with tab navigation
- Client-side tabs: 'discover' | 'apply'
- Will add 'profiles' tab

**Form Approach:**
- Manual form handling with useState
- No React Hook Form or Formik
- Inline validation

### Authentication & Security

**Current Status:**
- No authentication implemented
- Wide-open API (for local development)
- File operations on trusted paths only

### File System

**Directory Structure:**
```
Job-AI-Auto-Apply-UI/
├── profiles/                    # TOML profile files
│   └── {profile_id}.toml
├── resumes/                     # Resume PDFs
│   └── {resume_files}
├── data/
│   ├── queues/                 # Application queues (JSON)
│   └── artifacts/              # Browser artifacts
└── web_ui/
    ├── backend/
    └── frontend/
```

**File Naming:**
- Profiles: `{profile_id}.toml`
- Resumes: Free-form names (e.g., `profile_id_timestamp.pdf`)

---

## Phase-by-Phase Implementation

### Phase 1: Backend Foundation (2-3 days)

#### 1.1 Add Dependencies

**File:** `pyproject.toml`

Add to dependencies:
```toml
tomli-w = "^1.0.0"  # TOML writing (separate from tomllib read-only)
```

Install: `pip install tomli-w`

#### 1.2 Create Profile Write Function

**File:** `src/job_ai_auto_apply_ui/profile_manager.py`

Add function:
```python
def save_profile(profile: Profile, base_dir: Path | None = None) -> None:
    """Write profile to TOML file.

    Args:
        profile: Profile dataclass to save
        base_dir: Base directory for profiles (defaults to cwd)

    Raises:
        IOError: If file write fails
    """
    directory = profiles_root(base_dir)
    directory.mkdir(parents=True, exist_ok=True)

    filepath = directory / f"{profile.id}.toml"

    # Convert dataclass to dict
    data = {
        'id': profile.id,
        'name': profile.name,
        'resume_path': str(profile.resume_path),
    }

    if profile.preferred_browser:
        data['preferred_browser'] = profile.preferred_browser
    if profile.user_data_dir:
        data['user_data_dir'] = str(profile.user_data_dir)
    if profile.search_query:
        data['search_query'] = profile.search_query

    # Serialize nested structures
    data['defaults'] = dict(profile.defaults)
    data['keywords'] = {k: list(v) for k, v in profile.keywords.items()}
    data['prompts'] = dict(profile.prompts)

    if profile.experience:
        data['experience'] = [dict(exp) for exp in profile.experience]

    # Write TOML
    import tomli_w
    with open(filepath, 'wb') as f:
        tomli_w.dump(data, f)
```

#### 1.3 Create Backend Models

**File:** `web_ui/backend/models/profile.py` (new)

```python
from typing import Optional, List, Dict
from pydantic import BaseModel

class ExperienceItem(BaseModel):
    """Work experience entry."""
    company: str
    role: str
    dates: str
    location: Optional[str] = None
    context: Optional[str] = None
    highlights: List[str] = []
    tech_stack: List[str] = []
    metrics: Dict[str, str] = {}

class ProfileDetailResponse(BaseModel):
    """Complete profile data for editing."""
    id: str
    name: str
    resume_path: str
    preferred_browser: Optional[str] = None
    user_data_dir: Optional[str] = None
    search_query: Optional[str] = None
    defaults: Dict[str, str] = {}
    keywords: Dict[str, List[str]] = {}
    experience: List[ExperienceItem] = []
    prompts: Dict[str, str] = {}

class ProfileCreateRequest(ProfileDetailResponse):
    """Request to create new profile."""
    pass

class ProfileUpdateRequest(ProfileDetailResponse):
    """Request to update existing profile."""
    pass

class ResumeUploadResponse(BaseModel):
    """Response from resume upload."""
    filename: str
    path: str
```

#### 1.4 Add Backend Routes

**File:** `web_ui/backend/routes/profiles.py` (extend)

Add endpoints:

```python
from fastapi import UploadFile, File, HTTPException
from pathlib import Path
import shutil
from datetime import datetime

@router.get("/profiles/{profile_id}/detail", response_model=ProfileDetailResponse)
async def get_profile_detail(profile_id: str):
    """Get full profile data for editing."""
    try:
        profile = load_profile(profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

    return ProfileDetailResponse(
        id=profile.id,
        name=profile.name,
        resume_path=str(profile.resume_path),
        preferred_browser=profile.preferred_browser,
        user_data_dir=str(profile.user_data_dir) if profile.user_data_dir else None,
        search_query=profile.search_query,
        defaults=dict(profile.defaults),
        keywords={k: list(v) for k, v in profile.keywords.items()},
        experience=[ExperienceItem(**dict(exp)) for exp in (profile.experience or [])],
        prompts=dict(profile.prompts),
    )

@router.post("/profiles", response_model=ProfileDetailResponse)
async def create_profile(profile: ProfileCreateRequest):
    """Create new profile."""
    # Validate ID doesn't exist
    try:
        load_profile(profile.id)
        raise HTTPException(status_code=409, detail=f"Profile '{profile.id}' already exists")
    except ProfileNotFoundError:
        pass

    # Convert to Profile dataclass and save
    profile_data = Profile(
        id=profile.id,
        name=profile.name,
        resume_path=Path(profile.resume_path),
        defaults=profile.defaults,
        keywords=profile.keywords,
        prompts=profile.prompts,
        user_data_dir=Path(profile.user_data_dir) if profile.user_data_dir else None,
        preferred_browser=profile.preferred_browser,
        experience=[dict(exp) for exp in profile.experience] if profile.experience else None,
        search_query=profile.search_query,
    )

    save_profile(profile_data)
    return profile

@router.put("/profiles/{profile_id}", response_model=ProfileDetailResponse)
async def update_profile(profile_id: str, profile: ProfileUpdateRequest):
    """Update existing profile."""
    if profile_id != profile.id:
        raise HTTPException(status_code=400, detail="Profile ID mismatch")

    # Validate exists
    try:
        load_profile(profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

    # Convert and save
    profile_data = Profile(
        id=profile.id,
        name=profile.name,
        resume_path=Path(profile.resume_path),
        defaults=profile.defaults,
        keywords=profile.keywords,
        prompts=profile.prompts,
        user_data_dir=Path(profile.user_data_dir) if profile.user_data_dir else None,
        preferred_browser=profile.preferred_browser,
        experience=[dict(exp) for exp in profile.experience] if profile.experience else None,
        search_query=profile.search_query,
    )

    save_profile(profile_data)
    return profile

@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete profile."""
    # Validate exists
    try:
        load_profile(profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

    # Delete file
    filepath = profiles_root() / f"{profile_id}.toml"
    filepath.unlink()

    return {"deleted": profile_id}

@router.post("/profiles/{profile_id}/resume", response_model=ResumeUploadResponse)
async def upload_resume(profile_id: str, file: UploadFile = File(...)):
    """Upload resume PDF for profile."""
    # Validate profile exists
    try:
        profile = load_profile(profile_id)
    except ProfileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    # Validate file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    # Save to resumes/ directory
    resumes_dir = Path.cwd() / "resumes"
    resumes_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{profile_id}_{timestamp}.pdf"
    filepath = resumes_dir / filename

    # Write file
    with open(filepath, 'wb') as buffer:
        buffer.write(content)

    # Update profile
    profile.resume_path = Path("resumes") / filename
    save_profile(profile)

    return ResumeUploadResponse(
        filename=filename,
        path=str(filepath.relative_to(Path.cwd())),
    )
```

#### 1.5 Testing

Create unit tests:

```python
# tests/unit/test_profile_manager_save.py

def test_save_profile_creates_file():
    """Test that save_profile creates a TOML file."""
    # Create test profile
    # Save it
    # Verify file exists
    # Verify TOML contents

def test_save_and_load_roundtrip():
    """Test load → modify → save → load cycle."""
    # Load existing profile
    # Modify fields
    # Save
    # Load again
    # Verify all fields match

def test_save_profile_handles_optional_fields():
    """Test that optional fields serialize correctly."""
    # Profile with None values
    # Profile with empty arrays
    # Verify TOML format
```

---

### Phase 2: Frontend Components (3-4 days)

#### 2.1 Base UI Components

**File:** `web_ui/frontend/src/components/ui/Textarea.tsx` (new)

```typescript
import * as React from "react"

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className = "", ...props }, ref) => (
    <textarea
      ref={ref}
      className={`w-full px-3 py-2 border border-gray-300 rounded-md
        bg-white text-gray-900 placeholder-gray-400
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
        disabled:bg-gray-100 disabled:cursor-not-allowed resize-y min-h-[100px]
        ${className}`}
      {...props}
    />
  )
)
Textarea.displayName = "Textarea"

export { Textarea }
```

**File:** `web_ui/frontend/src/components/ui/Tag.tsx` (new)

```typescript
import { X } from 'lucide-react'

interface TagProps {
  value: string
  onRemove: () => void
  disabled?: boolean
}

export function Tag({ value, onRemove, disabled }: TagProps) {
  return (
    <div className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-900 rounded">
      <span className="text-sm">{value}</span>
      <button
        type="button"
        onClick={onRemove}
        disabled={disabled}
        className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
      >
        <X size={16} />
      </button>
    </div>
  )
}
```

**File:** `web_ui/frontend/src/components/ui/MultiInput.tsx` (new)

```typescript
import { useState } from 'react'
import { Input } from './Input'
import { Button } from './Button'
import { Tag } from './Tag'

interface MultiInputProps {
  values: string[]
  onChange: (values: string[]) => void
  placeholder?: string
  disabled?: boolean
  label?: string
}

export function MultiInput({
  values,
  onChange,
  placeholder,
  disabled,
  label,
}: MultiInputProps) {
  const [input, setInput] = useState('')

  const addValue = () => {
    if (input.trim() && !values.includes(input.trim())) {
      onChange([...values, input.trim()])
      setInput('')
    }
  }

  const removeValue = (index: number) => {
    onChange(values.filter((_, i) => i !== index))
  }

  return (
    <div>
      {label && <label className="block text-sm font-medium mb-2">{label}</label>}
      <div className="flex gap-2 mb-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addValue())}
          placeholder={placeholder}
          disabled={disabled}
        />
        <Button
          type="button"
          onClick={addValue}
          disabled={!input.trim() || disabled}
        >
          Add
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {values.map((value, index) => (
          <Tag
            key={index}
            value={value}
            onRemove={() => removeValue(index)}
            disabled={disabled}
          />
        ))}
      </div>
    </div>
  )
}
```

**File:** `web_ui/frontend/src/components/ui/FileUpload.tsx` (new)

```typescript
import { useState, useRef } from 'react'
import { Upload, X } from 'lucide-react'
import { Button } from './Button'
import { profilesApi } from '../../lib/api'
import { useToast } from '../../lib/toast'

interface FileUploadProps {
  profileId: string
  currentPath?: string
  onUploadComplete: (path: string, filename: string) => void
  disabled?: boolean
}

export function FileUpload({
  profileId,
  currentPath,
  onUploadComplete,
  disabled,
}: FileUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { addToast } = useToast()

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setProgress(0)

    try {
      const response = await profilesApi.uploadResume(profileId, file)
      onUploadComplete(response.data.path, response.data.filename)
      addToast({
        title: 'Resume uploaded',
        description: response.data.filename,
      })
    } catch (error) {
      addToast({
        title: 'Upload failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }

  return (
    <div className="space-y-2">
      {currentPath && (
        <div className="flex items-center justify-between text-sm text-gray-600 bg-gray-50 p-2 rounded">
          <span>Current: {currentPath}</span>
          <button
            type="button"
            onClick={() => onUploadComplete('', '')}
            className="text-gray-400 hover:text-gray-600"
          >
            <X size={16} />
          </button>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileSelect}
        disabled={disabled || uploading}
        className="hidden"
      />

      <Button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={disabled || uploading}
        className="w-full"
      >
        <Upload className="w-4 h-4 mr-2" />
        {uploading ? `Uploading... ${progress}%` : 'Upload Resume'}
      </Button>
    </div>
  )
}
```

#### 2.2 Wizard Container

**File:** `web_ui/frontend/src/components/ProfileForm.tsx` (new)

```typescript
import { useState } from 'react'
import { Button } from './ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { profilesApi } from '../lib/api'
import { useToast } from '../lib/toast'
import { BasicInfoStep } from './steps/BasicInfoStep'
import { ResumeStep } from './steps/ResumeStep'
import { ContactStep } from './steps/ContactStep'
import { KeywordsStep } from './steps/KeywordsStep'
import { ExperienceStep } from './steps/ExperienceStep'
import { PromptsStep } from './steps/PromptsStep'
import { ReviewStep } from './steps/ReviewStep'
import { ProfileDetailResponse } from '../lib/types'

interface ProfileFormProps {
  profileId?: string
  onSave: (profile: ProfileDetailResponse) => void
  onCancel: () => void
}

export function ProfileForm({ profileId, onSave, onCancel }: ProfileFormProps) {
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const { addToast } = useToast()

  const [formData, setFormData] = useState<Partial<ProfileDetailResponse>>({
    id: '',
    name: '',
    resume_path: '',
    preferred_browser: undefined,
    user_data_dir: undefined,
    search_query: undefined,
    defaults: {},
    keywords: {},
    experience: [],
    prompts: {},
  })

  // Load existing profile on mount
  const loadProfile = async () => {
    if (!profileId) return

    try {
      const response = await profilesApi.getDetail(profileId)
      setFormData(response.data)
    } catch (error) {
      addToast({
        title: 'Failed to load profile',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
      onCancel()
    }
  }

  // Load on mount
  React.useEffect(() => {
    loadProfile()
  }, [profileId])

  const steps = [
    { number: 1, title: 'Basic Info', component: BasicInfoStep },
    { number: 2, title: 'Resume & Search', component: ResumeStep },
    { number: 3, title: 'Contact', component: ContactStep },
    { number: 4, title: 'Keywords', component: KeywordsStep },
    { number: 5, title: 'Experience', component: ExperienceStep },
    { number: 6, title: 'Prompts', component: PromptsStep },
    { number: 7, title: 'Review', component: ReviewStep },
  ]

  const handleNext = () => {
    if (validateStep(step)) {
      setStep(step + 1)
    }
  }

  const handleBack = () => {
    setStep(step - 1)
  }

  const handleSubmit = async () => {
    if (!validateStep(step)) return

    setLoading(true)
    try {
      if (profileId) {
        await profilesApi.update(profileId, formData as ProfileDetailResponse)
        addToast({ title: 'Profile updated successfully' })
      } else {
        await profilesApi.create(formData as ProfileDetailResponse)
        addToast({ title: 'Profile created successfully' })
      }
      onSave(formData as ProfileDetailResponse)
    } catch (error) {
      addToast({
        title: 'Failed to save profile',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const validateStep = (stepNum: number): boolean => {
    // TODO: Implement per-step validation
    return true
  }

  const CurrentStep = steps[step - 1].component

  return (
    <div className="space-y-6">
      {/* Progress indicator */}
      <div className="flex items-center justify-between">
        {steps.map((s) => (
          <div
            key={s.number}
            className={`flex-1 h-1 ${
              s.number <= step ? 'bg-blue-500' : 'bg-gray-300'
            } ${s.number < step ? 'rounded-full' : ''}`}
          />
        ))}
      </div>

      {/* Step indicator */}
      <div className="text-center">
        <h2 className="text-2xl font-bold">Step {step} of {steps.length}</h2>
        <p className="text-gray-600">{steps[step - 1].title}</p>
      </div>

      {/* Step content */}
      <Card>
        <CardContent className="pt-6">
          <CurrentStep formData={formData} onChange={setFormData} />
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex gap-4 justify-between">
        <Button
          onClick={handleBack}
          disabled={step === 1 || loading}
          variant="outline"
        >
          Back
        </Button>

        <div className="flex gap-2">
          <Button onClick={onCancel} variant="outline" disabled={loading}>
            Cancel
          </Button>

          {step < steps.length ? (
            <Button onClick={handleNext} disabled={loading}>
              Next
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? 'Saving...' : 'Save Profile'}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
```

#### 2.3 Step Components

**File:** `web_ui/frontend/src/components/steps/BasicInfoStep.tsx` (new)

```typescript
import { Label } from '../ui/Label'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function BasicInfoStep({ formData, onChange }: StepProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="id">Profile ID *</Label>
        <Input
          id="id"
          value={formData.id || ''}
          onChange={(e) => onChange({ ...formData, id: e.target.value })}
          placeholder="my-profile (slug format)"
          disabled={!!formData.id}
        />
        <p className="text-sm text-gray-500 mt-1">
          Unique identifier (alphanumeric, underscore, hyphen only)
        </p>
      </div>

      <div>
        <Label htmlFor="name">Full Name *</Label>
        <Input
          id="name"
          value={formData.name || ''}
          onChange={(e) => onChange({ ...formData, name: e.target.value })}
          placeholder="John Doe"
        />
      </div>

      <div>
        <Label htmlFor="browser">Preferred Browser</Label>
        <Select
          id="browser"
          value={formData.preferred_browser || ''}
          onChange={(e) =>
            onChange({ ...formData, preferred_browser: e.target.value || undefined })
          }
        >
          <option value="">None</option>
          <option value="chrome">Chrome</option>
          <option value="chromium">Chromium</option>
          <option value="msedge">Microsoft Edge</option>
        </Select>
      </div>

      <div>
        <Label htmlFor="userDataDir">Browser Profile Directory</Label>
        <Input
          id="userDataDir"
          value={formData.user_data_dir || ''}
          onChange={(e) =>
            onChange({ ...formData, user_data_dir: e.target.value || undefined })
          }
          placeholder="/path/to/browser/profile"
        />
        <p className="text-sm text-gray-500 mt-1">Optional: For persistent browser sessions</p>
      </div>
    </div>
  )
}
```

**File:** `web_ui/frontend/src/components/steps/ResumeStep.tsx` (new)

```typescript
import { Label } from '../ui/Label'
import { Textarea } from '../ui/Textarea'
import { FileUpload } from '../ui/FileUpload'
import { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function ResumeStep({ formData, onChange }: StepProps) {
  return (
    <div className="space-y-6">
      <div>
        <Label>Resume PDF *</Label>
        <FileUpload
          profileId={formData.id!}
          currentPath={formData.resume_path}
          onUploadComplete={(path) => onChange({ ...formData, resume_path: path })}
        />
        <p className="text-sm text-gray-500 mt-2">Upload a PDF resume (max 10MB)</p>
      </div>

      <div>
        <Label htmlFor="searchQuery">Custom Search Query</Label>
        <Textarea
          id="searchQuery"
          value={formData.search_query || ''}
          onChange={(e) => onChange({ ...formData, search_query: e.target.value || undefined })}
          placeholder="Custom Google search query (e.g., 'React developer jobs remote')"
        />
        <p className="text-sm text-gray-500 mt-1">Optional: Override default job discovery query</p>
      </div>
    </div>
  )
}
```

**File:** `web_ui/frontend/src/components/steps/ContactStep.tsx` (new)

```typescript
import { useState } from 'react'
import { Label } from '../ui/Label'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function ContactStep({ formData, onChange }: StepProps) {
  const [showEEO, setShowEEO] = useState(false)

  const updateDefault = (key: string, value: string) => {
    onChange({
      ...formData,
      defaults: {
        ...(formData.defaults || {}),
        [key]: value,
      },
    })
  }

  return (
    <div className="space-y-6">
      {/* Personal Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Personal Information</h3>

        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={formData.defaults?.email || ''}
            onChange={(e) => updateDefault('email', e.target.value)}
            placeholder="email@example.com"
          />
        </div>

        <div>
          <Label htmlFor="phone">Phone</Label>
          <Input
            id="phone"
            value={formData.defaults?.phone || ''}
            onChange={(e) => updateDefault('phone', e.target.value)}
            placeholder="+1-555-0100"
          />
        </div>

        <div>
          <Label htmlFor="location">Location</Label>
          <Input
            id="location"
            value={formData.defaults?.location || ''}
            onChange={(e) => updateDefault('location', e.target.value)}
            placeholder="City, State"
          />
        </div>

        <div>
          <Label htmlFor="pronouns">Pronouns</Label>
          <Input
            id="pronouns"
            value={formData.defaults?.pronouns || ''}
            onChange={(e) => updateDefault('pronouns', e.target.value)}
            placeholder="she/her, he/him, they/them"
          />
        </div>
      </div>

      {/* Work Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Work Information</h3>

        <div>
          <Label htmlFor="currentCompany">Current Company</Label>
          <Input
            id="currentCompany"
            value={formData.defaults?.current_company || ''}
            onChange={(e) => updateDefault('current_company', e.target.value)}
            placeholder="Company name"
          />
        </div>

        <div>
          <Label htmlFor="workAuth">Work Authorization</Label>
          <Input
            id="workAuth"
            value={formData.defaults?.work_authorization || ''}
            onChange={(e) => updateDefault('work_authorization', e.target.value)}
            placeholder="e.g., Authorized to work"
          />
        </div>

        <div>
          <Label htmlFor="visa">Requires Visa Sponsorship</Label>
          <Input
            id="visa"
            value={formData.defaults?.requires_visa_sponsorship || ''}
            onChange={(e) => updateDefault('requires_visa_sponsorship', e.target.value)}
            placeholder="Yes / No"
          />
        </div>

        <div>
          <Label htmlFor="salary">Salary Expectation</Label>
          <Input
            id="salary"
            value={formData.defaults?.salary_expectation || ''}
            onChange={(e) => updateDefault('salary_expectation', e.target.value)}
            placeholder="e.g., $100k - $150k"
          />
        </div>
      </div>

      {/* Links Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Links</h3>

        <div>
          <Label htmlFor="portfolio">Portfolio URL</Label>
          <Input
            id="portfolio"
            type="url"
            value={formData.defaults?.portfolio_url || ''}
            onChange={(e) => updateDefault('portfolio_url', e.target.value)}
            placeholder="https://example.com"
          />
        </div>

        <div>
          <Label htmlFor="github">GitHub URL</Label>
          <Input
            id="github"
            type="url"
            value={formData.defaults?.github_url || ''}
            onChange={(e) => updateDefault('github_url', e.target.value)}
            placeholder="https://github.com/username"
          />
        </div>

        <div>
          <Label htmlFor="linkedin">LinkedIn URL</Label>
          <Input
            id="linkedin"
            type="url"
            value={formData.defaults?.linkedin_url || ''}
            onChange={(e) => updateDefault('linkedin_url', e.target.value)}
            placeholder="https://linkedin.com/in/username"
          />
        </div>
      </div>

      {/* EEO Section */}
      <div className="space-y-4">
        <Button
          type="button"
          variant="outline"
          onClick={() => setShowEEO(!showEEO)}
          className="w-full"
        >
          {showEEO ? '▼' : '▶'} EEO Information (Optional)
        </Button>

        {showEEO && (
          <div className="bg-gray-50 p-4 rounded space-y-4 border-l-4 border-blue-500">
            <p className="text-sm text-gray-600">
              Equal Employment Opportunity (EEO) fields for employer compliance
            </p>

            <div>
              <Label htmlFor="gender">Gender</Label>
              <Input
                id="gender"
                value={formData.defaults?.eeo_gender || ''}
                onChange={(e) => updateDefault('eeo_gender', e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="race">Race/Ethnicity</Label>
              <Input
                id="race"
                value={formData.defaults?.eeo_race || ''}
                onChange={(e) => updateDefault('eeo_race', e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="veteran">Veteran Status</Label>
              <Input
                id="veteran"
                value={formData.defaults?.eeo_veteran_status || ''}
                onChange={(e) => updateDefault('eeo_veteran_status', e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="disability">Disability Status</Label>
              <Input
                id="disability"
                value={formData.defaults?.eeo_disability_status || ''}
                onChange={(e) => updateDefault('eeo_disability_status', e.target.value)}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

**File:** `web_ui/frontend/src/components/steps/KeywordsStep.tsx` (new)

```typescript
import { MultiInput } from '../ui/MultiInput'
import { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function KeywordsStep({ formData, onChange }: StepProps) {
  const updateKeywords = (key: string, values: string[]) => {
    onChange({
      ...formData,
      keywords: {
        ...(formData.keywords || {}),
        [key]: values,
      },
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <MultiInput
          label="Job Roles"
          values={formData.keywords?.roles || []}
          onChange={(values) => updateKeywords('roles', values)}
          placeholder="e.g., 'Frontend Engineer', 'Full Stack Developer'"
        />
        <p className="text-sm text-gray-500 mt-2">
          Job titles you're interested in
        </p>
      </div>

      <div>
        <MultiInput
          label="Seniority Levels"
          values={formData.keywords?.seniority || []}
          onChange={(values) => updateKeywords('seniority', values)}
          placeholder="e.g., 'Senior', 'Staff', 'Lead'"
        />
        <p className="text-sm text-gray-500 mt-2">
          Seniority levels matching your experience
        </p>
      </div>

      <div>
        <MultiInput
          label="Technologies"
          values={formData.keywords?.tech_stack || []}
          onChange={(values) => updateKeywords('tech_stack', values)}
          placeholder="e.g., 'React', 'TypeScript', 'Node.js'"
        />
        <p className="text-sm text-gray-500 mt-2">
          Technologies and frameworks you work with
        </p>
      </div>

      <div>
        <MultiInput
          label="Domains/Industries"
          values={formData.keywords?.domains || []}
          onChange={(values) => updateKeywords('domains', values)}
          placeholder="e.g., 'FinTech', 'Healthcare', 'E-commerce'"
        />
        <p className="text-sm text-gray-500 mt-2">
          Industries and domains you're interested in
        </p>
      </div>
    </div>
  )
}
```

**File:** `web_ui/frontend/src/components/steps/ExperienceStep.tsx` (new)

```typescript
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Label } from '../ui/Label'
import { MultiInput } from '../ui/MultiInput'
import { Textarea } from '../ui/Textarea'
import { ExperienceItem, ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function ExperienceStep({ formData, onChange }: StepProps) {
  const experience = formData.experience || []

  const updateExperience = (index: number, exp: Partial<ExperienceItem>) => {
    const updated = [...experience]
    updated[index] = { ...updated[index], ...exp }
    onChange({ ...formData, experience: updated })
  }

  const addExperience = () => {
    onChange({
      ...formData,
      experience: [
        ...experience,
        {
          company: '',
          role: '',
          dates: '',
          highlights: [],
          tech_stack: [],
          metrics: {},
        },
      ],
    })
  }

  const removeExperience = (index: number) => {
    onChange({
      ...formData,
      experience: experience.filter((_, i) => i !== index),
    })
  }

  return (
    <div className="space-y-6">
      {experience.map((exp, index) => (
        <div key={index} className="border rounded-lg p-4 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Experience {index + 1}</h3>
            <Button
              type="button"
              onClick={() => removeExperience(index)}
              variant="destructive"
              size="sm"
            >
              Remove
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor={`company-${index}`}>Company *</Label>
              <Input
                id={`company-${index}`}
                value={exp.company}
                onChange={(e) => updateExperience(index, { company: e.target.value })}
                placeholder="Company name"
              />
            </div>

            <div>
              <Label htmlFor={`role-${index}`}>Job Title *</Label>
              <Input
                id={`role-${index}`}
                value={exp.role}
                onChange={(e) => updateExperience(index, { role: e.target.value })}
                placeholder="Senior Engineer"
              />
            </div>

            <div>
              <Label htmlFor={`dates-${index}`}>Dates *</Label>
              <Input
                id={`dates-${index}`}
                value={exp.dates}
                onChange={(e) => updateExperience(index, { dates: e.target.value })}
                placeholder="Jan 2020 - Present"
              />
            </div>

            <div>
              <Label htmlFor={`location-${index}`}>Location</Label>
              <Input
                id={`location-${index}`}
                value={exp.location || ''}
                onChange={(e) => updateExperience(index, { location: e.target.value })}
                placeholder="New York, NY"
              />
            </div>
          </div>

          <div>
            <Label htmlFor={`context-${index}`}>Context/Description</Label>
            <Textarea
              id={`context-${index}`}
              value={exp.context || ''}
              onChange={(e) => updateExperience(index, { context: e.target.value })}
              placeholder="Brief description of role and company"
            />
          </div>

          <div>
            <MultiInput
              label="Highlights"
              values={exp.highlights}
              onChange={(values) => updateExperience(index, { highlights: values })}
              placeholder="Key achievement or responsibility"
            />
          </div>

          <div>
            <MultiInput
              label="Technologies"
              values={exp.tech_stack}
              onChange={(values) => updateExperience(index, { tech_stack: values })}
              placeholder="React, TypeScript, etc."
            />
          </div>
        </div>
      ))}

      <Button type="button" onClick={addExperience} variant="outline" className="w-full">
        + Add Experience
      </Button>
    </div>
  )
}
```

**File:** `web_ui/frontend/src/components/steps/PromptsStep.tsx` (new)

```typescript
import { Label } from '../ui/Label'
import { Textarea } from '../ui/Textarea'
import { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function PromptsStep({ formData, onChange }: StepProps) {
  const updatePrompt = (key: string, value: string) => {
    onChange({
      ...formData,
      prompts: {
        ...(formData.prompts || {}),
        [key]: value,
      },
    })
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-600 bg-blue-50 p-3 rounded border border-blue-200">
        These prompts guide the AI when answering job application questions. They should
        contain instructions, not templates.
      </p>

      <div>
        <Label htmlFor="coverLetter">Cover Letter Guidance</Label>
        <Textarea
          id="coverLetter"
          value={formData.prompts?.cover_letter || ''}
          onChange={(e) => updatePrompt('cover_letter', e.target.value)}
          placeholder="Instructions for writing a cover letter..."
        />
        <p className="text-sm text-gray-500 mt-1">
          Guidance for AI when writing cover letters
        </p>
      </div>

      <div>
        <Label htmlFor="resumeSummary">Resume Summary Guidance</Label>
        <Textarea
          id="resumeSummary"
          value={formData.prompts?.resume_summary || ''}
          onChange={(e) => updatePrompt('resume_summary', e.target.value)}
          placeholder="Instructions for summarizing resume..."
        />
        <p className="text-sm text-gray-500 mt-1">
          Guidance for AI when summarizing your resume
        </p>
      </div>

      <div>
        <Label htmlFor="accomplishments">Key Accomplishments Guidance</Label>
        <Textarea
          id="accomplishments"
          value={formData.prompts?.key_accomplishments || ''}
          onChange={(e) => updatePrompt('key_accomplishments', e.target.value)}
          placeholder="Instructions for highlighting accomplishments..."
        />
        <p className="text-sm text-gray-500 mt-1">
          Guidance for AI when selecting key accomplishments
        </p>
      </div>

      <div>
        <Label htmlFor="experience">Experience Selection Guidance</Label>
        <Textarea
          id="experience"
          value={formData.prompts?.experience_selection || ''}
          onChange={(e) => updatePrompt('experience_selection', e.target.value)}
          placeholder="Instructions for selecting relevant experiences..."
        />
        <p className="text-sm text-gray-500 mt-1">
          Guidance for AI when choosing relevant work experiences
        </p>
      </div>

      <div>
        <Label htmlFor="aiTools">AI Tools Response (Optional)</Label>
        <Textarea
          id="aiTools"
          value={formData.prompts?.ai_tools_response || ''}
          onChange={(e) => updatePrompt('ai_tools_response', e.target.value)}
          placeholder="How to respond to AI tools questions..."
        />
        <p className="text-sm text-gray-500 mt-1">
          Guidance for responding to questions about AI tool usage
        </p>
      </div>
    </div>
  )
}
```

**File:** `web_ui/frontend/src/components/steps/ReviewStep.tsx` (new)

```typescript
import { Button } from '../ui/Button'
import { Card, CardContent } from '../ui/Card'
import { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
  onEditStep?: (step: number) => void
}

export function ReviewStep({ formData, onChange, onEditStep }: StepProps) {
  const steps = [
    { number: 1, title: 'Basic Info' },
    { number: 2, title: 'Resume' },
    { number: 3, title: 'Contact' },
    { number: 4, title: 'Keywords' },
    { number: 5, title: 'Experience' },
    { number: 6, title: 'Prompts' },
  ]

  return (
    <div className="space-y-6">
      <p className="text-gray-600">
        Please review all information before saving. Click on any section to edit.
      </p>

      {/* Basic Info */}
      <Card>
        <CardContent className="pt-6 space-y-2">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold">Basic Information</h3>
              <div className="text-sm text-gray-600 mt-2 space-y-1">
                <p><strong>ID:</strong> {formData.id}</p>
                <p><strong>Name:</strong> {formData.name}</p>
                {formData.preferred_browser && (
                  <p><strong>Browser:</strong> {formData.preferred_browser}</p>
                )}
              </div>
            </div>
            {onEditStep && (
              <Button
                type="button"
                onClick={() => onEditStep(1)}
                variant="outline"
                size="sm"
              >
                Edit
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Resume */}
      <Card>
        <CardContent className="pt-6 space-y-2">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold">Resume & Search</h3>
              <div className="text-sm text-gray-600 mt-2 space-y-1">
                <p><strong>Resume:</strong> {formData.resume_path}</p>
                {formData.search_query && (
                  <p><strong>Search Query:</strong> {formData.search_query}</p>
                )}
              </div>
            </div>
            {onEditStep && (
              <Button
                type="button"
                onClick={() => onEditStep(2)}
                variant="outline"
                size="sm"
              >
                Edit
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Keywords */}
      <Card>
        <CardContent className="pt-6 space-y-2">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold">Keywords</h3>
              <div className="text-sm text-gray-600 mt-2 space-y-1">
                {formData.keywords?.roles?.length! > 0 && (
                  <p><strong>Roles:</strong> {formData.keywords!.roles.join(', ')}</p>
                )}
                {formData.keywords?.tech_stack?.length! > 0 && (
                  <p><strong>Tech:</strong> {formData.keywords!.tech_stack.join(', ')}</p>
                )}
              </div>
            </div>
            {onEditStep && (
              <Button
                type="button"
                onClick={() => onEditStep(4)}
                variant="outline"
                size="sm"
              >
                Edit
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Experience Count */}
      <Card>
        <CardContent className="pt-6 space-y-2">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold">Experience</h3>
              <p className="text-sm text-gray-600 mt-2">
                {formData.experience?.length || 0} experience entries
              </p>
            </div>
            {onEditStep && (
              <Button
                type="button"
                onClick={() => onEditStep(5)}
                variant="outline"
                size="sm"
              >
                Edit
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

#### 2.4 Profile Management Page

**File:** `web_ui/frontend/src/pages/ProfilesPage.tsx` (new)

```typescript
import { useState } from 'react'
import { Button } from '../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { ProfileForm } from '../components/ProfileForm'
import { useToast } from '../lib/toast'
import { profilesApi } from '../lib/api'
import { Profile, ProfileDetailResponse } from '../lib/types'

export function ProfilesPage() {
  const [mode, setMode] = useState<'list' | 'create' | 'edit'>('list')
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [selectedProfileId, setSelectedProfileId] = useState<string>()
  const [loading, setLoading] = useState(false)
  const { addToast } = useToast()

  // Load profiles on mount
  React.useEffect(() => {
    loadProfiles()
  }, [])

  const loadProfiles = async () => {
    setLoading(true)
    try {
      const response = await profilesApi.list()
      setProfiles(response.data.profiles)
    } catch (error) {
      addToast({
        title: 'Failed to load profiles',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteProfile = async (profileId: string) => {
    if (!window.confirm(`Delete profile "${profileId}"?`)) return

    try {
      await profilesApi.delete(profileId)
      addToast({ title: 'Profile deleted' })
      await loadProfiles()
    } catch (error) {
      addToast({
        title: 'Failed to delete profile',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    }
  }

  if (mode === 'list') {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Profiles</h1>
          <Button onClick={() => setMode('create')}>+ New Profile</Button>
        </div>

        {loading ? (
          <p className="text-gray-600">Loading profiles...</p>
        ) : profiles.length === 0 ? (
          <Card>
            <CardContent className="pt-6 text-center">
              <p className="text-gray-600 mb-4">No profiles yet</p>
              <Button onClick={() => setMode('create')}>Create First Profile</Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {profiles.map((profile) => (
              <Card key={profile.id}>
                <CardHeader className="flex flex-row justify-between items-start">
                  <div>
                    <CardTitle>{profile.name}</CardTitle>
                    <p className="text-sm text-gray-600 mt-1">{profile.id}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => {
                        setSelectedProfileId(profile.id)
                        setMode('edit')
                      }}
                      variant="outline"
                      size="sm"
                    >
                      Edit
                    </Button>
                    <Button
                      onClick={() => handleDeleteProfile(profile.id)}
                      variant="destructive"
                      size="sm"
                    >
                      Delete
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="text-sm text-gray-600">
                  <p>Resume: {profile.resume_path}</p>
                  {profile.preferred_browser && (
                    <p>Browser: {profile.preferred_browser}</p>
                  )}
                  {profile.has_experience && (
                    <p className="text-blue-600 mt-1">Has work experience</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (mode === 'create') {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Create Profile</h1>
        <ProfileForm
          onSave={() => {
            setMode('list')
            loadProfiles()
          }}
          onCancel={() => setMode('list')}
        />
      </div>
    )
  }

  if (mode === 'edit' && selectedProfileId) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Edit Profile</h1>
        <ProfileForm
          profileId={selectedProfileId}
          onSave={() => {
            setMode('list')
            loadProfiles()
          }}
          onCancel={() => setMode('list')}
        />
      </div>
    )
  }
}
```

---

### Phase 3: API Integration (2 days)

**File:** `web_ui/frontend/src/lib/types.ts` (new)

```typescript
export interface Profile {
  id: string
  name: string
  resume_path: string
  preferred_browser?: string
  has_experience: boolean
}

export interface ExperienceItem {
  company: string
  role: string
  dates: string
  location?: string
  context?: string
  highlights: string[]
  tech_stack: string[]
  metrics: Record<string, string>
}

export interface ProfileDetailResponse {
  id: string
  name: string
  resume_path: string
  preferred_browser?: string
  user_data_dir?: string
  search_query?: string
  defaults: Record<string, string>
  keywords: Record<string, string[]>
  experience: ExperienceItem[]
  prompts: Record<string, string>
}

export interface ProfileListResponse {
  profiles: Profile[]
}

export interface ResumeUploadResponse {
  filename: string
  path: string
}
```

**File:** `web_ui/frontend/src/lib/api.ts` (extend)

```typescript
// Add to existing api.ts

export const profilesApi = {
  list: () => api.get<ProfileListResponse>('/api/profiles'),
  get: (id: string) => api.get<Profile>(`/api/profiles/${id}`),
  getDetail: (id: string) => api.get<ProfileDetailResponse>(`/api/profiles/${id}/detail`),
  create: (profile: ProfileDetailResponse) =>
    api.post<ProfileDetailResponse>('/api/profiles', profile),
  update: (id: string, profile: ProfileDetailResponse) =>
    api.put<ProfileDetailResponse>(`/api/profiles/${id}`, profile),
  delete: (id: string) =>
    api.delete(`/api/profiles/${id}`),
  uploadResume: (id: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<ResumeUploadResponse>(`/api/profiles/${id}/resume`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
```

---

### Phase 4: Navigation Integration (1-2 days)

**File:** `web_ui/frontend/src/App.tsx` (modify)

Add "Profiles" tab:

```typescript
import { useState } from 'react'
import { ProfilesPage } from './pages/ProfilesPage'
import { DiscoverForm } from './components/DiscoverForm'
import { ApplyForm } from './components/ApplyForm'

function App() {
  const [activeTab, setActiveTab] = useState<'profiles' | 'discover' | 'apply'>('profiles')

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 justify-between">
            <div className="flex space-x-8">
              <button
                onClick={() => setActiveTab('profiles')}
                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                  activeTab === 'profiles'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }`}
              >
                Profiles
              </button>
              <button
                onClick={() => setActiveTab('discover')}
                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                  activeTab === 'discover'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }`}
              >
                Discover
              </button>
              <button
                onClick={() => setActiveTab('apply')}
                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                  activeTab === 'apply'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }`}
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        {activeTab === 'profiles' && <ProfilesPage />}
        {activeTab === 'discover' && <DiscoverForm />}
        {activeTab === 'apply' && <ApplyForm />}
      </main>
    </div>
  )
}

export default App
```

---

## Files to Create/Modify

### Backend
- `pyproject.toml` - Add tomli-w dependency
- `src/job_ai_auto_apply_ui/profile_manager.py` - Add save_profile()
- `web_ui/backend/models/profile.py` - New file, Pydantic models
- `web_ui/backend/routes/profiles.py` - Extend with 6 new endpoints

### Frontend
- `web_ui/frontend/src/lib/types.ts` - New file, TypeScript interfaces
- `web_ui/frontend/src/lib/api.ts` - Extend profilesApi
- `web_ui/frontend/src/components/ui/Textarea.tsx` - New component
- `web_ui/frontend/src/components/ui/Tag.tsx` - New component
- `web_ui/frontend/src/components/ui/MultiInput.tsx` - New component
- `web_ui/frontend/src/components/ui/FileUpload.tsx` - New component
- `web_ui/frontend/src/components/ProfileForm.tsx` - New component
- `web_ui/frontend/src/components/steps/BasicInfoStep.tsx` - New component
- `web_ui/frontend/src/components/steps/ResumeStep.tsx` - New component
- `web_ui/frontend/src/components/steps/ContactStep.tsx` - New component
- `web_ui/frontend/src/components/steps/KeywordsStep.tsx` - New component
- `web_ui/frontend/src/components/steps/ExperienceStep.tsx` - New component
- `web_ui/frontend/src/components/steps/PromptsStep.tsx` - New component
- `web_ui/frontend/src/components/steps/ReviewStep.tsx` - New component
- `web_ui/frontend/src/pages/ProfilesPage.tsx` - New file
- `web_ui/frontend/src/App.tsx` - Add profiles tab

**Total:** 20 new/modified files

---

## Technology Decisions

### Backend
- **TOML Writing:** tomli-w library (write-only, separate from tomllib)
- **Validation:** Pydantic models for type safety and validation
- **File Operations:** Direct file I/O to profiles/ directory

### Frontend
- **Form Library:** Manual useState (evaluate React Hook Form after Phase 1)
- **State Management:** No additional library (useState/useEffect only)
- **Component Library:** Continue with custom shadcn/ui-inspired components
- **Form Validation:** Hybrid: HTML5 + custom per-step validation

### No Major Dependencies Added
- React Hook Form not added yet (manual approach suffices for MVP)
- No additional state management (useState is fine)
- No new UI library (custom components sufficient)

---

## Gotchas & Considerations

### Backend Gotchas

1. **Profile ID Validation**
   - Must be valid slug (alphanumeric, underscore, hyphen)
   - Used as filename, so filesystem restrictions apply
   - Prevent collision with existing files

2. **Resume Path Resolution**
   - Support both relative and absolute paths
   - Relative paths resolve against repo root
   - Validate file exists on load, not on save

3. **Experience Array Handling**
   - Can be None (not provided) vs empty array (no experience)
   - Preserve distinction in TOML serialization
   - Handle empty strings vs None for optional fields

4. **File Upload Security**
   - Validate PDF MIME type
   - Size limit (max 10MB)
   - Sanitize filenames (prevent path traversal)
   - Store in controlled directory (resumes/)

5. **Concurrent Edits**
   - No locking mechanism
   - Last write wins
   - Consider adding version/etag check later

6. **Queue Deletion Cascade**
   - Deleting profile doesn't delete queue
   - Should warn user or cascade delete

### Frontend Gotchas

1. **Deep Object Updates**
   - Nested state (defaults.*, keywords.*) requires careful immutability
   - Consider Immer library if handling becomes complex

2. **Array Field Performance**
   - Experience array can be large (10+ entries)
   - Each entry has nested arrays
   - May need virtualization if >20 entries

3. **File Upload Progress**
   - Show progress bar for large files
   - Handle upload cancellation
   - Retry on network failure

4. **Textarea Auto-Resize**
   - Prompt fields can be 500+ characters
   - Consider auto-growing textarea or fixed height with scroll

5. **Mobile Responsiveness**
   - Multi-column layouts may break on mobile
   - Test wizard navigation on mobile devices

6. **Unsaved Changes Warning**
   - Multi-step wizard has intermediate state
   - Implement "unsaved changes" warning before navigation

### Validation Edge Cases

1. **Empty Arrays vs Null**
   - Keywords with empty arrays vs None
   - Experience with empty array vs None
   - Backend must preserve distinction

2. **URL Validation**
   - Defaults fields (portfolio_url, github_url, linkedin_url)
   - Allow free-form or enforce format?

3. **Phone Number Formats**
   - Defaults.phone - no validation currently
   - International formats support?

4. **EEO Field Values**
   - Currently free-form
   - Consider enums for consistency

5. **Resume Path Circular Reference**
   - Upload changes path → triggers re-render
   - Implement controlled component pattern to prevent loops

---

## Testing Strategy

### Backend Tests
- `test_save_profile_creates_file()` - File creation
- `test_save_and_load_roundtrip()` - Serialization round-trip
- `test_save_profile_handles_optional_fields()` - Optional field handling
- `test_file_upload_validation()` - Upload validation
- `test_concurrent_writes()` - Race condition handling

### Frontend Tests
- `test_wizard_navigation()` - Step navigation
- `test_form_validation()` - Per-step validation
- `test_array_operations()` - Add/remove entries
- `test_file_upload()` - Upload success/failure
- `test_profile_list_actions()` - Edit/delete operations

### Integration Tests
- `test_create_profile_flow()` - Full creation workflow
- `test_update_profile_flow()` - Full update workflow
- `test_resume_upload_and_save()` - Upload + profile save
- `test_delete_profile()` - Deletion confirmation

---

## Timeline & Milestones

### Week 1 (5 days)
- **Days 1-2:** Backend foundation
  - Add tomli-w, create save_profile(), create models
  - 6 new endpoints
  - Unit tests

- **Days 3-4:** Frontend base components
  - Textarea, Tag, MultiInput, FileUpload components
  - Basic styles and interactions

- **Day 5:** Wizard container + first 2 steps
  - ProfileForm with navigation
  - BasicInfoStep, ResumeStep
  - Form state management

### Week 2 (5 days)
- **Days 1-2:** Remaining step components
  - ContactStep, KeywordsStep, ExperienceStep
  - PromptsStep, ReviewStep
  - All with proper validation

- **Day 3:** List and management
  - ProfileList component
  - ProfilesPage with mode switching
  - Delete confirmation

- **Day 4:** API integration
  - Wire wizard to backend
  - Handle loading/error states
  - Success notifications

- **Day 5:** Bug fixes + polish
  - Form validation refinement
  - Error message improvements
  - Loading state animations

### Week 3 (5 days)
- **Days 1-2:** Validation & error handling
  - Field validation rules
  - API error handling
  - Validation error display

- **Days 3-4:** UX enhancements
  - Unsaved changes warning
  - Mobile responsive design
  - Accessibility (ARIA, keyboard nav)
  - Progress indicators

- **Day 5:** Final testing
  - Integration test suite
  - Cross-browser testing
  - Accessibility audit
  - Documentation

**Total: ~15 days**

---

## Implementation Checklist

### Phase 1: Backend
- [ ] Add tomli-w to pyproject.toml
- [ ] Implement save_profile() in profile_manager.py
- [ ] Create web_ui/backend/models/profile.py
- [ ] Add GET /api/profiles/{id}/detail endpoint
- [ ] Add POST /api/profiles endpoint
- [ ] Add PUT /api/profiles/{id} endpoint
- [ ] Add DELETE /api/profiles/{id} endpoint (optional)
- [ ] Add POST /api/profiles/{id}/resume endpoint
- [ ] Write unit tests for save/load/upload
- [ ] Test with manual API calls (curl or Postman)

### Phase 2: Frontend
- [ ] Create Textarea component
- [ ] Create Tag component
- [ ] Create MultiInput component
- [ ] Create FileUpload component
- [ ] Create ProfileForm wizard container
- [ ] Create BasicInfoStep component
- [ ] Create ResumeStep component
- [ ] Create ContactStep component
- [ ] Create KeywordsStep component
- [ ] Create ExperienceStep component
- [ ] Create PromptsStep component
- [ ] Create ReviewStep component
- [ ] Create ProfileList component
- [ ] Create ProfilesPage
- [ ] Test component rendering

### Phase 3: Integration
- [ ] Create web_ui/frontend/src/lib/types.ts
- [ ] Extend web_ui/frontend/src/lib/api.ts
- [ ] Wire ProfileForm to API calls
- [ ] Implement form submission
- [ ] Add success/error toasts
- [ ] Test create flow end-to-end
- [ ] Test update flow end-to-end
- [ ] Test delete flow

### Phase 4: Navigation
- [ ] Add "Profiles" tab to App.tsx
- [ ] Set up tab navigation state
- [ ] Route ProfilesPage to profiles tab
- [ ] Test tab switching
- [ ] Ensure other tabs still work

### Phase 5: Polish
- [ ] Add form validation
- [ ] Add field error displays
- [ ] Add unsaved changes warning
- [ ] Mobile responsive testing
- [ ] Accessibility testing
- [ ] Cross-browser testing
- [ ] Load test with large profiles
- [ ] Documentation/comments
- [ ] Final user testing

---

## Success Metrics

✅ **Completion criteria:**
- [ ] Can create profile via UI
- [ ] Can edit profile via UI
- [ ] Can upload resume PDF
- [ ] Can delete profile
- [ ] All required fields validated
- [ ] Complex nested structures working
- [ ] Profile saves as valid TOML
- [ ] Profiles editable multiple times
- [ ] Error messages clear and helpful
- [ ] Mobile responsive
- [ ] Keyboard accessible
- [ ] All tests passing

