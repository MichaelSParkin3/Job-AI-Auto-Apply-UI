import { Download, FileText, Video, Code } from 'lucide-react'
import { Button } from '@/components/ui/button'
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

export function ArtifactsGallery({ artifacts, profileId }: ArtifactsGalleryProps) {
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
    {
      name: 'Before Screenshot',
      type: 'screenshot',
      path: artifacts.screenshot_before_path,
      icon: <Code size={20} />,
      description: 'Form state before submission',
    },
    {
      name: 'After Screenshot',
      type: 'screenshot',
      path: artifacts.screenshot_after_path,
      icon: <Code size={20} />,
      description: 'Confirmation page after submission',
    },
  ]

  const availableArtifacts = artifactItems.filter((item) => item.path)

  if (availableArtifacts.length === 0) {
    return null
  }

  const handleDownload = (path: string | undefined, name: string) => {
    if (!path) return

    const fileName = path.split('/').pop() || name
    const artifactType = getArtifactType(path)
    const url = `/api/artifacts/${profileId}/${artifactType}/${fileName}`

    const link = document.createElement('a')
    link.href = url
    link.download = fileName
    link.click()
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Captured Artifacts</h2>

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
    </div>
  )
}

function getArtifactType(path: string): string {
  if (path.includes('.mp4') || path.includes('.webm')) return 'videos'
  if (path.includes('.har') || path.includes('har')) return 'har'
  if (path.includes('.html') || path.includes('dom')) return 'dom_snapshots'
  return 'screenshots'
}
