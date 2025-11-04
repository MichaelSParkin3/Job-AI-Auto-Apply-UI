import { useState } from 'react'
import type { ActionPromptOption, PromptContext } from '@/lib/websocket'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

interface PromptModalProps {
  isOpen: boolean
  promptId: string
  message: string
  options: ActionPromptOption[]
  context?: PromptContext
  onRespond: (action: string) => void
  isLoading?: boolean
}

export function PromptModal({
  isOpen,
  promptId,
  message,
  options,
  context,
  onRespond,
  isLoading = false,
}: PromptModalProps) {
  const [selectedAction, setSelectedAction] = useState<string | null>(null)

  if (!isOpen) return null

  const handleRespond = (action: string) => {
    setSelectedAction(action)
    onRespond(action)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-lg">
        <CardContent className="space-y-6 pt-6">
          {/* Header */}
          <div className="space-y-2">
            <h2 className="text-lg font-semibold text-gray-900">Action Required</h2>
            <p className="text-sm text-gray-700">{message}</p>
          </div>

          {/* Context Information */}
          {context && (
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="space-y-2 pt-4">
                {context.company && (
                  <div>
                    <span className="font-medium text-gray-900">Company:</span>
                    <span className="ml-2 text-gray-700">{context.company}</span>
                  </div>
                )}
                {context.title && (
                  <div>
                    <span className="font-medium text-gray-900">Title:</span>
                    <span className="ml-2 text-gray-700">{context.title}</span>
                  </div>
                )}
                {context.screenshot_path && (
                  <div className="mt-3">
                    <p className="text-sm font-medium text-gray-900 mb-2">Current Form State</p>
                    <img
                      src={context.screenshot_path}
                      alt="Current form"
                      className="max-w-full border rounded bg-white"
                      style={{ maxHeight: '300px' }}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 justify-end flex-wrap">
            {options.map((option) => {
              const isPrimary = option.action === 'submit'
              const isWaiting = isLoading && selectedAction === option.action

              return (
                <Button
                  key={option.action}
                  onClick={() => handleRespond(option.action)}
                  disabled={isLoading}
                  variant={isPrimary ? 'default' : 'outline'}
                  className={isWaiting ? 'opacity-50' : ''}
                >
                  {isWaiting && <span className="mr-2 animate-spin">⟳</span>}
                  {option.label}
                  {option.key && <span className="ml-2 text-xs opacity-70">({option.key})</span>}
                </Button>
              )
            })}
          </div>

          {/* Prompt ID (for debugging) */}
          <p className="text-xs text-gray-400 text-center">Prompt ID: {promptId}</p>
        </CardContent>
      </Card>
    </div>
  )
}
