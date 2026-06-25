import { describe, it, expect, beforeEach } from 'vitest'
import { createTestPinia } from '@/utils/test/pinia'
import { useOperationParamsStore } from '@/store/operationParams'

beforeEach(() => {
  createTestPinia()
})

describe('useOperationParamsStore', () => {
  it('load returns null for unknown datastream id', () => {
    const store = useOperationParamsStore()
    expect(store.load('missing')).toBeNull()
  })

  it('load returns null when given null/undefined id', () => {
    const store = useOperationParamsStore()
    expect(store.load(null)).toBeNull()
    expect(store.load(undefined)).toBeNull()
  })

  it('save then load round-trips a single entry', () => {
    const store = useOperationParamsStore()
    store.save('ds-1', { gapAmount: 10, gapUnit: 'MINUTE' })
    expect(store.load('ds-1')).toEqual({ gapAmount: 10, gapUnit: 'MINUTE' })
  })

  it('save merges patches into existing entry', () => {
    const store = useOperationParamsStore()
    store.save('ds-1', { gapAmount: 10, gapUnit: 'MINUTE' })
    store.save('ds-1', { fillAmount: 5 })
    expect(store.load('ds-1')).toEqual({
      gapAmount: 10,
      gapUnit: 'MINUTE',
      fillAmount: 5,
    })
  })

  it('save overwrites overlapping keys', () => {
    const store = useOperationParamsStore()
    store.save('ds-1', { gapAmount: 10 })
    store.save('ds-1', { gapAmount: 42 })
    expect(store.load('ds-1')).toEqual({ gapAmount: 42 })
  })

  it('save ignores null/undefined datastream id', () => {
    const store = useOperationParamsStore()
    store.save(null, { gapAmount: 1 })
    store.save(undefined, { gapAmount: 2 })
    expect(store.byDatastream).toEqual({})
  })

  it('save on one id does not cross-contaminate another', () => {
    const store = useOperationParamsStore()
    store.save('ds-1', { gapAmount: 10 })
    expect(store.load('ds-2')).toBeNull()
  })
})
