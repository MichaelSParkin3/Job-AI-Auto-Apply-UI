import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Type definitions
export interface Profile {
  id: string
  name: string
  resume_path: string
  preferred_browser?: string
  has_experience: boolean
}

export interface ProfileListResponse {
  profiles: Profile[]
  count: number
}

export interface DiscoverRequest {
  profile_id: string
  window?: string
  cap?: number
}

export interface DiscoverResponse {
  success: boolean
  items_discovered: number
  message: string
  profile_id: string
}

export interface ApplyRequest {
  profile_id: string
  job_id?: string
  supervised?: boolean
  llm_provider?: string
  llm_model?: string
  use_llm_locator?: boolean
  debug_resume_widget?: boolean
  resume_wait_timeout_seconds?: number
  review_mode?: boolean
}

export interface ApplyResponse {
  task_id: string
  message: string
  websocket_url: string
}

// API methods
export const profilesApi = {
  list: () => api.get<ProfileListResponse>('/api/profiles'),
  get: (id: string) => api.get<Profile>(`/api/profiles/${id}`),
}

export const discoverApi = {
  start: (request: DiscoverRequest) =>
    api.post<DiscoverResponse>('/api/discover', request),
}

export const applyApi = {
  start: (request: ApplyRequest) =>
    api.post<ApplyResponse>('/api/apply', request),
}

export default api
