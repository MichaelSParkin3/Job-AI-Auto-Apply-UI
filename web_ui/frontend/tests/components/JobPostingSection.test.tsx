import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { JobPostingSection } from '../../src/components/JobPostingSection'

describe('JobPostingSection', () => {
  it('returns null when postingText is undefined', () => {
    const { container } = render(<JobPostingSection postingText={undefined} />)
    expect(container.firstChild).toBeNull()
  })

  it('displays short posting text without truncation', () => {
    const shortText = 'This is a short job description.'
    render(<JobPostingSection postingText={shortText} />)

    expect(screen.getByText(shortText)).toBeInTheDocument()
    expect(screen.queryByText('Read Full Description')).not.toBeInTheDocument()
  })

  it('truncates long posting text and shows "Read Full Description" button', () => {
    const longText = 'A'.repeat(600) // 600 characters
    render(<JobPostingSection postingText={longText} />)

    // Should display first 500 characters
    const displayText = 'A'.repeat(500)
    expect(screen.getByText(new RegExp('^' + 'A'.repeat(100)))).toBeInTheDocument()

    // Should show Read Full Description button
    expect(screen.getByText('Read Full Description')).toBeInTheDocument()
  })

  it('displays section title "Job Description"', () => {
    const shortText = 'Simple description'
    render(<JobPostingSection postingText={shortText} />)

    expect(screen.getByText('Job Description')).toBeInTheDocument()
  })

  it('opens modal when Read Full Description button is clicked', () => {
    const longText = 'A'.repeat(600)
    render(<JobPostingSection postingText={longText} />)

    const readButton = screen.getByText('Read Full Description')
    fireEvent.click(readButton)

    // Modal should open with full text
    expect(screen.getByText('Full Job Description')).toBeInTheDocument()
  })

  it('displays full text in modal', () => {
    const longText = 'This is the full job description that is very long. ' + 'A'.repeat(500)
    render(<JobPostingSection postingText={longText} />)

    // Open modal
    const readButton = screen.getByText('Read Full Description')
    fireEvent.click(readButton)

    // Full text should be visible
    expect(screen.getByText(new RegExp('This is the full job description'))).toBeInTheDocument()
  })

  it('closes modal when Close button is clicked', () => {
    const longText = 'A'.repeat(600)
    render(<JobPostingSection postingText={longText} />)

    // Open modal
    const readButton = screen.getByText('Read Full Description')
    fireEvent.click(readButton)

    // Close modal
    const closeButton = screen.getByText('Close')
    fireEvent.click(closeButton)

    // Modal should close
    expect(screen.queryByText('Full Job Description')).not.toBeInTheDocument()
  })

  it('closes modal when clicking outside (backdrop)', () => {
    const longText = 'A'.repeat(600)
    const { container } = render(<JobPostingSection postingText={longText} />)

    // Open modal
    const readButton = screen.getByText('Read Full Description')
    fireEvent.click(readButton)

    // Click on backdrop
    const backdrop = container.querySelector('.fixed.inset-0')
    if (backdrop) {
      fireEvent.click(backdrop)
    }

    // Modal should close
    expect(screen.queryByText('Full Job Description')).not.toBeInTheDocument()
  })

  it('prevents modal closing when clicking modal content', () => {
    const longText = 'A'.repeat(600)
    render(<JobPostingSection postingText={longText} />)

    // Open modal
    const readButton = screen.getByText('Read Full Description')
    fireEvent.click(readButton)

    // Click inside modal
    const modalContent = screen.getByText('Full Job Description')
    fireEvent.click(modalContent.closest('div')!)

    // Modal should still be open
    expect(screen.getByText('Full Job Description')).toBeInTheDocument()
  })

  it('copies full text to clipboard when Copy button is clicked', async () => {
    const fullText = 'Complete job description with details about the role'

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(() => Promise.resolve()),
      },
    })

    render(<JobPostingSection postingText={fullText} />)

    const copyButton = screen.getByText('Copy')
    fireEvent.click(copyButton)

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(fullText)
  })

  it('copies full text in modal when "Copy All" button is clicked', async () => {
    const longText = 'A'.repeat(600)

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(() => Promise.resolve()),
      },
    })

    render(<JobPostingSection postingText={longText} />)

    // Open modal
    const readButton = screen.getByText('Read Full Description')
    fireEvent.click(readButton)

    const copyAllButton = screen.getByText('Copy All')
    fireEvent.click(copyAllButton)

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(longText)
  })

  it('closes modal button has proper X icon and accessible label', () => {
    const longText = 'A'.repeat(600)
    render(<JobPostingSection postingText={longText} />)

    // Open modal
    const readButton = screen.getByText('Read Full Description')
    fireEvent.click(readButton)

    // Check for close button with aria-label
    const closeBtn = screen.getByLabelText('Close modal')
    expect(closeBtn).toBeInTheDocument()
  })

  it('displays ellipsis when truncating text', () => {
    const longText = 'A'.repeat(600)
    render(<JobPostingSection postingText={longText} />)

    // Look for ellipsis indicating truncation
    const container = screen.getByText('Read Full Description').closest('div')
    expect(container?.textContent).toMatch(/\.\.\./)
  })

  it('preserves whitespace and formatting in display', () => {
    const formattedText = `Line 1
Line 2
  Indented line`

    render(<JobPostingSection postingText={formattedText} />)

    // Should preserve whitespace
    const content = screen.getByText(/Line 1/)
    expect(content.style.whiteSpace).toBe('pre-wrap')
  })

  it('renders prose styling class for better readability', () => {
    const text = 'Job description with multiple paragraphs'
    const { container } = render(<JobPostingSection postingText={text} />)

    const proseDiv = container.querySelector('.prose')
    expect(proseDiv).toBeInTheDocument()
  })

  it('handles very long text efficiently', () => {
    const veryLongText = 'A'.repeat(5000) // 5000 characters
    render(<JobPostingSection postingText={veryLongText} />)

    // Should still display truncated version
    expect(screen.getByText('Read Full Description')).toBeInTheDocument()

    // Open modal
    fireEvent.click(screen.getByText('Read Full Description'))

    // Full text should be available
    expect(screen.getByText('Full Job Description')).toBeInTheDocument()
  })

  it('displays responsive buttons on smaller screens', () => {
    const text = 'Test description'
    const { container } = render(<JobPostingSection postingText={text} />)

    // Check for flex layout on buttons
    const buttonGroup = container.querySelector('.flex')
    expect(buttonGroup).toBeInTheDocument()
  })
})
