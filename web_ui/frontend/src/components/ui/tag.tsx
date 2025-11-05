import { X } from 'lucide-react'

interface TagProps {
  value: string
  onRemove: () => void
  disabled?: boolean
}

export function Tag({ value, onRemove, disabled }: TagProps) {
  return (
    <div className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-900 rounded">
      <span className="text-sm">{value}</span>
      <button
        type="button"
        onClick={onRemove}
        disabled={disabled}
        className="text-blue-600 hover:text-blue-800 disabled:opacity-50"
      >
        <X size={16} />
      </button>
    </div>
  )
}
