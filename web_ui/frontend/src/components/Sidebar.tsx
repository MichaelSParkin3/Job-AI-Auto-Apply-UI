import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useProfile } from '../hooks/useProfile'
import { useQueue } from '../hooks/useQueue'
import { cn } from '../lib/utils'
import { Button } from '@/components/ui/button'

interface NavItem {
  path: string
  label: string
  icon: string
}

const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/discover', label: 'Discover Jobs', icon: '🔍' },
  { path: '/profiles', label: 'Profiles', icon: '👤' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
  { path: '/artifacts', label: 'Artifacts', icon: '📦' },
]

export const Sidebar: React.FC = () => {
  const location = useLocation()
  const {
    profiles,
    activeProfile,
    isLoading: profilesLoading,
    switchProfile,
  } = useProfile()
  const { counts, isLoading: queueLoading } = useQueue(
    activeProfile || ''
  )
  const [isDropdownOpen, setIsDropdownOpen] =
    useState(false)

  const activeProfileData = profiles.find(
    (p) => p.id === activeProfile
  )

  const handleSwitchProfile = async (
    profileId: string
  ) => {
    try {
      await switchProfile(profileId)
      setIsDropdownOpen(false)
    } catch (err) {
      console.error('Failed to switch profile:', err)
    }
  }

  const getStatusColor = (
    status:
      | 'NEW'
      | 'IN_PROGRESS'
      | 'SUBMITTED'
      | 'FAILED'
      | 'CAPTCHA_BLOCKED'
  ): string => {
    const colors: Record<string, string> = {
      NEW: 'bg-blue-100 text-blue-800',
      IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
      SUBMITTED: 'bg-green-100 text-green-800',
      FAILED: 'bg-red-100 text-red-800',
      CAPTCHA_BLOCKED: 'bg-orange-100 text-orange-800',
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  const statusBadges = [
    {
      label: 'Jobs Waiting',
      count: counts.NEW,
      status: 'NEW' as const,
    },
    {
      label: 'In Progress',
      count: counts.IN_PROGRESS,
      status: 'IN_PROGRESS' as const,
    },
    {
      label: 'Submitted',
      count: counts.SUBMITTED,
      status: 'SUBMITTED' as const,
    },
    {
      label: 'Failed',
      count: counts.FAILED,
      status: 'FAILED' as const,
    },
    {
      label: 'Blocked',
      count: counts.CAPTCHA_BLOCKED,
      status: 'CAPTCHA_BLOCKED' as const,
    },
  ]

  return (
    <aside className="h-screen w-64 bg-slate-900 text-white flex flex-col border-r border-slate-700">
      {/* Header */}
      <div className="p-6 border-b border-slate-700">
        <div className="flex items-center gap-2 mb-6">
          <div className="text-2xl">🚀</div>
          <h1 className="text-xl font-bold">
            Job Apply
          </h1>
        </div>

        {/* Profile Dropdown */}
        <div className="relative">
          <button
            onClick={() =>
              setIsDropdownOpen(!isDropdownOpen)
            }
            onBlur={() =>
              setTimeout(
                () => setIsDropdownOpen(false),
                200
              )
            }
            className={cn(
              'w-full px-3 py-2 rounded-lg text-left font-medium',
              'bg-slate-800 hover:bg-slate-700',
              'border border-slate-600',
              'focus:outline-none focus:ring-2 focus:ring-blue-500',
              'transition-colors'
            )}
            aria-label="Profile dropdown"
            aria-haspopup="listbox"
          >
            {profilesLoading ? (
              <span className="text-slate-400">
                Loading...
              </span>
            ) : (
              <>
                <div className="truncate">
                  {activeProfileData?.name ||
                    'No Profile'}
                </div>
                <div className="text-xs text-slate-400">
                  {activeProfileData?.id}
                </div>
              </>
            )}
          </button>

          {/* Dropdown Menu */}
          {isDropdownOpen && !profilesLoading && (
            <div
              className={cn(
                'absolute top-full left-0 right-0 mt-2',
                'bg-slate-800 border border-slate-600',
                'rounded-lg shadow-lg z-50'
              )}
              role="listbox"
            >
              {profiles.length === 0 ? (
                <div className="px-3 py-2 text-slate-400 text-sm">
                  No profiles available
                </div>
              ) : (
                profiles.map((profile) => (
                  <button
                    key={profile.id}
                    onClick={() =>
                      handleSwitchProfile(
                        profile.id
                      )
                    }
                    className={cn(
                      'w-full px-3 py-2 text-left text-sm',
                      'hover:bg-slate-700',
                      'first:rounded-t-lg last:rounded-b-lg',
                      'focus:outline-none focus:ring-2 focus:ring-blue-500',
                      activeProfile === profile.id
                        ? 'bg-blue-600 font-semibold'
                        : ''
                    )}
                    role="option"
                    aria-selected={
                      activeProfile === profile.id
                    }
                  >
                    {profile.name}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Status Counts */}
      <div className="px-6 py-4 border-b border-slate-700">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
          Queue Status
        </h3>
        <div className="space-y-2">
          {statusBadges.map((badge) => (
            <div
              key={badge.status}
              className="flex items-center justify-between"
            >
              <span className="text-sm">
                {badge.label}
              </span>
              <span
                className={cn(
                  'px-2 py-1 rounded text-xs font-semibold',
                  getStatusColor(badge.status)
                )}
              >
                {queueLoading ? '-' : badge.count}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-6">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive =
              location.pathname === item.path
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={cn(
                    'block px-4 py-2 rounded-lg font-medium',
                    'transition-colors',
                    'focus:outline-none focus:ring-2 focus:ring-blue-500',
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  )}
                >
                  <span className="mr-2">
                    {item.icon}
                  </span>
                  {item.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-6 border-t border-slate-700">
        <div className="text-xs text-slate-400">
          <p>Job-AI-Auto-Apply</p>
          <p>UI v1.0.0</p>
        </div>
      </div>
    </aside>
  )
}
