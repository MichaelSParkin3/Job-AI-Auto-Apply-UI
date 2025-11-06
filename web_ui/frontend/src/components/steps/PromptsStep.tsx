import { Label } from '../ui/label'
import { Textarea } from '../ui/textarea'
import type { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
}

export function PromptsStep({ formData, onChange }: StepProps) {
  const updatePrompt = (key: string, value: string) => {
    onChange({
      ...formData,
      prompts: {
        ...(formData.prompts || {}),
        [key]: value,
      },
    })
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-gray-600 bg-blue-50 p-3 rounded border border-blue-200">
        These prompts guide the AI when answering job application questions. They should
        contain instructions, not templates.
      </p>

      <div>
        <Label htmlFor="coverLetter">Cover Letter Guidance</Label>
        <Textarea
          id="coverLetter"
          value={formData.prompts?.cover_letter || ''}
          onChange={(e) => updatePrompt('cover_letter', e.target.value)}
          placeholder="Instructions for writing a cover letter..."
          rows={4}
        />
        <p className="text-sm text-gray-500 mt-1">
          Guidance for AI when writing cover letters
        </p>
      </div>

      <div>
        <Label htmlFor="resumeSummary">Resume Summary Guidance</Label>
        <Textarea
          id="resumeSummary"
          value={formData.prompts?.resume_summary || ''}
          onChange={(e) => updatePrompt('resume_summary', e.target.value)}
          placeholder="Instructions for summarizing resume..."
          rows={4}
        />
        <p className="text-sm text-gray-500 mt-1">Guidance for AI when summarizing your resume</p>
      </div>

      <div>
        <Label htmlFor="accomplishments">Key Accomplishments Guidance</Label>
        <Textarea
          id="accomplishments"
          value={formData.prompts?.key_accomplishments || ''}
          onChange={(e) => updatePrompt('key_accomplishments', e.target.value)}
          placeholder="Instructions for highlighting accomplishments..."
          rows={4}
        />
        <p className="text-sm text-gray-500 mt-1">
          Guidance for AI when selecting key accomplishments
        </p>
      </div>

      <div>
        <Label htmlFor="experience">Experience Selection Guidance</Label>
        <Textarea
          id="experience"
          value={formData.prompts?.experience_selection || ''}
          onChange={(e) => updatePrompt('experience_selection', e.target.value)}
          placeholder="Instructions for selecting relevant experiences..."
          rows={4}
        />
        <p className="text-sm text-gray-500 mt-1">
          Guidance for AI when choosing relevant work experiences
        </p>
      </div>

      <div>
        <Label htmlFor="aiTools">AI Tools Response (Optional)</Label>
        <Textarea
          id="aiTools"
          value={formData.prompts?.ai_tools_response || ''}
          onChange={(e) => updatePrompt('ai_tools_response', e.target.value)}
          placeholder="How to respond to AI tools questions..."
          rows={3}
        />
        <p className="text-sm text-gray-500 mt-1">
          Guidance for responding to questions about AI tool usage
        </p>
      </div>
    </div>
  )
}
