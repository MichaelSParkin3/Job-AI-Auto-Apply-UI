import axios from 'axios'
import type {
  ExperienceItem,
  Profile,
  ProfileDetailResponse,
  ProfileListResponse,
  ResumeUploadResponse,
} from './types'

// Re-export types for backward compatibility
export type {
  ExperienceItem,
  Profile,
  ProfileDetailResponse,
  ProfileListResponse,
  ResumeUploadResponse,
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface DiscoverRequest {
  profile_id: string
  window?: string
  cap?: number
}

export interface DiscoverResponse {
  success: boolean
  items_discovered: number
  items_duplicate: number
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
  getDetail: (id: string) => api.get<ProfileDetailResponse>(`/api/profiles/${id}/detail`),
  create: (profile: ProfileDetailResponse) =>
    api.post<ProfileDetailResponse>('/api/profiles', profile),
  update: (id: string, profile: Partial<ProfileDetailResponse>) =>
    api.put<ProfileDetailResponse>(`/api/profiles/${id}`, profile),
  delete: (id: string) => api.delete(`/api/profiles/${id}`),
  uploadResume: (id: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<ResumeUploadResponse>(`/api/profiles/${id}/resume`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
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
