import { useState } from 'react'
import { Label } from '../ui/label'
import { Input } from '../ui/input'
import { Button } from '../ui/button'
import type { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function ContactStep({ formData, onChange }: StepProps) {
  const [showEEO, setShowEEO] = useState(false)

  const updateDefault = (key: string, value: string) => {
    onChange({
      ...formData,
      defaults: {
        ...(formData.defaults || {}),
        [key]: value,
      },
    })
  }

  return (
    <div className="space-y-6">
      {/* Personal Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Personal Information</h3>

        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={formData.defaults?.email || ''}
            onChange={(e) => updateDefault('email', e.target.value)}
            placeholder="email@example.com"
          />
        </div>

        <div>
          <Label htmlFor="phone">Phone</Label>
          <Input
            id="phone"
            value={formData.defaults?.phone || ''}
            onChange={(e) => updateDefault('phone', e.target.value)}
            placeholder="+1-555-0100"
          />
        </div>

        <div>
          <Label htmlFor="location">Location</Label>
          <Input
            id="location"
            value={formData.defaults?.location || ''}
            onChange={(e) => updateDefault('location', e.target.value)}
            placeholder="City, State"
          />
        </div>

        <div>
          <Label htmlFor="pronouns">Pronouns</Label>
          <Input
            id="pronouns"
            value={formData.defaults?.pronouns || ''}
            onChange={(e) => updateDefault('pronouns', e.target.value)}
            placeholder="she/her, he/him, they/them"
          />
        </div>
      </div>

      {/* Work Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Work Information</h3>

        <div>
          <Label htmlFor="currentCompany">Current Company</Label>
          <Input
            id="currentCompany"
            value={formData.defaults?.current_company || ''}
            onChange={(e) => updateDefault('current_company', e.target.value)}
            placeholder="Company name"
          />
        </div>

        <div>
          <Label htmlFor="workAuth">Work Authorization</Label>
          <Input
            id="workAuth"
            value={formData.defaults?.work_authorization || ''}
            onChange={(e) => updateDefault('work_authorization', e.target.value)}
            placeholder="e.g., Authorized to work"
          />
        </div>

        <div>
          <Label htmlFor="visa">Requires Visa Sponsorship</Label>
          <Input
            id="visa"
            value={formData.defaults?.requires_visa_sponsorship || ''}
            onChange={(e) => updateDefault('requires_visa_sponsorship', e.target.value)}
            placeholder="Yes / No"
          />
        </div>

        <div>
          <Label htmlFor="salary">Salary Expectation</Label>
          <Input
            id="salary"
            value={formData.defaults?.salary_expectation || ''}
            onChange={(e) => updateDefault('salary_expectation', e.target.value)}
            placeholder="e.g., $100k - $150k"
          />
        </div>
      </div>

      {/* Links Section */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Links</h3>

        <div>
          <Label htmlFor="portfolio">Portfolio URL</Label>
          <Input
            id="portfolio"
            type="url"
            value={formData.defaults?.portfolio_url || ''}
            onChange={(e) => updateDefault('portfolio_url', e.target.value)}
            placeholder="https://example.com"
          />
        </div>

        <div>
          <Label htmlFor="github">GitHub URL</Label>
          <Input
            id="github"
            type="url"
            value={formData.defaults?.github_url || ''}
            onChange={(e) => updateDefault('github_url', e.target.value)}
            placeholder="https://github.com/username"
          />
        </div>

        <div>
          <Label htmlFor="linkedin">LinkedIn URL</Label>
          <Input
            id="linkedin"
            type="url"
            value={formData.defaults?.linkedin_url || ''}
            onChange={(e) => updateDefault('linkedin_url', e.target.value)}
            placeholder="https://linkedin.com/in/username"
          />
        </div>
      </div>

      {/* EEO Section */}
      <div className="space-y-4">
        <Button
          type="button"
          variant="outline"
          onClick={() => setShowEEO(!showEEO)}
          className="w-full"
        >
          {showEEO ? '▼' : '▶'} EEO Information (Optional)
        </Button>

        {showEEO && (
          <div className="bg-gray-50 p-4 rounded space-y-4 border-l-4 border-blue-500">
            <p className="text-sm text-gray-600">
              Equal Employment Opportunity (EEO) fields for employer compliance
            </p>

            <div>
              <Label htmlFor="gender">Gender</Label>
              <Input
                id="gender"
                value={formData.defaults?.eeo_gender || ''}
                onChange={(e) => updateDefault('eeo_gender', e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="race">Race/Ethnicity</Label>
              <Input
                id="race"
                value={formData.defaults?.eeo_race || ''}
                onChange={(e) => updateDefault('eeo_race', e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="veteran">Veteran Status</Label>
              <Input
                id="veteran"
                value={formData.defaults?.eeo_veteran_status || ''}
                onChange={(e) => updateDefault('eeo_veteran_status', e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="disability">Disability Status</Label>
              <Input
                id="disability"
                value={formData.defaults?.eeo_disability_status || ''}
                onChange={(e) => updateDefault('eeo_disability_status', e.target.value)}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
