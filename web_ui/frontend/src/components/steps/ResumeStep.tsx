import { Label } from '../ui/label'
import { Textarea } from '../ui/textarea'
import { FileUpload } from '../ui/file-upload'
import type { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function ResumeStep({ formData, onChange }: StepProps) {
  return (
    <div className="space-y-6">
      <div>
        <Label>Resume PDF *</Label>
        <FileUpload
          profileId={formData.id}
          currentPath={formData.resume_path}
          onUploadComplete={(path) => onChange({ ...formData, resume_path: path })}
          accept=".pdf"
          label="Upload Resume"
        />
        <p className="text-sm text-gray-500 mt-2">Upload a PDF resume (max 10MB)</p>
      </div>

      <div>
        <Label htmlFor="searchQuery">Custom Search Query</Label>
        <Textarea
          id="searchQuery"
          value={formData.search_query || ''}
          onChange={(e) =>
            onChange({ ...formData, search_query: e.target.value || undefined })
          }
          placeholder="Custom Google search query (e.g., 'React developer jobs remote')"
          rows={3}
        />
        <p className="text-sm text-gray-500 mt-1">
          Optional: Override default job discovery query
        </p>
      </div>
    </div>
  )
}
