import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Edit, Trash2, CheckCircle, Mail, MapPin, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { ErrorMessage } from '@/components/ErrorMessage'
import { Profile, ProfilesResponse } from '@/types'
import { apiClient } from '@/services/api'

export default function ProfilesPage() {
  const navigate = useNavigate()
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [activeProfileId, setActiveProfileId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<Profile | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // Load profiles on mount
  useEffect(() => {
    loadProfiles()
  }, [])

  const loadProfiles = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiClient.get<ProfilesResponse>('/profiles')
      setProfiles(response.data.profiles)

      // Get active profile from localStorage
      const activeId = localStorage.getItem('job_apply_active_profile')
      if (activeId) {
        setActiveProfileId(activeId)
      } else if (response.data.profiles.length > 0) {
        // Set first profile as active if none selected
        setActiveProfileId(response.data.profiles[0].id)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load profiles'
      setError(message)
      console.error('Profiles load error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSwitchProfile = async (profileId: string) => {
    try {
      setError(null)
      await apiClient.post(`/profiles/${profileId}/switch`)
      setActiveProfileId(profileId)
      localStorage.setItem('job_apply_active_profile', profileId)
      setSuccessMessage(`Switched to profile: ${profiles.find(p => p.id === profileId)?.name}`)
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to switch profile'
      setError(message)
      console.error('Profile switch error:', err)
    }
  }

  const handleDeleteClick = (profile: Profile) => {
    setDeleteTarget(profile)
    setShowDeleteConfirm(true)
  }

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return

    try {
      setDeleting(true)
      setError(null)
      await apiClient.delete(`/profiles/${deleteTarget.id}`)

      // Remove from list
      setProfiles(profiles.filter(p => p.id !== deleteTarget.id))

      // If deleted profile was active, switch to first available
      if (activeProfileId === deleteTarget.id && profiles.length > 1) {
        const nextProfile = profiles.find(p => p.id !== deleteTarget.id)
        if (nextProfile) {
          handleSwitchProfile(nextProfile.id)
        }
      }

      setSuccessMessage(`Profile "${deleteTarget.name}" deleted successfully`)
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete profile'
      setError(message)
      console.error('Profile delete error:', err)
    } finally {
      setDeleting(false)
      setShowDeleteConfirm(false)
      setDeleteTarget(null)
    }
  }

  if (loading) {
    return <LoadingSpinner message="Loading profiles..." />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Profiles</h1>
          <p className="text-gray-600 mt-2">Manage your application profiles</p>
        </div>
        <Button onClick={() => navigate('/profiles/new')} className="gap-2">
          <Plus className="w-4 h-4" />
          New Profile
        </Button>
      </div>

      {/* Messages */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {successMessage && (
        <Alert className="bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800">
          <AlertDescription className="text-green-800 dark:text-green-200">
            {successMessage}
          </AlertDescription>
        </Alert>
      )}

      {/* Profiles Grid */}
      {profiles.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="text-6xl mb-4">📋</div>
          <h2 className="text-xl font-semibold mb-2">No Profiles Yet</h2>
          <p className="text-gray-600 mb-6">
            Create your first profile to get started with job applications.
          </p>
          <Button onClick={() => navigate('/profiles/new')}>
            <Plus className="w-4 h-4 mr-2" />
            Create Profile
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {profiles.map((profile) => (
            <Card
              key={profile.id}
              className={`p-6 hover:shadow-lg transition-shadow relative ${
                activeProfileId === profile.id
                  ? 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-950'
                  : ''
              }`}
            >
              {/* Active Badge */}
              {activeProfileId === profile.id && (
                <div className="absolute top-4 right-4">
                  <div className="flex items-center gap-1 bg-blue-500 text-white px-3 py-1 rounded-full text-xs font-semibold">
                    <CheckCircle className="w-3 h-3" />
                    Active
                  </div>
                </div>
              )}

              {/* Profile Info */}
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-bold truncate pr-20">{profile.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">ID: {profile.id}</p>
                </div>

                {/* Details */}
                <div className="space-y-2 text-sm">
                  {profile.email && (
                    <div className="flex items-start gap-2 text-gray-600">
                      <Mail className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      <span className="truncate">{profile.email}</span>
                    </div>
                  )}

                  {profile.location && (
                    <div className="flex items-start gap-2 text-gray-600">
                      <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      <span>{profile.location}</span>
                    </div>
                  )}

                  {profile.resume_path && (
                    <div className="flex items-start gap-2 text-gray-600">
                      <FileText className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      <span className="truncate text-xs">{profile.resume_path}</span>
                    </div>
                  )}
                </div>

                {/* Keywords */}
                {profile.keywords?.roles && profile.keywords.roles.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 mb-2">Target Roles</p>
                    <div className="flex flex-wrap gap-1">
                      {profile.keywords.roles.slice(0, 3).map((role) => (
                        <span
                          key={role}
                          className="inline-block bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-xs truncate"
                        >
                          {role}
                        </span>
                      ))}
                      {profile.keywords.roles.length > 3 && (
                        <span className="text-xs text-gray-500 px-2 py-1">
                          +{profile.keywords.roles.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Tech Stack */}
                {profile.keywords?.tech_stack && profile.keywords.tech_stack.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 mb-2">Tech Stack</p>
                    <div className="flex flex-wrap gap-1">
                      {profile.keywords.tech_stack.slice(0, 3).map((tech) => (
                        <span
                          key={tech}
                          className="inline-block bg-blue-100 dark:bg-blue-900 px-2 py-1 rounded text-xs text-blue-700 dark:text-blue-300 truncate"
                        >
                          {tech}
                        </span>
                      ))}
                      {profile.keywords.tech_stack.length > 3 && (
                        <span className="text-xs text-gray-500 px-2 py-1">
                          +{profile.keywords.tech_stack.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="mt-6 pt-4 border-t space-y-2">
                {activeProfileId !== profile.id && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleSwitchProfile(profile.id)}
                    className="w-full"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Set Active
                  </Button>
                )}

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/profiles/${profile.id}/edit`)}
                    className="flex-1"
                  >
                    <Edit className="w-4 h-4 mr-2" />
                    Edit
                  </Button>

                  {profiles.length > 1 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteClick(profile)}
                      className="text-destructive hover:text-destructive flex-1"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Profile?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the profile "{deleteTarget?.name}"? This action
              cannot be undone. Associated job queue data will be removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? 'Deleting...' : 'Delete Profile'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
