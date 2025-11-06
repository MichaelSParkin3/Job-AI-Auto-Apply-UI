import { Label } from '../ui/label'
import { Input } from '../ui/input'
import { Select } from '../ui/select'
import type { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function BasicInfoStep({ formData, onChange }: StepProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="id">Profile ID *</Label>
        <Input
          id="id"
          value={formData.id || ''}
          onChange={(e) => onChange({ ...formData, id: e.target.value })}
          placeholder="my-profile (slug format)"
          disabled={!!formData.id}
        />
        <p className="text-sm text-gray-500 mt-1">
          Unique identifier (alphanumeric, underscore, hyphen only)
        </p>
      </div>

      <div>
        <Label htmlFor="name">Full Name *</Label>
        <Input
          id="name"
          value={formData.name || ''}
          onChange={(e) => onChange({ ...formData, name: e.target.value })}
          placeholder="John Doe"
        />
      </div>

      <div>
        <Label htmlFor="browser">Preferred Browser</Label>
        <Select
          id="browser"
          value={formData.preferred_browser || ''}
          onChange={(e) =>
            onChange({ ...formData, preferred_browser: e.target.value || undefined })
          }
        >
          <option value="">None</option>
          <option value="chrome">Chrome</option>
          <option value="chromium">Chromium</option>
          <option value="msedge">Microsoft Edge</option>
        </Select>
      </div>

      <div>
        <Label htmlFor="userDataDir">Browser Profile Directory</Label>
        <Input
          id="userDataDir"
          value={formData.user_data_dir || ''}
          onChange={(e) =>
            onChange({ ...formData, user_data_dir: e.target.value || undefined })
          }
          placeholder="/path/to/browser/profile"
        />
        <p className="text-sm text-gray-500 mt-1">Optional: For persistent browser sessions</p>
      </div>
    </div>
  )
}
