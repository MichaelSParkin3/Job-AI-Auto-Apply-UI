import { MultiInput } from '../ui/multi-input'
import type { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function KeywordsStep({ formData, onChange }: StepProps) {
  const updateKeywords = (key: string, values: string[]) => {
    onChange({
      ...formData,
      keywords: {
        ...(formData.keywords || {}),
        [key]: values,
      },
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <MultiInput
          label="Job Roles"
          values={formData.keywords?.roles || []}
          onChange={(values) => updateKeywords('roles', values)}
          placeholder="e.g., 'Frontend Engineer', 'Full Stack Developer'"
        />
        <p className="text-sm text-gray-500 mt-2">Job titles you're interested in</p>
      </div>

      <div>
        <MultiInput
          label="Seniority Levels"
          values={formData.keywords?.seniority || []}
          onChange={(values) => updateKeywords('seniority', values)}
          placeholder="e.g., 'Senior', 'Staff', 'Lead'"
        />
        <p className="text-sm text-gray-500 mt-2">Seniority levels matching your experience</p>
      </div>

      <div>
        <MultiInput
          label="Technologies"
          values={formData.keywords?.tech_stack || []}
          onChange={(values) => updateKeywords('tech_stack', values)}
          placeholder="e.g., 'React', 'TypeScript', 'Node.js'"
        />
        <p className="text-sm text-gray-500 mt-2">
          Technologies and frameworks you work with
        </p>
      </div>

      <div>
        <MultiInput
          label="Domains/Industries"
          values={formData.keywords?.domains || []}
          onChange={(values) => updateKeywords('domains', values)}
          placeholder="e.g., 'FinTech', 'Healthcare', 'E-commerce'"
        />
        <p className="text-sm text-gray-500 mt-2">Industries and domains you're interested in</p>
      </div>
    </div>
  )
}
