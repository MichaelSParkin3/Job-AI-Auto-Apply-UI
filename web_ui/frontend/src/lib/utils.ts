import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Merge Tailwind CSS classes with clsx and tailwind-merge.
 * Handles both className strings and conditional classes.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format bytes to human-readable size.
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Format date to human-readable string.
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

/**
 * Get status badge color.
 */
export function getStatusColor(
  status: 'NEW' | 'IN_PROGRESS' | 'SUBMITTED' | 'FAILED' | 'CAPTCHA_BLOCKED'
): string {
  const colors = {
    NEW: 'bg-blue-100 text-blue-800',
    IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
    SUBMITTED: 'bg-green-100 text-green-800',
    FAILED: 'bg-red-100 text-red-800',
    CAPTCHA_BLOCKED: 'bg-orange-100 text-orange-800',
  }
  return colors[status]
}
