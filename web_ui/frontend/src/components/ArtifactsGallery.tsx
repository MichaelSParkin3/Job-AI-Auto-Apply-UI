import { useState } from 'react'
import { Download, FileText, Video, Code, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScreenshotViewer } from '@/components/ScreenshotViewer'
import type { ArtifactsResponse } from '@/lib/api'

interface ArtifactsGalleryProps {
  artifacts: ArtifactsResponse | undefined
  profileId: string
}

interface ArtifactItem {
  name: string
  type: 'video' | 'har' | 'dom' | 'screenshot'
  path: string | undefined
  icon: React.ReactNode
  description: string
}

interface ScreenshotItem {
  name: string
  path: string
  description: string
}

export function ArtifactsGallery({ artifacts, profileId }: ArtifactsGalleryProps) {
  const [selectedScreenshot, setSelectedScreenshot] = useState<ScreenshotItem | null>(null)

  if (!artifacts) {
    return null
  }

  const artifactItems: ArtifactItem[] = [
    {
      name: 'Video Recording',
      type: 'video',
      path: artifacts.video_path,
      icon: <Video size={20} />,
      description: 'Full application process recording',
    },
    {
      name: 'Network Log (HAR)',
      type: 'har',
      path: artifacts.har_path,
      icon: <Code size={20} />,
      description: 'HTTP Archive with network requests',
    },
    {
      name: 'DOM Snapshot',
      type: 'dom',
      path: artifacts.dom_snapshot_path,
      icon: <FileText size={20} />,
      description: 'HTML snapshot of the page',
    },
  ]

  // Separate screenshots from other artifacts
  const screenshots: ScreenshotItem[] = []
  if (artifacts.screenshot_before_path) {
    screenshots.push({
      name: 'Before Screenshot',
      path: artifacts.screenshot_before_path,
      description: 'Form state before submission',
    })
  }
  if (artifacts.screenshot_after_path) {
    screenshots.push({
      name: 'After Screenshot',
      path: artifacts.screenshot_after_path,
      description: 'Confirmation page after submission',
    })
  }
  if (artifacts.screenshot_path) {
    screenshots.push({
      name: 'Screenshot',
      path: artifacts.screenshot_path,
      description: 'Application screenshot',
    })
  }

  const availableArtifacts = artifactItems.filter((item) => item.path)
  const availableScreenshots = screenshots

  if (availableArtifacts.length === 0 && availableScreenshots.length === 0) {
    return null
  }

  const extractPathComponents = (path: string): { jobId: string; fileName: string } => {
    // Path format: data/artifacts/{profile_id}/{job_id}/{filename}
    const parts = path.split('/')
    const fileName = parts[parts.length - 1] || path
    const jobId = parts[parts.length - 2] || ''
    return { jobId, fileName }
  }

  const handleDownload = (path: string | undefined, _name: string) => {
    if (!path) return

    const { jobId, fileName } = extractPathComponents(path)
    const url = `/api/artifacts/${profileId}/${jobId}/${fileName}`

    const link = document.createElement('a')
    link.href = url
    link.download = fileName
    link.click()
  }

  const getScreenshotUrl = (path: string): string => {
    const { jobId, fileName } = extractPathComponents(path)
    return `/api/artifacts/${profileId}/${jobId}/${fileName}`
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Captured Artifacts</h2>

      {/* Screenshots Section */}
      {availableScreenshots.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Screenshots</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {availableScreenshots.map((screenshot) => (
              <div key={screenshot.name} className="relative group">
                <button
                  onClick={() => setSelectedScreenshot(screenshot)}
                  className="w-full aspect-video bg-gray-100 border border-gray-200 rounded-lg overflow-hidden hover:border-gray-300 transition-colors group cursor-pointer flex items-center justify-center"
                >
                  <img
                    src={getScreenshotUrl(screenshot.path)}
                    alt={screenshot.name}
                    className="w-full h-full object-cover group-hover:opacity-75 transition-opacity"
                  />
                </button>
                <div className="mt-2">
                  <h4 className="text-sm font-medium text-gray-900">{screenshot.name}</h4>
                  <p className="text-xs text-gray-600">{screenshot.description}</p>
                  <Button
                    onClick={() => handleDownload(screenshot.path, screenshot.name)}
                    variant="outline"
                    size="sm"
                    className="w-full mt-2"
                  >
                    <Download size={16} className="mr-2" />
                    Download
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Other Artifacts Section */}
      {availableArtifacts.length > 0 && (
        <div>
          {availableScreenshots.length > 0 && (
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Other Artifacts</h3>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {availableArtifacts.map((item) => (
              <div
                key={item.name}
                className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start gap-3 mb-3">
                  <div className="text-gray-400">{item.icon}</div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-900 truncate">{item.name}</h3>
                    <p className="text-sm text-gray-600">{item.description}</p>
                  </div>
                </div>
                <Button
                  onClick={() => handleDownload(item.path, item.name)}
                  variant="outline"
                  size="sm"
                  className="w-full"
                >
                  <Download size={16} className="mr-2" />
                  Download
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Confirmation Info */}
      {(artifacts.confirmation_text || artifacts.confirmation_id) && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="font-medium text-gray-900 mb-3">Confirmation Details</h3>
          {artifacts.confirmation_id && (
            <div className="mb-3">
              <p className="text-sm text-gray-600">Confirmation ID</p>
              <p className="font-mono text-sm text-gray-900">{artifacts.confirmation_id}</p>
            </div>
          )}
          {artifacts.confirmation_text && (
            <div>
              <p className="text-sm text-gray-600">Confirmation Text</p>
              <p className="text-sm text-gray-900 mt-1">{artifacts.confirmation_text}</p>
            </div>
          )}
        </div>
      )}

      {/* Screenshot Modal */}
      {selectedScreenshot && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedScreenshot(null)}
        >
          <div
            className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-gray-200 sticky top-0 bg-white">
              <div>
                <h3 className="font-semibold text-gray-900">{selectedScreenshot.name}</h3>
                <p className="text-sm text-gray-600">{selectedScreenshot.description}</p>
              </div>
              <button
                onClick={() => setSelectedScreenshot(null)}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                aria-label="Close"
              >
                <X size={20} className="text-gray-600" />
              </button>
            </div>
            <div className="p-4">
              <ScreenshotViewer
                screenshotPath={selectedScreenshot.path}
                profileId={profileId}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
