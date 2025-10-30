import React, { useState } from 'react'
import { cn } from '../lib/utils'
import { Button } from '@/components/ui/button'

interface RefreshButtonProps {
  onRefresh: () => Promise<void>
  isLoading?: boolean
  lastUpdated?: Date | null
}

export const RefreshButton: React.FC<RefreshButtonProps> = ({
  onRefresh,
  isLoading = false,
  lastUpdated,
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    if (isRefreshing) return

    setIsRefreshing(true)
    try {
      await onRefresh()
    } catch (error) {
      console.error('Failed to refresh:', error)
    } finally {
      setIsRefreshing(false)
    }
  }

  const formatLastUpdated = (date: Date): string => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSecs = Math.floor(diffMs / 1000)
    const diffMins = Math.floor(diffSecs / 60)
    const diffHours = Math.floor(diffMins / 60)

    if (diffSecs < 60) {
      return 'just now'
    } else if (diffMins < 60) {
      return `${diffMins}m ago`
    } else if (diffHours < 24) {
      return `${diffHours}h ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  return (
    <div className="flex items-center gap-3">
      <Button
        onClick={handleRefresh}
        disabled={isRefreshing || isLoading}
        isLoading={isRefreshing}
        size="sm"
        variant="outline"
        aria-label="Refresh job queue"
        title="Refresh job queue"
      >
        🔄 Refresh
      </Button>

      {lastUpdated && (
        <div
          className="text-xs text-gray-500"
          aria-live="polite"
          aria-label={`Last updated ${formatLastUpdated(lastUpdated)}`}
        >
          Updated {formatLastUpdated(lastUpdated)}
        </div>
      )}
    </div>
  )
}
