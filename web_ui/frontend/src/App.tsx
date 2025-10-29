import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from './services/api'

export default function App() {
  const [isHealthy, setIsHealthy] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check backend health on startup
    api.get('/health')
      .then(() => setIsHealthy(true))
      .catch(() => setIsHealthy(false))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>
  }

  return (
    <Router>
      <div className="min-h-screen bg-background text-foreground">
        {!isHealthy && (
          <div className="bg-destructive text-destructive-foreground p-4">
            ⚠️ Backend is unavailable. Please start the backend server.
          </div>
        )}
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/jobs/:jobId" element={<JobDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </Router>
  )
}

function Dashboard() {
  return <div className="p-6">Dashboard - Coming Soon</div>
}

function JobDetail() {
  return <div className="p-6">Job Details - Coming Soon</div>
}

function Settings() {
  return <div className="p-6">Settings - Coming Soon</div>
}
