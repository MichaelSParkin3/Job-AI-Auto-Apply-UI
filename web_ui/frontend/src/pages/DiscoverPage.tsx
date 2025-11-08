import { useOutletContext } from 'react-router-dom'
import { DiscoverForm } from '@/components/DiscoverForm'
import type { Profile } from '@/lib/api'

export function DiscoverPage() {
  const { selectedProfile } = useOutletContext<{ selectedProfile: Profile }>()

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Discover Jobs</h2>
        <p className="text-gray-600 mt-1">
          Search for new job postings and add them to your queue
        </p>
      </div>

      {selectedProfile && (
        <DiscoverForm profileId={selectedProfile.id} />
      )}
    </div>
  )
}
