import { useState, useRef } from 'react'
import { Upload, X } from 'lucide-react'
import { Button } from './button'

interface FileUploadProps {
  profileId?: string
  currentPath?: string
  onUploadComplete: (path: string, filename: string) => void
  disabled?: boolean
  accept?: string
  label?: string
  maxSize?: number
}

export function FileUpload({
  profileId: _profileId,
  currentPath,
  onUploadComplete,
  disabled,
  accept = '.pdf',
  label = 'Upload File',
  maxSize = 10 * 1024 * 1024, // 10MB default
}: FileUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setError(null)
    setUploading(true)

    try {
      // Validate file size
      if (file.size > maxSize) {
        throw new Error(
          `File size exceeds maximum allowed (${maxSize / 1024 / 1024}MB)`,
        )
      }

      // For now, just store the path locally
      // In the actual implementation with backend, we would upload here
      const path = `resumes/${file.name}`
      onUploadComplete(path, file.name)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      setError(message)
    } finally {
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div className="space-y-2">
      {currentPath && (
        <div className="flex items-center justify-between text-sm text-gray-600 bg-gray-50 p-2 rounded">
          <span>Current: {currentPath}</span>
          <button
            type="button"
            onClick={() => onUploadComplete('', '')}
            className="text-gray-400 hover:text-gray-600"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
          {error}
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleFileSelect}
        disabled={disabled || uploading}
        className="hidden"
      />

      <Button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={disabled || uploading}
        className="w-full"
      >
        <Upload className="w-4 h-4 mr-2" />
        {uploading ? 'Uploading...' : label}
      </Button>
    </div>
  )
}
