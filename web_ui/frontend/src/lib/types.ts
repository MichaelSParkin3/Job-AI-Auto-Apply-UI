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
