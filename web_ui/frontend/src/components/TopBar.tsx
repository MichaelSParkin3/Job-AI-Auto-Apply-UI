import React, { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { cn } from '../lib/utils'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/discover': 'Discover Jobs',
  '/profiles': 'Profiles',
  '/settings': 'Settings',
  '/artifacts': 'Artifacts',
}

export const TopBar: React.FC = () => {
  const location = useLocation()
  const [lastUpdated, setLastUpdated] = useState<
    Date | null
  >(null)

  useEffect(() => {
    // Update timestamp when component mounts
    setLastUpdated(new Date())
  }, [location.pathname])

  const pageTitle =
    PAGE_TITLES[location.pathname] || 'Page'

  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    })
  }

  return (
    <header
      className={cn(
        'flex items-center justify-between',
        'bg-white border-b border-gray-200',
        'px-8 py-4 sticky top-0 z-40'
      )}
    >
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          {pageTitle}
        </h2>
        {lastUpdated && (
          <p className="text-sm text-gray-500 mt-1">
            Last updated:{' '}
            {formatTime(lastUpdated)}
          </p>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Placeholder for future action buttons */}
        <div
          className="text-sm text-gray-600"
          aria-label="Page information"
        >
          {/* Can be extended with user menu, notifications, etc. */}
        </div>
      </div>
    </header>
  )
}
