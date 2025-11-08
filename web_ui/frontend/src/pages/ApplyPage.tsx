import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { ApplyForm } from '@/components/ApplyForm'
import { ApplyProgress } from '@/components/ApplyProgress'
import type { Profile } from '@/lib/api'

export function ApplyPage() {
  const { selectedProfile } = useOutletContext<{ selectedProfile: Profile }>()
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [activeWebsocketUrl, setActiveWebsocketUrl] = useState<string | null>(null)

  if (!selectedProfile) {
    return (
      <div className="p-8">
        <p className="text-gray-600">Please select a profile to apply to jobs</p>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Apply to Jobs</h2>
        <p className="text-gray-600 mt-1">
          Start the auto-apply process for jobs in your queue
        </p>
      </div>

      {activeTaskId && activeWebsocketUrl ? (
        <ApplyProgress
          taskId={activeTaskId}
          websocketUrl={activeWebsocketUrl}
          onClose={() => {
            setActiveTaskId(null)
            setActiveWebsocketUrl(null)
          }}
        />
      ) : (
        <ApplyForm
          profileId={selectedProfile.id}
          onTaskCreated={(taskId, websocketUrl) => {
            setActiveTaskId(taskId)
            setActiveWebsocketUrl(websocketUrl)
          }}
        />
      )}
    </div>
  )
}
