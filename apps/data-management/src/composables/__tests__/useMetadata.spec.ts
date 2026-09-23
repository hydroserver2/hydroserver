import { describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { effectScope } from 'vue'
import { ObservedProperty } from '@hydroserver/client'
import { useMetadata } from '../useMetadata'

vi.mock('@/store/workspaces', async () => {
  const { defineStore } = await import('pinia')
  return {
    useWorkspaceStore: defineStore('metadata-test-workspace', {
      state: () => ({ selectedWorkspace: null }),
    }),
  }
})

describe('observed property dropdown labels', () => {
  it('distinguishes properties by name and type without displaying optional codes', () => {
    setActivePinia(createPinia())
    const scope = effectScope()
    try {
      const metadata = scope.run(() => useMetadata())!
      metadata.observedProperties.value = [
        Object.assign(new ObservedProperty(), {
          name: 'Temperature', type: 'Water', code: 'W-TEMP',
        }),
        Object.assign(new ObservedProperty(), {
          name: 'Temperature', type: 'Air', code: null,
        }),
      ]
      expect(metadata.formattedObservedProperties.value.map((item) => item.title)).toEqual([
        'Temperature, Air',
        'Temperature, Water',
      ])
    } finally {
      scope.stop()
    }
  })
})
