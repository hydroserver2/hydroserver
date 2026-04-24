import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

// Shared mutable stub state so each test can reset between runs.
const mockPlotlyRef = ref<any>(null)
const mockGraphSeriesArray = ref<any[]>([])
const mockUpdateOptions = vi.fn()
const mockClearChartState = vi.fn()
const mockClearZoomHistory = vi.fn()
const mockFetchGraphSeries = vi.fn().mockResolvedValue({ id: 'stub', data: {} })
const mockRedraw = vi.fn()
const mockFetchObservationsInRange = vi
  .fn()
  .mockResolvedValue({ id: 'stub', data: {} })

vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({
    plotlyRef: mockPlotlyRef,
    graphSeriesArray: mockGraphSeriesArray,
    updateOptions: mockUpdateOptions,
    clearChartState: mockClearChartState,
    clearZoomHistory: mockClearZoomHistory,
    fetchGraphSeries: mockFetchGraphSeries,
    redraw: mockRedraw,
  }),
}))

vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({
    fetchObservationsInRange: mockFetchObservationsInRange,
  }),
}))

// handleNewPlot touches DOM / Plotly; stub everything the store imports.
vi.mock('@/utils/plotting/plotly', () => ({
  handleNewPlot: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('@uwrl/qc-utils', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>
  return {
    ...actual,
    Snackbar: { error: vi.fn(), success: vi.fn(), info: vi.fn() },
  }
})

const makeDs = (overrides: Record<string, any> = {}) => ({
  id: 'ds-1',
  name: 'Stream 1',
  thing: { id: 'thing-1' },
  observedProperty: { name: 'Temperature' },
  processingLevel: { definition: 'Raw' },
  ...overrides,
})

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockPlotlyRef.value = null
  mockGraphSeriesArray.value = []
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useDataVisStore.filteredDatastreams', () => {
  it('returns all datastreams when no filters are applied', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.datastreams = [
      makeDs({ id: 'a' }),
      makeDs({ id: 'b', thing: { id: 'thing-2' } }),
    ] as any
    expect(store.filteredDatastreams).toHaveLength(2)
  })

  it('filters by selected things', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.datastreams = [
      makeDs({ id: 'a', thing: { id: 'thing-1' } }),
      makeDs({ id: 'b', thing: { id: 'thing-2' } }),
    ] as any
    store.selectedThings = [{ id: 'thing-1' }] as any
    const ids = store.filteredDatastreams.map((d) => d.id)
    expect(ids).toEqual(['a'])
  })

  it('filters by observed property name', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.datastreams = [
      makeDs({ id: 'a', observedProperty: { name: 'Temperature' } }),
      makeDs({ id: 'b', observedProperty: { name: 'Pressure' } }),
    ] as any
    store.selectedObservedPropertyNames = ['Pressure']
    expect(store.filteredDatastreams.map((d) => d.id)).toEqual(['b'])
  })

  it('filters by processing level definition', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.datastreams = [
      makeDs({ id: 'a', processingLevel: { definition: 'Raw' } }),
      makeDs({ id: 'b', processingLevel: { definition: 'QC' } }),
    ] as any
    store.selectedProcessingLevelNames = ['QC']
    expect(store.filteredDatastreams.map((d) => d.id)).toEqual(['b'])
  })

  it('returns empty array when filter matches nothing', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.datastreams = [makeDs({ id: 'a' })] as any
    store.selectedThings = [{ id: 'nope' }] as any
    expect(store.filteredDatastreams).toEqual([])
  })

  it('intersects multiple active filters', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.datastreams = [
      makeDs({
        id: 'a',
        thing: { id: 'thing-1' },
        observedProperty: { name: 'Temperature' },
      }),
      makeDs({
        id: 'b',
        thing: { id: 'thing-1' },
        observedProperty: { name: 'Pressure' },
      }),
      makeDs({
        id: 'c',
        thing: { id: 'thing-2' },
        observedProperty: { name: 'Temperature' },
      }),
    ] as any
    store.selectedThings = [{ id: 'thing-1' }] as any
    store.selectedObservedPropertyNames = ['Temperature']
    expect(store.filteredDatastreams.map((d) => d.id)).toEqual(['a'])
  })

  it('returns [] safely when datastreams is cleared to null/undefined', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    ;(store as any).datastreams = null
    expect(store.filteredDatastreams).toEqual([])
  })

  it('skips datastreams missing thing/observedProperty/processingLevel when filtered', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.datastreams = [
      makeDs({ id: 'noThing', thing: undefined }),
      makeDs({ id: 'noOp', observedProperty: undefined }),
      makeDs({ id: 'noPl', processingLevel: undefined }),
    ] as any

    store.selectedThings = [{ id: 'thing-1' }] as any
    expect(store.filteredDatastreams.map((d) => d.id)).toEqual(['noOp', 'noPl'])

    store.selectedThings = []
    store.selectedObservedPropertyNames = ['Temperature']
    expect(store.filteredDatastreams.map((d) => d.id)).toEqual(['noThing', 'noPl'])

    store.selectedObservedPropertyNames = []
    store.selectedProcessingLevelNames = ['Raw']
    expect(store.filteredDatastreams.map((d) => d.id)).toEqual(['noThing', 'noOp'])
  })
})

describe('useDataVisStore.qcDatastream', () => {
  it('resolves the plotted datastream matching qcDatastreamId', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'a' }), makeDs({ id: 'b' })] as any
    store.qcDatastreamId = 'b'
    expect(store.qcDatastream?.id).toBe('b')
  })

  it('returns null when qcDatastreamId is unset', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'a' })] as any
    expect(store.qcDatastream).toBeNull()
  })

  it('returns null when qcDatastreamId is set but not in plottedDatastreams', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'a' })] as any
    store.qcDatastreamId = 'missing'
    expect(store.qcDatastream).toBeNull()
  })
})

describe('useDataVisStore.plotDatastream', () => {
  it('adds the datastream and auto-elects it as qc when none set', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.plotDatastream(makeDs({ id: 'a' }) as any)
    expect(store.plottedDatastreams.map((d) => d.id)).toEqual(['a'])
    expect(store.qcDatastreamId).toBe('a')
  })

  it('does not change qcDatastreamId when plotting a second datastream', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.plotDatastream(makeDs({ id: 'a' }) as any)
    await store.plotDatastream(makeDs({ id: 'b' }) as any)
    expect(store.plottedDatastreams).toHaveLength(2)
    expect(store.qcDatastreamId).toBe('a')
  })

  it('is idempotent when the datastream is already plotted', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    const ds = makeDs({ id: 'a' }) as any
    await store.plotDatastream(ds)
    await store.plotDatastream(ds)
    expect(store.plottedDatastreams).toHaveLength(1)
  })
})

describe('useDataVisStore.unplotDatastream', () => {
  it('removes the datastream and promotes the previous entry to qc when removing qc', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.plotDatastream(makeDs({ id: 'a' }) as any)
    await store.plotDatastream(makeDs({ id: 'b' }) as any)
    // qc = 'a'; removing 'a' promotes the datastream at max(0-1,0)=0, now 'b'.
    await store.unplotDatastream('a')
    expect(store.plottedDatastreams.map((d) => d.id)).toEqual(['b'])
    expect(store.qcDatastreamId).toBe('b')
  })

  it('leaves qcDatastreamId untouched when removing a non-qc datastream', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.plotDatastream(makeDs({ id: 'a' }) as any)
    await store.plotDatastream(makeDs({ id: 'b' }) as any)
    await store.unplotDatastream('b')
    expect(store.plottedDatastreams.map((d) => d.id)).toEqual(['a'])
    expect(store.qcDatastreamId).toBe('a')
  })

  it('clears qcDatastreamId when last plotted datastream is removed', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.plotDatastream(makeDs({ id: 'a' }) as any)
    await store.unplotDatastream('a')
    expect(store.plottedDatastreams).toEqual([])
    expect(store.qcDatastreamId).toBeNull()
  })

  it('is a no-op when the id is not present', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.unplotDatastream('ghost')
    expect(store.plottedDatastreams).toEqual([])
    expect(store.qcDatastreamId).toBeNull()
  })
})

describe('useDataVisStore.setPlottedDatastreams', () => {
  it('honors qcId when present in the new list', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.setPlottedDatastreams(
      [makeDs({ id: 'a' }), makeDs({ id: 'b' })] as any,
      'b'
    )
    expect(store.plottedDatastreams.map((d) => d.id)).toEqual(['a', 'b'])
    expect(store.qcDatastreamId).toBe('b')
  })

  it('falls back to first item when qcId is not in the list', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.setPlottedDatastreams(
      [makeDs({ id: 'a' }), makeDs({ id: 'b' })] as any,
      'missing'
    )
    expect(store.qcDatastreamId).toBe('a')
  })

  it('clears qcDatastreamId when the list is empty', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'a' })] as any
    store.qcDatastreamId = 'a'
    await store.setPlottedDatastreams([], null)
    expect(store.plottedDatastreams).toEqual([])
    expect(store.qcDatastreamId).toBeNull()
  })

  it('preserves qcDatastreamId when it still appears in the new list (no qcId arg)', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'a' })] as any
    store.qcDatastreamId = 'a'
    await store.setPlottedDatastreams([
      makeDs({ id: 'a' }),
      makeDs({ id: 'b' }),
    ] as any)
    expect(store.qcDatastreamId).toBe('a')
  })

  it('promotes first item when current qc is no longer in list (no qcId arg)', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'a' })] as any
    store.qcDatastreamId = 'a'
    await store.setPlottedDatastreams([makeDs({ id: 'c' })] as any)
    expect(store.qcDatastreamId).toBe('c')
  })
})

describe('useDataVisStore.setDateRange', () => {
  it('is a no-op when neither bound changes', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'a' })] as any
    const sameBegin = new Date(store.beginDate.getTime())
    const sameEnd = new Date(store.endDate.getTime())
    await store.setDateRange({ begin: sameBegin, end: sameEnd })
    expect(mockRedraw).not.toHaveBeenCalled()
  })

  it('updates both dates when they change and triggers redraw', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'a' })] as any
    const newBegin = new Date('2025-01-01T00:00:00Z')
    const newEnd = new Date('2025-02-01T00:00:00Z')
    await store.setDateRange({ begin: newBegin, end: newEnd })
    expect(store.beginDate.getTime()).toBe(newBegin.getTime())
    expect(store.endDate.getTime()).toBe(newEnd.getTime())
    expect(mockRedraw).toHaveBeenCalledTimes(1)
    expect(mockClearZoomHistory).toHaveBeenCalledTimes(1)
  })

  it('sets selectedDateBtnId to -1 by default (custom range)', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.selectedDateBtnId = 2
    await store.setDateRange({
      begin: new Date('2025-01-01T00:00:00Z'),
      end: new Date('2025-02-01T00:00:00Z'),
    })
    expect(store.selectedDateBtnId).toBe(-1)
  })

  it('leaves selectedDateBtnId alone when custom=false', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.selectedDateBtnId = 2
    await store.setDateRange({
      begin: new Date('2025-01-01T00:00:00Z'),
      end: new Date('2025-02-01T00:00:00Z'),
      custom: false,
    })
    expect(store.selectedDateBtnId).toBe(2)
  })

  it('does not redraw when no datastreams are plotted', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.setDateRange({
      begin: new Date('2025-01-01T00:00:00Z'),
      end: new Date('2025-02-01T00:00:00Z'),
    })
    expect(mockRedraw).not.toHaveBeenCalled()
  })
})

describe('useDataVisStore.onDateBtnClick', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-15T12:00:00Z'))
  })

  it('updates selectedDateBtnId and sets a 1-week window for id=0', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.onDateBtnClick(0)
    expect(store.selectedDateBtnId).toBe(0)
    const spanMs = store.endDate.getTime() - store.beginDate.getTime()
    expect(spanMs).toBe(7 * 24 * 60 * 60 * 1000)
  })

  it('sets a ~1-month window for id=1', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.onDateBtnClick(1)
    expect(store.selectedDateBtnId).toBe(1)
    expect(store.beginDate.getUTCMonth()).toBe(11) // December
    expect(store.beginDate.getUTCFullYear()).toBe(2025)
  })

  it('sets a YTD window for id=3 (Jan 1 local)', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.onDateBtnClick(3)
    expect(store.selectedDateBtnId).toBe(3)
    expect(store.beginDate.getMonth()).toBe(0)
    expect(store.beginDate.getDate()).toBe(1)
  })

  it('sets beginDate to epoch 0 for id=5 (All)', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.onDateBtnClick(5)
    expect(store.selectedDateBtnId).toBe(5)
    expect(store.beginDate.getTime()).toBe(0)
  })

  it('is a no-op when the id does not match any option', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    const prev = store.selectedDateBtnId
    store.onDateBtnClick(999)
    expect(store.selectedDateBtnId).toBe(prev)
  })
})

describe('useDataVisStore.resetState', () => {
  it('resets filter arrays, plotted state, and qc id', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.selectedThings = [{ id: 'x' }] as any
    store.selectedObservedPropertyNames = ['Temperature']
    store.selectedProcessingLevelNames = ['Raw']
    store.plottedDatastreams = [makeDs({ id: 'a' })] as any
    store.qcDatastreamId = 'a'

    store.resetState()

    expect(store.selectedThings).toEqual([])
    expect(store.selectedObservedPropertyNames).toEqual([])
    expect(store.selectedProcessingLevelNames).toEqual([])
    expect(store.plottedDatastreams).toEqual([])
    expect(store.qcDatastreamId).toBeNull()
  })

  it('calls clearChartState to flush plotly state', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.resetState()
    expect(mockClearChartState).toHaveBeenCalled()
  })

  it('preserves selectedDateBtnId (user preference, not workspace state)', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.selectedDateBtnId = 2
    store.resetState()
    expect(store.selectedDateBtnId).toBe(2)
  })

  it('reapplies the persisted preset to beginDate', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.selectedDateBtnId = 0 // "1w" preset
    store.resetState()
    const spanMs = store.endDate.getTime() - store.beginDate.getTime()
    expect(spanMs).toBe(7 * 24 * 60 * 60 * 1000)
  })
})

describe('useDataVisStore.setQcDatastream', () => {
  it('updates qcDatastreamId and calls updateOptions', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'a' }), makeDs({ id: 'b' })] as any
    store.qcDatastreamId = 'a'
    await store.setQcDatastream('b')
    expect(store.qcDatastreamId).toBe('b')
    expect(mockUpdateOptions).toHaveBeenCalled()
  })

  it('is a no-op when id matches current qcDatastreamId', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.qcDatastreamId = 'a'
    await store.setQcDatastream('a')
    expect(mockUpdateOptions).not.toHaveBeenCalled()
  })
})

describe('useDataVisStore.clearPlottedDatastreams + toggleDatastream', () => {
  it('clearPlottedDatastreams empties the list and clears qcDatastreamId', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.plotDatastream(makeDs({ id: 'a' }) as any)
    await store.plotDatastream(makeDs({ id: 'b' }) as any)
    await store.clearPlottedDatastreams()
    expect(store.plottedDatastreams).toEqual([])
    expect(store.qcDatastreamId).toBeNull()
  })

  it('clearPlottedDatastreams is a no-op when already empty', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.clearPlottedDatastreams()
    expect(mockClearChartState).not.toHaveBeenCalled()
  })

  it('toggleDatastream adds then removes the same datastream', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    const ds = makeDs({ id: 'a' }) as any
    await store.toggleDatastream(ds)
    expect(store.plottedDatastreams.map((d) => d.id)).toEqual(['a'])
    await store.toggleDatastream(ds)
    expect(store.plottedDatastreams).toEqual([])
  })
})
