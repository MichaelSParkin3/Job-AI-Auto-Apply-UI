import React, { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ApplicationItem, ApplicationStatus } from '../types/index'
import { jobsApi } from '../services/api'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorMessage } from '../components/ErrorMessage'
import { ErrorBoundary } from '../components/ErrorBoundary'
import { Button } from '../components/Button'
import { JobPostingSection } from '../components/JobPostingSection'
import { ArtifactsGallery } from '../components/ArtifactsGallery'
import { useJobStatusPolling } from '../hooks/useJobStatusPolling'
import { cn } from '../lib/utils'

export const JobDetail: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [statusUpdated, setStatusUpdated] = useState(false)

  const profileId = localStorage.getItem('job_apply_active_profile') || 'default'

  // Use polling hook for status changes
  const {
    job,
    isPolling,
    statusChanged,
    refetch,
  } = useJobStatusPolling(jobId, profileId, {
    pollIntervalMs: 5000,
    enabled: Boolean(jobId),
    onStatusChange: (oldStatus, newStatus) => {
      setStatusUpdated(true)
      // Auto-dismiss status update notification after 5 seconds
      setTimeout(() => setStatusUpdated(false), 5000)
    },
  })

  useEffect(() => {
    if (!jobId) {
      setError(new Error('Job ID not provided'))
      setIsLoading(false)
      return
    }

    const loadJob = async () => {
      try {
        setIsLoading(true)
        setError(null)
        await refetch()
      } catch (err) {
        setError(
          err instanceof Error ? err : new Error('Failed to load job')
        )
      } finally {
        setIsLoading(false)
      }
    }

    loadJob()
  }, [jobId, refetch])

  const getStatusColor = (status: ApplicationStatus): string => {
    const colors: Record<ApplicationStatus, string> = {
      NEW: 'bg-blue-100 text-blue-800',
      IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
      SUBMITTED: 'bg-green-100 text-green-800',
      FAILED: 'bg-red-100 text-red-800',
      CAPTCHA_BLOCKED: 'bg-orange-100 text-orange-800',
    }
    return colors[status]
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner message="Loading job details..." />
      </div>
    )
  }

  if (error || !job) {
    return (
      <div className="space-y-6">
        <div>
          <Button
            onClick={() => navigate(-1)}
            variant="outline"
          >
            ← Back
          </Button>
        </div>

        <ErrorMessage
          error={error || new Error('Job not found')}
          onRetry={() => window.location.reload()}
        />

        <Button onClick={() => navigate('/')}>
          Go to Dashboard
        </Button>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        {/* Status Update Notification */}
        {statusUpdated && (
          <div
            className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center gap-3"
            role="status"
            aria-live="polite"
            aria-atomic="true"
          >
            <span className="text-blue-600">
              ✓ Status updated to: <strong>{job?.status}</strong>
            </span>
          </div>
        )}

        {/* Header with Back Button */}
        <div className="flex items-center justify-between">
          <div>
            <Button
              onClick={() => navigate(-1)}
              variant="outline"
              size="sm"
              aria-label="Go back to job queue"
            >
              ← Back to Queue
            </Button>
          </div>
          <div
            className={cn(
              'px-3 py-1 rounded-full text-sm font-semibold',
              getStatusColor(job.status)
            )}
            role="status"
            aria-label={`Current status: ${job.status}`}
          >
            {job.status}
            {isPolling && (
              <span className="ml-2 inline-block h-2 w-2 bg-current rounded-full animate-pulse" />
            )}
          </div>
        </div>

        {/* Job Title and Company */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-gray-900" id="page-title">
            {job.title}
            <span className="sr-only"> at </span>
          </h1>
          <p className="text-xl text-gray-600">
            <span className="sr-only">Company: </span>
            {job.company}
          </p>
          {job.details?.location && (
            <p className="text-gray-500" aria-label={`Job location: ${job.details.location}`}>
              📍 <span className="sr-only">Location: </span>{job.details.location}
            </p>
          )}
        </div>

        {/* Basic Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <dt className="text-sm text-gray-600 mb-1">Status</dt>
            <dd className="text-lg font-semibold text-gray-900" aria-label={`Application status: ${job.status}`}>
              {job.status}
            </dd>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <dt className="text-sm text-gray-600 mb-1">Discovered</dt>
            <dd
              className="text-lg font-semibold text-gray-900"
              aria-label={`Job discovered on ${job.date_discovered ? new Date(job.date_discovered).toLocaleDateString() : 'unknown date'}`}
            >
              {job.date_discovered
                ? new Date(job.date_discovered).toLocaleDateString()
                : '—'}
            </dd>
          </div>

          {job.date_applied && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <dt className="text-sm text-gray-600 mb-1">Applied</dt>
              <dd
                className="text-lg font-semibold text-gray-900"
                aria-label={`Applied on ${new Date(job.date_applied).toLocaleDateString()}`}
              >
                {new Date(job.date_applied).toLocaleDateString()}
              </dd>
            </div>
          )}

          <div className="bg-gray-50 p-4 rounded-lg">
            <dt className="text-sm text-gray-600 mb-1">URL</dt>
            <dd>
              <a
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline text-sm truncate"
                aria-label={`View job posting on ${new URL(job.url).hostname}`}
              >
                View Job
              </a>
            </dd>
          </div>
        </div>

        {/* Job Details Section */}
        {job.details && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-2xl font-bold mb-4 text-gray-900">
              Job Details
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {job.details.work_model && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">
                    Work Model
                  </h3>
                  <p className="text-gray-600">
                    {job.details.work_model}
                  </p>
                </div>
              )}

              {job.details.employment_type && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">
                    Employment Type
                  </h3>
                  <p className="text-gray-600">
                    {job.details.employment_type}
                  </p>
                </div>
              )}

              {job.details.department && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">
                    Department
                  </h3>
                  <p className="text-gray-600">
                    {job.details.department}
                  </p>
                </div>
              )}

              {job.details.compensation && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">
                    Compensation
                  </h3>
                  <p className="text-gray-600">
                    {job.details.compensation}
                  </p>
                </div>
              )}

              {job.details.tech_tags &&
                job.details.tech_tags.length > 0 && (
                  <div className="md:col-span-2">
                    <h3 className="font-semibold text-gray-700 mb-2">
                      Technologies
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {job.details.tech_tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          </div>
        )}

        {/* Job Posting Section */}
        <JobPostingSection postingText={job.details?.posting_text} />

        {/* Artifacts Section */}
        {job.artifacts && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-2xl font-bold mb-4 text-gray-900">
              Artifacts
            </h2>
            <ArtifactsGallery
              artifacts={job.artifacts}
              profileId={localStorage.getItem('job_apply_active_profile') || 'default'}
              jobId={jobId || ''}
            />
          </div>
        )}

        {/* Failure Reason */}
        {job.status === 'FAILED' && job.reason && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-900 mb-2">
              Application Failed
            </h2>
            <p className="text-red-800">
              {job.reason.message}
            </p>
            {job.reason.code && (
              <p className="text-sm text-red-700 mt-2">
                Error Code: {job.reason.code}
              </p>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4">
          <Button onClick={() => navigate('/')}>
            Back to Dashboard
          </Button>
          <Button variant="secondary">
            ⚡ Apply Again
          </Button>
        </div>
      </div>
    </ErrorBoundary>
  )
}
