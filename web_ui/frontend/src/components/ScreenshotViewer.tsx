import { useState } from 'react'
import { ZoomIn, ZoomOut, Download, X } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ScreenshotViewerProps {
  screenshotPath: string
  profileId: string
}

export function ScreenshotViewer({ screenshotPath, profileId }: ScreenshotViewerProps) {
  const [zoom, setZoom] = useState(1)
  const [isFullscreen, setIsFullscreen] = useState(false)

  const imageUrl = `/api/artifacts/${profileId}/screenshots/${screenshotPath.split('/').pop()}`

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.2, 3))
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.2, 0.5))
  const handleDownload = () => {
    const link = document.createElement('a')
    link.href = imageUrl
    link.download = screenshotPath.split('/').pop() || 'screenshot.png'
    link.click()
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Screenshot</h2>

      {/* Controls */}
      <div className="flex items-center gap-2 mb-4 pb-4 border-b border-gray-200">
        <Button
          onClick={handleZoomOut}
          variant="outline"
          size="sm"
          disabled={zoom <= 0.5}
        >
          <ZoomOut size={16} />
        </Button>
        <span className="text-sm text-gray-600 min-w-12 text-center">
          {Math.round(zoom * 100)}%
        </span>
        <Button
          onClick={handleZoomIn}
          variant="outline"
          size="sm"
          disabled={zoom >= 3}
        >
          <ZoomIn size={16} />
        </Button>
        <Button
          onClick={handleDownload}
          variant="outline"
          size="sm"
          className="ml-auto"
        >
          <Download size={16} className="mr-2" />
          Download
        </Button>
        <Button
          onClick={() => setIsFullscreen(!isFullscreen)}
          variant="outline"
          size="sm"
        >
          {isFullscreen ? <X size={16} /> : 'Fullscreen'}
        </Button>
      </div>

      {/* Image Viewer */}
      {isFullscreen ? (
        <div className="fixed inset-0 bg-black z-50 flex items-center justify-center">
          <div className="relative w-full h-full flex items-center justify-center">
            <img
              src={imageUrl}
              alt="Job application screenshot"
              className="max-w-full max-h-full object-contain"
              style={{ transform: `scale(${zoom})` }}
            />
            <Button
              onClick={() => setIsFullscreen(false)}
              variant="outline"
              size="sm"
              className="absolute top-4 right-4 bg-white"
            >
              <X size={16} />
            </Button>
          </div>
        </div>
      ) : (
        <div className="overflow-auto rounded-lg bg-gray-50 p-4">
          <div className="flex items-center justify-center" style={{ minHeight: '400px' }}>
            <img
              src={imageUrl}
              alt="Job application screenshot"
              className="max-w-full object-contain transition-transform"
              style={{ transform: `scale(${zoom})` }}
              onError={(e) => {
                const img = e.target as HTMLImageElement
                img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23f3f4f6" width="400" height="300"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%236b7280" font-family="sans-serif"%3EScreenshot not found%3C/text%3E%3C/svg%3E'
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
