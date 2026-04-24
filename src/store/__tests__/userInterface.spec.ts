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
  useOperationParamsStore: () => ({}),
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
