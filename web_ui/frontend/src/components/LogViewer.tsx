import React, { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '../lib/utils'

export interface LogEntry {
  timestamp: string
  level: 'debug' | 'info' | 'warning' | 'error'
  message: string
}

interface LogViewerProps {
  logs: LogEntry[]
  isLive?: boolean
  onClear?: () => void
}

const getLevelColor = (
  level: LogEntry['level']
): string => {
  const colors: Record<LogEntry['level'], string> = {
    debug: 'text-gray-500',
    info: 'text-blue-600',
    warning: 'text-yellow-600',
    error: 'text-red-600',
  }
  return colors[level]
}

const getLevelBg = (
  level: LogEntry['level']
): string => {
  const colors: Record<LogEntry['level'], string> = {
    debug: 'bg-gray-50',
    info: 'bg-blue-50',
    warning: 'bg-yellow-50',
    error: 'bg-red-50',
  }
  return colors[level]
}

export const LogViewer: React.FC<LogViewerProps> = ({
  logs,
  isLive = false,
  onClear,
}) => {
  const [filter, setFilter] = useState<
    'all' | LogEntry['level']
  >('all')
  const [searchQuery, setSearchQuery] = useState('')
  const scrollEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (isLive && scrollEndRef.current) {
      scrollEndRef.current.scrollIntoView({
        behavior: 'smooth',
      })
    }
  }, [logs, isLive])

  const filteredLogs = logs.filter((log) => {
    const levelMatch =
      filter === 'all' || log.level === filter
    const searchMatch =
      log.message
        .toLowerCase()
        .includes(searchQuery.toLowerCase()) ||
      log.timestamp
        .toLowerCase()
        .includes(searchQuery.toLowerCase())
    return levelMatch && searchMatch
  })

  const levelCounts = {
    debug: logs.filter((l) => l.level === 'debug').length,
    info: logs.filter((l) => l.level === 'info').length,
    warning: logs.filter((l) => l.level === 'warning')
      .length,
    error: logs.filter((l) => l.level === 'error').length,
  }

  const handleCopy = () => {
    const text = filteredLogs
      .map(
        (log) =>
          `[${log.timestamp}] [${log.level.toUpperCase()}] ${log.message}`
      )
      .join('\n')
    navigator.clipboard.writeText(text)
    alert('Logs copied to clipboard!')
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">
          {isLive ? '🔴 Live Logs' : 'Application Logs'}
        </h2>
        <div className="flex gap-2">
          {onClear && (
            <Button
              size="sm"
              variant="outline"
              onClick={onClear}
            >
              Clear
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopy}
          >
            Copy
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Level Filters */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilter('all')}
            className={cn(
              'px-3 py-1 rounded text-sm font-medium transition-colors',
              filter === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
            )}
          >
            All ({logs.length})
          </button>
          <button
            onClick={() => setFilter('info')}
            className={cn(
              'px-3 py-1 rounded text-sm font-medium transition-colors',
              filter === 'info'
                ? 'bg-blue-600 text-white'
                : 'bg-blue-100 text-blue-800 hover:bg-blue-200'
            )}
          >
            ℹ️ Info ({levelCounts.info})
          </button>
          <button
            onClick={() => setFilter('warning')}
            className={cn(
              'px-3 py-1 rounded text-sm font-medium transition-colors',
              filter === 'warning'
                ? 'bg-yellow-600 text-white'
                : 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
            )}
          >
            ⚠️ Warning ({levelCounts.warning})
          </button>
          <button
            onClick={() => setFilter('error')}
            className={cn(
              'px-3 py-1 rounded text-sm font-medium transition-colors',
              filter === 'error'
                ? 'bg-red-600 text-white'
                : 'bg-red-100 text-red-800 hover:bg-red-200'
            )}
          >
            ❌ Error ({levelCounts.error})
          </button>
        </div>

        {/* Search Input */}
        <input
          type="text"
          placeholder="Search logs..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={cn(
            'flex-1 px-3 py-2 rounded border border-gray-300',
            'focus:outline-none focus:ring-2 focus:ring-blue-500',
            'text-sm'
          )}
        />
      </div>

      {/* Log Container */}
      <div
        ref={containerRef}
        className="bg-gray-900 rounded font-mono text-sm max-h-96 overflow-y-auto space-y-0"
        role="log"
        aria-live={isLive ? 'polite' : 'off'}
      >
        {filteredLogs.length === 0 ? (
          <div className="text-gray-500 p-4 text-center">
            No logs to display
          </div>
        ) : (
          filteredLogs.map((log, index) => (
            <div
              key={index}
              className={cn(
                'px-4 py-2 border-b border-gray-800 hover:bg-gray-800 transition-colors',
                getLevelBg(log.level)
              )}
            >
              <span className="text-gray-400">
                [{log.timestamp}]
              </span>
              <span
                className={cn(
                  'ml-2 font-bold',
                  getLevelColor(log.level)
                )}
              >
                [{log.level.toUpperCase()}]
              </span>
              <span className="ml-2 text-gray-100">
                {log.message}
              </span>
            </div>
          ))
        )}
        <div ref={scrollEndRef} />
      </div>

      {/* Info */}
      <div className="text-xs text-gray-500 text-right">
        Showing {filteredLogs.length} of {logs.length} logs
      </div>
    </div>
  )
}
