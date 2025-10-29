import React, { useState } from 'react'
import { Artifacts } from '../types/index'
import { Button } from './Button'
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
          <div
            key={artifact.type}
            className="border border-gray-200 rounded-lg p-4 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start justify-between mb-3">
              <h3 className="text-lg font-semibold text-gray-900">
                <span className="mr-2">{artifact.icon}</span>
                {artifact.type}
              </h3>
            </div>

            <p className="text-sm text-gray-600 mb-4 truncate">
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
          </div>
        ))}
      </div>

      {/* Confirmation Details */}
      {artifacts.confirmation_text && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-green-900 mb-3">
            ✓ Submission Confirmation
          </h3>

          <div className="space-y-3">
            <p className="text-green-800">
              {artifacts.confirmation_text}
            </p>

            {artifacts.confirmation_id && (
              <div className="flex items-center justify-between bg-white p-3 rounded border border-green-200">
                <div>
                  <p className="text-sm text-gray-600 mb-1">
                    Confirmation ID
                  </p>
                  <p className="font-mono text-lg text-gray-900">
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
          </div>
        </div>
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
