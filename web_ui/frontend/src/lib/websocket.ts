/**
 * WebSocket manager for real-time apply event streaming.
 * Handles connection, event subscriptions, and graceful disconnection.
 */

// Event types matching backend event models
export interface ReasonDetail {
  code: string
  message: string
}

export interface ApplyStartEvent {
  type: 'apply.start'
  profile_id: string
  timestamp?: string
}

export interface ItemStartEvent {
  type: 'item.start'
  item_id: string
  company?: string
  title?: string
}

export interface ItemSubmittedEvent {
  type: 'item.submitted'
  item_id: string
  confirmation_id?: string
  confirmation_text?: string
  screenshot_after_path?: string
}

export interface ItemSavedForReviewEvent {
  type: 'item.saved_for_review'
  item_id: string
  form_state_path?: string
  screenshot_before_path?: string
}

export interface ItemSkippedEvent {
  type: 'item.skipped'
  item_id: string
  reason?: ReasonDetail
}

export interface ItemCaptchaBlockedEvent {
  type: 'item.captcha_blocked'
  item_id: string
  reason?: ReasonDetail
  form_state_path?: string
  screenshot_before_path?: string
}

export interface ItemFailedEvent {
  type: 'item.failed'
  item_id: string
  reason: ReasonDetail
}

export interface ApplyEndEvent {
  type: 'apply.end'
  submitted: number
  failed: number
}

export interface ApplyErrorEvent {
  type: 'error'
  message: string
}

export type ApplyEvent =
  | ApplyStartEvent
  | ItemStartEvent
  | ItemSubmittedEvent
  | ItemSavedForReviewEvent
  | ItemSkippedEvent
  | ItemCaptchaBlockedEvent
  | ItemFailedEvent
  | ApplyEndEvent
  | ApplyErrorEvent

// Event subscription callbacks
export type EventCallback = (event: ApplyEvent) => void

/**
 * Manages WebSocket connection to /ws/apply/{task_id}
 * Provides event subscription interface for React components
 */
export class ApplyWebSocket {
  private ws: WebSocket | null = null
  private url: string
  private callbacks: Set<EventCallback> = new Set()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000 // ms
  private isIntentionallyClosed = false

  constructor(taskId: string) {
    // Determine WebSocket URL based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    this.url = `${protocol}//${host}/ws/apply/${taskId}`
  }

  /**
   * Connect to WebSocket and start receiving events
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('WebSocket connected:', this.url)
          this.reconnectAttempts = 0
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            this.emitEvent(data)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error, event.data)
            this.emitError(`Failed to parse message: ${error instanceof Error ? error.message : String(error)}`)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.emitError('WebSocket connection error')
          reject(error)
        }

        this.ws.onclose = () => {
          console.log('WebSocket closed')
          if (!this.isIntentionallyClosed) {
            this.attemptReconnect()
          }
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * Subscribe to events
   * @param callback Function to call when event is received
   * @returns Unsubscribe function
   */
  subscribe(callback: EventCallback): () => void {
    this.callbacks.add(callback)

    // Return unsubscribe function
    return () => {
      this.callbacks.delete(callback)
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.isIntentionallyClosed = true
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  /**
   * Emit event to all subscribers
   */
  private emitEvent(event: ApplyEvent): void {
    console.log('Event:', event.type, event)
    this.callbacks.forEach((callback) => {
      try {
        callback(event)
      } catch (error) {
        console.error('Error in event callback:', error)
      }
    })
  }

  /**
   * Emit error event
   */
  private emitError(message: string): void {
    const errorEvent: ApplyErrorEvent = {
      type: 'error',
      message,
    }
    this.emitEvent(errorEvent)
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`)

      setTimeout(() => {
        this.connect().catch((error) => {
          console.error('Reconnect failed:', error)
        })
      }, delay)
    } else {
      this.emitError('Max reconnection attempts reached')
    }
  }
}

/**
 * Hook-friendly WebSocket wrapper for React
 * Usage: const ws = useApplyWebSocket(taskId)
 */
export function createApplyWebSocket(taskId: string): ApplyWebSocket {
  return new ApplyWebSocket(taskId)
}
