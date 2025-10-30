/**
 * Tests for useQueue hook
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useQueue } from '../useQueue'
import { jobsApi } from '../../services/api'

// Mock the API
vi.mock('../../services/api', () => ({
  jobsApi: {
    listJobs: vi.fn(),
  },
}))

describe('useQueue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should extract items from API response correctly', async () => {
    const mockResponse = {
      profile_id: 'test_profile',
      items: [
        {
          id: 'ulid1',
          url: 'https://jobs.lever.co/company/job1',
          company: 'Company A',
          title: 'Engineer',
          status: 'NEW',
        },
        {
          id: 'ulid2',
          url: 'https://jobs.lever.co/company/job2',
          company: 'Company B',
          title: 'Designer',
          status: 'SUBMITTED',
        },
      ],
      count: 2,
    }

    vi.mocked(jobsApi.listJobs).mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useQueue('test_profile'))

    // Initially loading
    expect(result.current.isLoading).toBe(true)

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    // Verify items are loaded
    expect(result.current.items).toHaveLength(2)
    expect(result.current.items[0].company).toBe('Company A')
    expect(result.current.items[1].company).toBe('Company B')

    // Verify counts are calculated
    expect(result.current.counts.NEW).toBe(1)
    expect(result.current.counts.SUBMITTED).toBe(1)
  })

  it('should handle empty queue', async () => {
    const mockResponse = {
      profile_id: 'test_profile',
      items: [],
      count: 0,
    }

    vi.mocked(jobsApi.listJobs).mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useQueue('test_profile'))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.items).toHaveLength(0)
    expect(result.current.counts.NEW).toBe(0)
    expect(result.current.counts.SUBMITTED).toBe(0)
  })

  it('should calculate status counts correctly', async () => {
    const mockResponse = {
      profile_id: 'test_profile',
      items: [
        { id: 'u1', url: '', company: 'A', title: 'J1', status: 'NEW' },
        { id: 'u2', url: '', company: 'B', title: 'J2', status: 'NEW' },
        { id: 'u3', url: '', company: 'C', title: 'J3', status: 'SUBMITTED' },
        { id: 'u4', url: '', company: 'D', title: 'J4', status: 'FAILED' },
        { id: 'u5', url: '', company: 'E', title: 'J5', status: 'IN_PROGRESS' },
        { id: 'u6', url: '', company: 'F', title: 'J6', status: 'CAPTCHA_BLOCKED' },
      ],
      count: 6,
    }

    vi.mocked(jobsApi.listJobs).mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useQueue('test_profile'))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.counts.NEW).toBe(2)
    expect(result.current.counts.SUBMITTED).toBe(1)
    expect(result.current.counts.FAILED).toBe(1)
    expect(result.current.counts.IN_PROGRESS).toBe(1)
    expect(result.current.counts.CAPTCHA_BLOCKED).toBe(1)
  })

  it('should filter items by status', async () => {
    const mockResponse = {
      profile_id: 'test_profile',
      items: [
        { id: 'u1', url: '', company: 'A', title: 'J1', status: 'NEW' },
        { id: 'u2', url: '', company: 'B', title: 'J2', status: 'SUBMITTED' },
        { id: 'u3', url: '', company: 'C', title: 'J3', status: 'FAILED' },
      ],
      count: 3,
    }

    vi.mocked(jobsApi.listJobs).mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useQueue('test_profile'))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const failedItems = result.current.filterByStatus('FAILED')
    expect(failedItems).toHaveLength(1)
    expect(failedItems[0].company).toBe('C')
  })

  it('should search items by company or title', async () => {
    const mockResponse = {
      profile_id: 'test_profile',
      items: [
        { id: 'u1', url: '', company: 'Google', title: 'Engineer', status: 'NEW' },
        { id: 'u2', url: '', company: 'Apple', title: 'Designer', status: 'SUBMITTED' },
        { id: 'u3', url: '', company: 'Google', title: 'Manager', status: 'FAILED' },
      ],
      count: 3,
    }

    vi.mocked(jobsApi.listJobs).mockResolvedValue(mockResponse)

    const { result } = renderHook(() => useQueue('test_profile'))

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const googleJobs = result.current.searchItems('google')
    expect(googleJobs).toHaveLength(2)

    const engineerJobs = result.current.searchItems('engineer')
    expect(engineerJobs).toHaveLength(1)
    expect(engineerJobs[0].title).toBe('Engineer')
  })
})
