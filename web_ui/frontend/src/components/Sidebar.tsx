import { useNavigate } from 'react-router-dom'
import useSWR from 'swr'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { JobQueueSection } from '@/components/JobQueueSection'
import type { QueueResponse } from '@/lib/api'

interface SidebarProps {
  profileId: string
}

export function Sidebar({ profileId }: SidebarProps) {
  const navigate = useNavigate()
  const { data: queue, isLoading, error } = useSWR<QueueResponse>(
    profileId ? `/api/queues/${profileId}` : null,
    async (url) => {
      const res = await fetch(url)
      if (!res.ok) throw new Error('Failed to fetch queue')
      return res.json()
    },
    { refreshInterval: 5000 } // Poll every 5 seconds
  )

  return (
    <aside className="w-80 border-r border-gray-200 bg-white overflow-y-auto">
      {/* Sidebar Header */}
      <div className="sticky top-0 border-b border-gray-200 bg-white p-4 z-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700">Jobs Queue</h2>
          {isLoading && <Loader2 className="h-4 w-4 animate-spin text-gray-400" />}
        </div>

        {/* Action Buttons */}
        <div className="space-y-2">
          <Button
            onClick={() => navigate('/discover')}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
            size="sm"
          >
            Discover Jobs
          </Button>
          <Button
            onClick={() => navigate('/apply')}
            className="w-full bg-green-600 hover:bg-green-700 text-white"
            size="sm"
          >
            Apply to Jobs
          </Button>
        </div>
      </div>

      {/* Queue Content */}
      <div className="p-4">
        {error ? (
          <div className="rounded-lg bg-red-50 p-3">
            <p className="text-sm text-red-600">Error loading queue</p>
          </div>
        ) : !queue || queue.groups.length === 0 ? (
          <div className="rounded-lg bg-gray-50 p-3 text-center">
            <p className="text-sm text-gray-600">No jobs in queue</p>
            <p className="text-xs text-gray-500 mt-1">
              Start by discovering jobs
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {queue.groups.map((group) => (
              <JobQueueSection
                key={group.label}
                group={group}
                onJobClick={(jobId) => {
                  navigate(`/jobs/${profileId}/${jobId}`)
                }}
              />
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}
