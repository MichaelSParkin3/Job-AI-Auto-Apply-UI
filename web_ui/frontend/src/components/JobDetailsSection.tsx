import React from 'react'
import { JobDetails } from '../types/index'
import { cn } from '../lib/utils'

interface JobDetailsSectionProps {
  details: JobDetails | undefined
}

const DetailItem: React.FC<{
  label: string
  value: string | undefined
  icon?: string
}> = ({ label, value, icon }) => {
  const displayValue = value || 'Not available'
  const isEmpty = !value

  return (
    <div className="py-4 border-b last:border-b-0">
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
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-900">
        Job Details
      </h2>

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
            <div className="py-4 border-b">
              <dt className="text-sm font-medium text-gray-900 mb-2">
                🔧 Technologies
              </dt>
              <dd className="flex flex-wrap gap-2">
                {details.tech_tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium"
                  >
                    {tag}
                  </span>
                ))}
              </dd>
            </div>
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
        />
      </dl>
    </div>
  )
}
