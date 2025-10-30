import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import axios from 'axios'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { ErrorBoundary } from './components/ErrorBoundary'
import { LoadingSpinner } from './components/LoadingSpinner'
import { Dashboard } from './pages/Dashboard'
import Settings from './pages/Settings'
import ProfileEdit from './pages/ProfileEdit'
import { JobDetail } from './pages/JobDetail'
import ProfilesPage from './pages/ProfilesPage'
import DiscoverPage from './pages/DiscoverPage'
import ArtifactsPage from './pages/ArtifactsPage'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

export default function App() {
  const [isHealthy, setIsHealthy] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check backend health on startup
    axios
      .get(`${API_BASE_URL.replace('/api/v1', '')}/health`)
      .then(() => setIsHealthy(true))
      .catch(() => {
        console.error('Backend is unavailable')
        setIsHealthy(false)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner message="Checking server health..." />
      </div>
    )
  }

  if (!isHealthy) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold mb-2">
            Backend Unavailable
          </h1>
          <p className="text-gray-600">
            Please start the backend server on port 5000.
          </p>
          <p className="text-sm text-gray-500 mt-4">
            Run: <code className="bg-gray-100 px-2 py-1">python web_ui/backend/src/app.py</code>
          </p>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <Router>
        <div className="flex h-screen overflow-hidden bg-gray-50">
          {/* Sidebar */}
          <Sidebar />

          {/* Main Content */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Top Bar */}
            <TopBar />

            {/* Page Content */}
            <main className="flex-1 overflow-auto">
              <div className="max-w-7xl mx-auto p-8">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route
                    path="/job/:jobId"
                    element={<JobDetail />}
                  />
                  <Route
                    path="/discover"
                    element={<DiscoverPage />}
                  />
                  <Route
                    path="/profiles/:profileId/edit"
                    element={<ProfileEdit />}
                  />
                  <Route
                    path="/profiles"
                    element={<ProfilesPage />}
                  />
                  <Route
                    path="/profiles/new"
                    element={<ProfileEdit isNew={true} />}
                  />
                  <Route
                    path="/settings"
                    element={<Settings />}
                  />
                  <Route
                    path="/artifacts"
                    element={<ArtifactsPage />}
                  />
                  <Route
                    path="*"
                    element={<Navigate to="/" replace />}
                  />
                </Routes>
              </div>
            </main>
          </div>
        </div>
      </Router>
    </ErrorBoundary>
  )
}

