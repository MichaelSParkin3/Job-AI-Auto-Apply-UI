import { Outlet, useNavigate } from 'react-router-dom'
import { Settings } from 'lucide-react'
import { ProfileSelector } from '@/components/ProfileSelector'
import { Sidebar } from '@/components/Sidebar'
import type { Profile } from '@/lib/api'
import { useState } from 'react'

export function Layout() {
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null)
  const navigate = useNavigate()

  const handleProfileSelect = (profile: Profile | null) => {
    setSelectedProfile(profile)
    if (profile) {
      navigate('/discover')
    }
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900">
                Job Auto-Apply
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <ProfileSelector
                selectedProfileId={selectedProfile?.id}
                onSelect={handleProfileSelect}
              />
              <button
                onClick={() => navigate('/settings')}
                className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 hover:text-gray-900"
                title="Settings"
              >
                <Settings size={20} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content with sidebar */}
      {selectedProfile ? (
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <Sidebar profileId={selectedProfile.id} />

          {/* Main content area */}
          <main className="flex-1 overflow-auto">
            <Outlet context={{ selectedProfile }} />
          </main>
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center">
          <div className="rounded-lg bg-blue-50 p-8 text-center">
            <h2 className="mb-2 text-lg font-semibold text-blue-900">
              Select a Profile
            </h2>
            <p className="text-blue-700">
              Please select a profile from the header to get started
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
