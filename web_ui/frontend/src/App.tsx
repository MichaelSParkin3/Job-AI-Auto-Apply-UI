import { useState } from 'react'
import type { Profile } from '@/lib/api'
import { ProfileSelector } from '@/components/ProfileSelector'
import { DiscoverForm } from '@/components/DiscoverForm'
import { ApplyForm } from '@/components/ApplyForm'
import { ApplyProgress } from '@/components/ApplyProgress'
import { ProfilesPage } from '@/pages/ProfilesPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { ToastProvider } from '@/lib/toast'
import { Toaster } from '@/components/ui/toast'
import './App.css'

function AppContent() {
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null)
  const [activeTab, setActiveTab] = useState<'profiles' | 'discover' | 'apply' | 'settings'>('discover')
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [activeWebsocketUrl, setActiveWebsocketUrl] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-6xl px-6 py-6">
          <h1 className="mb-4 text-3xl font-bold text-gray-900">
            Job Auto-Apply
          </h1>
          <ProfileSelector
            selectedProfileId={selectedProfile?.id}
            onSelect={setSelectedProfile}
          />
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-6xl px-6 py-8">
        {selectedProfile ? (
          <>
            {/* Tabs */}
            <div className="mb-6 border-b border-gray-200">
              <nav className="flex gap-8" aria-label="Tabs">
                <button
                  onClick={() => setActiveTab('profiles')}
                  className={`border-b-2 px-1 py-4 text-sm font-medium ${
                    activeTab === 'profiles'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-900'
                  }`}
                  aria-current={activeTab === 'profiles' ? 'page' : undefined}
                >
                  Profiles
                </button>
                <button
                  onClick={() => setActiveTab('discover')}
                  className={`border-b-2 px-1 py-4 text-sm font-medium ${
                    activeTab === 'discover'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-900'
                  }`}
                  aria-current={activeTab === 'discover' ? 'page' : undefined}
                >
                  Discover
                </button>
                <button
                  onClick={() => setActiveTab('apply')}
                  className={`border-b-2 px-1 py-4 text-sm font-medium ${
                    activeTab === 'apply'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-900'
                  }`}
                  aria-current={activeTab === 'apply' ? 'page' : undefined}
                >
                  Apply
                </button>
                <button
                  onClick={() => setActiveTab('settings')}
                  className={`border-b-2 px-1 py-4 text-sm font-medium ${
                    activeTab === 'settings'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-900'
                  }`}
                  aria-current={activeTab === 'settings' ? 'page' : undefined}
                >
                  Settings
                </button>
              </nav>
            </div>

            {/* Tab Content */}
            <div>
              {activeTab === 'profiles' && (
                <ProfilesPage />
              )}

              {activeTab === 'discover' && selectedProfile && (
                <DiscoverForm profileId={selectedProfile.id} />
              )}

              {activeTab === 'apply' && (
                <>
                  {activeTaskId && activeWebsocketUrl ? (
                    <ApplyProgress
                      taskId={activeTaskId}
                      websocketUrl={activeWebsocketUrl}
                      onClose={() => {
                        setActiveTaskId(null)
                        setActiveWebsocketUrl(null)
                      }}
                    />
                  ) : (
                    <ApplyForm
                      profileId={selectedProfile.id}
                      onTaskCreated={(taskId, websocketUrl) => {
                        setActiveTaskId(taskId)
                        setActiveWebsocketUrl(websocketUrl)
                      }}
                    />
                  )}
                </>
              )}

              {activeTab === 'settings' && (
                <SettingsPage />
              )}
            </div>

      <Toaster />
          </>
        ) : (
          <div className="rounded-lg bg-blue-50 p-6 text-center">
            <h2 className="mb-2 text-lg font-semibold text-blue-900">
              Select a Profile
            </h2>
            <p className="text-blue-700">
              Please select a profile from the header to get started
            </p>
          </div>
        )}
      </main>
    </div>
  )
}

function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  )
}

export default App
