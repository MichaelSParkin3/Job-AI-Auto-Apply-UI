import {
  ApplicationItem,
  ApplicationStatus,
  Profile,
  JobDetails,
} from '../types/index'

/**
 * Validates an ApplicationStatus value
 */
export const isValidStatus = (
  value: unknown
): value is ApplicationStatus => {
  const validStatuses: ApplicationStatus[] = [
    'NEW',
    'IN_PROGRESS',
    'SUBMITTED',
    'FAILED',
    'CAPTCHA_BLOCKED',
  ]
  return (
    typeof value === 'string' &&
    validStatuses.includes(value as ApplicationStatus)
  )
}

/**
 * Validates an ApplicationItem has required fields
 */
export const isValidApplicationItem = (
  item: unknown
): item is ApplicationItem => {
  if (typeof item !== 'object' || item === null) {
    return false
  }

  const obj = item as Record<string, unknown>

  // Check required fields
  if (!obj.id || typeof obj.id !== 'string') {
    return false
  }
  if (!obj.url || typeof obj.url !== 'string') {
    return false
  }
  if (!obj.company || typeof obj.company !== 'string') {
    return false
  }
  if (!obj.title || typeof obj.title !== 'string') {
    return false
  }
  if (!isValidStatus(obj.status)) {
    return false
  }

  return true
}

/**
 * Validates a Profile has required fields
 */
export const isValidProfile = (
  item: unknown
): item is Profile => {
  if (typeof item !== 'object' || item === null) {
    return false
  }

  const obj = item as Record<string, unknown>

  if (!obj.id || typeof obj.id !== 'string') {
    return false
  }
  if (!obj.name || typeof obj.name !== 'string') {
    return false
  }
  if (
    !obj.resume_path ||
    typeof obj.resume_path !== 'string'
  ) {
    return false
  }

  return true
}

/**
 * Sanitizes an ApplicationItem, filling missing fields with defaults
 */
export const sanitizeApplicationItem = (
  item: unknown
): ApplicationItem | null => {
  if (!isValidApplicationItem(item)) {
    console.warn(
      'Invalid ApplicationItem:',
      item
    )
    return null
  }

  const obj = item as ApplicationItem

  return {
    id: obj.id,
    url: obj.url,
    company: obj.company,
    title: obj.title,
    status: obj.status,
    details: obj.details || undefined,
    artifacts: obj.artifacts || undefined,
    reason: obj.reason || undefined,
    date_discovered: obj.date_discovered || undefined,
    date_applied: obj.date_applied || undefined,
    source_query: obj.source_query || undefined,
    source_rank: obj.source_rank || undefined,
    hash: obj.hash || undefined,
  }
}

/**
 * Validates an array of ApplicationItems
 */
export const validateApplicationItems = (
  items: unknown[]
): ApplicationItem[] => {
  if (!Array.isArray(items)) {
    console.warn('Items is not an array:', items)
    return []
  }

  const validated: ApplicationItem[] = []
  items.forEach((item, index) => {
    const sanitized = sanitizeApplicationItem(item)
    if (sanitized) {
      validated.push(sanitized)
    } else {
      console.warn(
        `Invalid item at index ${index}:`,
        item
      )
    }
  })

  return validated
}

/**
 * Validates a job ID format
 */
export const isValidJobId = (
  jobId: unknown
): jobId is string => {
  return (
    typeof jobId === 'string' && jobId.length > 0
  )
}

/**
 * Validates a profile ID format
 */
export const isValidProfileId = (
  profileId: unknown
): profileId is string => {
  return (
    typeof profileId === 'string' &&
    profileId.length > 0
  )
}

/**
 * Type guard for checking if an object is JobDetails
 */
export const isJobDetails = (
  value: unknown
): value is Partial<JobDetails> => {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  // JobDetails is all optional, so just check it's an object
  return true
}

/**
 * Logs validation warnings for development
 */
export const validateAndLog = (
  items: unknown[],
  source: string
): ApplicationItem[] => {
  const startTime = performance.now()
  const validated = validateApplicationItems(items)
  const duration = performance.now() - startTime

  if (items.length !== validated.length) {
    console.warn(
      `Validation removed ${items.length - validated.length} items from ${source}`
    )
  }

  if (duration > 100) {
    console.warn(
      `Validation took ${duration.toFixed(2)}ms for ${items.length} items (source: ${source})`
    )
  }

  return validated
}
