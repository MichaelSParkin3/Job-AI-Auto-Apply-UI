import { Button } from '../ui/button'
import { Card, CardContent } from '../ui/card'
import { ProfileDetailResponse } from '../../lib/types'

interface StepProps {
  formData: Partial<ProfileDetailResponse>
  onChange: (data: Partial<ProfileDetailResponse>) => void
  onEditStep?: (step: number) => void
}

export function ReviewStep({ formData, onChange, onEditStep }: StepProps) {
  return (
    <div className="space-y-6">
      <p className="text-gray-600">
        Please review all information before saving. Click on any section to edit.
      </p>

      {/* Basic Info */}
      <Card>
        <CardContent className="pt-6 space-y-2">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold">Basic Information</h3>
              <div className="text-sm text-gray-600 mt-2 space-y-1">
                <p>
                  <strong>ID:</strong> {formData.id}
                </p>
                <p>
                  <strong>Name:</strong> {formData.name}
                </p>
                {formData.preferred_browser && (
                  <p>
                    <strong>Browser:</strong> {formData.preferred_browser}
                  </p>
                )}
              </div>
            </div>
            {onEditStep && (
              <Button
                type="button"
                onClick={() => onEditStep(1)}
                variant="outline"
                size="sm"
              >
                Edit
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Resume */}
      <Card>
        <CardContent className="pt-6 space-y-2">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold">Resume & Search</h3>
              <div className="text-sm text-gray-600 mt-2 space-y-1">
                <p>
                  <strong>Resume:</strong> {formData.resume_path}
                </p>
                {formData.search_query && (
                  <p>
                    <strong>Search Query:</strong> {formData.search_query}
                  </p>
                )}
              </div>
            </div>
            {onEditStep && (
              <Button
                type="button"
                onClick={() => onEditStep(2)}
                variant="outline"
                size="sm"
              >
                Edit
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Keywords */}
      <Card>
        <CardContent className="pt-6 space-y-2">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold">Keywords</h3>
              <div className="text-sm text-gray-600 mt-2 space-y-1">
                {formData.keywords?.roles && formData.keywords.roles.length > 0 && (
                  <p>
                    <strong>Roles:</strong> {formData.keywords.roles.join(', ')}
                  </p>
                )}
                {formData.keywords?.tech_stack && formData.keywords.tech_stack.length > 0 && (
                  <p>
                    <strong>Tech:</strong> {formData.keywords.tech_stack.join(', ')}
                  </p>
                )}
                {formData.keywords?.seniority && formData.keywords.seniority.length > 0 && (
                  <p>
                    <strong>Seniority:</strong> {formData.keywords.seniority.join(', ')}
                  </p>
                )}
              </div>
            </div>
            {onEditStep && (
              <Button
                type="button"
                onClick={() => onEditStep(4)}
                variant="outline"
                size="sm"
              >
                Edit
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Experience Count */}
      <Card>
        <CardContent className="pt-6 space-y-2">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold">Experience</h3>
              <p className="text-sm text-gray-600 mt-2">
                {formData.experience?.length || 0} experience
                {(formData.experience?.length || 0) !== 1 ? ' entries' : ' entry'}
              </p>
              {formData.experience && formData.experience.length > 0 && (
                <div className="text-sm text-gray-600 mt-2 space-y-1">
                  {formData.experience.slice(0, 3).map((exp, idx) => (
                    <p key={idx}>
                      • {exp.company} - {exp.role}
                    </p>
                  ))}
                  {formData.experience.length > 3 && (
                    <p>• ... and {formData.experience.length - 3} more</p>
                  )}
                </div>
              )}
            </div>
            {onEditStep && (
              <Button
                type="button"
                onClick={() => onEditStep(5)}
                variant="outline"
                size="sm"
              >
                Edit
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Contact Info Summary */}
      <Card>
        <CardContent className="pt-6 space-y-2">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="font-semibold">Contact Information</h3>
              <div className="text-sm text-gray-600 mt-2 space-y-1">
                {formData.defaults?.email && <p>{formData.defaults.email}</p>}
                {formData.defaults?.phone && <p>{formData.defaults.phone}</p>}
                {formData.defaults?.location && <p>{formData.defaults.location}</p>}
              </div>
            </div>
            {onEditStep && (
              <Button
                type="button"
                onClick={() => onEditStep(3)}
                variant="outline"
                size="sm"
              >
                Edit
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
