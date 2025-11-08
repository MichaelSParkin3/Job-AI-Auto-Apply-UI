import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ToastProvider } from '@/lib/toast'
import { Toaster } from '@/components/ui/toast'
import { Layout } from '@/components/Layout'
import { DiscoverPage } from '@/pages/DiscoverPage'
import { ApplyPage } from '@/pages/ApplyPage'
import { ProfilesPage } from '@/pages/ProfilesPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { JobDetailsPage } from '@/pages/JobDetailsPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<DiscoverPage />} />
            <Route path="profiles" element={<ProfilesPage />} />
            <Route path="discover" element={<DiscoverPage />} />
            <Route path="apply" element={<ApplyPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="jobs/:profileId/:jobId" element={<JobDetailsPage />} />
          </Route>
        </Routes>
        <Toaster />
      </ToastProvider>
    </BrowserRouter>
  )
}

export default App
