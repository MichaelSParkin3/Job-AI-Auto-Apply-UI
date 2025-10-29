import { useEffect, useState, useCallback } from 'react'
import { ApplicationItem, ApplicationStatus } from '../types'
import { jobsApi } from '../services/api'

interface UseJobStatusPollingOptions {
  pollIntervalMs?: number
  onStatusChange?: (oldStatus: ApplicationStatus, newStatus: ApplicationStatus) => void
  enabled?: boolean
}

/**
 * Hook for polling job status changes
 *
 * @param jobId Job ID to poll
 * @param profileId Profile ID
 * @param options Configuration options
 * @returns Current job item and polling state
 */
export const useJobStatusPolling = (
  jobId: string | undefined,
  profileId: string,
  options: UseJobStatusPollingOptions = {}
) => {
  const {
    pollIntervalMs = 5000, // Default 5 second poll
    onStatusChange,
    enabled = true,
  } = options

  const [job, setJob] = useState<ApplicationItem | null>(null)
  const [previousStatus, setPreviousStatus] = useState<ApplicationStatus | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const fetchJob = useCallback(async () => {
    if (!jobId) return

    try {
      setError(null)
      const jobData = await jobsApi.getJob(jobId, profileId)
      setJob(jobData)

      // Detect status change
      if (previousStatus && jobData.status !== previousStatus) {
        onStatusChange?.(previousStatus, jobData.status)
      }

      setPreviousStatus(jobData.status)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch job'))
    }
  }, [jobId, profileId, previousStatus, onStatusChange])

  useEffect(() => {
    if (!enabled || !jobId) {
      setIsPolling(false)
      return
    }

    // Initial fetch
    fetchJob()

    // Set up polling interval
    const pollInterval = setInterval(fetchJob, pollIntervalMs)
    setIsPolling(true)

    return () => {
      clearInterval(pollInterval)
      setIsPolling(false)
    }
  }, [jobId, profileId, pollIntervalMs, enabled, fetchJob])

  return {
    job,
    isPolling,
    error,
    refetch: fetchJob,
    statusChanged: previousStatus && job && previousStatus !== job.status,
  }
}
