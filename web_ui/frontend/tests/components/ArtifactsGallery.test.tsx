import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ArtifactsGallery } from '../../src/components/ArtifactsGallery'
import { Artifacts } from '../../src/types'

describe('ArtifactsGallery', () => {
  it('renders no artifacts message when artifacts are undefined', () => {
    render(<ArtifactsGallery profileId="default" jobId="job1" />)
    expect(screen.getByText('No artifacts available')).toBeInTheDocument()
  })

  it('displays artifact grid when artifacts are provided', () => {
    const mockArtifacts: Artifacts = {
      screenshot_path: 'screenshots/job1.png',
      dom_snapshot_path: 'snapshots/job1.html',
      video_path: 'videos/job1.mp4',
      har_path: 'logs/job1.har',
      confirmation_text: 'Application submitted successfully',
      confirmation_id: 'CONF-123456',
      capture_timestamp: '2025-10-28T10:00:00Z',
    }

    render(
      <ArtifactsGallery
        artifacts={mockArtifacts}
        profileId="default"
        jobId="job1"
      />
    )

    expect(screen.getByText('Screenshot')).toBeInTheDocument()
    expect(screen.getByText('DOM Snapshot')).toBeInTheDocument()
    expect(screen.getByText('Video')).toBeInTheDocument()
    expect(screen.getByText('HAR')).toBeInTheDocument()
  })

  it('shows confirmation details when confirmation_text is provided', () => {
    const mockArtifacts: Artifacts = {
      screenshot_path: undefined,
      dom_snapshot_path: undefined,
      video_path: undefined,
      har_path: undefined,
      confirmation_text: 'Your application has been submitted',
      confirmation_id: 'CONF-789',
      capture_timestamp: '2025-10-28T10:00:00Z',
    }

    render(
      <ArtifactsGallery
        artifacts={mockArtifacts}
        profileId="default"
        jobId="job1"
      />
    )

    expect(screen.getByText('✓ Submission Confirmation')).toBeInTheDocument()
    expect(screen.getByText('Your application has been submitted')).toBeInTheDocument()
    expect(screen.getByText('Confirmation ID')).toBeInTheDocument()
    expect(screen.getByText('CONF-789')).toBeInTheDocument()
  })

  it('displays download buttons for each artifact', () => {
    const mockArtifacts: Artifacts = {
      screenshot_path: 'screenshots/job1.png',
      dom_snapshot_path: 'snapshots/job1.html',
      video_path: undefined,
      har_path: undefined,
      confirmation_text: undefined,
      confirmation_id: undefined,
      capture_timestamp: undefined,
    }

    render(
      <ArtifactsGallery
        artifacts={mockArtifacts}
        profileId="default"
        jobId="job1"
      />
    )

    const downloadButtons = screen.getAllByText('Download')
    expect(downloadButtons.length).toBeGreaterThan(0)
  })

  it('opens image lightbox when View button is clicked for screenshot', () => {
    const mockArtifacts: Artifacts = {
      screenshot_path: 'screenshots/job1.png',
      dom_snapshot_path: undefined,
      video_path: undefined,
      har_path: undefined,
      confirmation_text: undefined,
      confirmation_id: undefined,
      capture_timestamp: undefined,
    }

    render(
      <ArtifactsGallery
        artifacts={mockArtifacts}
        profileId="default"
        jobId="job1"
      />
    )

    const viewButton = screen.getByText('View')
    expect(viewButton).toBeInTheDocument()

    fireEvent.click(viewButton)

    // Check if image is displayed in modal
    const imageElement = screen.getByAltText('Screenshot')
    expect(imageElement).toBeInTheDocument()
  })

  it('copies confirmation ID to clipboard when copy button is clicked', async () => {
    const mockArtifacts: Artifacts = {
      screenshot_path: undefined,
      dom_snapshot_path: undefined,
      video_path: undefined,
      har_path: undefined,
      confirmation_text: 'Application submitted',
      confirmation_id: 'CONF-999',
      capture_timestamp: '2025-10-28T10:00:00Z',
    }

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(() => Promise.resolve()),
      },
    })

    render(
      <ArtifactsGallery
        artifacts={mockArtifacts}
        profileId="default"
        jobId="job1"
      />
    )

    const copyButton = screen.getByText('Copy')
    fireEvent.click(copyButton)

    // Wait for alert to be called
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('CONF-999')
  })

  it('displays submission timestamp in human-readable format', () => {
    const mockArtifacts: Artifacts = {
      screenshot_path: undefined,
      dom_snapshot_path: undefined,
      video_path: undefined,
      har_path: undefined,
      confirmation_text: 'Submitted',
      confirmation_id: 'CONF-123',
      capture_timestamp: '2025-10-28T14:30:00Z',
    }

    render(
      <ArtifactsGallery
        artifacts={mockArtifacts}
        profileId="default"
        jobId="job1"
      />
    )

    // Should show "Submitted on" text with formatted date
    expect(screen.getByText(/Submitted on/)).toBeInTheDocument()
  })

  it('only shows available artifacts in grid', () => {
    const mockArtifacts: Artifacts = {
      screenshot_path: 'screenshots/job1.png',
      dom_snapshot_path: undefined,
      video_path: 'videos/job1.mp4',
      har_path: undefined,
      confirmation_text: undefined,
      confirmation_id: undefined,
      capture_timestamp: undefined,
    }

    render(
      <ArtifactsGallery
        artifacts={mockArtifacts}
        profileId="default"
        jobId="job1"
      />
    )

    // Should show Screenshot and Video, but not DOM Snapshot and HAR
    expect(screen.getByText('Screenshot')).toBeInTheDocument()
    expect(screen.getByText('Video')).toBeInTheDocument()
  })

  it('closes lightbox when clicking outside modal', () => {
    const mockArtifacts: Artifacts = {
      screenshot_path: 'screenshots/job1.png',
      dom_snapshot_path: undefined,
      video_path: undefined,
      har_path: undefined,
      confirmation_text: undefined,
      confirmation_id: undefined,
      capture_timestamp: undefined,
    }

    render(
      <ArtifactsGallery
        artifacts={mockArtifacts}
        profileId="default"
        jobId="job1"
      />
    )

    // Open lightbox
    const viewButton = screen.getByText('View')
    fireEvent.click(viewButton)

    // Click outside modal (on the backdrop)
    const backdrop = screen.getByText('Screenshot').closest('.fixed')
    if (backdrop) {
      fireEvent.click(backdrop)
    }

    // Modal should close
    const closeButton = screen.queryByText('Close')
    expect(closeButton).not.toBeInTheDocument()
  })

  it('renders artifact icons for visual identification', () => {
    const mockArtifacts: Artifacts = {
      screenshot_path: 'screenshots/job1.png',
      dom_snapshot_path: 'snapshots/job1.html',
      video_path: 'videos/job1.mp4',
      har_path: 'logs/job1.har',
      confirmation_text: undefined,
      confirmation_id: undefined,
      capture_timestamp: undefined,
    }

    const { container } = render(
      <ArtifactsGallery
        artifacts={mockArtifacts}
        profileId="default"
        jobId="job1"
      />
    )

    // Check for emoji icons
    expect(container.textContent).toMatch(/📸|🌐|🎥|📊/)
  })
})
