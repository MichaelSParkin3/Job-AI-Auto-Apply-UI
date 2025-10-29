import axios, { AxiosError, AxiosResponse } from 'axios'
import type {
  Profile,
  ApplicationItem,
  Setting,
  ProfilesResponse,
  QueueResponse,
  SettingsResponse,
  ApiError,
} from '../types'

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1'

interface RetryConfig {
  maxRetries: number
  initialDelayMs: number
  backoffMultiplier: number
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelayMs: 1000,
  backoffMultiplier: 2,
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
})

// Error interceptor with retry logic
let retryCount = 0

const shouldRetry = (error: AxiosError): boolean => {
  if (!error.response) {
    // Network error
    return true
  }

  const status = error.response.status
  // Retry on network errors, server errors, and timeout
  return status >= 500 || status === 408 || status === 429
}

const sleep = (ms: number): Promise<void> => {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const config = error.config as any

    if (!config || !shouldRetry(error) || retryCount >= DEFAULT_RETRY_CONFIG.maxRetries) {
      // Build user-friendly error message
      if (error.response?.status === 401) {
        console.error('Unauthorized access')
      } else if (error.response?.status === 404) {
        console.error('Resource not found')
      } else if (error.response?.status === 400) {
        console.error('Bad request:', error.response.data)
      } else if (!error.response) {
        console.error('Network error - check your connection')
      }

      return Promise.reject(error)
    }

    retryCount++
    const delayMs =
      DEFAULT_RETRY_CONFIG.initialDelayMs *
      Math.pow(DEFAULT_RETRY_CONFIG.backoffMultiplier, retryCount - 1)

    console.log(
      `Retrying request (attempt ${retryCount}/${DEFAULT_RETRY_CONFIG.maxRetries}) after ${delayMs}ms`
    )

    await sleep(delayMs)
    return api(config)
  }
)

// ============================================================================
// PROFILES API
// ============================================================================

export const profilesApi = {
  listProfiles: async (): Promise<ProfilesResponse> => {
    const { data } = await api.get<ProfilesResponse>('/profiles')
    return data
  },

  getProfile: async (profileId: string): Promise<Profile> => {
    const { data } = await api.get<Profile>(`/profiles/${profileId}`)
    return data
  },

  updateProfile: async (profileId: string, profile: Profile): Promise<Profile> => {
    const { data } = await api.put<Profile>(`/profiles/${profileId}`, profile)
    return data
  },

  switchProfile: async (profileId: string): Promise<{ profile_id: string; status: string }> => {
    const { data } = await api.post(`/profiles/${profileId}/switch`)
    return data
  },
}

// ============================================================================
// JOBS API
// ============================================================================

export const jobsApi = {
  listJobs: async (profileId: string, status?: string): Promise<QueueResponse> => {
    const { data } = await api.get<QueueResponse>('/jobs', {
      params: { profile_id: profileId, status },
    })
    return data
  },

  getJob: async (jobId: string, profileId: string): Promise<ApplicationItem> => {
    const { data } = await api.get<ApplicationItem>(`/jobs/${jobId}`, {
      params: { profile_id: profileId },
    })
    return data
  },

  updateJobStatus: async (jobId: string, profileId: string, status: string) => {
    const { data } = await api.put(`/jobs/${jobId}/status`, { profile_id: profileId, status })
    return data
  },

  deleteJob: async (jobId: string, profileId: string) => {
    const { data } = await api.delete(`/jobs/${jobId}`, {
      params: { profile_id: profileId },
    })
    return data
  },
}

// ============================================================================
// DISCOVERY API
// ============================================================================

export const discoveryApi = {
  execute: async (profileId: string, searchWindow?: string, jobCap?: number) => {
    const { data } = await api.post('/discover/execute', {
      profile_id: profileId,
      search_window: searchWindow,
      job_cap: jobCap,
    })
    return data
  },

  getStatus: async (profileId: string) => {
    const { data } = await api.get('/discover/status', {
      params: { profile_id: profileId },
    })
    return data
  },

  getLastOptions: async (profileId: string) => {
    const { data } = await api.get(`/discover/last-options/${profileId}`)
    return data
  },
}

// ============================================================================
// APPLY API
// ============================================================================

export const applyApi = {
  applySingle: async (profileId: string, jobId: string) => {
    const { data } = await api.post('/apply/single', {
      profile_id: profileId,
      job_id: jobId,
    })
    return data
  },

  applyBulk: async (profileId: string) => {
    const { data } = await api.post('/apply/bulk', {
      profile_id: profileId,
    })
    return data
  },

  getStatus: async (jobId: string, profileId: string) => {
    const { data } = await api.get(`/apply/status/${jobId}`, {
      params: { profile_id: profileId },
    })
    return data
  },

  getLogs: async (jobId: string, profileId: string) => {
    const { data } = await api.get(`/apply/logs/${jobId}`, {
      params: { profile_id: profileId },
    })
    return data
  },
}

// ============================================================================
// SETTINGS API
// ============================================================================

export const settingsApi = {
  listSettings: async (): Promise<SettingsResponse> => {
    const { data } = await api.get<SettingsResponse>('/settings')
    return data
  },

  getSetting: async (key: string): Promise<Setting> => {
    const { data } = await api.get<Setting>(`/settings/${key}`)
    return data
  },

  updateSettings: async (updates: Record<string, string>) => {
    const { data } = await api.put('/settings', updates)
    return data
  },

  resetSetting: async (key: string) => {
    const { data } = await api.delete(`/settings/${key}`)
    return data
  },

  resetAll: async () => {
    const { data } = await api.post('/settings/reset')
    return data
  },
}

// ============================================================================
// ARTIFACTS API
// ============================================================================

export const artifactsApi = {
  listArtifacts: async (profileId: string, jobId: string) => {
    const { data } = await api.get(`/artifacts/${profileId}/${jobId}/`)
    return data
  },

  getArtifact: async (profileId: string, jobId: string, filename: string) => {
    const { data } = await api.get(`/artifacts/${profileId}/${jobId}/${filename}`)
    return data
  },
}

export default api
