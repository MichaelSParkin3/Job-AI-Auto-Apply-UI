import { useState } from 'react'
import type { SettingField as SettingFieldType } from '@/lib/types'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'

interface SettingFieldProps {
  field: SettingFieldType
  value: any
  onChange: (value: any) => void
  error?: string
  disabled?: boolean
}

export function SettingField({
  field,
  value,
  onChange,
  error,
  disabled,
}: SettingFieldProps) {
  const [isRevealed, setIsRevealed] = useState(false)

  const handleChange = (newValue: any) => {
    onChange(newValue)
  }

  // Render different input types
  const renderInput = () => {
    switch (field.type) {
      case 'password':
        return (
          <div className="space-y-2">
            <div className="flex gap-2">
              <Input
                type={isRevealed ? 'text' : 'password'}
                value={value || ''}
                onChange={(e) => handleChange(e.target.value)}
                placeholder={field.label}
                disabled={disabled}
                className={error ? 'border-red-500' : ''}
              />
              <button
                type="button"
                onClick={() => setIsRevealed(!isRevealed)}
                className="px-3 py-2 border border-gray-300 rounded-md text-gray-600 hover:bg-gray-50 text-sm font-medium"
                disabled={disabled}
              >
                {isRevealed ? 'Hide' : 'Show'}
              </button>
            </div>
            {field.sensitive && value && (
              <p className="text-xs text-yellow-600">
                🔒 This value is masked in the UI
              </p>
            )}
          </div>
        )

      case 'bool':
        return (
          <Select
            value={value ? 'true' : 'false'}
            onChange={(e) => handleChange(e.target.value === 'true')}
            disabled={disabled}
          >
            <option value="true">Enabled</option>
            <option value="false">Disabled</option>
          </Select>
        )

      case 'int':
        return (
          <Input
            type="number"
            step="1"
            value={value || ''}
            onChange={(e) =>
              handleChange(e.target.value ? parseInt(e.target.value) : field.default)
            }
            disabled={disabled}
            className={error ? 'border-red-500' : ''}
            min={field.validation?.min}
            max={field.validation?.max}
          />
        )

      case 'float':
        return (
          <Input
            type="number"
            step="0.1"
            value={value || ''}
            onChange={(e) =>
              handleChange(e.target.value ? parseFloat(e.target.value) : field.default)
            }
            disabled={disabled}
            className={error ? 'border-red-500' : ''}
            min={field.validation?.min}
            max={field.validation?.max}
          />
        )

      case 'list':
        return (
          <Input
            type="text"
            value={Array.isArray(value) ? value.join(', ') : value || ''}
            onChange={(e) => {
              const items = e.target.value.split(',').map((s) => s.trim()).filter(Boolean)
              handleChange(items)
            }}
            placeholder="Enter values separated by commas"
            disabled={disabled}
            className={error ? 'border-red-500' : ''}
          />
        )

      default:
        // string, or validation with options
        if (field.validation?.options && field.validation.options.length > 0) {
          return (
            <Select
              value={value || ''}
              onChange={(e) => handleChange(e.target.value)}
              disabled={disabled}
            >
              <option value="">Select an option</option>
              {field.validation.options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
          )
        }

        return (
          <Input
            type="text"
            value={value || ''}
            onChange={(e) => handleChange(e.target.value)}
            placeholder={field.label}
            disabled={disabled}
            className={error ? 'border-red-500' : ''}
          />
        )
    }
  }

  return (
    <div className="space-y-2">
      <div>
        <Label htmlFor={field.key} className="font-medium">
          {field.label}
          {field.sensitive && <span className="ml-1 text-red-500">🔒</span>}
        </Label>
        <p className="text-xs text-gray-600 mt-1">{field.description}</p>
      </div>

      {renderInput()}

      {field.validation && (
        <div className="text-xs text-gray-500 space-y-1">
          {field.validation.min !== undefined && (
            <p>Minimum: {field.validation.min}</p>
          )}
          {field.validation.max !== undefined && (
            <p>Maximum: {field.validation.max}</p>
          )}
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {field.default !== null && field.default !== undefined && (
        <p className="text-xs text-gray-500">
          Default: <span className="font-mono">{String(field.default)}</span>
        </p>
      )}
    </div>
  )
}
