import React from 'react'
import { useProfile } from '../hooks/useProfile'
import { JobQueue } from '../components/JobQueue'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { Button } from '../components/Button'

export const Dashboard: React.FC = () => {
  const {
    activeProfile,
    profileData,
    isLoading,
    error,
  } = useProfile()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner message="Loading profile..." />
      </div>
    )
  }

  if (error || !activeProfile) {
    return (
      <div className="p-8">
        <ErrorMessage
          error={error || new Error('No profile selected')}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Intro */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Job Queue
        </h1>
        <p className="text-gray-600 mt-1">
          View and manage your job applications
          {profileData?.name &&
            ` for ${profileData.name}`}
        </p>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button
          onClick={() => {
            // This will be connected to discover modal in US4
            alert(
              'Discover Jobs modal will open here'
            )
          }}
        >
          🔍 Discover Jobs
        </Button>
        <Button
          variant="secondary"
          onClick={() => {
            // This will be connected to apply panel in US5
            alert(
              'Apply Options panel will open here'
            )
          }}
        >
          ⚡ Apply to Waiting Jobs
        </Button>
      </div>

      {/* Queue Display */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <JobQueue profileId={activeProfile} />
      </div>
    </div>
  )
}
