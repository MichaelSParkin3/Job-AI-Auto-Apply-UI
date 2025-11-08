import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

interface AnswerCachePreviewProps {
  cache: Record<string, string>
}

export function AnswerCachePreview({ cache }: AnswerCachePreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const entries = Object.entries(cache)

  if (entries.length === 0) {
    return null
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
            Cached Answers ({entries.length})
          </h2>
        </div>
        <p className="text-sm text-gray-600">
          Answers from previous applications
        </p>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="border-t border-gray-200 bg-gray-50">
          <div className="divide-y divide-gray-200">
            {entries.map(([question, answer]) => (
              <div key={question} className="px-6 py-4">
                <h3 className="font-medium text-gray-900 mb-2">{question}</h3>
                <p className="text-gray-700 text-sm whitespace-pre-wrap">
                  {answer}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
