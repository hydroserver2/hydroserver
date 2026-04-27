import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

// --- Light stubs to keep the import graph deterministic.

const plotlyRef = ref<any>({ data: [{ id: 'qc' }] })
const selectedSeries = ref<any>({
  data: { dispatchFilter: vi.fn().mockResolvedValue([]) },
})
const isUpdating = ref(false)

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ plotlyRef, selectedSeries, isUpdating }),
}))

vi.mock('@/composables/useDataSelection', () => ({
  useDataSelection: () => ({
    setPlotSelection: vi.fn().mockResolvedValue(undefined),
    clearSelected: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@uwrl/qc-utils', () => ({
  EnumFilterOperations: {
    PERSISTENCE: 'PERSISTENCE',
    CHANGE: 'CHANGE',
    RATE_OF_CHANGE: 'RATE_OF_CHANGE',
    VALUE_THRESHOLD: 'VALUE_THRESHOLD',
    FIND_GAPS: 'FIND_GAPS',
    DATETIME_RANGE: 'DATETIME_RANGE',
    SELECTION: 'SELECTION',
  },
  // useUIStore (transitively imported via getActiveFilterRange)
  // pulls these enums from qc-utils.
  Operator: { ADD: 'ADD', SUB: 'SUB', MULT: 'MULT', DIV: 'DIV', ASSIGN: 'ASSIGN' },
  LogicalOperation: {
    LT: 'Less than',
    LTE: 'Less than or equal to',
    GT: 'Greater than',
    GTE: 'Greater than or equal to',
    E: 'Equal',
  },
  TimeUnit: {
    SECOND: 's',
    MINUTE: 'm',
    HOUR: 'h',
    DAY: 'D',
    WEEK: 'W',
    MONTH: 'M',
    YEAR: 'Y',
  },
}))

// Stubs for the data-vis store + observation store referenced by
// `useDataSelection`'s static imports.
vi.mock('@/store/dataVisualization', () => {
  const { ref } = require('vue') as typeof import('vue')
  const selectedData = ref<number[] | null>(null)
  const hasSelectionShape = ref(false)
  return {
    useDataVisStore: () => ({ selectedData, hasSelectionShape }),
  }
})

vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({
    fetchObservationsInRange: vi.fn().mockResolvedValue(undefined),
  }),
}))

vi.mock('@/store/operationParams', () => ({
  useOperationParamsStore: () => ({}),
}))

describe('useFilterDispatch.getActiveFilterRange', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  const useStores = async () => {
    const { useFilterDispatch } = await import(
      '@/composables/useFilterDispatch'
    )
    const { useUIStore } = await import('@/store/userInterface')
    return { dispatch: useFilterDispatch(), ui: useUIStore() }
  }

  it('returns undefined when filterRangeActive is false', async () => {
    const { dispatch, ui } = await useStores()
    ui.filterRangeActive = false
    ui.filterRangeFromTs = 100
    ui.filterRangeToTs = 200
    expect(dispatch.getActiveFilterRange()).toBeUndefined()
  })

  it('returns the [from, to] tuple when active with valid bounds', async () => {
    const { dispatch, ui } = await useStores()
    ui.filterRangeActive = true
    ui.filterRangeFromTs = 100
    ui.filterRangeToTs = 200
    expect(dispatch.getActiveFilterRange()).toEqual([100, 200])
  })

  it('returns undefined when active but bounds are null', async () => {
    const { dispatch, ui } = await useStores()
    ui.filterRangeActive = true
    ui.filterRangeFromTs = null
    ui.filterRangeToTs = null
    expect(dispatch.getActiveFilterRange()).toBeUndefined()
  })

  it('returns undefined when active but from >= to (degenerate window)', async () => {
    const { dispatch, ui } = await useStores()
    ui.filterRangeActive = true
    ui.filterRangeFromTs = 500
    ui.filterRangeToTs = 500
    expect(dispatch.getActiveFilterRange()).toBeUndefined()
    ui.filterRangeToTs = 100 // inverted
    expect(dispatch.getActiveFilterRange()).toBeUndefined()
  })

  it('returns undefined when bounds are non-finite', async () => {
    const { dispatch, ui } = await useStores()
    ui.filterRangeActive = true
    ui.filterRangeFromTs = NaN
    ui.filterRangeToTs = 200
    expect(dispatch.getActiveFilterRange()).toBeUndefined()
    ui.filterRangeFromTs = 100
    ui.filterRangeToTs = Infinity
    expect(dispatch.getActiveFilterRange()).toBeUndefined()
  })
})

describe('useFilterDispatch.dispatchFilter', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    isUpdating.value = false
  })

  it('forwards args verbatim to the series dispatchFilter', async () => {
    const { useFilterDispatch } = await import(
      '@/composables/useFilterDispatch'
    )
    const { dispatchFilter } = useFilterDispatch()
    selectedSeries.value.data.dispatchFilter.mockResolvedValueOnce([1, 2, 3])
    const out = await dispatchFilter('PERSISTENCE' as any, 5, [10, 20])
    expect(selectedSeries.value.data.dispatchFilter).toHaveBeenCalledWith(
      'PERSISTENCE',
      5,
      [10, 20],
    )
    expect(out).toEqual([1, 2, 3])
  })

  it('flips isUpdating during the call', async () => {
    const { useFilterDispatch } = await import(
      '@/composables/useFilterDispatch'
    )
    const { dispatchFilter } = useFilterDispatch()
    let observed = false
    selectedSeries.value.data.dispatchFilter.mockImplementationOnce(
      async () => {
        observed = isUpdating.value
        return []
      },
    )
    await dispatchFilter('CHANGE' as any, 'Greater than', 1)
    expect(observed).toBe(true)
    expect(isUpdating.value).toBe(false)
  })

  it('returns [] when no series is loaded', async () => {
    const orig = selectedSeries.value
    selectedSeries.value = undefined
    try {
      const { useFilterDispatch } = await import(
        '@/composables/useFilterDispatch'
      )
      const { dispatchFilter } = useFilterDispatch()
      const out = await dispatchFilter('CHANGE' as any, 'Greater than', 1)
      expect(out).toEqual([])
    } finally {
      selectedSeries.value = orig
    }
  })
})
