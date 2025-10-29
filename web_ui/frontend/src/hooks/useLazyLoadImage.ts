import { useEffect, useRef, useState } from 'react'

interface UseLazyLoadImageOptions {
  threshold?: number
  rootMargin?: string
}

/**
 * Hook for lazy loading images using Intersection Observer API
 *
 * @param options Configuration options for Intersection Observer
 * @returns Object with ref to attach to image and isVisible state
 */
export const useLazyLoadImage = (
  options: UseLazyLoadImageOptions = {}
) => {
  const imageRef = useRef<HTMLImageElement>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsVisible(true)
        // Stop observing once image is visible
        if (imageRef.current) {
          observer.unobserve(imageRef.current)
        }
      }
    }, {
      threshold: options.threshold || 0.1,
      rootMargin: options.rootMargin || '50px',
    })

    if (imageRef.current) {
      observer.observe(imageRef.current)
    }

    return () => {
      observer.disconnect()
    }
  }, [options.threshold, options.rootMargin])

  return { imageRef, isVisible }
}
