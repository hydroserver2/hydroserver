import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

vi.mock('@uwrl/qc-utils', () => ({
  EnumFilterOperations: { SELECTION: 'SELECTION' },
}))

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({
    plotlyRef: ref(null),
    selectedSeries: ref(null),
    isUpdating: ref(false),
    editHistory: ref([]),
    suppressSelectionEchoUntil: ref(0),
  }),
}))

vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({
    selectedData: ref(null),
    qcDatastream: ref(null),
  }),
}))

import { handleSelected } from '../selected'

describe('selected.ts smoke', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('exports handleSelected as a function', () => {
    expect(typeof handleSelected).toBe('function')
  })

  it('does not throw when called with undefined and plotlyRef is null', async () => {
    await expect(handleSelected(undefined)).resolves.toBeUndefined()
  })

  it('does not throw when called with null', async () => {
    await expect(handleSelected(null)).resolves.toBeUndefined()
  })
})
