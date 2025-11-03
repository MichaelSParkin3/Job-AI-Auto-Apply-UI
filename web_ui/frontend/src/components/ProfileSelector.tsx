import { useEffect, useState } from 'react'
import type { Profile } from '@/lib/api'
import { profilesApi } from '@/lib/api'

interface ProfileSelectorProps {
  onSelect: (profile: Profile) => void
  selectedProfileId?: string
}

export function ProfileSelector({ onSelect, selectedProfileId }: ProfileSelectorProps) {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadProfiles = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await profilesApi.list()
        setProfiles(response.data.profiles)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load profiles'
        setError(message)
        console.error('Failed to load profiles:', err)
      } finally {
        setLoading(false)
      }
    }

    loadProfiles()
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const profileId = e.target.value
    const selected = profiles.find((p) => p.id === profileId)
    if (selected) {
      onSelect(selected)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2">
        <label htmlFor="profile-select" className="font-medium">
          Profile:
        </label>
        <div className="text-sm text-gray-500">Loading profiles...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-2">
        <label htmlFor="profile-select" className="font-medium">
          Profile:
        </label>
        <div className="text-sm text-red-600">Error: {error}</div>
      </div>
    )
  }

  if (profiles.length === 0) {
    return (
      <div className="flex items-center gap-2">
        <label htmlFor="profile-select" className="font-medium">
          Profile:
        </label>
        <div className="text-sm text-gray-500">No profiles available</div>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="profile-select" className="font-medium">
        Profile:
      </label>
      <select
        id="profile-select"
        value={selectedProfileId || ''}
        onChange={handleChange}
        className="rounded border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        <option value="">Select a profile...</option>
        {profiles.map((profile) => (
          <option key={profile.id} value={profile.id}>
            {profile.name} ({profile.id})
          </option>
        ))}
      </select>
    </div>
  )
}
