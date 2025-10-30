import { RunConfiguration } from '../types/index'

const STORAGE_PREFIX = 'job_apply_'
const ACTIVE_PROFILE_KEY = `${STORAGE_PREFIX}active_profile`
const UI_STATE_KEY = `${STORAGE_PREFIX}ui_state_`
const RUN_OPTIONS_KEY = `${STORAGE_PREFIX}run_options_`

class StorageService {
  getUIState(key: string): any {
    try {
      const item = localStorage.getItem(
        `${UI_STATE_KEY}${key}`
      )
      return item ? JSON.parse(item) : null
    } catch (e) {
      console.error(
        `Failed to get UI state for ${key}:`,
        e
      )
      return null
    }
  }

  setUIState(key: string, value: any): void {
    try {
      localStorage.setItem(
        `${UI_STATE_KEY}${key}`,
        JSON.stringify(value)
      )
    } catch (e) {
      if (
        e instanceof DOMException &&
        e.code === 22
      ) {
        console.warn(
          'localStorage quota exceeded'
        )
      } else {
        console.error(
          `Failed to set UI state for ${key}:`,
          e
        )
      }
    }
  }

  getRunOptions(
    profileId: string,
    operationType: string
  ): Partial<RunConfiguration> | null {
    try {
      const item = localStorage.getItem(
        `${RUN_OPTIONS_KEY}${profileId}_${operationType}`
      )
      return item ? JSON.parse(item) : null
    } catch (e) {
      console.error(
        `Failed to get run options for ${profileId}/${operationType}:`,
        e
      )
      return null
    }
  }

  setRunOptions(
    profileId: string,
    operationType: string,
    options: Partial<RunConfiguration>
  ): void {
    try {
      localStorage.setItem(
        `${RUN_OPTIONS_KEY}${profileId}_${operationType}`,
        JSON.stringify(options)
      )
    } catch (e) {
      if (
        e instanceof DOMException &&
        e.code === 22
      ) {
        console.warn(
          'localStorage quota exceeded'
        )
      } else {
        console.error(
          `Failed to set run options for ${profileId}/${operationType}:`,
          e
        )
      }
    }
  }

  getActiveProfile(): string | null {
    try {
      return localStorage.getItem(
        ACTIVE_PROFILE_KEY
      )
    } catch (e) {
      console.error(
        'Failed to get active profile:',
        e
      )
      return null
    }
  }

  setActiveProfile(profileId: string): void {
    try {
      localStorage.setItem(
        ACTIVE_PROFILE_KEY,
        profileId
      )
    } catch (e) {
      console.error(
        'Failed to set active profile:',
        e
      )
    }
  }

  clearUIState(key: string): void {
    try {
      localStorage.removeItem(`${UI_STATE_KEY}${key}`)
    } catch (e) {
      console.error(
        `Failed to clear UI state for ${key}:`,
        e
      )
    }
  }

  clearRunOptions(
    profileId: string,
    operationType: string
  ): void {
    try {
      localStorage.removeItem(
        `${RUN_OPTIONS_KEY}${profileId}_${operationType}`
      )
    } catch (e) {
      console.error(
        `Failed to clear run options for ${profileId}/${operationType}:`,
        e
      )
    }
  }

  clearAll(): void {
    try {
      const keys = Object.keys(localStorage)
      keys.forEach((key) => {
        if (
          key.startsWith(STORAGE_PREFIX)
        ) {
          localStorage.removeItem(key)
        }
      })
    } catch (e) {
      console.error(
        'Failed to clear all storage:',
        e
      )
    }
  }
}

export const storage =
  new StorageService()
