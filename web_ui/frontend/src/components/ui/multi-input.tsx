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

  const addValue = () => {
    if (input.trim() && !values.includes(input.trim())) {
      onChange([...values, input.trim()])
      setInput('')
    }
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
