import { afterEach, describe, expect, it } from 'vitest'
import { settings } from '@/config/settings'
import { isOrchestrationEnabled } from '../orchestrationAvailability'

describe('isOrchestrationEnabled', () => {
  const original = settings.extensionsConfiguration.orchestrationEnabled

  afterEach(() => {
    settings.extensionsConfiguration.orchestrationEnabled = original
  })

  it('defaults to enabled', () => {
    expect(isOrchestrationEnabled()).toBe(true)
  })

  it('follows the server setting', () => {
    settings.extensionsConfiguration.orchestrationEnabled = false
    expect(isOrchestrationEnabled()).toBe(false)

    settings.extensionsConfiguration.orchestrationEnabled = true
    expect(isOrchestrationEnabled()).toBe(true)
  })
})
