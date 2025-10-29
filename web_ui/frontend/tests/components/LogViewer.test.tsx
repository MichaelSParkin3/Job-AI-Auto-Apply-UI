import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { LogViewer, LogEntry } from '../../src/components/LogViewer'

describe('LogViewer', () => {
  const mockLogs: LogEntry[] = [
    {
      timestamp: '2025-10-28 10:00:00',
      level: 'info',
      message: 'Application started',
    },
    {
      timestamp: '2025-10-28 10:00:05',
      level: 'debug',
      message: 'Loading configuration',
    },
    {
      timestamp: '2025-10-28 10:00:10',
      level: 'warning',
      message: 'No resume found',
    },
    {
      timestamp: '2025-10-28 10:00:15',
      level: 'error',
      message: 'Failed to submit form',
    },
  ]

  it('renders all logs when no filters are applied', () => {
    render(<LogViewer logs={mockLogs} />)

    expect(screen.getByText('Application started')).toBeInTheDocument()
    expect(screen.getByText('Loading configuration')).toBeInTheDocument()
    expect(screen.getByText('No resume found')).toBeInTheDocument()
    expect(screen.getByText('Failed to submit form')).toBeInTheDocument()
  })

  it('filters logs by level', () => {
    render(<LogViewer logs={mockLogs} />)

    // Click on Error filter
    const errorButton = screen.getByText(/❌ Error/)
    fireEvent.click(errorButton)

    // Only error log should be visible
    expect(screen.getByText('Failed to submit form')).toBeInTheDocument()
    expect(screen.queryByText('Application started')).not.toBeInTheDocument()
  })

  it('searches logs by message content', () => {
    render(<LogViewer logs={mockLogs} />)

    const searchInput = screen.getByPlaceholderText('Search logs...')
    fireEvent.change(searchInput, { target: { value: 'resume' } })

    // Only warning log with "resume" should be visible
    expect(screen.getByText('No resume found')).toBeInTheDocument()
    expect(screen.queryByText('Application started')).not.toBeInTheDocument()
  })

  it('searches logs by timestamp', () => {
    render(<LogViewer logs={mockLogs} />)

    const searchInput = screen.getByPlaceholderText('Search logs...')
    fireEvent.change(searchInput, { target: { value: '10:00:10' } })

    // Only log with matching timestamp should be visible
    expect(screen.getByText('No resume found')).toBeInTheDocument()
  })

  it('displays correct log level counts in filter buttons', () => {
    render(<LogViewer logs={mockLogs} />)

    expect(screen.getByText(/ℹ️ Info \(1\)/)).toBeInTheDocument()
    expect(screen.getByText(/❌ Error \(1\)/)).toBeInTheDocument()
    expect(screen.getByText(/⚠️ Warning \(1\)/)).toBeInTheDocument()
  })

  it('displays "All" button with total log count', () => {
    render(<LogViewer logs={mockLogs} />)

    expect(screen.getByText(/All \(4\)/)).toBeInTheDocument()
  })

  it('copies all visible logs to clipboard when Copy button is clicked', async () => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(() => Promise.resolve()),
      },
    })

    render(<LogViewer logs={mockLogs} />)

    const copyButton = screen.getByText('Copy')
    fireEvent.click(copyButton)

    expect(navigator.clipboard.writeText).toHaveBeenCalled()
    const copiedText = (navigator.clipboard.writeText as any).mock.calls[0][0]
    expect(copiedText).toContain('Application started')
  })

  it('calls onClear callback when Clear button is clicked', () => {
    const mockOnClear = vi.fn()
    render(<LogViewer logs={mockLogs} onClear={mockOnClear} />)

    const clearButton = screen.getByText('Clear')
    fireEvent.click(clearButton)

    expect(mockOnClear).toHaveBeenCalled()
  })

  it('hides Clear button when onClear is not provided', () => {
    render(<LogViewer logs={mockLogs} />)

    // Look for Clear button that's not provided
    const buttons = screen.getAllByRole('button')
    const clearButton = buttons.find((btn) => btn.textContent === 'Clear')
    expect(clearButton).not.toBeInTheDocument()
  })

  it('displays live indicator when isLive prop is true', () => {
    render(<LogViewer logs={mockLogs} isLive={true} />)

    expect(screen.getByText(/🔴 Live Logs/)).toBeInTheDocument()
  })

  it('displays standard title when isLive is false', () => {
    render(<LogViewer logs={mockLogs} isLive={false} />)

    expect(screen.getByText('Application Logs')).toBeInTheDocument()
  })

  it('displays "No logs to display" message when logs array is empty', () => {
    render(<LogViewer logs={[]} />)

    expect(screen.getByText('No logs to display')).toBeInTheDocument()
  })

  it('displays correct log count at bottom', () => {
    render(<LogViewer logs={mockLogs} />)

    expect(screen.getByText('Showing 4 of 4 logs')).toBeInTheDocument()
  })

  it('displays correct filtered log count', () => {
    render(<LogViewer logs={mockLogs} />)

    const errorButton = screen.getByText(/❌ Error/)
    fireEvent.click(errorButton)

    expect(screen.getByText('Showing 1 of 4 logs')).toBeInTheDocument()
  })

  it('resets search when clicking All filter', () => {
    render(<LogViewer logs={mockLogs} />)

    // Apply search
    const searchInput = screen.getByPlaceholderText('Search logs...')
    fireEvent.change(searchInput, { target: { value: 'error' } })

    // Then click All
    const allButton = screen.getByText(/All \(/)
    fireEvent.click(allButton)

    // All logs should be visible
    expect(screen.getByText('Application started')).toBeInTheDocument()
  })

  it('combines filter and search correctly', () => {
    render(<LogViewer logs={mockLogs} />)

    // Filter by info level
    const infoButton = screen.getByText(/ℹ️ Info/)
    fireEvent.click(infoButton)

    // Search within filtered results
    const searchInput = screen.getByPlaceholderText('Search logs...')
    fireEvent.change(searchInput, { target: { value: 'started' } })

    expect(screen.getByText('Application started')).toBeInTheDocument()
    expect(screen.queryByText('Loading configuration')).not.toBeInTheDocument()
  })

  it('displays color-coded log levels', () => {
    const { container } = render(<LogViewer logs={mockLogs} />)

    // Check for log level styling classes
    expect(container.textContent).toMatch(/\[INFO\]|\[DEBUG\]|\[WARNING\]|\[ERROR\]/)
  })

  it('applies correct aria-live attribute for accessibility', () => {
    const { container } = render(
      <LogViewer logs={mockLogs} isLive={true} />
    )

    const logContainer = container.querySelector('[role="log"]')
    expect(logContainer).toHaveAttribute('aria-live', 'polite')
  })

  it('applies aria-live="off" when not live', () => {
    const { container } = render(
      <LogViewer logs={mockLogs} isLive={false} />
    )

    const logContainer = container.querySelector('[role="log"]')
    expect(logContainer).toHaveAttribute('aria-live', 'off')
  })
})
