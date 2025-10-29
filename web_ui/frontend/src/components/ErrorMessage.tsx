import React from 'react'
import { cn } from '../lib/utils'
import { Button } from './Button'

interface ErrorMessageProps {
  error: Error | string | null
  onRetry?: () => void
  dismissible?: boolean
  onDismiss?: () => void
}

export const ErrorMessage: React.FC<
  ErrorMessageProps
> = ({
  error,
  onRetry,
  dismissible = false,
  onDismiss,
}) => {
  if (!error) return null

  const errorMessage =
    typeof error === 'string'
      ? error
      : error instanceof Error
        ? error.message
        : 'An unexpected error occurred'

  return (
    <div
      className={cn(
        'p-4 bg-red-50 border border-red-200 rounded-lg',
        'flex items-start gap-4'
      )}
      role="alert"
    >
      <div className="text-2xl">⚠️</div>
      <div className="flex-1">
        <h3 className="font-semibold text-red-900 mb-1">
          Error
        </h3>
        <p className="text-red-800 text-sm">
          {errorMessage}
        </p>
        <div className="flex gap-2 mt-3">
          {onRetry && (
            <Button
              size="sm"
              variant="destructive"
              onClick={onRetry}
            >
              Retry
            </Button>
          )}
          {dismissible && onDismiss && (
            <Button
              size="sm"
              variant="outline"
              onClick={onDismiss}
            >
              Dismiss
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
