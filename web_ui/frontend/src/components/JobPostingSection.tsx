import React, { useState } from 'react'
import { Button } from '@/components/ui/button'

interface JobPostingSectionProps {
  postingText: string | undefined
}

export const JobPostingSection: React.FC<JobPostingSectionProps> = ({
  postingText,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false)

  if (!postingText) {
    return null
  }

  const isLong = postingText.length > 500
  const displayText = isLong ? postingText.substring(0, 500) : postingText

  const handleCopy = () => {
    navigator.clipboard.writeText(postingText)
    alert('Job description copied to clipboard!')
  }

  return (
    <>
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">
            Job Description
          </h2>
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopy}
          >
            Copy
          </Button>
        </div>

        <div
          className="prose prose-sm max-w-none text-gray-700"
          style={{ whiteSpace: 'pre-wrap' }}
        >
          {displayText}
          {isLong && (
            <>
              <span className="text-gray-500">...</span>
              <div className="mt-4">
                <Button
                  onClick={() => setIsModalOpen(true)}
                  variant="outline"
                  size="sm"
                >
                  Read Full Description
                </Button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Modal for full text */}
      {isModalOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => setIsModalOpen(false)}
        >
          <div
            className="bg-white rounded-lg p-6 max-w-2xl max-h-96 overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Full Job Description
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
                aria-label="Close modal"
              >
                ×
              </button>
            </div>

            <div
              className="prose prose-sm max-w-none text-gray-700 mb-4"
              style={{ whiteSpace: 'pre-wrap' }}
            >
              {postingText}
            </div>

            <div className="flex gap-2 justify-end border-t pt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsModalOpen(false)}
              >
                Close
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(postingText)
                  alert('Copied to clipboard!')
                }}
              >
                Copy All
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
