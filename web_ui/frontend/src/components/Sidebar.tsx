import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useProfile } from '../hooks/useProfile'
import { useQueue } from '../hooks/useQueue'
import { cn } from '../lib/utils'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'

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

  const activeProfileData = profiles.find(
    (p) => p.id === activeProfile
  )

  const handleSwitchProfile = async (
    profileId: string
  ) => {
    try {
      await switchProfile(profileId)
    } catch (err) {
      console.error('Failed to switch profile:', err)
    }
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
      <div className="p-6">
        <div className="flex items-center gap-2 mb-6">
          <div className="text-2xl">🚀</div>
          <h1 className="text-xl font-bold">
            Job Apply
          </h1>
        </div>

        {/* Profile Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className={cn(
                'w-full justify-start text-left font-medium',
                'bg-slate-800 border-slate-600 text-white',
                'hover:bg-slate-700 hover:text-white'
              )}
              disabled={profilesLoading}
            >
              {profilesLoading ? (
                <span className="text-slate-400">
                  Loading...
                </span>
              ) : (
                <div className="flex flex-col gap-1 w-full">
                  <div className="truncate">
                    {activeProfileData?.name ||
                      'No Profile'}
                  </div>
                  <div className="text-xs text-slate-400">
                    {activeProfileData?.id}
                  </div>
                </div>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56 bg-slate-800 border-slate-600">
            {profiles.length === 0 ? (
              <div className="px-3 py-2 text-slate-400 text-sm">
                No profiles available
              </div>
            ) : (
              profiles.map((profile) => (
                <DropdownMenuItem
                  key={profile.id}
                  onClick={() =>
                    handleSwitchProfile(profile.id)
                  }
                  className={cn(
                    'cursor-pointer',
                    activeProfile === profile.id
                      ? 'bg-blue-600 font-semibold'
                      : ''
                  )}
                >
                  {profile.name}
                </DropdownMenuItem>
              ))
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <Separator className="mt-6 bg-slate-700" />
      </div>

      {/* Status Counts */}
      <div className="px-6 py-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
          Queue Status
        </h3>
        <div className="space-y-2">
          {statusBadges.map((badge) => (
            <div
              key={badge.status}
              className="flex items-center justify-between"
            >
              <span className="text-sm text-slate-300">
                {badge.label}
              </span>
              <Badge
                variant={badge.status === 'SUBMITTED' ? 'default' : 'secondary'}
                className={cn(
                  'text-xs',
                  badge.status === 'NEW' &&
                    'bg-blue-600 text-white',
                  badge.status === 'IN_PROGRESS' &&
                    'bg-yellow-600 text-white',
                  badge.status === 'SUBMITTED' &&
                    'bg-green-600 text-white',
                  badge.status === 'FAILED' &&
                    'bg-red-600 text-white',
                  badge.status === 'CAPTCHA_BLOCKED' &&
                    'bg-orange-600 text-white'
                )}
              >
                {queueLoading ? '-' : badge.count}
              </Badge>
            </div>
          ))}
        </div>
        <Separator className="mt-4 bg-slate-700" />
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
      <div className="p-6">
        <Separator className="mb-4 bg-slate-700" />
        <div className="text-xs text-slate-400 space-y-1">
          <p>Job-AI-Auto-Apply</p>
          <p>UI v1.0.0</p>
        </div>
      </div>
    </aside>
  )
}
