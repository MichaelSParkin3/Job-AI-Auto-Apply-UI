import React, { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueue } from '../hooks/useQueue'
import {
  ApplicationItem,
  ApplicationStatus,
} from '../types/index'
import { cn } from '../lib/utils'
import { LoadingSpinner } from './LoadingSpinner'
import { ErrorMessage } from './ErrorMessage'
import { Button } from './Button'

interface JobQueueProps {
  profileId: string
  itemsPerPage?: number
}

export const JobQueue: React.FC<JobQueueProps> = ({
  profileId,
  itemsPerPage = 50,
}) => {
  const navigate = useNavigate()
  const {
    items,
    counts,
    isLoading,
    error,
    lastUpdated,
    refresh,
    filterByStatus,
    searchItems,
  } = useQueue(profileId)

  const [
    selectedStatus,
    setSelectedStatus,
  ] = useState<ApplicationStatus | 'ALL'>('ALL')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)

  // Filter and search
  const filteredItems = useMemo(() => {
    let result = items

    // Filter by status
    if (selectedStatus !== 'ALL') {
      result = filterByStatus(selectedStatus)
    }

    // Search
    if (searchQuery) {
      result = result.filter(
        (item) =>
          item.title
            .toLowerCase()
            .includes(searchQuery.toLowerCase()) ||
          item.company
            .toLowerCase()
            .includes(searchQuery.toLowerCase())
      )
    }

    return result
  }, [items, selectedStatus, searchQuery, filterByStatus])

  // Pagination
  const totalPages = Math.ceil(
    filteredItems.length / itemsPerPage
  )
  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage
    return filteredItems.slice(
      start,
      start + itemsPerPage
    )
  }, [filteredItems, currentPage, itemsPerPage])

  const getStatusColor = (
    status: ApplicationStatus
  ): string => {
    const colors: Record<ApplicationStatus, string> = {
      NEW: 'bg-blue-100 text-blue-800',
      IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
      SUBMITTED: 'bg-green-100 text-green-800',
      FAILED: 'bg-red-100 text-red-800',
      CAPTCHA_BLOCKED: 'bg-orange-100 text-orange-800',
    }
    return colors[status]
  }

  const statusTabs: Array<{
    label: string
    status: ApplicationStatus | 'ALL'
    count: number
  }> = [
    { label: 'All', status: 'ALL', count: items.length },
    { label: 'Waiting', status: 'NEW', count: counts.NEW },
    {
      label: 'In Progress',
      status: 'IN_PROGRESS',
      count: counts.IN_PROGRESS,
    },
    {
      label: 'Submitted',
      status: 'SUBMITTED',
      count: counts.SUBMITTED,
    },
    { label: 'Failed', status: 'FAILED', count: counts.FAILED },
    {
      label: 'Blocked',
      status: 'CAPTCHA_BLOCKED',
      count: counts.CAPTCHA_BLOCKED,
    },
  ]

  if (isLoading) {
    return <LoadingSpinner message="Loading queue..." />
  }

  if (error) {
    return (
      <ErrorMessage
        error={error}
        onRetry={refresh}
        dismissible={true}
      />
    )
  }

  return (
    <div className="space-y-4">
      {/* Status Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {statusTabs.map((tab) => (
          <button
            key={tab.status}
            onClick={() => {
              setSelectedStatus(tab.status)
              setCurrentPage(1)
            }}
            className={cn(
              'px-4 py-2 rounded-lg font-medium',
              'whitespace-nowrap transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-blue-500',
              selectedStatus === tab.status
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
            )}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      {/* Search Bar */}
      <div>
        <input
          type="text"
          placeholder="Search by job title or company..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value)
            setCurrentPage(1)
          }}
          className={cn(
            'w-full px-4 py-2 rounded-lg',
            'border border-gray-300',
            'focus:outline-none focus:ring-2 focus:ring-blue-500'
          )}
          aria-label="Search jobs"
        />
      </div>

      {/* Job List */}
      {paginatedItems.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 bg-gray-50 rounded-lg">
          <div className="text-4xl mb-2">📭</div>
          <p className="text-gray-600">
            No jobs found
          </p>
          <p className="text-sm text-gray-500">
            {selectedStatus !== 'ALL' ||
            searchQuery
              ? 'Try adjusting your filters'
              : 'Discover new jobs to get started'}
          </p>
        </div>
      ) : (
        <>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-100 border-b">
                <tr>
                  <th className="px-4 py-2 text-left font-semibold">
                    Job Title
                  </th>
                  <th className="px-4 py-2 text-left font-semibold">
                    Company
                  </th>
                  <th className="px-4 py-2 text-left font-semibold">
                    Status
                  </th>
                  <th className="px-4 py-2 text-left font-semibold">
                    Discovered
                  </th>
                </tr>
              </thead>
              <tbody>
                {paginatedItems.map(
                  (item: ApplicationItem) => (
                    <tr
                      key={item.id}
                      className="border-b hover:bg-gray-50 cursor-pointer"
                      onClick={() =>
                        navigate(`/job/${item.id}`)
                      }
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (
                          e.key === 'Enter' ||
                          e.key === ' '
                        ) {
                          navigate(
                            `/job/${item.id}`
                          )
                        }
                      }}
                    >
                      <td className="px-4 py-3">
                        <div className="font-medium text-blue-600 hover:underline">
                          {item.title}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {item.company}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            'px-2 py-1 rounded text-xs font-semibold',
                            getStatusColor(
                              item.status
                            )
                          )}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-sm">
                        {item.date_discovered
                          ? new Date(
                              item.date_discovered
                            ).toLocaleDateString()
                          : '—'}
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between py-4">
              <div className="text-sm text-gray-600">
                Showing {(currentPage - 1) *
                  itemsPerPage +
                  1} to{' '}
                {Math.min(
                  currentPage * itemsPerPage,
                  filteredItems.length
                )}{' '}
                of {filteredItems.length} jobs
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setCurrentPage(
                      Math.max(1, currentPage - 1)
                    )
                  }
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <span className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">
                    Page
                  </span>
                  <input
                    type="number"
                    min="1"
                    max={totalPages}
                    value={currentPage}
                    onChange={(e) =>
                      setCurrentPage(
                        Math.max(
                          1,
                          Math.min(
                            totalPages,
                            parseInt(
                              e.target.value
                            ) || 1
                          )
                        )
                      )
                    }
                    className={cn(
                      'w-12 px-2 py-1 rounded',
                      'border border-gray-300',
                      'focus:outline-none focus:ring-2 focus:ring-blue-500'
                    )}
                    aria-label="Page number"
                  />
                  <span className="text-sm text-gray-600">
                    of {totalPages}
                  </span>
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setCurrentPage(
                      Math.min(
                        totalPages,
                        currentPage + 1
                      )
                    )
                  }
                  disabled={
                    currentPage === totalPages
                  }
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Last Updated */}
      {lastUpdated && (
        <div className="text-xs text-gray-500 text-right">
          Last updated:{' '}
          {lastUpdated.toLocaleTimeString()}
        </div>
      )}
    </div>
  )
}
