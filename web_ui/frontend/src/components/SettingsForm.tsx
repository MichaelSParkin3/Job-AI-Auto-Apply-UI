import { useState } from 'react'
import type { SettingsResponse } from '@/lib/types'
import { settingsApi } from '@/lib/api'
import { useToast } from '@/lib/toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { SettingField } from '@/components/SettingField'
import { CategoryTabs } from '@/components/CategoryTabs'

interface SettingsFormProps {
  settings: SettingsResponse
  onSaved?: () => void
}

export function SettingsForm({ settings, onSaved }: SettingsFormProps) {
  const [activeCategory, setActiveCategory] = useState(settings.categories[0]?.id || '')
  const [formValues, setFormValues] = useState<Record<string, any>>(() => {
    const values: Record<string, any> = {}
    Object.entries(settings.fields).forEach(([, fields]) => {
      fields.forEach((field) => {
        values[field.key] = field.current || field.default || ''
      })
    })
    return values
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const { addToast } = useToast()

  const handleFieldChange = (key: string, value: any) => {
    setFormValues((prev) => ({
      ...prev,
      [key]: value,
    }))
    // Clear error for this field when user starts editing
    if (errors[key]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[key]
        return newErrors
      })
    }
  }

  const handleValidate = async () => {
    try {
      const response = await settingsApi.validateSettings(formValues)
      if (!response.data.valid) {
        setErrors(response.data.errors)

        // Calculate which categories have errors
        const errorsPerCategory: Record<string, number> = {}
        Object.entries(response.data.errors).forEach(([fieldKey]) => {
          // Find which category this field belongs to
          for (const [categoryId, fields] of Object.entries(settings.fields)) {
            if (fields.some((f) => f.key === fieldKey)) {
              errorsPerCategory[categoryId] = (errorsPerCategory[categoryId] || 0) + 1
              break
            }
          }
        })

        const errorCategories = Object.entries(errorsPerCategory)
          .map(([catId, count]) => {
            const category = settings.categories.find((c) => c.id === catId)
            return `${category?.name || catId} (${count})`
          })
          .join(', ')

        addToast({
          title: 'Validation Failed',
          description: `${Object.keys(response.data.errors).length} error(s) in: ${errorCategories}`,
          variant: 'destructive',
        })
        return false
      } else {
        setErrors({})
        return true
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Validation failed'
      addToast({
        title: 'Validation Error',
        description: errorMessage,
        variant: 'destructive',
      })
      return false
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const isValid = await handleValidate()
    if (!isValid) return

    setLoading(true)
    try {
      const response = await settingsApi.updateSettings(formValues)

      addToast({
        title: 'Settings Saved',
        description: response.data.message,
      })

      if (response.data.requires_restart) {
        addToast({
          title: 'Restart Required',
          description: 'Please restart the application for changes to take effect',
          variant: 'default',
        })
      }

      if (onSaved) {
        onSaved()
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to save settings'
      addToast({
        title: 'Save Failed',
        description: errorMessage,
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async (keys?: string[]) => {
    if (!window.confirm('Are you sure you want to reset these settings to defaults?')) {
      return
    }

    setLoading(true)
    try {
      const response = await settingsApi.resetSettings(keys, !keys || keys.length === 0)

      // Update form values with reset values
      if (response.data.updated_settings) {
        const newValues: Record<string, any> = { ...formValues }
        Object.entries(response.data.updated_settings).forEach(([key, field]) => {
          newValues[key] = field.default || ''
        })
        setFormValues(newValues)
      }

      addToast({
        title: 'Settings Reset',
        description: response.data.message,
      })

      if (onSaved) {
        onSaved()
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to reset settings'
      addToast({
        title: 'Reset Failed',
        description: errorMessage,
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const currentCategoryFields = settings.fields[activeCategory] || []

  // Calculate error counts per category
  const errorCounts: Record<string, number> = {}
  Object.entries(errors).forEach(([fieldKey]) => {
    for (const [categoryId, fields] of Object.entries(settings.fields)) {
      if (fields.some((f) => f.key === fieldKey)) {
        errorCounts[categoryId] = (errorCounts[categoryId] || 0) + 1
        break
      }
    }
  })

  return (
    <div className="space-y-6">
      <CategoryTabs
        categories={settings.categories}
        activeCategory={activeCategory}
        onCategoryChange={setActiveCategory}
        errorCounts={errorCounts}
      />

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Current Category Fields */}
        <Card>
          <CardHeader>
            <CardTitle>
              {settings.categories.find((c) => c.id === activeCategory)?.name}
            </CardTitle>
            <CardDescription>
              {settings.categories.find((c) => c.id === activeCategory)?.description}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {currentCategoryFields.length === 0 ? (
                <p className="text-gray-600 text-center py-8">No settings in this category</p>
              ) : (
                currentCategoryFields.map((field) => (
                  <SettingField
                    key={field.key}
                    field={field}
                    value={formValues[field.key]}
                    onChange={(value) => handleFieldChange(field.key, value)}
                    error={errors[field.key]}
                    disabled={loading}
                  />
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex gap-3 justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={() => handleReset(currentCategoryFields.map((f) => f.key))}
            disabled={loading || currentCategoryFields.length === 0}
          >
            Reset Category
          </Button>
          <Button type="button" variant="outline" disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading}>
            {loading ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </form>
    </div>
  )
}
