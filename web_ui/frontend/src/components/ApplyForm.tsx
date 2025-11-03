import { useState } from 'react'
import type { ApplyRequest } from '@/lib/api'
import { applyApi } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface ApplyFormProps {
  profileId: string
  onTaskCreated: (taskId: string, websocketUrl: string) => void
}

export function ApplyForm({ profileId, onTaskCreated }: ApplyFormProps) {
  const [jobId, setJobId] = useState('')
  const [supervised, setSupervised] = useState(true)
  const [reviewMode, setReviewMode] = useState(false)
  const [useLlmLocator, setUseLlmLocator] = useState(false)
  const [debugResumeWidget, setDebugResumeWidget] = useState(false)
  const [llmProvider, setLlmProvider] = useState<string>('')
  const [llmModel, setLlmModel] = useState('')
  const [resumeWaitTimeout, setResumeWaitTimeout] = useState<number | ''>('')
  const [loading, setLoading] = useState(false)
  const { addToast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!profileId) {
      addToast({
        title: 'Error',
        description: 'Please select a profile first',
        variant: 'destructive',
      })
      return
    }

    setLoading(true)

    try {
      const request: ApplyRequest = {
        profile_id: profileId,
        supervised,
        review_mode: reviewMode,
        use_llm_locator: useLlmLocator,
        debug_resume_widget: debugResumeWidget,
      }

      // Add optional fields if provided
      if (jobId) {
        request.job_id = jobId
      }
      if (llmProvider) {
        request.llm_provider = llmProvider
      }
      if (llmModel) {
        request.llm_model = llmModel
      }
      if (resumeWaitTimeout !== '') {
        request.resume_wait_timeout_seconds = Number(resumeWaitTimeout)
      }

      const response = await applyApi.start(request)

      addToast({
        title: 'Apply Started',
        description: response.data.message,
      })

      // Notify parent component to show progress
      onTaskCreated(response.data.task_id, response.data.websocket_url)

      // Reset form
      setJobId('')
      setSupervised(true)
      setReviewMode(false)
      setUseLlmLocator(false)
      setDebugResumeWidget(false)
      setLlmProvider('')
      setLlmModel('')
      setResumeWaitTimeout('')
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error'
      addToast({
        title: 'Apply Failed',
        description: errorMessage,
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Apply to Jobs</CardTitle>
        <CardDescription>
          Configure and start applying to queued jobs from your profile
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Job ID */}
          <div className="space-y-2">
            <Label htmlFor="jobId">Job ID (Optional)</Label>
            <Input
              id="jobId"
              type="text"
              placeholder="Leave blank to apply to all queued jobs"
              value={jobId}
              onChange={(e) => setJobId(e.target.value)}
              disabled={loading}
            />
            <p className="text-xs text-gray-500">
              Specify a job ID to apply to only that job
            </p>
          </div>

          {/* Supervised Mode */}
          <div className="space-y-2">
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={supervised}
                onChange={(e) => setSupervised(e.target.checked)}
                disabled={loading}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm font-medium text-gray-700">
                Supervised Mode (pause before submitting)
              </span>
            </label>
            <p className="text-xs text-gray-500">
              When enabled, form will be filled but paused for review before submission
            </p>
          </div>

          {/* Review Mode */}
          <div className="space-y-2">
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={reviewMode}
                onChange={(e) => setReviewMode(e.target.checked)}
                disabled={loading}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm font-medium text-gray-700">
                Review Mode (capture only, no submit)
              </span>
            </label>
            <p className="text-xs text-gray-500">
              When enabled, forms will be analyzed but not submitted
            </p>
          </div>

          {/* LLM Provider */}
          <div className="space-y-2">
            <Label htmlFor="llmProvider">LLM Provider (Optional)</Label>
            <Select
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
              disabled={loading}
            >
              <option value="">Use default provider</option>
              <option value="openrouter">OpenRouter</option>
              <option value="google">Google</option>
            </Select>
          </div>

          {/* LLM Model */}
          <div className="space-y-2">
            <Label htmlFor="llmModel">LLM Model (Optional)</Label>
            <Input
              id="llmModel"
              type="text"
              placeholder="e.g., gpt-4-turbo, claude-3-opus-20240229"
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              disabled={loading}
            />
            <p className="text-xs text-gray-500">
              Leave blank to use default model for selected provider
            </p>
          </div>

          {/* Advanced Options */}
          <div className="space-y-3 rounded-lg bg-gray-50 p-4">
            <h3 className="text-sm font-semibold text-gray-900">Advanced Options</h3>

            {/* Use LLM Locator */}
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={useLlmLocator}
                onChange={(e) => setUseLlmLocator(e.target.checked)}
                disabled={loading}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">
                Use LLM-powered element finding
              </span>
            </label>

            {/* Debug Resume Widget */}
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={debugResumeWidget}
                onChange={(e) => setDebugResumeWidget(e.target.checked)}
                disabled={loading}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">
                Debug resume upload widget
              </span>
            </label>

            {/* Resume Wait Timeout */}
            <div className="space-y-2">
              <Label htmlFor="resumeWaitTimeout" className="text-sm">
                Resume Upload Timeout (seconds)
              </Label>
              <Input
                id="resumeWaitTimeout"
                type="number"
                min={5}
                max={120}
                placeholder="Default: 25"
                value={resumeWaitTimeout}
                onChange={(e) =>
                  setResumeWaitTimeout(e.target.value ? Number(e.target.value) : '')
                }
                disabled={loading}
              />
              <p className="text-xs text-gray-500">
                Maximum seconds to wait for resume upload to complete
              </p>
            </div>
          </div>

          <Button type="submit" disabled={loading || !profileId} className="w-full">
            {loading ? 'Starting Apply...' : 'Run Apply'}
          </Button>

          {!profileId && (
            <p className="text-sm text-red-600">Please select a profile to run apply</p>
          )}
        </form>
      </CardContent>
    </Card>
  )
}
