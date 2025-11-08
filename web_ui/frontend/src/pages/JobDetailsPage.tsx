import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import useSWR from 'swr'
import { ArrowLeft, Loader2, AlertCircle, ExternalLink, RotateCcw, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScreenshotViewer } from '@/components/ScreenshotViewer'
import { ArtifactsGallery } from '@/components/ArtifactsGallery'
import { AnswerCachePreview } from '@/components/AnswerCachePreview'
import { LogViewer } from '@/components/LogViewer'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/lib/toast'
import { queuesApi } from '@/lib/api'
import type { JobDetailPageResponse } from '@/lib/api'

export function JobDetailsPage() {
  const { profileId, jobId } = useParams<{ profileId: string; jobId: string }>()
  const navigate = useNavigate()
  const { addToast } = useToast()
  const [statusLoading, setStatusLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [selectedStatus, setSelectedStatus] = useState<string>('')

  const { data, isLoading, error, mutate } = useSWR<JobDetailPageResponse>(
    profileId && jobId ? `/api/queues/${profileId}/jobs/${jobId}` : null,
    async (url: string) => {
      const res = await fetch(url)
      if (!res.ok) throw new Error('Failed to fetch job details')
      return res.json()
    }
  )

  const handleResume = async () => {
    if (!profileId || !jobId) return

    setActionLoading(true)
    try {
      await queuesApi.resumeJob(profileId, jobId)
      addToast({
        title: 'Job Resumed',
        description: 'The job has been resumed and is ready to reapply',
      })
      mutate()
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to resume job'
      addToast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      })
    } finally {
      setActionLoading(false)
    }
  }

  const handleReapply = async () => {
    if (!profileId || !jobId) return

    setActionLoading(true)
    try {
      await queuesApi.reapplyJob(profileId, jobId)
      addToast({
        title: 'Reapply Started',
        description: 'Starting to reapply for this job',
      })
      // Could navigate to apply progress page if desired
      mutate()
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to start reapply'
      addToast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      })
    } finally {
      setActionLoading(false)
    }
  }

  const handleStatusChange = async (newStatus: string) => {
    if (!profileId || !jobId || !newStatus) return

    setStatusLoading(true)
    try {
      await queuesApi.updateJobStatus(profileId, jobId, newStatus, 'manual_update', 'Manually updated status')
      addToast({
        title: 'Status Updated',
        description: `Job status changed to ${newStatus}`,
      })
      mutate()
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to update status'
      addToast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      })
    } finally {
      setStatusLoading(false)
    }
  }

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
        return 'CAPTCHA Blocked'
      case 'pending_review':
        return 'Pending Review'
      default:
        return status
    }
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="flex items-center gap-2 mb-6">
          <Button
            onClick={() => navigate(-1)}
            variant="ghost"
            size="sm"
          >
            <ArrowLeft size={16} className="mr-2" />
            Back
          </Button>
        </div>
        <div className="rounded-lg bg-red-50 p-6 flex items-start gap-3">
          <AlertCircle size={20} className="text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h2 className="text-lg font-semibold text-red-900">Error loading job</h2>
            <p className="text-red-700 text-sm mt-1">{error.message}</p>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading || !data) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="flex items-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          <p className="text-gray-600">Loading job details...</p>
        </div>
      </div>
    )
  }

  const { job, answer_cache } = data

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div className="flex-1">
          <Button
            onClick={() => navigate(-1)}
            variant="ghost"
            size="sm"
            className="mb-4"
          >
            <ArrowLeft size={16} className="mr-2" />
            Back to Queue
          </Button>

          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900">{job.title}</h1>
              <p className="text-lg text-gray-600 mt-1">{job.company}</p>
            </div>
            <Badge className={`text-base px-3 py-1 ${getStatusColor(job.status)}`}>
              {getStatusLabel(job.status)}
            </Badge>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Actions</h3>
        <div className="flex flex-wrap gap-3">
          {/* Open Job Posting */}
          <Button
            onClick={() => window.open(job.url, '_blank')}
            variant="outline"
            size="sm"
          >
            <ExternalLink size={16} className="mr-2" />
            Open Job Posting
          </Button>

          {/* Resume Button (for CAPTCHA_BLOCKED) */}
          {job.status === 'captcha_blocked' && (
            <Button
              onClick={handleResume}
              disabled={actionLoading}
              variant="outline"
              size="sm"
              className="bg-amber-50 border-amber-300 text-amber-900"
            >
              <Play size={16} className="mr-2" />
              {actionLoading ? 'Resuming...' : 'Resume'}
            </Button>
          )}

          {/* Reapply Button (for FAILED/SKIPPED) */}
          {(job.status === 'failed' || job.status === 'skipped') && (
            <Button
              onClick={handleReapply}
              disabled={actionLoading}
              variant="outline"
              size="sm"
              className="bg-blue-50 border-blue-300 text-blue-900"
            >
              <RotateCcw size={16} className="mr-2" />
              {actionLoading ? 'Starting...' : 'Reapply'}
            </Button>
          )}

          {/* Change Status Dropdown */}
          <div className="flex items-center gap-2">
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value)
                if (e.target.value) {
                  handleStatusChange(e.target.value)
                  setSelectedStatus('')
                }
              }}
              disabled={statusLoading}
              className="px-3 py-2 text-sm border border-gray-300 rounded-md bg-white hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              <option value="">Change Status...</option>
              <option value="new">New</option>
              <option value="in_progress">In Progress</option>
              <option value="submitted">Submitted</option>
              <option value="failed">Failed</option>
              <option value="skipped">Skipped</option>
              <option value="captcha_blocked">CAPTCHA Blocked</option>
              <option value="pending_review">Pending Review</option>
            </select>
          </div>
        </div>
      </div>

      {/* Job Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Basic Info */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Job Information</h2>
          <div className="space-y-4">
            {job.details?.location && (
              <div>
                <p className="text-sm text-gray-600">Location</p>
                <p className="text-gray-900">{job.details.location}</p>
              </div>
            )}
            {job.details?.employment_type && job.details.employment_type !== 'unknown' && (
              <div>
                <p className="text-sm text-gray-600">Employment Type</p>
                <p className="text-gray-900">{job.details.employment_type}</p>
              </div>
            )}
            {job.details?.work_model && job.details.work_model !== 'unknown' && (
              <div>
                <p className="text-sm text-gray-600">Work Model</p>
                <p className="text-gray-900">{job.details.work_model}</p>
              </div>
            )}
            {job.details?.department && (
              <div>
                <p className="text-sm text-gray-600">Department</p>
                <p className="text-gray-900">{job.details.department}</p>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-600">Discovered</p>
              <p className="text-gray-900">
                {new Date(job.discovered_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>

        {/* Tech Tags */}
        {job.details?.tech_tags && job.details.tech_tags.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Technologies</h2>
            <div className="flex flex-wrap gap-2">
              {job.details.tech_tags.map((tag) => (
                <Badge key={tag} className="bg-blue-100 text-blue-800">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Job Description */}
      {job.details?.posting_excerpt && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Job Description</h2>
          <div className="prose prose-sm max-w-none">
            <p className="text-gray-700 whitespace-pre-wrap">
              {job.details.posting_excerpt}
            </p>
          </div>
        </div>
      )}

      {/* Error Reason */}
      {job.reason && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-8">
          <h2 className="text-lg font-semibold text-red-900 mb-2">Why This Failed</h2>
          <div className="text-red-700">
            <p className="font-semibold">{job.reason.code}</p>
            <p className="mt-1">{job.reason.message}</p>
          </div>
        </div>
      )}

      {/* Screenshots */}
      {job.artifacts?.screenshot_path && (
        <div className="mb-8">
          <ScreenshotViewer
            screenshotPath={job.artifacts.screenshot_path}
            profileId={profileId || ''}
          />
        </div>
      )}

      {/* Artifacts Gallery */}
      <div className="mb-8">
        <ArtifactsGallery
          artifacts={job.artifacts}
          profileId={profileId || ''}
        />
      </div>

      {/* Answer Cache */}
      {answer_cache && Object.keys(answer_cache).length > 0 && (
        <div className="mb-8">
          <AnswerCachePreview cache={answer_cache} />
        </div>
      )}

      {/* Logs (if available) */}
      {job.artifacts?.screenshot_path && (
        <div className="mb-8">
          <LogViewer jobId={job.id} profileId={profileId || ''} />
        </div>
      )}
    </div>
  )
}
