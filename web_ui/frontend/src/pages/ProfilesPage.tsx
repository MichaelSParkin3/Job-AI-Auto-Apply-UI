import { useState, useEffect } from 'react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { ProfileForm } from '../components/ProfileForm'
import type { Profile, ProfileDetailResponse } from '../lib/types'
import { profilesApi } from '../lib/api'

export function ProfilesPage() {
  const [mode, setMode] = useState<'list' | 'create' | 'edit'>('list')
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [selectedProfileId, setSelectedProfileId] = useState<string>()
  const [loading, setLoading] = useState(false)

  // Load profiles on mount
  useEffect(() => {
    loadProfiles()
  }, [])

  const loadProfiles = async () => {
    setLoading(true)
    try {
      const response = await profilesApi.list()
      setProfiles(response.data.profiles)
    } catch (error) {
      console.error('Failed to load profiles:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteProfile = async (profileId: string) => {
    if (!window.confirm(`Delete profile "${profileId}"?`)) return

    try {
      await profilesApi.delete(profileId)
      await loadProfiles()
    } catch (error) {
      console.error('Failed to delete profile:', error)
    }
  }

  const handleSaveProfile = async (profile: ProfileDetailResponse) => {
    try {
      // ProfileForm handles API calls (POST/PUT) via profilesApi
      // Just reload and return to list
      await loadProfiles()
      setMode('list')
    } catch (error) {
      console.error('Failed to save profile:', error)
    }
  }

  if (mode === 'list') {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Profiles</h1>
          <Button onClick={() => setMode('create')}>+ New Profile</Button>
        </div>

        {loading ? (
          <p className="text-gray-600">Loading profiles...</p>
        ) : profiles.length === 0 ? (
          <Card>
            <CardContent className="pt-6 text-center">
              <p className="text-gray-600 mb-4">No profiles yet</p>
              <Button onClick={() => setMode('create')}>Create First Profile</Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {profiles.map((profile) => (
              <Card key={profile.id}>
                <CardHeader className="flex flex-row justify-between items-start">
                  <div>
                    <CardTitle>{profile.name}</CardTitle>
                    <p className="text-sm text-gray-600 mt-1">{profile.id}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => {
                        setSelectedProfileId(profile.id)
                        setMode('edit')
                      }}
                      variant="outline"
                      size="sm"
                    >
                      Edit
                    </Button>
                    <Button
                      onClick={() => handleDeleteProfile(profile.id)}
                      variant="destructive"
                      size="sm"
                    >
                      Delete
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="text-sm text-gray-600">
                  <p>Resume: {profile.resume_path}</p>
                  {profile.preferred_browser && (
                    <p>Browser: {profile.preferred_browser}</p>
                  )}
                  {profile.has_experience && (
                    <p className="text-blue-600 mt-1">Has work experience</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (mode === 'create') {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Create Profile</h1>
        <ProfileForm
          onSave={(profile) => {
            handleSaveProfile(profile)
          }}
          onCancel={() => setMode('list')}
        />
      </div>
    )
  }

  if (mode === 'edit' && selectedProfileId) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Edit Profile</h1>
        <ProfileForm
          profileId={selectedProfileId}
          onSave={(profile) => {
            handleSaveProfile(profile)
          }}
          onCancel={() => setMode('list')}
        />
      </div>
    )
  }

  return null
}
