// Profile management types

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

export interface Profile {
  id: string
  name: string
  resume_path: string
  preferred_browser?: string
  has_experience: boolean
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

// Settings types
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

export interface SettingsCategory {
  id: string
  name: string
  description: string
  icon?: string
}

export interface SettingsResponse {
  categories: SettingsCategory[]
  fields: Record<string, SettingField[]>
}

export interface ValidationResult {
  valid: boolean
  errors: Record<string, string>
  warnings: string[]
}

export interface SettingsUpdateRequest {
  updates: Record<string, any>
}

export interface SettingsUpdateResponse {
  success: boolean
  message: string
  updated_keys: string[]
  requires_restart?: boolean
  updated_settings?: Record<string, SettingField>
}

export interface ResetRequest {
  keys?: string[]
  reset_all: boolean
}

export interface CategoriesResponse {
  categories: SettingsCategory[]
}

// Queue and Job types
export interface JobDetailsResponse {
  location?: string
  work_model: string
  employment_type: string
  department?: string
  posting_date?: string
  compensation?: Record<string, any>
  posting_excerpt?: string
  posting_text?: string
  tech_tags: string[]
  source_query?: string
  source_rank?: number
  apply_url?: string
  closed: boolean
  extracted_at?: string
}

export interface ArtifactsResponse {
  dom_snapshot_path?: string
  screenshot_path?: string
  video_path?: string
  har_path?: string
  confirmation_text?: string
  confirmation_id?: string
  form_state_path?: string
  screenshot_before_path?: string
  screenshot_after_path?: string
}

export interface ReasonResponse {
  code: string
  message: string
}

export interface JobItemResponse {
  id: string
  url: string
  company: string
  title: string
  status: string
  discovered_at: string
  last_updated_at: string
  details?: JobDetailsResponse
  artifacts?: ArtifactsResponse
  reason?: ReasonResponse
}

export interface QueueGroupResponse {
  label: string
  status_values: string[]
  count: number
  items: JobItemResponse[]
}

export interface QueueResponse {
  profile_id: string
  total_count: number
  groups: QueueGroupResponse[]
}

export interface JobDetailPageResponse {
  job: JobItemResponse
  profile_id: string
  answer_cache?: Record<string, string>
}

// Apply and Resume response types
export interface ResumeResponse {
  success: boolean
  message: string
  job_id: string
  new_status: string
  task_id?: string
  websocket_url?: string
}

export interface ReapplyResponse {
  success: boolean
  message: string
  task_id: string
  websocket_url: string
}
