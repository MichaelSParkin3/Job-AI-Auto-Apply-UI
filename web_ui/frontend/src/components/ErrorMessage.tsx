import React from 'react'
import { cn } from '../lib/utils'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'

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
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <div className="flex-1">
        <AlertDescription className="mt-2">
          <p className="font-semibold mb-2">Error</p>
          <p className="text-sm mb-3">{errorMessage}</p>
          <div className="flex gap-2">
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
        </AlertDescription>
      </div>
    </Alert>
  )
}
