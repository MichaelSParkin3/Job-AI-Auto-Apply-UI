import { useState, useEffect, useCallback } from 'react'
import { Profile } from '../types/index'
import { profilesApi } from '../services/api'
import { storageService } from '../services/storage'

export interface UseProfileResult {
  profiles: Profile[]
  activeProfile: string | null
  profileData: Profile | null
  isLoading: boolean
  error: Error | null
  switchProfile: (profileId: string) => Promise<void>
  refreshProfiles: () => Promise<void>
}

export function useProfile(): UseProfileResult {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [activeProfile, setActiveProfile] = useState<string | null>(null)
  const [profileData, setProfileData] = useState<Profile | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [lastUpdate, setLastUpdate] = useState<number>(0)

  const loadProfiles = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await profilesApi.listProfiles()
      setProfiles(response.profiles || [])

      // Restore active profile from storage or use first profile
      let active = storageService.getActiveProfile()
      if (
        !active ||
        !response.profiles?.find(
          (p: Profile) => p.id === active
        )
      ) {
        active = response.profiles?.[0]?.id || null
        if (active) {
          storageService.setActiveProfile(active)
        }
      }

      setActiveProfile(active)

      // Load profile data if active profile exists
      if (active) {
        const profile = await profilesApi.getProfile(active)
        setProfileData(profile)
      }

      setLastUpdate(Date.now())
    } catch (err) {
      setError(
        err instanceof Error
          ? err
          : new Error('Failed to load profiles')
      )
    } finally {
      setIsLoading(false)
    }
  }, [])

  const switchProfile = useCallback(
    async (profileId: string) => {
      try {
        setError(null)
        await profilesApi.switchProfile(profileId)
        storageService.setActiveProfile(profileId)
        setActiveProfile(profileId)

        const profile = await profilesApi.getProfile(profileId)
        setProfileData(profile)
      } catch (err) {
        const error =
          err instanceof Error
            ? err
            : new Error('Failed to switch profile')
        setError(error)
        throw error
      }
    },
    []
  )

  const refreshProfiles = useCallback(async () => {
    const now = Date.now()
    if (now - lastUpdate > 30000) {
      // Refresh if more than 30 seconds
      await loadProfiles()
    }
  }, [lastUpdate, loadProfiles])

  // Load profiles on mount
  useEffect(() => {
    loadProfiles()
  }, [loadProfiles])

  return {
    profiles,
    activeProfile,
    profileData,
    isLoading,
    error,
    switchProfile,
    refreshProfiles,
  }
}
