import { useState, useEffect } from 'react'
import { settingsApi } from '@/lib/api'
import type { SettingsResponse } from '@/lib/types'
import { useToast } from '@/lib/toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { SettingsForm } from '@/components/SettingsForm'

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { addToast } = useToast()

  const loadSettings = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await settingsApi.getSettings()
      setSettings(response.data)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to load settings'
      setError(errorMessage)
      addToast({
        title: 'Error Loading Settings',
        description: errorMessage,
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleResetAll = async () => {
    if (!window.confirm('Reset ALL settings to their default values? This action cannot be undone.')) {
      return
    }

    try {
      const response = await settingsApi.resetSettings(undefined, true)
      addToast({
        title: 'All Settings Reset',
        description: response.data.message,
      })
      // Reload settings
      await loadSettings()
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to reset settings'
      addToast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      })
    }
  }

  useEffect(() => {
    loadSettings()
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Settings</h1>
        <Card>
          <CardContent className="pt-6 text-center">
            <p className="text-gray-600">Loading settings...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !settings) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Settings</h1>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-red-600 mb-4">{error || 'Failed to load settings'}</p>
              <Button onClick={loadSettings} variant="outline">
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-gray-600 mt-2">
            Manage application configuration and environment variables
          </p>
        </div>
        <Button
          variant="destructive"
          onClick={handleResetAll}
          className="text-sm"
        >
          Reset All
        </Button>
      </div>

      {/* Info Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardHeader>
          <CardTitle className="text-base">About Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="text-sm space-y-2 text-gray-700">
            <li>• Settings are stored in your .env file</li>
            <li>• 🔒 Sensitive fields (API keys) are masked for security</li>
            <li>• Some settings may require restarting the application</li>
            <li>• Use the category tabs to organize settings by purpose</li>
          </ul>
        </CardContent>
      </Card>

      {/* Settings Form */}
      <SettingsForm settings={settings} onSaved={loadSettings} />
    </div>
  )
}
