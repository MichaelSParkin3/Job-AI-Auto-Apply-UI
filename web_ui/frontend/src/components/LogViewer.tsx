import { useState } from 'react'
import { ChevronDown, Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface LogViewerProps {
  jobId: string
  profileId: string
}

export function LogViewer({ jobId, profileId }: LogViewerProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  // This is a placeholder since we don't have actual logs stored yet
  // In the future, this could fetch logs from a separate endpoint
  // or load them from the artifacts

  const handleCopyLogs = async () => {
    const text = `Job ID: ${jobId}\nProfile ID: ${profileId}\n\nNo structured logs available for this job yet.`
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-6 py-4 hover:bg-gray-50 flex items-center justify-between transition-colors"
      >
        <div className="flex items-center gap-3">
          <ChevronDown
            size={18}
            className={`transition-transform ${isExpanded ? 'rotate-0' : '-rotate-90'}`}
          />
          <h2 className="text-lg font-semibold text-gray-900">
            Application Logs
          </h2>
        </div>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="border-t border-gray-200 bg-gray-50">
          <div className="px-6 py-4 flex items-center justify-between mb-4">
            <p className="text-sm text-gray-600">
              Structured event logs from the application attempt
            </p>
            <Button
              onClick={handleCopyLogs}
              variant="outline"
              size="sm"
            >
              {copied ? (
                <>
                  <Check size={16} className="mr-2" />
                  Copied
                </>
              ) : (
                <>
                  <Copy size={16} className="mr-2" />
                  Copy
                </>
              )}
            </Button>
          </div>

          <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-xs overflow-x-auto max-h-96 overflow-y-auto">
            <div className="space-y-2">
              <div className="text-gray-500">
                # Application logs for job {jobId}
              </div>
              <div>
                <span className="text-blue-400">Job ID:</span>{' '}
                <span className="text-green-400">{jobId}</span>
              </div>
              <div>
                <span className="text-blue-400">Profile:</span>{' '}
                <span className="text-green-400">{profileId}</span>
              </div>
              <div className="text-gray-500 mt-4">
                # Event logs
              </div>
              <div className="text-yellow-600">
                [INFO] Logs are captured during apply process
              </div>
              <div className="text-yellow-600">
                [INFO] Check artifacts for complete diagnostics (video, HAR, DOM snapshots)
              </div>
              <div className="text-gray-600 mt-4 text-xs">
                Note: Detailed structured logs are captured to the artifacts directory.
                Enable AUTO_APPLY_DIAGNOSTICS=1 for comprehensive logging.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
