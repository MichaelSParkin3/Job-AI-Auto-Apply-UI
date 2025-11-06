import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { MultiInput } from '../ui/multi-input'
import { Textarea } from '../ui/textarea'
import type { ExperienceItem, ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function ExperienceStep({ formData, onChange }: StepProps) {
  const experience = formData.experience || []

  const updateExperience = (index: number, exp: Partial<ExperienceItem>) => {
    const updated = [...experience]
    updated[index] = { ...updated[index], ...exp } as ExperienceItem
    onChange({ ...formData, experience: updated })
  }

  const addExperience = () => {
    onChange({
      ...formData,
      experience: [
        ...experience,
        {
          company: '',
          role: '',
          dates: '',
          highlights: [],
          tech_stack: [],
          metrics: {},
        },
      ],
    })
  }

  const removeExperience = (index: number) => {
    onChange({
      ...formData,
      experience: experience.filter((_, i) => i !== index),
    })
  }

  return (
    <div className="space-y-6">
      {experience.map((exp, index) => (
        <div key={index} className="border rounded-lg p-4 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Experience {index + 1}</h3>
            <Button
              type="button"
              onClick={() => removeExperience(index)}
              variant="destructive"
              size="sm"
            >
              Remove
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor={`company-${index}`}>Company *</Label>
              <Input
                id={`company-${index}`}
                value={exp.company}
                onChange={(e) => updateExperience(index, { company: e.target.value })}
                placeholder="Company name"
              />
            </div>

            <div>
              <Label htmlFor={`role-${index}`}>Job Title *</Label>
              <Input
                id={`role-${index}`}
                value={exp.role}
                onChange={(e) => updateExperience(index, { role: e.target.value })}
                placeholder="Senior Engineer"
              />
            </div>

            <div>
              <Label htmlFor={`dates-${index}`}>Dates *</Label>
              <Input
                id={`dates-${index}`}
                value={exp.dates}
                onChange={(e) => updateExperience(index, { dates: e.target.value })}
                placeholder="Jan 2020 - Present"
              />
            </div>

            <div>
              <Label htmlFor={`location-${index}`}>Location</Label>
              <Input
                id={`location-${index}`}
                value={exp.location || ''}
                onChange={(e) => updateExperience(index, { location: e.target.value })}
                placeholder="New York, NY"
              />
            </div>
          </div>

          <div>
            <Label htmlFor={`context-${index}`}>Context/Description</Label>
            <Textarea
              id={`context-${index}`}
              value={exp.context || ''}
              onChange={(e) => updateExperience(index, { context: e.target.value })}
              placeholder="Brief description of role and company"
              rows={2}
            />
          </div>

          <div>
            <MultiInput
              label="Highlights"
              values={exp.highlights}
              onChange={(values) => updateExperience(index, { highlights: values })}
              placeholder="Key achievement or responsibility"
            />
          </div>

          <div>
            <MultiInput
              label="Technologies"
              values={exp.tech_stack}
              onChange={(values) => updateExperience(index, { tech_stack: values })}
              placeholder="React, TypeScript, etc."
            />
          </div>
        </div>
      ))}

      <Button
        type="button"
        onClick={addExperience}
        variant="outline"
        className="w-full"
      >
        + Add Experience
      </Button>
    </div>
  )
}
