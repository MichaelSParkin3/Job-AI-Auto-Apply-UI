import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { QueueGroupResponse, JobItemResponse } from '@/lib/api'

interface JobQueueSectionProps {
  group: QueueGroupResponse
  onJobClick: (jobId: string) => void
}

export function JobQueueSection({
  group,
  onJobClick,
}: JobQueueSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Status color mapping
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new':
        return 'bg-blue-100 text-blue-800'
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800'
      case 'submitted':
        return 'bg-green-100 text-green-800'
      case 'failed':
      case 'skipped':
        return 'bg-red-100 text-red-800'
      case 'captcha_blocked':
        return 'bg-orange-100 text-orange-800'
      case 'pending_review':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'new':
        return 'New'
      case 'in_progress':
        return 'In Progress'
      case 'submitted':
        return 'Submitted'
      case 'failed':
        return 'Failed'
      case 'skipped':
        return 'Skipped'
      case 'captcha_blocked':
        return 'CAPTCHA'
      case 'pending_review':
        return 'Review'
      default:
        return status
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 hover:bg-gray-50 flex items-center justify-between transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <ChevronDown
            size={16}
            className={`flex-shrink-0 transition-transform ${
              isExpanded ? 'rotate-0' : '-rotate-90'
            }`}
          />
          <h3 className="text-sm font-semibold text-gray-700 truncate">
            {group.label}
          </h3>
        </div>
        <Badge className="bg-gray-200 text-gray-800 flex-shrink-0">
          {group.count}
        </Badge>
      </button>

      {/* Items */}
      {isExpanded && (
        <div className="border-t border-gray-200 bg-gray-50">
          <div className="max-h-96 overflow-y-auto">
            {group.items.length === 0 ? (
              <div className="px-4 py-3 text-center">
                <p className="text-xs text-gray-500">No items</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {group.items.map((item) => (
                  <JobQueueItem
                    key={item.id}
                    item={item}
                    getStatusColor={getStatusColor}
                    getStatusLabel={getStatusLabel}
                    onClick={() => onJobClick(item.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

interface JobQueueItemProps {
  item: JobItemResponse
  getStatusColor: (status: string) => string
  getStatusLabel: (status: string) => string
  onClick: () => void
}

function JobQueueItem({
  item,
  getStatusColor,
  getStatusLabel,
  onClick,
}: JobQueueItemProps) {
  return (
    <button
      onClick={onClick}
      className="w-full px-4 py-3 text-left hover:bg-white transition-colors flex flex-col gap-2"
    >
      {/* Job Title */}
      <div className="flex items-start gap-2 min-w-0">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-900 truncate">
            {item.title}
          </h4>
          <p className="text-xs text-gray-600 truncate">{item.company}</p>
        </div>
        <Badge className={`flex-shrink-0 text-xs ${getStatusColor(item.status)}`}>
          {getStatusLabel(item.status)}
        </Badge>
      </div>

      {/* Meta information */}
      <div className="text-xs text-gray-500">
        {item.details?.location && <span>{item.details.location}</span>}
      </div>
    </button>
  )
}
