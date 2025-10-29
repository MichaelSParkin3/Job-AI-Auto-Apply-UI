// ============================================================================
// PROFILES
// ============================================================================

export interface ProfileDefaults {
  name?: string
  email?: string
  phone?: string
  location?: string
  portfolio_url?: string
  github_url?: string
  linkedin_url?: string
}

export interface ProfileKeywords {
  roles?: string[]
  tech_stack?: string[]
}

export interface ProfileExperience {
  company: string
  role: string
  dates: string
  highlights: string[]
  tech_stack?: string[]
  metrics?: Record<string, string>
}

export interface ProfilePrompts {
  cover_letter?: string
  resume_summary?: string
  key_accomplishments?: string
  experience_selection?: string
}

export interface Profile {
  id: string
  name: string
  email?: string
  phone?: string
  location?: string
  resume_path: string
  preferred_browser?: string
  user_data_dir?: string
  defaults?: ProfileDefaults
  keywords?: ProfileKeywords
  experience?: ProfileExperience[]
  prompts?: ProfilePrompts
}

// ============================================================================
// JOB ITEMS & DETAILS
// ============================================================================

export type ApplicationStatus =
  | 'NEW'
  | 'IN_PROGRESS'
  | 'SUBMITTED'
  | 'FAILED'
  | 'CAPTCHA_BLOCKED'

export interface JobDetails {
  location?: string
  work_model?: string
  employment_type?: string
  department?: string
  compensation?: string
  posting_text?: string
  tech_tags?: string[]
  apply_url?: string
  posting_date?: string
}

export interface Artifacts {
  screenshot_path?: string
  dom_snapshot_path?: string
  video_path?: string
  har_path?: string
  confirmation_text?: string
  confirmation_id?: string
  paths?: string[]
  capture_timestamp?: string
}

export interface FailureReason {
  code: string
  message: string
}

export interface ApplicationItem {
  id: string
  url: string
  company: string
  title: string
  status: ApplicationStatus
  details?: JobDetails
  artifacts?: Artifacts
  reason?: FailureReason
  date_discovered?: string
  date_applied?: string
  source_query?: string
  source_rank?: number
  hash?: string
}

// ============================================================================
// CONFIGURATION & SETTINGS
// ============================================================================

export type OperationType = 'discover' | 'apply_single' | 'apply_bulk'
export type ApplyMode = 'supervised' | 'automated'

export interface RunConfiguration {
  profile_id: string
  operation_type: OperationType
  search_window?: string
  job_cap?: number
  custom_query?: string
  mode?: ApplyMode
  review_mode?: boolean
  llm_provider_override?: string
  llm_model_override?: string
  use_llm_locator?: boolean
  debug_resume_widget?: boolean
  resume_wait_timeout?: number
  audit_after_submit?: boolean
  save_logs?: boolean
  logs_dir?: string
  max_concurrent?: number
  stop_on_failure?: boolean
  last_updated?: string
}

export type SettingCategory = 'server' | 'discovery' | 'application' | 'llm' | 'diagnostics' | 'performance'
export type SettingInputType = 'text' | 'number' | 'boolean' | 'select' | 'textarea'

export interface Setting {
  key: string
  value?: string
  description: string
  category: SettingCategory
  input_type: SettingInputType
  default_value?: string
  options?: string[]
  min?: number
  max?: number
  is_secret: boolean
  required: boolean
}

// ============================================================================
// API RESPONSES
// ============================================================================

export interface ProfilesResponse {
  profiles: Profile[]
  count: number
}

export interface QueueResponse {
  profile_id: string
  items: ApplicationItem[]
  count: number
  status_counts: Record<ApplicationStatus, number>
}

export interface SettingsResponse {
  settings: Setting[]
  count: number
}

export interface ArtifactsResponse {
  profile_id: string
  job_id: string
  artifacts: Array<{
    name: string
    type: string
    size_bytes: number
    created_at: number
  }>
  count: number
}

// ============================================================================
// API ERROR TYPES
// ============================================================================

export interface ApiError {
  error: string
  message: string
}
