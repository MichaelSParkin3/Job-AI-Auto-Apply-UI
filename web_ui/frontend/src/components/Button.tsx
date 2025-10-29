import React from 'react'
import { cn } from '../lib/utils'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'default',
      size = 'md',
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium rounded-md transition-colors'

    const variantStyles = {
      default: 'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50',
      secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/90 disabled:opacity-50',
      destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50',
      outline: 'border border-input bg-background hover:bg-accent disabled:opacity-50',
    }

    const sizeStyles = {
      sm: 'h-8 px-3 text-sm',
      md: 'h-10 px-4 text-base',
      lg: 'h-12 px-6 text-lg',
    }

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {isLoading ? <span className="animate-spin mr-2">⏳</span> : null}
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'
