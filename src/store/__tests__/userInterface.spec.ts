import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, beforeEach, vi } from 'vitest'

const { qcDatastreamRef } = vi.hoisted(() => {
  const { ref } = require('vue') as typeof import('vue')
  return { qcDatastreamRef: ref<{ id: string } | null>(null) }
})

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ qcDatastream: qcDatastreamRef }),
}))
vi.mock('@/store/operationParams', () => ({
  useOperationParamsStore: () => ({ load: () => null, save: () => {} }),
}))
vi.mock('@uwrl/qc-utils', () => ({
  TimeUnit: { SECOND: 's', MINUTE: 'm', HOUR: 'h', DAY: 'D', WEEK: 'W', MONTH: 'M', YEAR: 'Y' },
  Operator: { ADD: 'ADD', SUB: 'SUB', MULT: 'MULT', DIV: 'DIV', ASSIGN: 'ASSIGN' },
  LogicalOperation: { LT: 'Less than', LTE: 'Less than or equal to', GT: 'Greater than', GTE: 'Greater than or equal to', E: 'Equal' },
}))

import { useUIStore, DrawerType, timeSpacingUnitToTimeUnitKey } from '@/store/userInterface'

describe('timeSpacingUnitToTimeUnitKey', () => {
  it('maps seconds', () => expect(timeSpacingUnitToTimeUnitKey('seconds')).toBe('SECOND'))
  it('maps minutes', () => expect(timeSpacingUnitToTimeUnitKey('minutes')).toBe('MINUTE'))
  it('maps hours', () => expect(timeSpacingUnitToTimeUnitKey('hours')).toBe('HOUR'))
  it('maps days', () => expect(timeSpacingUnitToTimeUnitKey('days')).toBe('DAY'))
  it('returns null for unknown', () => expect(timeSpacingUnitToTimeUnitKey('weeks')).toBeNull())
  it('returns null for null', () => expect(timeSpacingUnitToTimeUnitKey(null)).toBeNull())
})

describe('useUIStore drawer', () => {
  beforeEach(() => { setActivePinia(createPinia()); qcDatastreamRef.value = null })

  it('defaults to Select drawer open', () => {
    const store = useUIStore()
    expect(store.selectedDrawer).toBe(DrawerType.Select)
    expect(store.isDrawerOpen).toBe(true)
  })
  it('onRailItemClicked switches drawer', () => {
    const store = useUIStore()
    store.onRailItemClicked(DrawerType.Edit)
    expect(store.selectedDrawer).toBe(DrawerType.Edit)
  })
  it('onRailItemClicked same drawer toggles closed', () => {
    const store = useUIStore()
    store.onRailItemClicked(DrawerType.Select)
    expect(store.isDrawerOpen).toBe(false)
  })
  it('onRailItemClicked same drawer twice re-opens', () => {
    const store = useUIStore()
    store.onRailItemClicked(DrawerType.Select)
    store.onRailItemClicked(DrawerType.Select)
    expect(store.isDrawerOpen).toBe(true)
  })
})

describe('useUIStore defaults', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('operators from Operator enum keys', () => expect(useUIStore().operators).toContain('ADD'))
  it('selectedOperator defaults to 0', () => expect(useUIStore().selectedOperator).toBe(0))
  it('gapAmount defaults to 15', () => expect(useUIStore().gapAmount).toBe(15))
  it('fillAmount defaults to 15', () => expect(useUIStore().fillAmount).toBe(15))
  it('shiftAmount defaults to 15', () => expect(useUIStore().shiftAmount).toBe(15))
  it('noDataValue defaults to -9999', () => expect(useUIStore().noDataValue).toBe(-9999))
})

describe('useUIStore qcDatastream watcher', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    qcDatastreamRef.value = null
  })

  it('seeds gap/fill/noDataValue from intended cadence + noDataValue', async () => {
    const store = useUIStore()
    qcDatastreamRef.value = {
      id: 'ds-1',
      intendedTimeSpacing: 5,
      intendedTimeSpacingUnit: 'minutes',
      noDataValue: -8888,
    } as any
    // Vue's `watch` is sync for refs by default; the immediate
    // option already fired with `null`. Now wait a microtask so
    // the change-driven invocation lands before assertions.
    await Promise.resolve()
    expect(store.gapAmount).toBe(5)
    expect(store.selectedGapUnit).toBe('MINUTE')
    expect(store.fillAmount).toBe(5)
    expect(store.selectedFillUnit).toBe('MINUTE')
    expect(store.noDataValue).toBe(-8888)
  })

  it('leaves form state alone when intended cadence is missing', async () => {
    const store = useUIStore()
    const initialGap = store.gapAmount
    const initialFill = store.fillAmount
    const initialNd = store.noDataValue
    qcDatastreamRef.value = {
      id: 'ds-2',
      // Missing `intendedTimeSpacing` / unit / noDataValue.
    } as any
    await Promise.resolve()
    expect(store.gapAmount).toBe(initialGap)
    expect(store.fillAmount).toBe(initialFill)
    expect(store.noDataValue).toBe(initialNd)
  })

  it('skips entirely when datastream is reset to null', async () => {
    const store = useUIStore()
    store.gapAmount = 42
    qcDatastreamRef.value = null
    await Promise.resolve()
    // Watcher's early-out (`if (!ds) return`) keeps the user's value.
    expect(store.gapAmount).toBe(42)
  })
})

describe('useUIStore filter range', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('filterRangeActive defaults to false', () => {
    expect(useUIStore().filterRangeActive).toBe(false)
  })
  it('filterRangeFromTs / filterRangeToTs default to null', () => {
    const store = useUIStore()
    expect(store.filterRangeFromTs).toBeNull()
    expect(store.filterRangeToTs).toBeNull()
  })
  it('filterRangeActive is reactive', () => {
    const store = useUIStore()
    store.filterRangeActive = true
    expect(store.filterRangeActive).toBe(true)
    store.filterRangeActive = false
    expect(store.filterRangeActive).toBe(false)
  })
  it('filter range timestamps accept numeric values', () => {
    const store = useUIStore()
    store.filterRangeFromTs = 1_000
    store.filterRangeToTs = 2_000
    expect(store.filterRangeFromTs).toBe(1_000)
    expect(store.filterRangeToTs).toBe(2_000)
  })
})
