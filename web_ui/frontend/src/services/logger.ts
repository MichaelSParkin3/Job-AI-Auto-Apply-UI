/**
 * Frontend logging service with structured JSON logging.
 */

interface LogEvent {
  timestamp: string
  level: 'debug' | 'info' | 'warning' | 'error'
  message: string
  data?: Record<string, any>
  error?: {
    message: string
    stack?: string
  }
}

class Logger {
  private logsBuffer: LogEvent[] = []
  private maxBufferSize = 100

  private log(
    level: 'debug' | 'info' | 'warning' | 'error',
    message: string,
    data?: Record<string, any>,
    error?: Error
  ) {
    const event: LogEvent = {
      timestamp: new Date().toISOString(),
      level,
      message,
      data,
    }

    if (error) {
      event.error = {
        message: error.message,
        stack: error.stack,
      }
    }

    // Log to console
    const consoleMethod = level === 'debug' ? 'log' : level
    console[consoleMethod as keyof typeof console](
      JSON.stringify(event)
    )

    // Store in buffer
    this.logsBuffer.push(event)
    if (this.logsBuffer.length > this.maxBufferSize) {
      this.logsBuffer.shift()
    }

    // Optionally send to backend (commented out for now)
    // this.sendToBackend(event)
  }

  debug(message: string, data?: Record<string, any>) {
    this.log('debug', message, data)
  }

  info(message: string, data?: Record<string, any>) {
    this.log('info', message, data)
  }

  warning(message: string, data?: Record<string, any>) {
    this.log('warning', message, data)
  }

  error(message: string, error?: Error, data?: Record<string, any>) {
    this.log('error', message, data, error)
  }

  getLogs(): LogEvent[] {
    return [...this.logsBuffer]
  }

  clearLogs() {
    this.logsBuffer = []
  }

  private async sendToBackend(event: LogEvent) {
    try {
      await fetch('/api/v1/logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event),
      })
    } catch (err) {
      // Silently fail - don't create infinite loop
    }
  }
}

export const logger = new Logger()
