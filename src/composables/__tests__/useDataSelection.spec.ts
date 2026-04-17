import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

vi.mock('@/utils/plotting/plotly', () => ({
  setSelectedPoints: vi.fn().mockResolvedValue(undefined),
  clearSelection: vi.fn().mockResolvedValue(undefined),
  handleSelected: vi.fn().mockResolvedValue(undefined),
}))

// Stub the Plotly pinia store so `plotlyRef.value.data.length` is deterministic
// and no real Plotly runtime is required.
vi.mock('@/store/plotly', () => {
  const plotlyRef = ref({ data: [{ id: 'qc' }] } as any)
  const selectedSeries = ref(undefined as any)
  const graphSeriesArray = ref([] as any[])
  return {
    usePlotlyStore: () => ({
      plotlyRef,
      selectedSeries,
      graphSeriesArray,
      updateOptions: vi.fn(),
      clearChartState: vi.fn(),
      fetchGraphSeries: vi.fn().mockResolvedValue(undefined),
    }),
  }
})

vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({
    fetchObservationsInRange: vi.fn().mockResolvedValue(undefined),
  }),
}))

describe('useDataSelection.dispatchSelection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('writes the selection array directly to selectedData', async () => {
    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const { setSelectedPoints } = await import('@/utils/plotting/plotly')

    const { dispatchSelection } = useDataSelection()
    await dispatchSelection([3, 5, 7])

    expect(useDataVisStore().selectedData).toEqual([3, 5, 7])
    expect(setSelectedPoints).toHaveBeenCalledWith(
      expect.anything(), // plotlyRef.value (the stub gd)
      0, // traceIndex = data.length - 1
      [3, 5, 7]
    )
  })

  it('clearSelected resets selectedData to an empty array', async () => {
    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { useDataVisStore } = await import('@/store/dataVisualization')

    const { dispatchSelection, clearSelected } = useDataSelection()

    // Populate via the tested public API to avoid tripping store watchers.
    await dispatchSelection([1, 2, 3])
    expect(useDataVisStore().selectedData).toEqual([1, 2, 3])

    await clearSelected()
    expect(useDataVisStore().selectedData).toEqual([])
  })
})
