import { useState, useEffect, useCallback, useRef } from 'react'
import { ApplicationItem, ApplicationStatus } from '../types/index'
import { jobsApi } from '../services/api'

export interface QueueCounts {
  NEW: number
  IN_PROGRESS: number
  SUBMITTED: number
  FAILED: number
  CAPTCHA_BLOCKED: number
}

export interface UseQueueResult {
  items: ApplicationItem[]
  counts: QueueCounts
  isLoading: boolean
  error: Error | null
  lastUpdated: Date | null
  refresh: () => Promise<void>
  filterByStatus: (status: ApplicationStatus) => ApplicationItem[]
  searchItems: (query: string) => ApplicationItem[]
}

export function useQueue(
  profileId: string,
  pollInterval: number = 2000
): UseQueueResult {
  const [items, setItems] = useState<ApplicationItem[]>([])
  const [counts, setCounts] = useState<QueueCounts>({
    NEW: 0,
    IN_PROGRESS: 0,
    SUBMITTED: 0,
    FAILED: 0,
    CAPTCHA_BLOCKED: 0,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isMountedRef = useRef(true)

  const calculateCounts = (items: ApplicationItem[]): QueueCounts => {
    const counts: QueueCounts = {
      NEW: 0,
      IN_PROGRESS: 0,
      SUBMITTED: 0,
      FAILED: 0,
      CAPTCHA_BLOCKED: 0,
    }
    items.forEach((item) => {
      counts[item.status as ApplicationStatus]++
    })
    return counts
  }

  const loadQueue = useCallback(async () => {
    if (!profileId) return

    try {
      setError(null)
      const response = await jobsApi.listJobs(profileId)
      if (isMountedRef.current) {
        setItems(response.items || [])
        setCounts(calculateCounts(response.items || []))
        setLastUpdated(new Date())
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(
          err instanceof Error
            ? err
            : new Error('Failed to load queue')
        )
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false)
      }
    }
  }, [profileId])

  const refresh = useCallback(async () => {
    setIsLoading(true)
    await loadQueue()
  }, [loadQueue])

  const filterByStatus = useCallback(
    (status: ApplicationStatus): ApplicationItem[] => {
      return items.filter((item) => item.status === status)
    },
    [items]
  )

  const searchItems = useCallback(
    (query: string): ApplicationItem[] => {
      const q = query.toLowerCase()
      return items.filter(
        (item) =>
          item.title.toLowerCase().includes(q) ||
          item.company.toLowerCase().includes(q)
      )
    },
    [items]
  )

  // Load queue on mount and when profileId changes
  useEffect(() => {
    isMountedRef.current = true
    setIsLoading(true)
    loadQueue()

    return () => {
      isMountedRef.current = false
    }
  }, [profileId, loadQueue])

  // Set up polling
  useEffect(() => {
    if (!isMountedRef.current) return

    // Initial load already happened, set up polling
    const poll = async () => {
      await loadQueue()
      if (isMountedRef.current) {
        pollTimeoutRef.current = setTimeout(
          poll,
          pollInterval
        )
      }
    }

    pollTimeoutRef.current = setTimeout(
      poll,
      pollInterval
    )

    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current)
      }
    }
  }, [pollInterval, loadQueue])

  return {
    items,
    counts,
    isLoading,
    error,
    lastUpdated,
    refresh,
    filterByStatus,
    searchItems,
  }
}
