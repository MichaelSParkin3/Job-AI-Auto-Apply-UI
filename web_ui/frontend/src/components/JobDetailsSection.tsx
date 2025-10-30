import React from 'react'
import { JobDetails } from '../types/index'
import { cn } from '../lib/utils'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'

interface JobDetailsSectionProps {
  details: JobDetails | undefined
}

const DetailItem: React.FC<{
  label: string
  value?: React.ReactNode
  icon?: string
  showSeparator?: boolean
}> = ({ label, value, icon, showSeparator = true }) => {
  const displayValue = value || 'Not available'
  const isEmpty = !value

  return (
    <>
      <div className="py-4">
        <dt
          className={cn(
            'text-sm font-medium mb-1',
            isEmpty
              ? 'text-gray-500'
              : 'text-gray-900'
          )}
        >
          {icon && <span className="mr-2">{icon}</span>}
          {label}
        </dt>
        <dd
          className={cn(
            'text-base',
            isEmpty
              ? 'text-gray-400 italic'
              : 'text-gray-700'
          )}
        >
          {displayValue}
        </dd>
      </div>
      {showSeparator && <Separator />}
    </>
  )
}

export const JobDetailsSection: React.FC<
  JobDetailsSectionProps
> = ({ details }) => {
  if (!details) {
    return (
      <div className="text-center py-8 text-gray-500">
        No job details available
      </div>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">
          Job Details
        </CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="space-y-0">
          <DetailItem
            label="Location"
            value={details.location}
            icon="📍"
          />

          <DetailItem
            label="Work Model"
            value={details.work_model}
            icon="💼"
          />

          <DetailItem
            label="Employment Type"
            value={details.employment_type}
            icon="📋"
          />

          <DetailItem
            label="Department"
            value={details.department}
            icon="🏢"
          />

          <DetailItem
            label="Compensation"
            value={details.compensation}
            icon="💰"
          />

          <DetailItem
            label="Posted On"
            value={
              details.posting_date
                ? new Date(details.posting_date).toLocaleDateString()
                : undefined
            }
            icon="📅"
          />

          {details.tech_tags &&
            details.tech_tags.length > 0 && (
              <>
                <div className="py-4">
                  <dt className="text-sm font-medium text-gray-900 mb-3">
                    🔧 Technologies
                  </dt>
                  <dd className="flex flex-wrap gap-2">
                    {details.tech_tags.map((tag) => (
                      <Badge
                        key={tag}
                        variant="secondary"
                        className="bg-blue-100 text-blue-800"
                      >
                        {tag}
                      </Badge>
                    ))}
                  </dd>
                </div>
                <Separator />
              </>
            )}

          <DetailItem
            label="Apply URL"
            value={
              details.apply_url ? (
                <a
                  href={details.apply_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline break-all"
                >
                  Open Job Post
                </a>
              ) : undefined
            }
            icon="🔗"
            showSeparator={false}
          />
        </dl>
      </CardContent>
    </Card>
  )
}
