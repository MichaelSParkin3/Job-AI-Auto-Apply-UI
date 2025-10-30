import React, { Component, ReactNode } from 'react'
import { logger } from '../services/logger'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AlertCircle } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
    }
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    logger.error('React Error Boundary caught an error', error, {
      componentStack: errorInfo.componentStack,
    })
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <h2 className="text-lg font-semibold mb-2">
                Something went wrong
              </h2>
              <p className="text-sm mb-4">
                {this.state.error?.message}
              </p>
              <Button
                variant="destructive"
                size="sm"
                onClick={this.handleReset}
              >
                Try again
              </Button>
            </AlertDescription>
          </Alert>
        </div>
      )
    }

    return this.props.children
  }
}
