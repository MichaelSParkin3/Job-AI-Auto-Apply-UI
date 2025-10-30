import { useState, useMemo } from 'react'
import { Search, FileText, Loader2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { ArtifactsGallery } from '@/components/ArtifactsGallery'
import { useProfile } from '@/hooks/useProfile'
import { useQueue } from '@/hooks/useQueue'
import { ApplicationItem } from '@/types'

export default function ArtifactsPage() {
  const { activeProfile, isLoading: profilesLoading } = useProfile()
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null)

  // Use queue hook to get all jobs
  const {
    items: queueItems,
    isLoading: queueLoading,
  } = useQueue(activeProfile?.id || '', 3000)

  // Filter jobs that have artifacts
  const jobsWithArtifacts = useMemo(() => {
    return queueItems.filter((item) => item.artifacts && item.artifacts.paths && item.artifacts.paths.length > 0)
  }, [queueItems])

  // Filter by search query
  const filteredJobs = useMemo(() => {
    return jobsWithArtifacts.filter((item) => {
      const searchLower = searchQuery.toLowerCase()
      return (
        item.company.toLowerCase().includes(searchLower) ||
        item.title.toLowerCase().includes(searchLower) ||
        item.url.toLowerCase().includes(searchLower)
      )
    })
  }, [jobsWithArtifacts, searchQuery])

  // Count artifacts
  const totalArtifacts = useMemo(() => {
    return jobsWithArtifacts.reduce((sum, item) => {
      return sum + (item.artifacts?.paths?.length || 0)
    }, 0)
  }, [jobsWithArtifacts])

  if (profilesLoading) {
    return <LoadingSpinner message="Loading profiles..." />
  }

  if (!activeProfile) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Artifacts</h1>
          <p className="text-gray-600 mt-2">Browse and download application artifacts</p>
        </div>

        <Card className="p-12 text-center">
          <div className="text-6xl mb-4">😕</div>
          <h2 className="text-xl font-semibold mb-2">No Profile Selected</h2>
          <p className="text-gray-600">
            Please create or select a profile to view artifacts.
          </p>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Artifacts</h1>
        <p className="text-gray-600 mt-2">
          Browse screenshots, videos, and other artifacts for <span className="font-semibold">{activeProfile.name}</span>
        </p>
      </div>

      {/* Stats */}
      {jobsWithArtifacts.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Card className="p-4">
            <p className="text-sm text-gray-600">Jobs with Artifacts</p>
            <p className="text-2xl font-bold">{jobsWithArtifacts.length}</p>
          </Card>

          <Card className="p-4">
            <p className="text-sm text-gray-600">Total Artifacts</p>
            <p className="text-2xl font-bold">{totalArtifacts}</p>
          </Card>

          <Card className="p-4">
            <p className="text-sm text-gray-600">Queue Total</p>
            <p className="text-2xl font-bold">{queueItems.length}</p>
          </Card>
        </div>
      )}

      {/* Search */}
      {jobsWithArtifacts.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
          <Input
            placeholder="Search by company, job title, or URL..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      )}

      {/* Loading State */}
      {queueLoading && jobsWithArtifacts.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      )}

      {/* Empty State */}
      {!queueLoading && jobsWithArtifacts.length === 0 && (
        <Card className="p-12 text-center">
          <div className="text-6xl mb-4">📦</div>
          <h2 className="text-xl font-semibold mb-2">No Artifacts Yet</h2>
          <p className="text-gray-600 mb-6">
            Artifacts will appear here once you submit job applications. Screenshots, videos, and other
            evidence will be captured and stored here.
          </p>
          <Button disabled>No Jobs to Apply to</Button>
        </Card>
      )}

      {/* No Results */}
      {!queueLoading && jobsWithArtifacts.length > 0 && filteredJobs.length === 0 && (
        <Alert>
          <AlertDescription>
            No jobs found matching "{searchQuery}". Try adjusting your search.
          </AlertDescription>
        </Alert>
      )}

      {/* Jobs with Artifacts */}
      {!queueLoading && filteredJobs.length > 0 && (
        <div className="space-y-6">
          {filteredJobs.map((job) => (
            <div key={job.id} className="space-y-3">
              {/* Job Header Card */}
              <Card
                className="p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                onClick={() =>
                  setExpandedJobId(expandedJobId === job.id ? null : job.id)
                }
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold truncate">{job.title}</h3>
                      <span className="text-sm bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-1 rounded whitespace-nowrap">
                        {job.artifacts?.paths?.length || 0} artifact{job.artifacts?.paths?.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{job.company}</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {/* Status Badge */}
                      <span
                        className={`text-xs px-2 py-1 rounded font-medium ${
                          job.status === 'SUBMITTED'
                            ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                            : job.status === 'FAILED'
                              ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300'
                              : job.status === 'CAPTCHA_BLOCKED'
                                ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300'
                                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300'
                        }`}
                      >
                        {job.status}
                      </span>

                      {/* Date */}
                      {job.date_applied && (
                        <span className="text-xs text-gray-600">
                          {new Date(job.date_applied).toLocaleDateString()} {new Date(job.date_applied).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="ml-4 flex-shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                    >
                      {expandedJobId === job.id ? 'Hide' : 'View'} Artifacts
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Expanded Artifacts */}
              {expandedJobId === job.id && job.artifacts && (
                <Card className="p-6 bg-gray-50 dark:bg-gray-900">
                  <div className="mb-4">
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
                      Application Evidence
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      URL: <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline break-all">
                        {job.url}
                      </a>
                    </p>
                  </div>

                  <ArtifactsGallery
                    artifacts={job.artifacts}
                    profileId={activeProfile.id}
                    jobId={job.id}
                  />
                </Card>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
