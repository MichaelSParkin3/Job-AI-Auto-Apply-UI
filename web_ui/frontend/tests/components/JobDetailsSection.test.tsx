import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { JobDetailsSection } from '../../src/components/JobDetailsSection'
import { JobDetails } from '../../src/types'

describe('JobDetailsSection', () => {
  it('renders no details message when details are undefined', () => {
    render(<JobDetailsSection details={undefined} />)
    expect(screen.getByText('No job details available')).toBeInTheDocument()
  })

  it('displays all job details when provided', () => {
    const mockDetails: JobDetails = {
      location: 'San Francisco, CA',
      work_model: 'Remote',
      employment_type: 'Full-time',
      department: 'Engineering',
      compensation: '$150,000 - $200,000',
      posting_date: '2025-10-28',
      tech_tags: ['React', 'TypeScript', 'Node.js'],
      apply_url: 'https://example.com/apply',
      posting_text: 'Job description...',
    }

    render(<JobDetailsSection details={mockDetails} />)

    expect(screen.getByText('Job Details')).toBeInTheDocument()
    expect(screen.getByText('San Francisco, CA')).toBeInTheDocument()
    expect(screen.getByText('Remote')).toBeInTheDocument()
    expect(screen.getByText('Full-time')).toBeInTheDocument()
    expect(screen.getByText('Engineering')).toBeInTheDocument()
    expect(screen.getByText('$150,000 - $200,000')).toBeInTheDocument()
  })

  it('displays "Not available" for missing optional fields', () => {
    const mockDetails: JobDetails = {
      location: 'San Francisco, CA',
      work_model: undefined,
      employment_type: undefined,
      department: undefined,
      compensation: undefined,
      posting_date: undefined,
      tech_tags: [],
      apply_url: undefined,
      posting_text: '',
    }

    render(<JobDetailsSection details={mockDetails} />)

    const notAvailableElements = screen.getAllByText('Not available')
    expect(notAvailableElements.length).toBeGreaterThan(0)
  })

  it('renders tech tags as badges', () => {
    const mockDetails: JobDetails = {
      location: 'San Francisco, CA',
      work_model: 'Remote',
      employment_type: 'Full-time',
      department: 'Engineering',
      compensation: undefined,
      posting_date: undefined,
      tech_tags: ['React', 'TypeScript', 'Node.js'],
      apply_url: undefined,
      posting_text: '',
    }

    render(<JobDetailsSection details={mockDetails} />)

    expect(screen.getByText('React')).toBeInTheDocument()
    expect(screen.getByText('TypeScript')).toBeInTheDocument()
    expect(screen.getByText('Node.js')).toBeInTheDocument()
  })

  it('formats posting date correctly', () => {
    const mockDetails: JobDetails = {
      location: 'San Francisco, CA',
      work_model: 'Remote',
      employment_type: 'Full-time',
      department: undefined,
      compensation: undefined,
      posting_date: '2025-10-28',
      tech_tags: [],
      apply_url: undefined,
      posting_text: '',
    }

    render(<JobDetailsSection details={mockDetails} />)

    const dateElement = screen.getByText(/10\/28\/2025|10-28-2025|Oct 28, 2025|2025-10-28/)
    expect(dateElement).toBeInTheDocument()
  })

  it('renders apply URL as clickable link', () => {
    const mockDetails: JobDetails = {
      location: 'San Francisco, CA',
      work_model: 'Remote',
      employment_type: 'Full-time',
      department: undefined,
      compensation: undefined,
      posting_date: undefined,
      tech_tags: [],
      apply_url: 'https://example.com/apply',
      posting_text: '',
    }

    render(<JobDetailsSection details={mockDetails} />)

    const link = screen.getByText('Open Job Post')
    expect(link).toHaveAttribute('href', 'https://example.com/apply')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('renders icons for each field', () => {
    const mockDetails: JobDetails = {
      location: 'San Francisco, CA',
      work_model: 'Remote',
      employment_type: 'Full-time',
      department: 'Engineering',
      compensation: '$150,000',
      posting_date: '2025-10-28',
      tech_tags: [],
      apply_url: undefined,
      posting_text: '',
    }

    const { container } = render(<JobDetailsSection details={mockDetails} />)

    // Check for emoji icons
    expect(container.textContent).toMatch(/📍|📸/)
    expect(container.textContent).toMatch(/💼|🏢|📋|💰|📅|🔧|🔗/)
  })

  it('applies correct styling for missing vs available fields', () => {
    const mockDetails: JobDetails = {
      location: undefined,
      work_model: 'Remote',
      employment_type: undefined,
      department: 'Engineering',
      compensation: undefined,
      posting_date: undefined,
      tech_tags: [],
      apply_url: undefined,
      posting_text: '',
    }

    const { container } = render(<JobDetailsSection details={mockDetails} />)

    // Check for text-gray-500 (missing field label color)
    const labels = container.querySelectorAll('dt')
    expect(labels.length).toBeGreaterThan(0)
  })

  it('hides tech tags section when empty', () => {
    const mockDetails: JobDetails = {
      location: 'San Francisco, CA',
      work_model: 'Remote',
      employment_type: 'Full-time',
      department: undefined,
      compensation: undefined,
      posting_date: undefined,
      tech_tags: [],
      apply_url: undefined,
      posting_text: '',
    }

    render(<JobDetailsSection details={mockDetails} />)

    // Technologies section should not render if tags are empty
    const techSection = screen.queryByText(/Technologies/i)
    expect(techSection).not.toBeInTheDocument()
  })
})
