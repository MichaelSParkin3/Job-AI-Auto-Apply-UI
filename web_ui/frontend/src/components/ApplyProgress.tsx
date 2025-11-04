import { useEffect, useRef, useState } from 'react'
import { ApplyWebSocket, type ApplyEvent, type ActionPromptEvent } from '@/lib/websocket'
import { useToast } from '@/lib/toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PromptModal } from './PromptModal'

interface ApplyProgressProps {
  taskId: string
  websocketUrl: string
  onClose: () => void
}

interface EventLog {
  timestamp: string
  type: string
  data: ApplyEvent
}

interface PendingPrompt {
  promptId: string
  message: string
  options: Array<{ action: string; label: string; key?: string }>
  context?: { item_id?: string; company?: string; title?: string; screenshot_path?: string }
}

export function ApplyProgress({ taskId, websocketUrl, onClose }: ApplyProgressProps) {
  const [events, setEvents] = useState<EventLog[]>([])
  const [connected, setConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(0)
  const [failed, setFailed] = useState(0)
  const [total, setTotal] = useState(0)
  const [completed, setCompleted] = useState(false)
  const [pendingPrompt, setPendingPrompt] = useState<PendingPrompt | null>(null)
  const [promptLoading, setPromptLoading] = useState(false)
  const wsRef = useRef<ApplyWebSocket | null>(null)
  const eventsEndRef = useRef<HTMLDivElement>(null)
  const { addToast } = useToast()

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  useEffect(() => {
    let isActive = true
    const ws = new ApplyWebSocket(taskId)
    wsRef.current = ws

    const unsubscribe = ws.subscribe((event: ApplyEvent) => {
      // Skip state updates if component unmounted during React StrictMode cleanup
      if (!isActive) return

      const timestamp = new Date().toLocaleTimeString()

      // Handle action prompts specially (don't add to log, show modal instead)
      if (event.type === 'prompt.action_required') {
        const promptEvent = event as ActionPromptEvent
        setPendingPrompt({
          promptId: promptEvent.prompt_id,
          message: promptEvent.message,
          options: promptEvent.options,
          context: promptEvent.context,
        })
        addToast({
          title: 'Action Required',
          description: promptEvent.message,
        })
        return // Don't add prompt event to log
      }

      setEvents((prev) => [...prev, { timestamp, type: event.type, data: event }])

      // Update counters based on event type
      if (event.type === 'item.start') {
        setTotal((prev) => prev + 1)
      } else if (event.type === 'item.submitted') {
        setSubmitted((prev) => prev + 1)
      } else if (event.type === 'item.failed' || event.type === 'item.captcha_blocked') {
        setFailed((prev) => prev + 1)
      } else if (event.type === 'apply.end') {
        setCompleted(true)
        // Disconnect WebSocket to prevent reconnection attempts on normal completion
        wsRef.current?.disconnect()
        addToast({
          title: 'Apply Complete',
          description: `Submitted: ${event.submitted}, Failed: ${event.failed}`,
        })
      } else if (event.type === 'error') {
        setConnectionError(event.message)
        addToast({
          title: 'Apply Error',
          description: event.message,
          variant: 'destructive',
        })
      }
    })

    // Connect to WebSocket
    ws.connect()
      .then(() => {
        // Only update state if component is still active
        if (isActive) {
          setConnected(true)
          setConnectionError(null)
        } else {
          // Component unmounted during connection, disconnect
          ws.disconnect()
        }
      })
      .catch((error) => {
        // Only update state if component is still active
        if (!isActive) return

        const errorMsg = error instanceof Error ? error.message : String(error)
        setConnectionError(errorMsg)
        addToast({
          title: 'Connection Failed',
          description: errorMsg,
          variant: 'destructive',
        })
      })

    // Cleanup function - runs on unmount or when dependencies change
    return () => {
      isActive = false
      unsubscribe()
      ws.disconnect()
    }
  }, [taskId])

  const getEventBadgeColor = (type: string) => {
    if (type === 'item.submitted') return 'bg-green-100 text-green-800'
    if (type === 'item.failed') return 'bg-red-100 text-red-800'
    if (type === 'item.captcha_blocked') return 'bg-yellow-100 text-yellow-800'
    if (type === 'item.saved_for_review') return 'bg-blue-100 text-blue-800'
    if (type === 'item.skipped') return 'bg-gray-100 text-gray-800'
    if (type === 'apply.end') return 'bg-purple-100 text-purple-800'
    if (type === 'error') return 'bg-red-100 text-red-800'
    return 'bg-gray-100 text-gray-800'
  }

  const getEventLabel = (type: string) => {
    return type
      .replace(/\./g, ' ')
      .split(' ')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const getEventSummary = (event: ApplyEvent): string => {
    switch (event.type) {
      case 'item.start':
        return event.company ? `Starting apply to ${event.company}` : 'Processing job'
      case 'item.submitted':
        return 'Successfully submitted'
      case 'item.failed':
        return `Failed: ${event.reason?.message || 'Unknown error'}`
      case 'item.captcha_blocked':
        return `CAPTCHA detected: ${event.reason?.message || 'Manual intervention needed'}`
      case 'item.saved_for_review':
        return 'Saved for review'
      case 'item.skipped':
        return `Skipped: ${event.reason?.message || 'User action'}`
      case 'apply.end':
        return `Completed: ${event.submitted} submitted, ${event.failed} failed`
      case 'error':
        return event.message || 'Unknown error'
      default:
        return 'Event occurred'
    }
  }

  const handlePromptResponse = (action: string) => {
    if (!pendingPrompt || !wsRef.current) return

    setPromptLoading(true)
    try {
      wsRef.current.sendResponse(pendingPrompt.promptId, action)
      addToast({
        title: 'Response Sent',
        description: `Action: ${action}`,
      })
      setPendingPrompt(null)
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error)
      addToast({
        title: 'Failed to Send Response',
        description: errorMsg,
        variant: 'destructive',
      })
    } finally {
      setPromptLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle>Apply Progress</CardTitle>
            <CardDescription>
              Real-time updates for task {taskId.slice(0, 8)}...
            </CardDescription>
          </div>
          {completed && (
            <Button onClick={onClose} variant="outline" size="sm">
              Close
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Connection Status */}
        <div className="flex items-center gap-2 text-sm">
          <div
            className={`h-3 w-3 rounded-full ${
              connected ? 'bg-green-500' : connectionError ? 'bg-red-500' : 'bg-yellow-500'
            }`}
          />
          <span className="text-gray-700">
            {connectionError
              ? `Error: ${connectionError}`
              : connected
                ? 'Connected'
                : 'Connecting...'}
          </span>
        </div>

        {/* Progress Summary */}
        <div className="grid grid-cols-4 gap-4">
          <div className="rounded-lg bg-gray-50 p-4 text-center">
            <div className="text-2xl font-bold text-gray-900">{total}</div>
            <div className="text-sm text-gray-600">Total</div>
          </div>
          <div className="rounded-lg bg-green-50 p-4 text-center">
            <div className="text-2xl font-bold text-green-600">{submitted}</div>
            <div className="text-sm text-green-700">Submitted</div>
          </div>
          <div className="rounded-lg bg-red-50 p-4 text-center">
            <div className="text-2xl font-bold text-red-600">{failed}</div>
            <div className="text-sm text-red-700">Failed</div>
          </div>
          <div className="rounded-lg bg-blue-50 p-4 text-center">
            <div className="text-2xl font-bold text-blue-600">{total > 0 ? Math.round((submitted / total) * 100) : 0}%</div>
            <div className="text-sm text-blue-700">Success Rate</div>
          </div>
        </div>

        {/* Progress Bar */}
        {total > 0 && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium text-gray-700">Progress</span>
              <span className="text-gray-600">
                {submitted + failed} of {total}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${total > 0 ? ((submitted + failed) / total) * 100 : 0}%` }}
              />
            </div>
          </div>
        )}

        {/* Event Log */}
        <div className="space-y-2">
          <h3 className="font-semibold text-gray-900">Event Log</h3>
          <div className="max-h-96 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50">
            {events.length === 0 ? (
              <div className="p-4 text-center text-gray-500">Waiting for events...</div>
            ) : (
              <div className="divide-y divide-gray-200">
                {events.map((log, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 border-l-4 border-l-gray-300 p-3 hover:bg-white"
                  >
                    <div className="pt-0.5">
                      <span
                        className={`inline-block rounded px-2 py-1 text-xs font-semibold ${getEventBadgeColor(
                          log.type
                        )}`}
                      >
                        {getEventLabel(log.type)}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900 break-words">
                        {getEventSummary(log.data)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">{log.timestamp}</p>
                    </div>
                  </div>
                ))}
                <div ref={eventsEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Completion Message */}
        {completed && (
          <div className="rounded-lg bg-green-50 p-4 text-center">
            <p className="font-semibold text-green-900">Apply session completed!</p>
            <p className="text-sm text-green-700 mt-1">
              {submitted} submitted, {failed} failed out of {total} jobs
            </p>
          </div>
        )}
      </CardContent>

      {/* Action Prompt Modal */}
      {pendingPrompt && (
        <PromptModal
          isOpen={true}
          promptId={pendingPrompt.promptId}
          message={pendingPrompt.message}
          options={pendingPrompt.options}
          context={pendingPrompt.context}
          onRespond={handlePromptResponse}
          isLoading={promptLoading}
        />
      )}
    </Card>
  )
}
