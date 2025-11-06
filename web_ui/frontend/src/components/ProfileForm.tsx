import { useState, useEffect } from 'react'
import { Button } from './ui/button'
import { Card, CardContent } from './ui/card'
import {
  BasicInfoStep,
  ResumeStep,
  ContactStep,
  KeywordsStep,
  ExperienceStep,
  PromptsStep,
  ReviewStep,
} from './steps'
import type { ProfileDetailResponse } from '../lib/types'
import { profilesApi } from '../lib/api'

interface ProfileFormProps {
  profileId?: string
  onSave: (profile: ProfileDetailResponse) => void
  onCancel: () => void
}

export function ProfileForm({ profileId, onSave, onCancel }: ProfileFormProps) {
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [formData, setFormData] = useState<Partial<ProfileDetailResponse>>({
    id: '',
    name: '',
    resume_path: '',
    preferred_browser: undefined,
    user_data_dir: undefined,
    search_query: undefined,
    defaults: {},
    keywords: {},
    experience: [],
    prompts: {},
  })

  // Load existing profile on mount
  useEffect(() => {
    if (profileId) {
      setLoading(true)
      profilesApi
        .getDetail(profileId)
        .then((response) => {
          setFormData(response.data)
        })
        .catch((err) => {
          const message = err instanceof Error ? err.message : 'Failed to load profile'
          setError(message)
        })
        .finally(() => {
          setLoading(false)
        })
    }
  }, [profileId])

  const steps = [
    { number: 1, title: 'Basic Info', component: BasicInfoStep },
    { number: 2, title: 'Resume & Search', component: ResumeStep },
    { number: 3, title: 'Contact', component: ContactStep },
    { number: 4, title: 'Keywords', component: KeywordsStep },
    { number: 5, title: 'Experience', component: ExperienceStep },
    { number: 6, title: 'Prompts', component: PromptsStep },
    { number: 7, title: 'Review', component: ReviewStep },
  ]

  const validateStep = (stepNum: number): boolean => {
    switch (stepNum) {
      case 1:
        // Basic info validation
        return !!(formData.id?.trim() && formData.name?.trim())
      case 2:
        // Resume validation
        return !!formData.resume_path?.trim()
      default:
        return true
    }
  }

  const handleNext = () => {
    setError(null)
    if (validateStep(step)) {
      setStep(step + 1)
    } else {
      setError('Please fill in required fields')
    }
  }

  const handleBack = () => {
    setError(null)
    setStep(step - 1)
  }

  const handleEditStep = (stepNum: number) => {
    setError(null)
    setStep(stepNum)
  }

  const handleSubmit = async () => {
    setError(null)
    if (!validateStep(step)) {
      setError('Please fill in required fields')
      return
    }

    setLoading(true)
    try {
      const profileData = formData as ProfileDetailResponse

      if (profileId) {
        // Update existing profile
        await profilesApi.update(profileId, profileData)
      } else {
        // Create new profile
        await profilesApi.create(profileData)
      }

      onSave(profileData)
    } catch (err) {
      const message =
        err instanceof Error && err.message
          ? err.message
          : 'Failed to save profile'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  const CurrentStep = steps[step - 1].component

  return (
    <div className="space-y-6">
      {/* Progress indicator */}
      <div className="flex items-center justify-between gap-1">
        {steps.map((s) => (
          <div key={s.number} className="flex-1 space-y-1">
            <button
              type="button"
              onClick={() => handleEditStep(s.number)}
              className={`w-full h-2 rounded-full transition-colors ${
                s.number <= step ? 'bg-blue-500' : 'bg-gray-300'
              }`}
            />
            <p className="text-xs text-center text-gray-600">{s.title}</p>
          </div>
        ))}
      </div>

      {/* Step indicator */}
      <div className="text-center">
        <h2 className="text-2xl font-bold">
          Step {step} of {steps.length}
        </h2>
        <p className="text-gray-600">{steps[step - 1].title}</p>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Step content */}
      <Card>
        <CardContent className="pt-6">
          <CurrentStep
            formData={formData}
            onChange={setFormData}
            onEditStep={step === 7 ? handleEditStep : undefined}
          />
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex gap-4 justify-between">
        <Button
          onClick={handleBack}
          disabled={step === 1 || loading}
          variant="outline"
        >
          Back
        </Button>

        <div className="flex gap-2">
          <Button onClick={onCancel} variant="outline" disabled={loading}>
            Cancel
          </Button>

          {step < steps.length ? (
            <Button onClick={handleNext} disabled={loading}>
              Next
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? 'Saving...' : 'Save Profile'}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
