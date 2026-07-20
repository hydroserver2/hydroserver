import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

vi.mock('@/utils/plotting/plotly', () => ({
  setSelectedPoints: vi.fn().mockResolvedValue(undefined),
  clearSelection: vi.fn().mockResolvedValue(undefined),
  handleSelected: vi.fn().mockResolvedValue(undefined),
}))

// Shared ref handles so tests can mutate the stub state between cases
// without needing to re-mock the entire module.
const plotlyRef = ref<any>({ data: [{ id: 'qc', x: [] }] })
const selectedSeries = ref<any>(undefined)

// Stub the Plotly pinia store so `plotlyRef.value.data.length` is deterministic
// and no real Plotly runtime is required.
const suppressedEchoSelection = ref<number[] | null>(null)
vi.mock('@/store/plotly', () => {
  const graphSeriesArray = ref([] as any[])
  return {
    usePlotlyStore: () => ({
      plotlyRef,
      selectedSeries,
      suppressedEchoSelection,
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

// `@uwrl/qc-utils` pulls in heavy browser-only deps (shared-array-buffer
// workers). Stub just the helpers `useDataSelection` touches so the
// import graph stays light and deterministic.
vi.mock('@uwrl/qc-utils', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>
  return {
    ...actual,
    formatDate: (d: Date) => d.toISOString(),
  }
})

describe('useDataSelection.setPlotSelection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Shared ref persists across tests; reset so each test sees the
    // documented "no echo suppression armed" baseline.
    suppressedEchoSelection.value = null
  })

  it('writes the selection array directly to selectedData', async () => {
    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const { setSelectedPoints } = await import('@/utils/plotting/plotly')

    const { setPlotSelection } = useDataSelection()
    await setPlotSelection([3, 5, 7])

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

    const { setPlotSelection, clearSelected } = useDataSelection()

    // Populate via the tested public API to avoid tripping store watchers.
    await setPlotSelection([1, 2, 3])
    expect(useDataVisStore().selectedData).toEqual([1, 2, 3])

    await clearSelected()
    expect(useDataVisStore().selectedData).toEqual([])
  })

  it('clearSelected arms the suppress-echo sentinel with an empty payload', async () => {
    const { useDataSelection } = await import('@/composables/useDataSelection')

    expect(suppressedEchoSelection.value).toBeNull()

    const { clearSelected } = useDataSelection()
    await clearSelected()

    // Payload-keyed sentinel: empty array, not just `true`. handleSelected
    // matches it against the trace's actual selectedpoints to suppress
    // only the genuine echo, not a user gesture that races the debounce.
    expect(suppressedEchoSelection.value).toEqual([])
  })

  it('qcTraceIndex falls back to the trailing trace when no id matches', async () => {
    // No `selectedSeries.id` is set, so the composable should fall back
    // to `data.length - 1`. This exercises the fallback branch in
    // `qcTraceIndex` without needing to match by id.
    plotlyRef.value = {
      data: [{ id: 'other-a' }, { id: 'other-b' }],
    } as any
    selectedSeries.value = undefined

    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { setSelectedPoints } = await import('@/utils/plotting/plotly')

    const { setPlotSelection } = useDataSelection()
    await setPlotSelection([9])

    expect(setSelectedPoints).toHaveBeenCalledWith(
      expect.anything(),
      1, // data.length - 1 fallback
      [9]
    )
  })

  it('setPlotSelection is a no-op when no traces exist', async () => {
    plotlyRef.value = { data: [] } as any
    selectedSeries.value = undefined

    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const { setSelectedPoints } = await import('@/utils/plotting/plotly')

    const { setPlotSelection } = useDataSelection()
    await setPlotSelection([1, 2])

    expect(setSelectedPoints).not.toHaveBeenCalled()
    // When we bail early the store state shouldn't be touched.
    expect(useDataVisStore().selectedData).toBeNull()
  })
})

describe('useDataSelection date-range helpers', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()

    // Seed the plotly ref with a deterministic x-axis so the
    // computeds can look up dates by index without a real Plotly
    // runtime. One-hour spacing over four points lets us pick clear
    // index boundaries for `selectDateRange`.
    const base = new Date('2025-01-01T00:00:00Z').getTime()
    const hour = 60 * 60 * 1000
    const xs = [
      base,
      base + hour,
      base + 2 * hour,
      base + 3 * hour,
    ]
    plotlyRef.value = { data: [{ id: 'qc', x: xs }] } as any

    // The composable reads `dataX` straight off `selectedSeries.data`;
    // handing back the same timestamps keeps the two views consistent.
    selectedSeries.value = {
      id: 'qc',
      data: {
        beginTime: new Date(base),
        endTime: new Date(base + 3 * hour),
        dataX: xs,
      },
    }
  })

  it('startDate / endDate fall back to the series bookends with no selection', async () => {
    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { startDate, endDate } = useDataSelection()

    expect(startDate.value.toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect(endDate.value.toISOString()).toBe('2025-01-01T03:00:00.000Z')
  })

  it('startDate / endDate reflect the selected range when selectedData is set', async () => {
    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.selectedData = [1, 2]

    const { startDate, endDate } = useDataSelection()
    expect(startDate.value.toISOString()).toBe('2025-01-01T01:00:00.000Z')
    expect(endDate.value.toISOString()).toBe('2025-01-01T02:00:00.000Z')
  })

  it('startDateString / endDateString use formatDate on the resolved dates', async () => {
    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { startDateString, endDateString } = useDataSelection()

    // formatDate is stubbed to ISO in the module mock above, so the
    // ternary `startDate.value ? formatDate(...) : ''` should emit an
    // ISO string — the non-empty branch.
    expect(startDateString.value).toBe('2025-01-01T00:00:00.000Z')
    expect(endDateString.value).toBe('2025-01-01T03:00:00.000Z')
  })

  it('selectDateRange selects every point in the inclusive window', async () => {
    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const { setSelectedPoints } = await import('@/utils/plotting/plotly')

    const { selectDateRange } = useDataSelection()
    await selectDateRange(
      new Date('2025-01-01T01:00:00Z'),
      new Date('2025-01-01T02:00:00Z')
    )

    expect(setSelectedPoints).toHaveBeenCalledWith(
      expect.anything(),
      0, // trace id === 'qc', matched at index 0
      [1, 2]
    )
    expect(useDataVisStore().selectedData).toEqual([1, 2])
  })

  it('selectDateRange bails out when the range is inverted', async () => {
    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { setSelectedPoints } = await import('@/utils/plotting/plotly')

    const { selectDateRange } = useDataSelection()
    // `to` earlier than `from` — startIdx > endIdx, should no-op.
    await selectDateRange(
      new Date('2025-01-01T03:00:00Z'),
      new Date('2025-01-01T00:30:00Z')
    )

    expect(setSelectedPoints).not.toHaveBeenCalled()
  })

  it('selectDateRange bails out when the series has no data', async () => {
    selectedSeries.value = {
      id: 'qc',
      data: {
        beginTime: null,
        endTime: null,
        dataX: [],
      },
    }

    const { useDataSelection } = await import('@/composables/useDataSelection')
    const { setSelectedPoints } = await import('@/utils/plotting/plotly')

    const { selectDateRange } = useDataSelection()
    await selectDateRange(
      new Date('2025-01-01T00:00:00Z'),
      new Date('2025-01-01T03:00:00Z')
    )

    expect(setSelectedPoints).not.toHaveBeenCalled()
  })
})
