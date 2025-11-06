# Settings UI Implementation Plan

**Document Status**: Complete Plan
**Last Updated**: November 6, 2025
**Author**: Claude Code + User Requirements

---

## 1. Project Overview & Goals

### Objective
Create a comprehensive Settings UI within the web application that allows users to easily manage application configuration stored in `.env` files. Instead of manually editing `.env` files, users can modify settings through an intuitive web interface with validation, security, and immediate feedback.

### Key Goals
- **Usability**: Intuitive interface organized by logical categories
- **Safety**: Validation before saving, confirmation for sensitive changes
- **Security**: Proper handling of API keys and credentials
- **Maintainability**: Clear, documented implementation with phases
- **Performance**: No restart required for most settings (immediate in-memory updates)

### User Requirements
Based on stakeholder input:
- ✅ **Categories**: LLM Configuration, Browser & Automation, Discovery Settings, Diagnostics & Debug
- ✅ **Security**: Masked sensitive data (••••) with reveal button
- ✅ **Behavior**: Immediate apply without server restart
- ✅ **Validation**: Type validation, range checks, API key testing, path validation

---

## 2. Complete Environment Variables Inventory

### 2.1 LLM & Provider Configuration

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `LLM_PROVIDER` | string | None | No | LLM provider selection: `openrouter` or `google` |
| `LLM_MODEL` | string | None | No | Model identifier for selected provider |
| `OPENROUTER_API_KEY` | string | None | **Yes** | API key for OpenRouter LLM provider |
| `GOOGLE_API_KEY` | string | None | **Yes** | API key for Google (Gemini) provider |
| `LLM_TEMPERATURE` | float | 0.0 | No | Temperature control (range: 0.0-2.0) |
| `LLM_TIMEOUT_SECONDS` | int | 30 | No | Request timeout in seconds |
| `LLM_REFERER` | string | None | No | Optional referer header (provider branding) |
| `LLM_USER_AGENT` | string | None | No | Optional user agent override (provider branding) |

**Section Notes**:
- Only one of OPENROUTER_API_KEY or GOOGLE_API_KEY needs to be set
- LLM_PROVIDER determines which key is used
- Temperature range enforced: 0.0 (deterministic) to 2.0 (more creative)

---

### 2.2 Browser & Automation Settings

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `BROWSER_LOCALE` | string | "en-US" | No | Browser locale (e.g., en-US, fr-FR, de-DE) |
| `BROWSER_TIMEZONE` | string | "America/Los_Angeles" | No | Browser timezone (IANA format) |
| `BROWSER_VIEWPORT_WIDTH` | int | 1280 | No | Browser viewport width in pixels |
| `BROWSER_VIEWPORT_HEIGHT` | int | 800 | No | Browser viewport height in pixels |
| `AUTO_APPLY_DISABLE_DEFAULT_EXTENSIONS` | bool | True | No | Disable browser extensions (true = disabled) |
| `AUTO_APPLY_CHROME_ARGS` | list | See below | No | Semicolon-separated Chrome command line arguments |

**Default Chrome Args**:
```
--disable-autofill;--disable-autofill-keyboard-accessory-view;--disable-features=Autofill,AutofillServerCommunication
```

**Section Notes**:
- Viewport settings affect how forms are rendered and filled
- Chrome args use semicolon delimiter (not comma) for proper parsing
- Locale and timezone spoof helps avoid detection and ensures consistent form rendering

**Valid Timezones** (common examples):
- `America/New_York`, `America/Chicago`, `America/Denver`, `America/Los_Angeles`
- `Europe/London`, `Europe/Paris`, `Europe/Berlin`
- `Asia/Tokyo`, `Asia/Singapore`, `Australia/Sydney`

**Valid Locales** (ISO 639-1 + ISO 3166):
- `en-US`, `en-GB`, `fr-FR`, `de-DE`, `es-ES`, `ja-JP`, `zh-CN`, `pt-BR`

---

### 2.3 General Behavior Settings

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `DWELL_SECONDS` | float | 0.8 | No | Delay between actions (human-like behavior) |
| `JITTER_SECONDS` | float | 0.4 | No | Random variance in delays |
| `MAX_TABS` | int | 3 | No | Maximum concurrent browser tabs |
| `RETRIES` | int | 2 | No | Retry attempts for failed operations |
| `DISCOVERY_WINDOW_HOURS` | int | 24 | No | Default discovery time window in hours |
| `DISCOVERY_CAP` | int | 10 | No | Default maximum jobs to discover (1-100) |
| `AUTO_APPLY_PROFILES_DIR` | string | "profiles" | No | Directory path for job profiles |

**Section Notes**:
- DWELL_SECONDS + JITTER_SECONDS combined for human-like timing
- MAX_TABS controls parallelization (higher = faster but more resource intensive)
- DISCOVERY_CAP has strict bounds (1-100)
- AUTO_APPLY_PROFILES_DIR can be absolute or relative path

**Validation Rules**:
- DWELL_SECONDS: min=0.1, max=5.0
- JITTER_SECONDS: min=0.0, max=2.0
- MAX_TABS: min=1, max=10
- RETRIES: min=0, max=5
- DISCOVERY_WINDOW_HOURS: min=1, max=8760 (1 year)
- DISCOVERY_CAP: min=1, max=100
- AUTO_APPLY_PROFILES_DIR: must be writable directory

---

### 2.4 Networking & Proxy Settings

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `PROXY_URL` | string | None | **Yes** | Full proxy URL with credentials: `http://user:pass@host:port` |
| `HTTP_PROXY` | string | None | **Yes** | HTTP proxy for requests |
| `HTTPS_PROXY` | string | None | **Yes** | HTTPS proxy for secure requests |
| `USER_AGENT` | string | None | No | Custom User-Agent header override |
| `ALLOWED_DOMAINS` | list | "google.*,jobs.lever.co" | No | Comma-separated domains allowed (supports wildcards) |

**Section Notes**:
- Only one of PROXY_URL, HTTP_PROXY/HTTPS_PROXY should be set
- PROXY_URL is simpler (single value); HTTP_PROXY/HTTPS_PROXY for protocol-specific proxies
- ALLOWED_DOMAINS enforces security (prevents crawling unintended sites)
- Wildcard format: `google.*` matches google.com, google.fr, etc.

**Validation Rules**:
- PROXY_URL: must be valid URL format
- USER_AGENT: no validation (any string accepted)
- ALLOWED_DOMAINS: comma-separated, no spaces

---

### 2.5 Diagnostics & Artifacts

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `AUTO_APPLY_DIAGNOSTICS` | bool | False | No | Enable ALL diagnostic captures (master switch) |
| `AUTO_APPLY_CAPTURE_VIDEO` | bool | False | No | Record browser session video |
| `AUTO_APPLY_CAPTURE_HAR` | bool | False | No | Record network traffic (HAR format) |
| `AUTO_APPLY_ARTIFACTS_DIR` | string | "data/artifacts" | No | Directory to store diagnostic artifacts |

**Section Notes**:
- AUTO_APPLY_DIAGNOSTICS=1 enables all captures (overrides individual flags)
- Video and HAR capture consume significant disk space
- Artifacts essential for debugging application failures
- Artifacts are namespaced per profile

**Validation Rules**:
- AUTO_APPLY_ARTIFACTS_DIR: must be writable directory, create if doesn't exist

---

### 2.6 Resume Upload Settings (Advanced)

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `AUTO_APPLY_USE_LLM_LOCATOR` | bool | False | No | Enable LLM-powered resume input field detection |
| `AUTO_APPLY_DEBUG_RESUME_WIDGET` | bool | False | No | Emit DOM snapshot on resume upload failure |
| `AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS` | int | 25 | No | Maximum wait time for resume upload completion |

**Section Notes**:
- AUTO_APPLY_USE_LLM_LOCATOR helps on non-standard form layouts
- AUTO_APPLY_DEBUG_RESUME_WIDGET useful for troubleshooting upload failures
- Long timeouts (30+s) needed for slow form processors

**Validation Rules**:
- AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS: min=5, max=120

---

### 2.7 CAPTCHA Detection Settings (Advanced)

| Variable | Type | Default | Sensitive | Description |
|----------|------|---------|-----------|-------------|
| `AUTO_APPLY_CAPTCHA_VISUAL_CHECK` | bool | False | No | Enable vision-based CAPTCHA detection |
| `AUTO_APPLY_CAPTCHA_VISION_MODEL` | string | "google/gemini-2.0-flash-exp:free" | No | Vision model for CAPTCHA analysis |
| `CAPTCHA_VISUAL_DELAY_SECONDS` | float | 3.0 | No | Wait before taking screenshot for analysis |
| `AUTO_APPLY_CAPTCHA_TIMEOUT_SECONDS` | int | 60 | No | Timeout for manual CAPTCHA solving |

**Section Notes**:
- CAPTCHA_VISUAL_CHECK enables automatic CAPTCHA detection (requires vision model)
- Common models: `google/gemini-2.0-flash-exp:free`, `openrouter/anthropic/claude-3-5-sonnet`
- CAPTCHA_VISUAL_DELAY_SECONDS allows form to fully load before screenshot
- In supervised mode, user has CAPTCHA_TIMEOUT_SECONDS to solve manually

**Validation Rules**:
- CAPTCHA_VISUAL_DELAY_SECONDS: min=1.0, max=10.0
- AUTO_APPLY_CAPTCHA_TIMEOUT_SECONDS: min=10, max=300

---

## 3. Current Configuration System Analysis

### 3.1 How Settings Are Loaded

**Source File**: `src/job_ai_auto_apply_ui/config.py`

**Current Pattern**:
- `Settings` dataclass loads from environment variables
- Uses factory defaults: `field(default_factory=...)`
- Helper functions for type coercion: `_get_float()`, `_get_int()`, `_get_bool()`, `_get_chrome_args()`
- Boolean convention: accepts `1/0`, `true/false`, `on/off`, `yes/no` (case-insensitive)
- List parsing: Chrome args use `;` delimiter, domains use `,` delimiter

**Key Properties**:
```python
@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Each setting is a field with default_factory
    llm_provider: str = field(default_factory=lambda: os.getenv('LLM_PROVIDER', ''))
    llm_model: str = field(default_factory=lambda: os.getenv('LLM_MODEL', ''))
    # ... etc
```

**Loading Function**:
```python
def load_settings() -> Settings:
    """Load settings from environment variables."""
    return Settings()
```

**Important Notes**:
- Settings are loaded fresh each time `load_settings()` is called
- NOT cached as singleton (each call creates new instance)
- Environment variables set at Python startup persist for lifetime of process
- Changes to `.env` file are NOT automatically reflected (would need restart)

### 3.2 Validation Strategy

**Current State**: Minimal validation at load time
- Type coercion happens automatically
- Heavy validation in `profile_manager.py` (profile-specific)
- No explicit input validation for settings themselves

**For Settings UI**: Need explicit validation layer
- Validate before writing to `.env`
- Test API keys before persisting
- Check path validity
- Range validation for numeric values

### 3.3 Sensitive Data Handling

**Current State**: No special handling
- API keys can be read from environment in any part of code
- No masking or encryption

**For Settings UI**: Need masking layer
- Never return full API key values in API responses
- Use placeholder: `••••••••` or last 4 chars: `...abc123`
- Allow updating without revealing current value

---

## 4. Backend Implementation Plan

### 4.1 New Route: `web_ui/backend/routes/settings.py`

Create new file: `web_ui/backend/routes/settings.py`

**Endpoints to Implement**:

#### **1. GET /api/settings**
Returns current settings grouped by category, with sensitive values masked.

**Response**:
```json
{
  "categories": [
    {
      "id": "llm",
      "name": "LLM & AI Configuration",
      "description": "API keys, model selection, and LLM behavior settings",
      "icon": "brain"
    },
    ...
  ],
  "fields": {
    "llm": [
      {
        "key": "LLM_PROVIDER",
        "label": "LLM Provider",
        "description": "Choose between OpenRouter and Google (Gemini)",
        "type": "string",
        "default": "",
        "current": "openrouter",
        "sensitive": false,
        "validation": {
          "options": ["openrouter", "google"]
        }
      },
      {
        "key": "OPENROUTER_API_KEY",
        "label": "OpenRouter API Key",
        "description": "API key for OpenRouter (keep secret)",
        "type": "password",
        "default": "",
        "current": "••••••••",  // MASKED
        "sensitive": true,
        "validation": null
      },
      ...
    ],
    ...
  }
}
```

**Implementation Notes**:
- Read from environment variables (current state)
- Mask sensitive fields using helper function
- Group by category
- Include validation metadata for frontend

---

#### **2. PUT /api/settings**
Update settings and persist to `.env` file.

**Request**:
```json
{
  "updates": {
    "DWELL_SECONDS": "1.0",
    "JITTER_SECONDS": "0.5",
    "LLM_PROVIDER": "google",
    "GOOGLE_API_KEY": "new-secret-key-here"
  }
}
```

**Response** (success):
```json
{
  "success": true,
  "message": "Settings saved successfully",
  "updated_keys": ["DWELL_SECONDS", "JITTER_SECONDS", "LLM_PROVIDER", "GOOGLE_API_KEY"],
  "requires_restart": false,
  "updated_settings": { /* updated field objects */ }
}
```

**Response** (validation error):
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "DWELL_SECONDS": "Must be between 0.1 and 5.0",
    "GOOGLE_API_KEY": "API key test failed: Invalid authentication"
  }
}
```

**Implementation Logic**:
1. Parse request JSON
2. Validate all updates (see validation functions below)
3. Test API keys if provided
4. Write to `.env` file using `python-dotenv`
5. Update in-memory config (reload settings)
6. Return updated state

---

#### **3. POST /api/settings/validate**
Validate settings without persisting.

**Request**:
```json
{
  "settings": {
    "DWELL_SECONDS": "1.0",
    "LLM_TEMPERATURE": "0.5",
    "GOOGLE_API_KEY": "test-key"
  }
}
```

**Response**:
```json
{
  "valid": true,
  "errors": {},
  "warnings": []
}
```

or with errors:

```json
{
  "valid": false,
  "errors": {
    "DWELL_SECONDS": "Must be between 0.1 and 5.0",
    "LLM_TEMPERATURE": "Must be between 0.0 and 2.0"
  },
  "warnings": [
    "GOOGLE_API_KEY: Could not test API connectivity"
  ]
}
```

---

#### **4. GET /api/settings/categories**
Return category definitions (used by frontend to build dynamic UI).

**Response**:
```json
{
  "categories": [
    {
      "id": "llm",
      "name": "LLM & AI Configuration",
      "description": "API keys and model selection",
      "icon": "brain",
      "fields": ["LLM_PROVIDER", "LLM_MODEL", ...]
    },
    ...
  ]
}
```

---

#### **5. POST /api/settings/reset**
Reset specific settings to defaults.

**Request**:
```json
{
  "keys": ["DWELL_SECONDS", "JITTER_SECONDS"],
  "reset_all": false
}
```

**Response**: Same as PUT (returns updated settings)

---

### 4.2 Backend Model: `web_ui/backend/models/settings.py`

Create new file: `web_ui/backend/models/settings.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any, Dict

class SettingsCategory(BaseModel):
    """Settings category metadata."""
    id: str = Field(..., description="Category identifier (e.g., 'llm')")
    name: str = Field(..., description="User-facing category name")
    description: str = Field(..., description="Category description")
    icon: Optional[str] = Field(None, description="Icon name (e.g., 'brain', 'settings')")

class SettingValidation(BaseModel):
    """Validation rules for a setting."""
    min: Optional[float] = None
    max: Optional[float] = None
    pattern: Optional[str] = None  # Regex pattern
    options: Optional[list[str]] = None  # Valid enum values

class SettingField(BaseModel):
    """Individual setting field."""
    key: str = Field(..., description="Environment variable name")
    label: str = Field(..., description="User-facing label")
    description: str = Field(..., description="Help text")
    type: Literal["string", "int", "float", "bool", "list", "password"] = Field(...)
    default: Any = Field(..., description="Default value")
    current: Any = Field(..., description="Current value (masked if sensitive)")
    sensitive: bool = Field(False, description="Whether to mask in responses")
    validation: Optional[SettingValidation] = None

class SettingsResponse(BaseModel):
    """Settings GET response."""
    categories: list[SettingsCategory]
    fields: Dict[str, list[SettingField]] = Field(..., description="Category ID -> Fields")

class SettingsUpdateRequest(BaseModel):
    """Settings PUT request."""
    updates: Dict[str, Any] = Field(..., description="Key -> Value pairs to update")

class ValidationResult(BaseModel):
    """Validation result."""
    valid: bool
    errors: Dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
```

---

### 4.3 Implementation Functions

Create utility functions in `web_ui/backend/routes/settings.py`:

#### **A. Mask Sensitive Values**
```python
def mask_sensitive(key: str, value: str) -> str:
    """Mask sensitive values for API responses."""
    if not value:
        return ""

    sensitive_keys = [
        'API_KEY', 'SECRET', 'PASSWORD', 'TOKEN', 'PROXY'
    ]

    if any(s in key.upper() for s in sensitive_keys):
        # Show last 4 characters
        if len(value) > 4:
            return f"••••{value[-4:]}"
        return "••••••••"

    return value
```

#### **B. Validate Settings**
```python
def validate_settings(updates: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate settings before persisting.
    Returns dict of key -> error message.
    """
    errors = {}

    # LLM_TEMPERATURE validation
    if 'LLM_TEMPERATURE' in updates:
        try:
            temp = float(updates['LLM_TEMPERATURE'])
            if not 0.0 <= temp <= 2.0:
                errors['LLM_TEMPERATURE'] = 'Must be between 0.0 and 2.0'
        except ValueError:
            errors['LLM_TEMPERATURE'] = 'Must be a valid number'

    # DWELL_SECONDS validation
    if 'DWELL_SECONDS' in updates:
        try:
            dwell = float(updates['DWELL_SECONDS'])
            if not 0.1 <= dwell <= 5.0:
                errors['DWELL_SECONDS'] = 'Must be between 0.1 and 5.0'
        except ValueError:
            errors['DWELL_SECONDS'] = 'Must be a valid number'

    # DISCOVERY_CAP validation
    if 'DISCOVERY_CAP' in updates:
        try:
            cap = int(updates['DISCOVERY_CAP'])
            if not 1 <= cap <= 100:
                errors['DISCOVERY_CAP'] = 'Must be between 1 and 100'
        except ValueError:
            errors['DISCOVERY_CAP'] = 'Must be a valid integer'

    # LLM_PROVIDER validation
    if 'LLM_PROVIDER' in updates:
        provider = updates['LLM_PROVIDER']
        if provider not in ['openrouter', 'google']:
            errors['LLM_PROVIDER'] = 'Must be "openrouter" or "google"'

    # AUTO_APPLY_ARTIFACTS_DIR validation
    if 'AUTO_APPLY_ARTIFACTS_DIR' in updates:
        path = Path(updates['AUTO_APPLY_ARTIFACTS_DIR'])
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors['AUTO_APPLY_ARTIFACTS_DIR'] = f'Invalid path: {str(e)}'

    # ... more validations

    return errors
```

#### **C. Test API Keys**
```python
async def test_api_key(provider: str, api_key: str) -> tuple[bool, str]:
    """
    Test if API key is valid by making a simple API call.
    Returns (is_valid, error_message).
    """
    if provider == 'openrouter':
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://api.openrouter.ai/api/v1/models',
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=10
                )
                return response.status_code == 200, ""
        except Exception as e:
            return False, str(e)

    elif provider == 'google':
        try:
            # Use Google API client to validate
            # ...implementation depends on google-api-python-client
            return True, ""
        except Exception as e:
            return False, str(e)

    return False, "Unknown provider"
```

#### **D. Convert to ENV Format**
```python
def to_env_value(key: str, value: Any) -> str:
    """Convert Python value to .env file format (all strings)."""

    if isinstance(value, bool):
        # Boolean to 0/1
        return '1' if value else '0'

    if isinstance(value, list):
        # List to comma or semicolon separated
        if key == 'AUTO_APPLY_CHROME_ARGS':
            return ';'.join(str(v) for v in value)
        else:
            return ','.join(str(v) for v in value)

    if isinstance(value, (int, float)):
        return str(value)

    return str(value)
```

#### **E. Load .env File**
```python
from dotenv import load_dotenv, set_key, unset_key
from pathlib import Path

def get_env_path() -> Path:
    """Get path to .env file."""
    return Path(__file__).parent.parent.parent.parent / '.env'

def read_env_file() -> Dict[str, str]:
    """Read current .env file values."""
    env_path = get_env_path()
    if not env_path.exists():
        return {}

    load_dotenv(env_path)
    return dict(os.environ)

def write_env_file(key: str, value: str) -> None:
    """Write single key to .env file."""
    set_key(str(get_env_path()), key, value)

def remove_env_file(key: str) -> None:
    """Remove key from .env file."""
    unset_key(str(get_env_path()), key)
```

---

### 4.4 Wire Settings Routes

Update `web_ui/backend/app.py`:

```python
from .routes import discover, settings  # Add import

app = FastAPI(...)

# Register routers
app.include_router(discover.router)
app.include_router(settings.router)  # Add this line
```

---

### 4.5 Dependencies

Ensure `python-dotenv` is installed:
```bash
pip install python-dotenv
```

Add to `web_ui/backend/requirements.txt` or `pyproject.toml`:
```
python-dotenv>=1.0.0
```

---

## 5. Frontend Implementation Plan

### 5.1 Main Settings Page: `web_ui/frontend/src/pages/SettingsPage.tsx`

Create new file: `web_ui/frontend/src/pages/SettingsPage.tsx`

```typescript
import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useToast } from '@/lib/toast'
import { settingsApi } from '@/lib/api'
import type { SettingsResponse, SettingField } from '@/lib/types'
import CategoryTabs from '@/components/settings/CategoryTabs'
import SettingsForm from '@/components/settings/SettingsForm'

export function SettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [activeCategory, setActiveCategory] = useState('llm')
  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [formValues, setFormValues] = useState<Record<string, any>>({})
  const [changes, setChanges] = useState<Record<string, any>>({})
  const [needsRestart, setNeedsRestart] = useState(false)
  const { addToast } = useToast()

  // Load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    try {
      setLoading(true)
      const response = await settingsApi.getSettings()
      setSettings(response.data)

      // Initialize form with current values
      const initial: Record<string, any> = {}
      response.data.fields['llm'].forEach(field => {
        initial[field.key] = field.current
      })
      // ... populate for all categories

      setFormValues(initial)
      setChanges({})
    } catch (error) {
      addToast({
        title: 'Error',
        description: 'Failed to load settings',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  function handleChange(key: string, value: any) {
    setFormValues(prev => ({ ...prev, [key]: value }))
    setChanges(prev => ({ ...prev, [key]: value }))
  }

  async function handleSave() {
    try {
      setSaving(true)
      const response = await settingsApi.updateSettings(changes)

      addToast({
        title: 'Success',
        description: 'Settings saved successfully',
      })

      setNeedsRestart(response.data.requires_restart)
      setChanges({})

      // Reload to reflect changes
      await loadSettings()
    } catch (error: any) {
      const errors = error.response?.data?.errors
      if (errors) {
        Object.entries(errors).forEach(([key, message]) => {
          addToast({
            title: 'Validation Error',
            description: `${key}: ${message}`,
            variant: 'destructive',
          })
        })
      } else {
        addToast({
          title: 'Error',
          description: 'Failed to save settings',
          variant: 'destructive',
        })
      }
    } finally {
      setSaving(false)
    }
  }

  function handleReset() {
    // Reset to last saved values
    if (settings) {
      const values: Record<string, any> = {}
      Object.values(settings.fields).forEach(categoryFields => {
        categoryFields.forEach(field => {
          values[field.key] = field.current
        })
      })
      setFormValues(values)
      setChanges({})
    }
  }

  if (loading || !settings) {
    return <div className="p-6">Loading settings...</div>
  }

  const currentCategoryFields = settings.fields[activeCategory] || []

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-gray-600">Manage application configuration</p>
      </div>

      {needsRestart && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800">
          <strong>⚠️ Restart Required</strong>
          <p className="text-sm mt-1">Some changes require a server restart to take effect.</p>
        </div>
      )}

      <CategoryTabs
        categories={settings.categories}
        activeCategory={activeCategory}
        onChange={setActiveCategory}
      />

      <SettingsForm
        fields={currentCategoryFields}
        values={formValues}
        onChange={handleChange}
        onSave={handleSave}
        onReset={handleReset}
        saving={saving}
        hasChanges={Object.keys(changes).length > 0}
      />
    </div>
  )
}
```

---

### 5.2 Component: CategoryTabs

Create: `web_ui/frontend/src/components/settings/CategoryTabs.tsx`

```typescript
import type { SettingsCategory } from '@/lib/types'

interface CategoryTabsProps {
  categories: SettingsCategory[]
  activeCategory: string
  onChange: (categoryId: string) => void
}

export function CategoryTabs({
  categories,
  activeCategory,
  onChange,
}: CategoryTabsProps) {
  return (
    <div className="border-b border-gray-200">
      <div className="flex space-x-8 overflow-x-auto">
        {categories.map(category => (
          <button
            key={category.id}
            onClick={() => onChange(category.id)}
            className={`px-1 py-4 border-b-2 font-medium text-sm transition-colors ${
              activeCategory === category.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
            }`}
            title={category.description}
          >
            {category.icon && <span className="mr-2">{category.icon}</span>}
            {category.name}
          </button>
        ))}
      </div>
    </div>
  )
}
```

---

### 5.3 Component: SettingField

Create: `web_ui/frontend/src/components/settings/SettingField.tsx`

```typescript
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import type { SettingField as SettingFieldType } from '@/lib/types'
import SensitiveField from './SensitiveField'

interface SettingFieldProps {
  field: SettingFieldType
  value: any
  onChange: (value: any) => void
  error?: string
}

export function SettingField({
  field,
  value,
  onChange,
  error,
}: SettingFieldProps) {
  const handleChange = (newValue: any) => {
    onChange(newValue)
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={field.key}>
        {field.label}
        {field.sensitive && <span className="text-red-500">*</span>}
      </Label>

      <p className="text-sm text-gray-600">{field.description}</p>

      {field.type === 'password' && (
        <SensitiveField
          id={field.key}
          value={value}
          onChange={handleChange}
          placeholder="Enter API key or credential"
        />
      )}

      {field.type === 'string' && field.validation?.options && (
        <Select
          id={field.key}
          value={value || ''}
          onChange={(e) => handleChange(e.target.value)}
        >
          <option value="">-- Select --</option>
          {field.validation.options.map(opt => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </Select>
      )}

      {(field.type === 'string' || field.type === 'list') &&
        (!field.validation?.options) && (
          <Input
            id={field.key}
            type="text"
            value={value || ''}
            onChange={(e) => handleChange(e.target.value)}
            placeholder={field.type === 'list' ? 'Comma-separated values' : ''}
          />
        )}

      {field.type === 'int' && (
        <Input
          id={field.key}
          type="number"
          value={value || ''}
          onChange={(e) => handleChange(parseInt(e.target.value))}
          min={field.validation?.min}
          max={field.validation?.max}
        />
      )}

      {field.type === 'float' && (
        <Input
          id={field.key}
          type="number"
          step="0.1"
          value={value || ''}
          onChange={(e) => handleChange(parseFloat(e.target.value))}
          min={field.validation?.min}
          max={field.validation?.max}
        />
      )}

      {field.type === 'bool' && (
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => handleChange(e.target.checked)}
            className="rounded"
          />
          <span className="text-sm">Enabled</span>
        </label>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {field.validation && (
        <div className="text-xs text-gray-500 space-y-1">
          {field.validation.min !== undefined && (
            <p>Minimum: {field.validation.min}</p>
          )}
          {field.validation.max !== undefined && (
            <p>Maximum: {field.validation.max}</p>
          )}
        </div>
      )}
    </div>
  )
}
```

---

### 5.4 Component: SensitiveField

Create: `web_ui/frontend/src/components/settings/SensitiveField.tsx`

```typescript
import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

interface SensitiveFieldProps {
  id: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function SensitiveField({
  id,
  value,
  onChange,
  placeholder,
}: SensitiveFieldProps) {
  const [showValue, setShowValue] = useState(false)
  const [isEditing, setIsEditing] = useState(!value) // Edit if not set
  const [editValue, setEditValue] = useState(value)

  const handleSave = () => {
    onChange(editValue)
    setIsEditing(false)
  }

  const handleCancel = () => {
    setEditValue(value)
    setIsEditing(false)
  }

  if (isEditing) {
    return (
      <div className="space-y-2">
        <Input
          id={id}
          type={showValue ? 'text' : 'password'}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          placeholder={placeholder}
          autoFocus
        />
        <div className="flex gap-2">
          <Button
            onClick={handleSave}
            size="sm"
            variant="default"
          >
            Save
          </Button>
          <Button
            onClick={handleCancel}
            size="sm"
            variant="outline"
          >
            Cancel
          </Button>
          <Button
            onClick={() => setShowValue(!showValue)}
            size="sm"
            variant="ghost"
          >
            {showValue ? 'Hide' : 'Show'}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-2 items-center">
      <Input
        id={id}
        type={showValue ? 'text' : 'password'}
        value={editValue}
        disabled
        placeholder="••••••••"
        className="bg-gray-50"
      />
      <Button
        onClick={() => setIsEditing(true)}
        size="sm"
        variant="outline"
      >
        Change
      </Button>
      {value && (
        <Button
          onClick={() => setShowValue(!showValue)}
          size="sm"
          variant="ghost"
        >
          {showValue ? 'Hide' : 'Show'}
        </Button>
      )}
    </div>
  )
}
```

---

### 5.5 Component: SettingsForm

Create: `web_ui/frontend/src/components/settings/SettingsForm.tsx`

```typescript
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { SettingField } from './SettingField'
import type { SettingField as SettingFieldType } from '@/lib/types'

interface SettingsFormProps {
  fields: SettingFieldType[]
  values: Record<string, any>
  onChange: (key: string, value: any) => void
  onSave: () => void
  onReset: () => void
  saving: boolean
  hasChanges: boolean
}

export function SettingsForm({
  fields,
  values,
  onChange,
  onSave,
  onReset,
  saving,
  hasChanges,
}: SettingsFormProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Settings</CardTitle>
        <CardDescription>
          Configure application behavior and integrations
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">
        <div className="space-y-6">
          {fields.map(field => (
            <SettingField
              key={field.key}
              field={field}
              value={values[field.key]}
              onChange={(value) => onChange(field.key, value)}
            />
          ))}
        </div>

        <div className="border-t pt-6 flex gap-2 justify-end">
          <Button
            onClick={onReset}
            disabled={!hasChanges || saving}
            variant="outline"
          >
            Reset
          </Button>
          <Button
            onClick={onSave}
            disabled={!hasChanges || saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

### 5.6 API Integration: `web_ui/frontend/src/lib/api.ts`

Add new settings API methods:

```typescript
export const settingsApi = {
  getSettings: () =>
    api.get<SettingsResponse>('/api/settings'),

  updateSettings: (updates: SettingsUpdateRequest) =>
    api.put<SettingsUpdateResponse>('/api/settings', updates),

  validateSettings: (settings: Record<string, any>) =>
    api.post<ValidationResult>('/api/settings/validate', { settings }),

  getCategories: () =>
    api.get<CategoriesResponse>('/api/settings/categories'),

  resetSettings: (keys: string[], resetAll: boolean = false) =>
    api.post<SettingsUpdateResponse>('/api/settings/reset', { keys, reset_all: resetAll }),
}
```

---

### 5.7 Types: `web_ui/frontend/src/lib/types.ts`

Add settings types:

```typescript
export interface SettingsCategory {
  id: string
  name: string
  description: string
  icon?: string
}

export interface SettingValidation {
  min?: number
  max?: number
  pattern?: string
  options?: string[]
}

export interface SettingField {
  key: string
  label: string
  description: string
  type: 'string' | 'int' | 'float' | 'bool' | 'list' | 'password'
  default: any
  current: any
  sensitive: boolean
  validation?: SettingValidation
}

export interface SettingsResponse {
  categories: SettingsCategory[]
  fields: Record<string, SettingField[]>
}

export interface SettingsUpdateRequest {
  updates: Record<string, any>
}

export interface SettingsUpdateResponse {
  success: boolean
  message: string
  updated_keys: string[]
  requires_restart: boolean
  updated_settings: Record<string, SettingField>
}

export interface ValidationResult {
  valid: boolean
  errors: Record<string, string>
  warnings: string[]
}
```

---

### 5.8 Navigation: Update `web_ui/frontend/src/App.tsx`

Add Settings tab to main navigation:

```typescript
// In the tab bar section, add:
<button
  onClick={() => setActiveTab('settings')}
  className={`border-b-2 px-1 py-4 text-sm font-medium transition-colors ${
    activeTab === 'settings'
      ? 'border-blue-500 text-blue-600'
      : 'border-transparent text-gray-600 hover:border-gray-300'
  }`}
>
  Settings
</button>

// In the content section, add:
{activeTab === 'settings' && <SettingsPage />}

// Import at top:
import { SettingsPage } from '@/pages/SettingsPage'
```

---

## 6. Implementation Challenges & Solutions

### Challenge 1: .env File Parsing & Writing

**Problem**: Python `os.getenv()` reads from environment, not `.env` file. Changes to `.env` don't affect current process.

**Solution**:
- Use `python-dotenv` library: `pip install python-dotenv`
- Use `set_key()` and `unset_key()` to write to `.env`
- Update in-memory environment immediately after file write
- Restart frontend reconnects, picks up new values

**Implementation**:
```python
from dotenv import load_dotenv, set_key
import os

def update_setting(key: str, value: str):
    env_path = Path('.env')
    set_key(str(env_path), key, value)
    # Update in-memory
    os.environ[key] = value
```

---

### Challenge 2: Sensitive Data Never Leaves Server

**Problem**: API keys stored in memory/env could be exposed.

**Solution**:
- Never return full API key in API responses
- Use placeholder: `••••••••` or masked last 4 chars: `sk-...abc123`
- API key is write-only (can update, never retrieve)
- Store in-memory for operations, persist to `.env`

**Implementation**:
```python
def mask_value(key: str, value: str) -> str:
    if 'API_KEY' in key and value:
        return f"••••{value[-4:]}" if len(value) > 4 else "••••••••"
    return value
```

---

### Challenge 3: Type Coercion

**Problem**: Frontend sends JSON types (string, number, boolean), but `.env` files store only strings.

**Solution**:
- Create converter to go from JSON → string format
- Booleans: `true` → `"1"`, `false` → `"0"`
- Lists: `["a", "b"]` → `"a,b"` or `"a;b"`
- Numbers: convert to string

**Implementation**:
```python
def to_env_string(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, list):
        separator = ';' if key == 'AUTO_APPLY_CHROME_ARGS' else ','
        return separator.join(str(v) for v in value)
    return str(value)
```

---

### Challenge 4: API Key Validation

**Problem**: Users might enter invalid API keys. Should catch before saving.

**Solution**:
- Test API key by making test API call to provider
- Return clear error message if invalid
- Don't persist invalid keys

**Implementation**:
```python
async def test_openrouter_key(api_key: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                'https://api.openrouter.ai/api/v1/models',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
```

---

### Challenge 5: Restart Requirement

**Problem**: Changing `.env` doesn't affect running Python process unless restarted.

**Solution**: Three-tier approach:
1. **Info Only**: Show message "Some changes require restart"
2. **Manual Restart**: User restarts backend when ready
3. **Auto-Restart** (optional): Backend gracefully restarts (complex, use only if needed)

**Recommended**: Info-only approach with optional restart button

**Implementation**:
```python
# Response indicates which settings require restart
return {
    "success": True,
    "message": "Settings saved",
    "requires_restart": "BROWSER_LOCALE" in updates or "BROWSER_TIMEZONE" in updates
}
```

---

### Challenge 6: Validation Metadata

**Problem**: Frontend needs to know validation rules (min/max, options, etc.)

**Solution**:
- Define all validation rules in one place
- Return validation rules with settings metadata
- Frontend enforces client-side, backend enforces server-side

**Implementation**:
```python
VALIDATION_RULES = {
    'LLM_TEMPERATURE': {'type': 'float', 'min': 0.0, 'max': 2.0},
    'DWELL_SECONDS': {'type': 'float', 'min': 0.1, 'max': 5.0},
    'DISCOVERY_CAP': {'type': 'int', 'min': 1, 'max': 100},
    'LLM_PROVIDER': {'type': 'enum', 'options': ['openrouter', 'google']},
}
```

---

## 7. Implementation Phases

### Phase 1: Backend Foundation (Estimated: 4-6 hours)

**Deliverables**:
- ✅ `web_ui/backend/models/settings.py` - Pydantic models
- ✅ `web_ui/backend/routes/settings.py` - All 5 endpoints
- ✅ Validation functions
- ✅ .env file reading/writing
- ✅ API key testing
- ✅ Tests in `tests/test_routes_settings.py`

**Success Criteria**:
- GET /api/settings returns all settings with masked sensitive data
- PUT /api/settings validates and persists to .env
- POST /api/settings/validate tests without persisting
- POST /api/settings/reset resets to defaults

---

### Phase 2: Frontend Foundation (Estimated: 6-8 hours)

**Deliverables**:
- ✅ `SettingsPage.tsx` - Main page
- ✅ `CategoryTabs.tsx` - Category navigation
- ✅ `SettingField.tsx` - Generic field component
- ✅ `SensitiveField.tsx` - Password-style inputs
- ✅ `SettingsForm.tsx` - Form wrapper
- ✅ API methods in `api.ts`
- ✅ Types in `types.ts`

**Success Criteria**:
- Settings page renders with all categories
- Fields display current values
- Changes can be made and saved
- Sensitive fields are masked

---

### Phase 3: UI Polish (Estimated: 4-6 hours)

**Deliverables**:
- ✅ Settings tab in main navigation
- ✅ Validation error display
- ✅ Success/error toasts
- ✅ "Restart Required" banner
- ✅ Confirmation modal for sensitive changes
- ✅ Help text and tooltips
- ✅ Loading states

**Success Criteria**:
- All validation errors shown clearly
- User understands which changes need restart
- Sensitive changes require confirmation
- Responsive design on mobile

---

### Phase 4: Advanced Features (Estimated: 4-6 hours, optional)

**Deliverables**:
- Settings history / change log
- Import/Export settings as JSON
- Per-profile setting overrides
- Settings diff viewer
- Batch validation endpoint

**Success Criteria**:
- Users can see what changed when
- Settings can be backed up and restored
- Easy comparison of configurations

---

## 8. Testing Strategy

### Backend Tests

**Unit Tests** (`tests/unit/test_settings_validation.py`):
```python
def test_validate_dwell_seconds():
    # Valid
    assert validate_settings({'DWELL_SECONDS': '1.0'}) == {}
    # Invalid
    errors = validate_settings({'DWELL_SECONDS': '10.0'})
    assert 'DWELL_SECONDS' in errors
```

**Integration Tests** (`tests/integration/test_settings_api.py`):
```python
async def test_get_settings(client):
    response = await client.get('/api/settings')
    assert response.status_code == 200
    assert 'categories' in response.json()
    assert 'fields' in response.json()

async def test_update_settings(client):
    response = await client.put(
        '/api/settings',
        json={'updates': {'DWELL_SECONDS': '1.5'}}
    )
    assert response.status_code == 200
    assert response.json()['success']
```

---

### Frontend Tests

**Component Tests** (`web_ui/tests/components/SettingField.test.tsx`):
```typescript
test('renders text field correctly', () => {
  const field = { key: 'TEST', type: 'string', ... }
  render(<SettingField field={field} value="" onChange={() => {}} />)
  expect(screen.getByRole('textbox')).toBeInTheDocument()
})

test('masks sensitive fields', () => {
  const field = { key: 'API_KEY', type: 'password', ... }
  render(<SettingField field={field} value="secret" onChange={() => {}} />)
  expect(screen.getByDisplayValue('••••••••')).toBeInTheDocument()
})
```

**Integration Tests** (`web_ui/tests/pages/SettingsPage.test.tsx`):
```typescript
test('loads and displays settings', async () => {
  render(<SettingsPage />)
  await waitFor(() => {
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })
})

test('saves settings with validation', async () => {
  const user = userEvent.setup()
  render(<SettingsPage />)

  const input = screen.getByLabelText('Dwell Seconds')
  await user.clear(input)
  await user.type(input, '1.5')

  await user.click(screen.getByText('Save Changes'))

  expect(await screen.findByText('Settings saved')).toBeInTheDocument()
})
```

---

## 9. File Structure Summary

### Backend Files to Create/Modify

```
web_ui/backend/
├── models/
│   ├── __init__.py
│   ├── command.py (existing)
│   └── settings.py (NEW)
├── routes/
│   ├── __init__.py
│   ├── discover.py (existing)
│   └── settings.py (NEW)
├── app.py (MODIFY - add settings router)
└── requirements.txt (MODIFY - add python-dotenv)
```

### Frontend Files to Create/Modify

```
web_ui/frontend/src/
├── components/
│   └── settings/ (NEW)
│       ├── CategoryTabs.tsx
│       ├── SettingField.tsx
│       ├── SensitiveField.tsx
│       └── SettingsForm.tsx
├── pages/
│   └── SettingsPage.tsx (NEW)
├── lib/
│   ├── api.ts (MODIFY - add settingsApi)
│   └── types.ts (MODIFY - add settings types)
└── App.tsx (MODIFY - add Settings tab)
```

### Test Files to Create

```
tests/
├── unit/
│   └── test_settings_validation.py (NEW)
├── integration/
│   └── test_settings_api.py (NEW)
└── web_ui/tests/
    ├── components/
    │   └── SettingField.test.tsx (NEW)
    └── pages/
        └── SettingsPage.test.tsx (NEW)
```

---

## 10. Getting Started Checklist

### Pre-Implementation
- [ ] Review this plan with team
- [ ] Determine implementation timeline
- [ ] Assign Phase 1 developer
- [ ] Set up development branches

### Phase 1: Backend (Week 1)
- [ ] Create `web_ui/backend/models/settings.py`
- [ ] Create `web_ui/backend/routes/settings.py` with all endpoints
- [ ] Implement validation functions
- [ ] Add `python-dotenv` to requirements
- [ ] Register router in `app.py`
- [ ] Write and pass unit tests
- [ ] Write and pass integration tests
- [ ] Test with Postman/curl

### Phase 2: Frontend (Week 1-2)
- [ ] Create `SettingsPage.tsx`
- [ ] Create all components in `settings/`
- [ ] Add API methods to `lib/api.ts`
- [ ] Add types to `lib/types.ts`
- [ ] Update `App.tsx` navigation
- [ ] Test basic functionality
- [ ] Fix any type errors

### Phase 3: Polish (Week 2)
- [ ] Add validation error display
- [ ] Add success/error toasts
- [ ] Add "Restart Required" banner
- [ ] Add confirmation modals
- [ ] Add help text and tooltips
- [ ] Test responsive design
- [ ] User testing

### Phase 4: Advanced (Week 3, optional)
- [ ] Settings history
- [ ] Import/Export
- [ ] Per-profile overrides
- [ ] Settings diff

---

## 11. Success Metrics

After implementation, verify:

1. ✅ User can navigate Settings page
2. ✅ User can modify all 40+ settings
3. ✅ Sensitive data is masked in UI
4. ✅ Changes are validated before save
5. ✅ Changes persist to .env file
6. ✅ Validation errors displayed clearly
7. ✅ API keys can be tested before saving
8. ✅ Settings can be reset to defaults
9. ✅ No server restart needed for most settings
10. ✅ Settings tab visible in main navigation

---

## 12. Future Enhancements

After Phase 1-3 completion:

1. **Settings Profiles**: Save and switch between setting configurations
2. **Settings History**: View change log with timestamps and old/new values
3. **Undo/Redo**: Revert recent changes
4. **Settings Export**: Download current settings as JSON for backup
5. **Settings Import**: Load settings from JSON file
6. **Scheduled Tasks**: Set settings to change at specific times
7. **Multi-language**: Translate settings UI to other languages
8. **Audit Log**: Track who changed what when (for team setups)

---

## Conclusion

This comprehensive plan provides a solid foundation for implementing the Settings UI. The phased approach allows incremental development, testing, and deployment. Each phase is self-contained and can be completed independently.

The key success factors:
- **Backend first**: Get the API working before UI
- **Testing throughout**: Unit and integration tests at each phase
- **Clear validation**: Prevent invalid configurations
- **Security conscious**: Never expose API keys
- **User friendly**: Clear messaging and error handling

For questions or clarifications during implementation, refer to the specific section numbers in this plan.

**Total Estimated Effort**: 18-26 hours (all phases)
- Phase 1: 4-6 hours
- Phase 2: 6-8 hours
- Phase 3: 4-6 hours
- Phase 4: 4-6 hours (optional)
