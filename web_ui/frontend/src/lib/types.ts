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
