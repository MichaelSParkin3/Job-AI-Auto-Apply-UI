import { useState } from 'react'
import type { DiscoverRequest } from '@/lib/api'
import { discoverApi } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface DiscoverFormProps {
  profileId: string
}

export function DiscoverForm({ profileId }: DiscoverFormProps) {
  const [window, setWindow] = useState('24h')
  const [cap, setCap] = useState(10)
  const [loading, setLoading] = useState(false)
  const { addToast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!profileId) {
      addToast({
        title: 'Error',
        description: 'Please select a profile first',
        variant: 'destructive',
      })
      return
    }

    if (cap < 1 || cap > 100) {
      addToast({
        title: 'Error',
        description: 'Maximum jobs must be between 1 and 100',
        variant: 'destructive',
      })
      return
    }

    setLoading(true)

    try {
      const request: DiscoverRequest = {
        profile_id: profileId,
        window,
        cap,
      }

      const response = await discoverApi.start(request)

      addToast({
        title: 'Discover Started',
        description: response.data.message,
      })

      // Reset form
      setWindow('24h')
      setCap(10)
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error'
      addToast({
        title: 'Discover Failed',
        description: errorMessage,
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Discover Jobs</CardTitle>
        <CardDescription>
          Search for new job postings and add them to your queue
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="window">Time Window</Label>
            <Select value={window} onChange={(e) => setWindow(e.target.value)} disabled={loading}>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
              <option value="1w">Last week</option>
              <option value="1m">Last month</option>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="cap">Maximum Jobs to Discover</Label>
            <Input
              id="cap"
              type="number"
              min={1}
              max={100}
              value={cap}
              onChange={(e) => setCap(Math.max(1, Math.min(100, parseInt(e.target.value) || 10)))}
              disabled={loading}
            />
            <p className="text-xs text-gray-500">Between 1 and 100 jobs</p>
          </div>

          <Button type="submit" disabled={loading || !profileId} className="w-full">
            {loading ? 'Discovering...' : 'Run Discover'}
          </Button>

          {!profileId && (
            <p className="text-sm text-red-600">Please select a profile to run discover</p>
          )}
        </form>
      </CardContent>
    </Card>
  )
}
