import type { LabelHTMLAttributes } from 'react'
import { forwardRef } from 'react'

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {}

const Label = forwardRef<HTMLLabelElement, LabelProps>(({ className = '', ...props }, ref) => (
  <label
    ref={ref}
    className={`block text-sm font-medium text-gray-700 mb-1 ${className}`}
    {...props}
  />
))

Label.displayName = 'Label'

export { Label }
