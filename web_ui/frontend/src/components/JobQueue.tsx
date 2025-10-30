import React, { useMemo, useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueue } from '../hooks/useQueue'
import {
  ApplicationItem,
  ApplicationStatus,
} from '../types/index'
import { cn } from '../lib/utils'
import { LoadingSpinner } from './LoadingSpinner'
import { ErrorMessage } from './ErrorMessage'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface JobQueueProps {
  profileId: string
  itemsPerPage?: number
}

type SortField = 'title' | 'company' | 'date' | 'status'
type SortDirection = 'asc' | 'desc'

export const JobQueue: React.FC<JobQueueProps> = ({
  profileId,
  itemsPerPage = 50,
}) => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
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

  // Load from URL parameters
  const [
    selectedStatus,
    setSelectedStatus,
  ] = useState<ApplicationStatus | 'ALL'>(
    (searchParams.get('status') as ApplicationStatus | 'ALL') || 'ALL'
  )
  const [searchQuery, setSearchQuery] = useState(
    searchParams.get('search') || ''
  )
  const [currentPage, setCurrentPage] = useState(
    parseInt(searchParams.get('page') || '1')
  )
  const [sortField, setSortField] = useState<SortField>(
    (searchParams.get('sort') as SortField) || 'date'
  )
  const [sortDirection, setSortDirection] = useState<SortDirection>(
    (searchParams.get('order') as SortDirection) || 'desc'
  )

  // Update URL when parameters change
  useEffect(() => {
    const params = new URLSearchParams()
    if (selectedStatus !== 'ALL') {
      params.set('status', selectedStatus)
    }
    if (searchQuery) {
      params.set('search', searchQuery)
    }
    if (currentPage > 1) {
      params.set('page', currentPage.toString())
    }
    if (sortField !== 'date') {
      params.set('sort', sortField)
    }
    if (sortDirection !== 'desc') {
      params.set('order', sortDirection)
    }
    setSearchParams(params, { replace: true })
  }, [selectedStatus, searchQuery, currentPage, sortField, sortDirection, setSearchParams])

  // Sort function
  const getSortValue = (item: ApplicationItem, field: SortField): any => {
    switch (field) {
      case 'title':
        return item.title.toLowerCase()
      case 'company':
        return item.company.toLowerCase()
      case 'date':
        return new Date(item.date_discovered || 0).getTime()
      case 'status':
        return item.status
      default:
        return null
    }
  }

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

    // Sort
    result = [...result].sort((a, b) => {
      const aVal = getSortValue(a, sortField)
      const bVal = getSortValue(b, sortField)

      if (aVal === null || bVal === null) return 0

      let comparison = 0
      if (aVal < bVal) {
        comparison = -1
      } else if (aVal > bVal) {
        comparison = 1
      }

      return sortDirection === 'asc' ? comparison : -comparison
    })

    return result
  }, [items, selectedStatus, searchQuery, sortField, sortDirection, filterByStatus])

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
      <Tabs
        value={selectedStatus}
        onValueChange={(value) => {
          setSelectedStatus(value as ApplicationStatus | 'ALL')
          setCurrentPage(1)
        }}
      >
        <TabsList className="grid w-full grid-cols-6">
          {statusTabs.map((tab) => (
            <TabsTrigger key={tab.status} value={tab.status}>
              {tab.label}{' '}
              <Badge variant="outline" className="ml-2">
                {tab.count}
              </Badge>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* Search Bar */}
      <Input
        type="text"
        placeholder="Search by job title or company..."
        value={searchQuery}
        onChange={(e) => {
          setSearchQuery(e.target.value)
          setCurrentPage(1)
        }}
        aria-label="Search jobs"
      />

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
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead
                  className="cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => {
                    if (sortField === 'title') {
                      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                    } else {
                      setSortField('title')
                      setSortDirection('asc')
                    }
                    setCurrentPage(1)
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      if (sortField === 'title') {
                        setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                      } else {
                        setSortField('title')
                        setSortDirection('asc')
                      }
                      setCurrentPage(1)
                    }
                  }}
                  aria-label="Sort by job title"
                >
                  Job Title {sortField === 'title' && (sortDirection === 'asc' ? '↑' : '↓')}
                </TableHead>
                <TableHead
                  className="cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => {
                    if (sortField === 'company') {
                      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                    } else {
                      setSortField('company')
                      setSortDirection('asc')
                    }
                    setCurrentPage(1)
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      if (sortField === 'company') {
                        setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                      } else {
                        setSortField('company')
                        setSortDirection('asc')
                      }
                      setCurrentPage(1)
                    }
                  }}
                  aria-label="Sort by company"
                >
                  Company {sortField === 'company' && (sortDirection === 'asc' ? '↑' : '↓')}
                </TableHead>
                <TableHead
                  className="cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => {
                    if (sortField === 'status') {
                      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                    } else {
                      setSortField('status')
                      setSortDirection('asc')
                    }
                    setCurrentPage(1)
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      if (sortField === 'status') {
                        setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                      } else {
                        setSortField('status')
                        setSortDirection('asc')
                      }
                      setCurrentPage(1)
                    }
                  }}
                  aria-label="Sort by status"
                >
                  Status {sortField === 'status' && (sortDirection === 'asc' ? '↑' : '↓')}
                </TableHead>
                <TableHead
                  className="cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => {
                    if (sortField === 'date') {
                      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                    } else {
                      setSortField('date')
                      setSortDirection('desc')
                    }
                    setCurrentPage(1)
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      if (sortField === 'date') {
                        setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
                      } else {
                        setSortField('date')
                        setSortDirection('desc')
                      }
                      setCurrentPage(1)
                    }
                  }}
                  aria-label="Sort by discovery date"
                >
                  Discovered {sortField === 'date' && (sortDirection === 'asc' ? '↑' : '↓')}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedItems.map(
                (item: ApplicationItem) => (
                  <TableRow
                    key={item.id}
                    className="hover:bg-gray-50 cursor-pointer"
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
                    <TableCell>
                      <div className="font-medium text-blue-600 hover:underline">
                        {item.title}
                      </div>
                    </TableCell>
                    <TableCell className="text-gray-700">
                      {item.company}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={item.status === 'SUBMITTED' ? 'default' : 'secondary'}
                        className={cn(
                          'text-xs',
                          item.status === 'NEW' &&
                            'bg-blue-100 text-blue-800',
                          item.status === 'IN_PROGRESS' &&
                            'bg-yellow-100 text-yellow-800',
                          item.status === 'SUBMITTED' &&
                            'bg-green-600 text-white',
                          item.status === 'FAILED' &&
                            'bg-red-100 text-red-800',
                          item.status === 'CAPTCHA_BLOCKED' &&
                            'bg-orange-100 text-orange-800'
                        )}
                      >
                        {item.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-gray-600 text-sm">
                      {item.date_discovered
                        ? new Date(
                            item.date_discovered
                          ).toLocaleDateString()
                        : '—'}
                    </TableCell>
                  </TableRow>
                )
              )}
            </TableBody>
          </Table>

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
                  <Input
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
                    className="w-12 h-9"
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
