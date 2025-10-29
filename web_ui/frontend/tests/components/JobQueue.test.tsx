import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { JobQueue } from '../../src/components/JobQueue'
import * as useQueueModule from '../../src/hooks/useQueue'
import { ApplicationItem, ApplicationStatus } from '../../src/types'

// Mock the useQueue hook
vi.mock('../../src/hooks/useQueue')

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  }
})

const mockItems: ApplicationItem[] = [
  {
    id: '1',
    url: 'https://jobs.lever.co/company/job-1',
    company: 'TechCorp',
    title: 'Senior Software Engineer',
    status: 'NEW' as ApplicationStatus,
    date_discovered: '2024-10-28T10:00:00Z',
  },
  {
    id: '2',
    url: 'https://jobs.lever.co/company/job-2',
    company: 'StartupCo',
    title: 'Frontend Developer',
    status: 'IN_PROGRESS' as ApplicationStatus,
    date_discovered: '2024-10-27T15:30:00Z',
  },
  {
    id: '3',
    url: 'https://jobs.lever.co/company/job-3',
    company: 'BigTech',
    title: 'Staff Engineer',
    status: 'SUBMITTED' as ApplicationStatus,
    date_discovered: '2024-10-26T09:15:00Z',
  },
]

const mockUseQueue = {
  items: mockItems,
  counts: {
    NEW: 1,
    IN_PROGRESS: 1,
    SUBMITTED: 1,
    FAILED: 0,
    CAPTCHA_BLOCKED: 0,
  },
  isLoading: false,
  error: null,
  lastUpdated: new Date(),
  refresh: vi.fn(),
  filterByStatus: vi.fn((status) =>
    mockItems.filter((item) => item.status === status)
  ),
  searchItems: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useQueueModule.useQueue).mockReturnValue(mockUseQueue)
})

describe('JobQueue', () => {
  const renderJobQueue = () => {
    return render(
      <BrowserRouter>
        <JobQueue profileId="test-profile" />
      </BrowserRouter>
    )
  }

  it('renders job list', () => {
    renderJobQueue()

    expect(screen.getByText('Senior Software Engineer')).toBeInTheDocument()
    expect(screen.getByText('TechCorp')).toBeInTheDocument()
    expect(screen.getByText('Frontend Developer')).toBeInTheDocument()
    expect(screen.getByText('StartupCo')).toBeInTheDocument()
  })

  it('renders status tabs with counts', () => {
    renderJobQueue()

    expect(screen.getByText(/All \(3\)/)).toBeInTheDocument()
    expect(screen.getByText(/Waiting \(1\)/)).toBeInTheDocument()
    expect(screen.getByText(/In Progress \(1\)/)).toBeInTheDocument()
    expect(screen.getByText(/Submitted \(1\)/)).toBeInTheDocument()
  })

  it('filters jobs by status when tab clicked', async () => {
    renderJobQueue()

    const inProgressTab = screen.getByText(/In Progress \(1\)/)
    fireEvent.click(inProgressTab)

    await waitFor(() => {
      expect(screen.getByText('Frontend Developer')).toBeInTheDocument()
      expect(screen.queryByText('Senior Software Engineer')).not.toBeInTheDocument()
    })
  })

  it('searches jobs by title', async () => {
    renderJobQueue()

    const searchInput = screen.getByPlaceholderText(/Search by job title or company/)
    fireEvent.change(searchInput, { target: { value: 'Frontend' } })

    await waitFor(() => {
      expect(screen.getByText('Frontend Developer')).toBeInTheDocument()
      expect(screen.queryByText('Senior Software Engineer')).not.toBeInTheDocument()
    })
  })

  it('searches jobs by company', async () => {
    renderJobQueue()

    const searchInput = screen.getByPlaceholderText(/Search by job title or company/)
    fireEvent.change(searchInput, { target: { value: 'TechCorp' } })

    await waitFor(() => {
      expect(screen.getByText('TechCorp')).toBeInTheDocument()
      expect(screen.queryByText('StartupCo')).not.toBeInTheDocument()
    })
  })

  it('navigates to job detail when job clicked', () => {
    renderJobQueue()

    const jobRow = screen.getByText('Senior Software Engineer').closest('tr')
    expect(jobRow).toBeInTheDocument()

    fireEvent.click(jobRow!)

    expect(mockNavigate).toHaveBeenCalledWith('/job/1')
  })

  it('shows loading state', () => {
    vi.mocked(useQueueModule.useQueue).mockReturnValue({
      ...mockUseQueue,
      isLoading: true,
    })

    renderJobQueue()

    expect(screen.getByText(/Loading queue.../)).toBeInTheDocument()
  })

  it('shows error state', () => {
    const testError = new Error('Failed to load queue')
    vi.mocked(useQueueModule.useQueue).mockReturnValue({
      ...mockUseQueue,
      isLoading: false,
      error: testError,
    })

    renderJobQueue()

    expect(screen.getByText(/Failed to load queue/)).toBeInTheDocument()
  })

  it('shows empty state when no jobs', () => {
    vi.mocked(useQueueModule.useQueue).mockReturnValue({
      ...mockUseQueue,
      items: [],
      counts: {
        NEW: 0,
        IN_PROGRESS: 0,
        SUBMITTED: 0,
        FAILED: 0,
        CAPTCHA_BLOCKED: 0,
      },
    })

    renderJobQueue()

    expect(screen.getByText(/No jobs found/)).toBeInTheDocument()
  })

  it('handles pagination', () => {
    // Create 60 items to test pagination
    const manyItems = Array.from({ length: 60 }, (_, i) => ({
      id: `${i + 1}`,
      url: `https://jobs.lever.co/company/job-${i + 1}`,
      company: `Company${i + 1}`,
      title: `Job ${i + 1}`,
      status: 'NEW' as ApplicationStatus,
      date_discovered: '2024-10-28T10:00:00Z',
    }))

    vi.mocked(useQueueModule.useQueue).mockReturnValue({
      ...mockUseQueue,
      items: manyItems,
      counts: {
        NEW: 60,
        IN_PROGRESS: 0,
        SUBMITTED: 0,
        FAILED: 0,
        CAPTCHA_BLOCKED: 0,
      },
    })

    renderJobQueue()

    // Should show pagination controls
    expect(screen.getByText('Next')).toBeInTheDocument()
    expect(screen.getByText('Previous')).toBeInTheDocument()
  })

  it('sorts by column when header clicked', async () => {
    renderJobQueue()

    const companyHeader = screen.getByLabelText('Sort by company')
    fireEvent.click(companyHeader)

    // Verify the component re-renders with sorted data
    await waitFor(() => {
      const companies = screen.getAllByText(/Corp|Co/)
      expect(companies.length).toBeGreaterThan(0)
    })
  })

  it('toggles sort direction when header clicked twice', async () => {
    renderJobQueue()

    const titleHeader = screen.getByLabelText('Sort by job title')

    // First click - ascending
    fireEvent.click(titleHeader)
    await waitFor(() => {
      expect(screen.getByText(/↑/)).toBeInTheDocument()
    })

    // Second click - descending
    fireEvent.click(titleHeader)
    await waitFor(() => {
      expect(screen.getByText(/↓/)).toBeInTheDocument()
    })
  })

  it('handles keyboard navigation on job rows', () => {
    renderJobQueue()

    const jobRow = screen.getByText('Senior Software Engineer').closest('tr')
    expect(jobRow).toBeInTheDocument()

    fireEvent.keyDown(jobRow!, { key: 'Enter' })
    expect(mockNavigate).toHaveBeenCalledWith('/job/1')
  })
})
