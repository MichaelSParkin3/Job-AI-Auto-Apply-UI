import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'

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
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-2xl">
            Job Description
          </CardTitle>
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopy}
          >
            Copy
          </Button>
        </CardHeader>

        <CardContent>
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
        </CardContent>
      </Card>

      {/* Dialog for full text */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-2xl max-h-96 overflow-auto">
          <DialogHeader>
            <DialogTitle>Full Job Description</DialogTitle>
          </DialogHeader>

          <div
            className="prose prose-sm max-w-none text-gray-700 my-4"
            style={{ whiteSpace: 'pre-wrap' }}
          >
            {postingText}
          </div>

          <DialogFooter>
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
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
