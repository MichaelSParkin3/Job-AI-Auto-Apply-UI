import { useState } from 'react'
import { Input } from './input'
import { Button } from './button'
import { Tag } from './tag'

interface MultiInputProps {
  values: string[]
  onChange: (values: string[]) => void
  placeholder?: string
  disabled?: boolean
  label?: string
}

export function MultiInput({
  values,
  onChange,
  placeholder,
  disabled,
  label,
}: MultiInputProps) {
  const [input, setInput] = useState('')

  // Helper function to parse comma-separated input
  const parseCommaSeparatedInput = (text: string): string[] => {
    return text
      .split(',')
      .map((v) => v.trim())
      .filter((v) => v.length > 0)
      .filter((v) => !values.includes(v)) // Remove duplicates
  }

  const addValue = () => {
    const inputValue = input.trim()
    if (!inputValue) return

    let newValues: string[]

    // Check if input contains commas
    if (inputValue.includes(',')) {
      newValues = parseCommaSeparatedInput(inputValue)
    } else {
      // Single value
      newValues = values.includes(inputValue) ? [] : [inputValue]
    }

    if (newValues.length > 0) {
      onChange([...values, ...newValues])
      setInput('')
    }
  }

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pastedText = e.clipboardData.getData('text')

    // Only intercept if pasted text contains commas
    if (pastedText.includes(',')) {
      e.preventDefault()

      const newValues = parseCommaSeparatedInput(pastedText)

      if (newValues.length > 0) {
        onChange([...values, ...newValues])
        setInput('')
      }
    }
    // If no commas, allow default paste behavior
  }

  const removeValue = (index: number) => {
    onChange(values.filter((_, i) => i !== index))
  }

  return (
    <div>
      {label && <label className="block text-sm font-medium mb-2">{label}</label>}
      <div className="flex gap-2 mb-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addValue())}
          onPaste={handlePaste}
          placeholder={placeholder}
          disabled={disabled}
        />
        <Button
          type="button"
          onClick={addValue}
          disabled={!input.trim() || disabled}
        >
          Add
        </Button>
      </div>
      <p className="text-xs text-gray-500 mb-2">
        Tip: Paste comma-separated values or type values separated by commas
      </p>
      <div className="flex flex-wrap gap-2">
        {values.map((value, index) => (
          <Tag
            key={index}
            value={value}
            onRemove={() => removeValue(index)}
            disabled={disabled}
          />
        ))}
      </div>
    </div>
  )
}
