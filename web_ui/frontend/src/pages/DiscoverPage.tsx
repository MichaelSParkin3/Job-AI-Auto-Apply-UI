import { useState, useEffect } from 'react'
import { Search, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { ErrorMessage } from '@/components/ErrorMessage'
import { JobQueue } from '@/components/JobQueue'
import { DiscoveryModal } from '@/components/DiscoveryModal'
import { useProfile } from '@/hooks/useProfile'
import { useQueue } from '@/hooks/useQueue'

export default function DiscoverPage() {
  const { profiles, activeProfile, isLoading: profilesLoading } = useProfile()
  const [showDiscoveryModal, setShowDiscoveryModal] = useState(false)
  const [hasDiscovered, setHasDiscovered] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')

  // Use queue hook to show discovered jobs
  const {
    items: queueItems,
    counts: queueCounts,
    isLoading: queueLoading,
    refresh: refreshQueue,
  } = useQueue(activeProfile?.id || '', 5000)

  // Check if there are any NEW items (just discovered)
  const newJobsCount = queueCounts?.NEW || 0

  const handleDiscoveryComplete = async (discoveredCount: number) => {
    setHasDiscovered(true)
    setSuccessMessage(
      `Successfully discovered ${discoveredCount} job(s) and added to queue!`
    )
    setTimeout(() => setSuccessMessage(''), 5000)

    // Refresh queue to show new jobs
    await refreshQueue()
  }

  if (profilesLoading) {
    return <LoadingSpinner message="Loading profiles..." />
  }

  if (!activeProfile) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Discover Jobs</h1>
          <p className="text-gray-600 mt-2">
            Find new job opportunities from Lever job boards
          </p>
        </div>

        <Card className="p-12 text-center">
          <div className="text-6xl mb-4">😕</div>
          <h2 className="text-xl font-semibold mb-2">No Profile Selected</h2>
          <p className="text-gray-600">
            Please create or select a profile before discovering jobs.
          </p>
          <Button className="mt-6">Go to Profiles</Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Discover Jobs</h1>
          <p className="text-gray-600 mt-2">
            Find new opportunities for <span className="font-semibold">{activeProfile.name}</span>
          </p>
        </div>
        <Button
          onClick={() => setShowDiscoveryModal(true)}
          size="lg"
          className="gap-2"
        >
          <Search className="w-5 h-5" />
          Start Discovery
        </Button>
      </div>

      {/* Messages */}
      {successMessage && (
        <Alert className="bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800">
          <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
          <AlertDescription className="text-green-800 dark:text-green-200 ml-2">
            {successMessage}
          </AlertDescription>
        </Alert>
      )}

      {/* Discovery Stats */}
      {queueItems.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <p className="text-sm text-gray-600">Total Jobs</p>
            <p className="text-2xl font-bold">{queueItems.length}</p>
          </Card>

          <Card className="p-4">
            <p className="text-sm text-gray-600">Not Yet Applied</p>
            <p className="text-2xl font-bold">{newJobsCount}</p>
          </Card>

          <Card className="p-4">
            <p className="text-sm text-gray-600">In Progress</p>
            <p className="text-2xl font-bold">{queueCounts?.IN_PROGRESS || 0}</p>
          </Card>

          <Card className="p-4">
            <p className="text-sm text-gray-600">Completed</p>
            <p className="text-2xl font-bold">
              {(queueCounts?.SUBMITTED || 0) + (queueCounts?.FAILED || 0)}
            </p>
          </Card>
        </div>
      )}

      {/* Empty State */}
      {queueItems.length === 0 && !queueLoading && (
        <Card className="p-12 text-center">
          <div className="text-6xl mb-4">🔍</div>
          <h2 className="text-xl font-semibold mb-2">No Jobs Discovered Yet</h2>
          <p className="text-gray-600 mb-6">
            Start a discovery to find job opportunities matching your profile keywords.
          </p>
          <Button
            onClick={() => setShowDiscoveryModal(true)}
            size="lg"
            className="gap-2"
          >
            <Search className="w-4 h-4" />
            Start Discovery
          </Button>
        </Card>
      )}

      {/* Queue of Discovered Jobs */}
      {queueItems.length > 0 && (
        <div className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold mb-4">Job Queue</h2>
            <p className="text-sm text-gray-600 mb-4">
              These are the jobs discovered for your profile. Review and apply when ready.
            </p>
          </div>

          {queueLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
          )}

          {!queueLoading && <JobQueue items={queueItems} />}
        </div>
      )}

      {/* Discovery Modal */}
      <DiscoveryModal
        isOpen={showDiscoveryModal}
        profileId={activeProfile.id}
        onClose={() => setShowDiscoveryModal(false)}
        onDiscoveryComplete={handleDiscoveryComplete}
        onRefreshQueue={refreshQueue}
      />
    </div>
  )
}
