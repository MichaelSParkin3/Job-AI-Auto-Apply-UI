import React, { useState } from 'react'
import { Artifacts } from '../types/index'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useLazyLoadImage } from '../hooks/useLazyLoadImage'

interface ArtifactsGalleryProps {
  artifacts?: Artifacts
  profileId: string
  jobId: string
}

export const ArtifactsGallery: React.FC<
  ArtifactsGalleryProps
> = ({ artifacts, profileId, jobId }) => {
  const [selectedImage, setSelectedImage] = useState<
    string | null
  >(null)

  if (!artifacts) {
    return (
      <div className="text-center py-8 text-gray-500">
        No artifacts available
      </div>
    )
  }

  const artifactList: Array<{
    type: string
    path: string | undefined
    icon: string
  }> = [
    {
      type: 'Screenshot',
      path: artifacts.screenshot_path,
      icon: '📸',
    },
    {
      type: 'DOM Snapshot',
      path: artifacts.dom_snapshot_path,
      icon: '🌐',
    },
    {
      type: 'Video',
      path: artifacts.video_path,
      icon: '🎥',
    },
    {
      type: 'HAR',
      path: artifacts.har_path,
      icon: '📊',
    },
  ]

  const availableArtifacts = artifactList.filter(
    (a) => a.path
  )

  if (availableArtifacts.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No artifacts available
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Artifacts List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {availableArtifacts.map((artifact) => (
          <Card key={artifact.type}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span>{artifact.icon}</span>
                {artifact.type}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-gray-600 truncate">
                {artifact.path}
              </p>

              <div className="flex gap-2">
                {artifact.type === 'Screenshot' &&
                  artifact.path && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setSelectedImage(artifact.path || null)
                      }
                    >
                      View
                    </Button>
                  )}

                <a
                  href={`/api/v1/artifacts/${profileId}/${jobId}/${artifact.path?.split('/').pop()}`}
                  download
                >
                  <Button size="sm">Download</Button>
                </a>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Confirmation Details */}
      {artifacts.confirmation_text && (
        <Card className="border-green-200 bg-green-50">
          <CardHeader>
            <div className="flex items-center gap-2">
              <span className="text-lg">✓</span>
              <CardTitle className="text-green-900">
                Submission Confirmation
              </CardTitle>
              <Badge variant="default" className="ml-auto bg-green-600">
                Confirmed
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-green-800">
              {artifacts.confirmation_text}
            </p>

            {artifacts.confirmation_id && (
              <div className="flex items-center justify-between bg-white p-4 rounded-lg border border-green-200">
                <div>
                  <p className="text-sm text-gray-600 mb-2">
                    Confirmation ID
                  </p>
                  <p className="font-mono text-sm text-gray-900 break-all">
                    {artifacts.confirmation_id}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    navigator.clipboard.writeText(
                      artifacts.confirmation_id || ''
                    )
                    alert('Copied to clipboard!')
                  }}
                  className="ml-4 flex-shrink-0"
                >
                  Copy
                </Button>
              </div>
            )}

            {artifacts.capture_timestamp && (
              <p className="text-sm text-gray-600">
                Submitted on{' '}
                {new Date(
                  artifacts.capture_timestamp
                ).toLocaleString()}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Image Lightbox */}
      {selectedImage && <ImageLightbox imageUrl={selectedImage} onClose={() => setSelectedImage(null)} />}
    </div>
  )
}

interface ImageLightboxProps {
  imageUrl: string
  onClose: () => void
}

const ImageLightbox: React.FC<ImageLightboxProps> = ({
  imageUrl,
  onClose,
}) => {
  const { imageRef, isVisible } = useLazyLoadImage({
    threshold: 0.5,
    rootMargin: '0px',
  })

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg max-w-2xl max-h-96 overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 text-center">
          {isVisible ? (
            <img
              ref={imageRef}
              src={imageUrl}
              alt="Screenshot"
              className="max-w-full h-auto"
              loading="lazy"
            />
          ) : (
            <div className="h-96 flex items-center justify-center text-gray-500">
              Loading image...
            </div>
          )}
        </div>
        <div className="p-4 border-t flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  )
}
