import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { createApp, ref } from 'vue'
import { subtractMonths } from '@/utils/dateMath'

// Shared mutable stub state so each test can reset between runs.
const mockPlotlyRef = ref<any>(null)
const mockGraphSeriesArray = ref<any[]>([])
const mockUpdateOptions = vi.fn()
const mockClearChartState = vi.fn()
const mockClearZoomHistory = vi.fn()
const mockFetchGraphSeries = vi.fn().mockResolvedValue({ id: 'stub', data: {} })
const mockAssignSeriesColors = vi.fn()
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
    assignSeriesColors: mockAssignSeriesColors,
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
})

describe('useDataVisStore time range presets', () => {
  const OLD_END = '2021-06-30T12:00:00Z'
  const oldDs = (overrides: Record<string, any> = {}) =>
    makeDs({
      id: 'old',
      phenomenonBeginTime: '2019-01-01T00:00:00Z',
      phenomenonEndTime: OLD_END,
      ...overrides,
    })
  const newerDs = () =>
    makeDs({
      id: 'newer',
      phenomenonBeginTime: '2020-01-01T00:00:00Z',
      phenomenonEndTime: '2022-03-01T00:00:00Z',
    })

  it('defaults to the 1m preset', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    expect(useDataVisStore().selectedDateBtnId).toBe(1)
  })

  it('anchors a preset click to the plotted data end, not now', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [oldDs()] as any
    await store.onDateBtnClick(0)
    expect(store.selectedDateBtnId).toBe(0)
    expect(store.endDate.toISOString()).toBe('2021-06-30T12:00:00.000Z')
    expect(store.endDate.getTime() - store.beginDate.getTime()).toBe(
      7 * 24 * 60 * 60 * 1000
    )
  })

  it('All spans every plotted datastream', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [oldDs(), newerDs()] as any
    await store.onDateBtnClick(5)
    expect(store.beginDate.toISOString()).toBe('2019-01-01T00:00:00.000Z')
    expect(store.endDate.toISOString()).toBe('2022-03-01T00:00:00.000Z')
  })

  it('ignores datastreams without observations when anchoring', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'empty' }), oldDs()] as any
    await store.onDateBtnClick(0)
    expect(store.endDate.toISOString()).toBe('2021-06-30T12:00:00.000Z')
  })

  it('selects the preset without moving the window when nothing is plotted', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    const begin = store.beginDate.getTime()
    await store.onDateBtnClick(5)
    expect(store.selectedDateBtnId).toBe(5)
    expect(store.beginDate.getTime()).toBe(begin)
    expect(mockRedraw).not.toHaveBeenCalled()
  })

  it('is a no-op for an unknown preset id', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.onDateBtnClick(999)
    expect(store.selectedDateBtnId).toBe(1)
  })

  it('re-anchors the active preset when a datastream is plotted', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.plotDatastream(oldDs() as any)
    const end = new Date(OLD_END)
    expect(store.endDate.getTime()).toBe(end.getTime())
    expect(store.beginDate.getTime()).toBe(subtractMonths(end, 1).getTime())
    expect(mockFetchGraphSeries).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'old' }),
      store.beginDate,
      store.endDate
    )
  })

  it('re-anchors when the newest datastream is unplotted', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [oldDs(), newerDs()] as any
    store.qcDatastreamId = 'old'
    await store.unplotDatastream('newer')
    expect(store.endDate.toISOString()).toBe('2021-06-30T12:00:00.000Z')
  })

  it('keeps a custom range when the plotted set changes', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    const begin = new Date('2025-01-01T00:00:00Z')
    const end = new Date('2025-02-01T00:00:00Z')
    await store.setDateRange({ begin, end })
    await store.plotDatastream(oldDs() as any)
    expect(store.selectedDateBtnId).toBe(-1)
    expect(store.beginDate.getTime()).toBe(begin.getTime())
    expect(store.endDate.getTime()).toBe(end.getTime())
  })
})

// The persistence plugin only activates once the pinia is installed on an
// app, so these go through `app.use(pinia)`.
describe('useDataVisStore persisted preset', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => localStorage.clear())

  const installPinia = () => {
    const pinia = createPinia()
    pinia.use(piniaPluginPersistedstate)
    createApp({ render: () => null }).use(pinia)
  }

  it('restores the persisted preset id', async () => {
    localStorage.setItem(
      'dataVisualization',
      JSON.stringify({ selectedDateBtnId: 5 })
    )
    installPinia()
    const { useDataVisStore } = await import('@/store/dataVisualization')
    expect(useDataVisStore().selectedDateBtnId).toBe(5)
  })

  it('defaults to 1m when nothing is persisted', async () => {
    installPinia()
    const { useDataVisStore } = await import('@/store/dataVisualization')
    expect(useDataVisStore().selectedDateBtnId).toBe(1)
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

describe('useDataVisStore.adoptManagedDatastream', () => {
  it('reuses the source series as the managed working copy (one item, data kept)', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    const sourceData = { tag: 'loaded-record' }
    store.plottedDatastreams = [makeDs({ id: 'src', name: 'Raw' })] as any
    store.qcDatastreamId = 'src'
    mockGraphSeriesArray.value = [
      { id: 'src', name: 'Raw', data: sourceData, color: '#1', yAxisLabel: 'T' },
    ]

    await store.adoptManagedDatastream(
      makeDs({ id: 'mgd', name: 'Raw (QC)' }) as any,
      'src'
    )

    // Single plotted item, now the managed datastream as the QC target.
    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual(['mgd'])
    expect(store.qcDatastreamId).toBe('mgd')
    // The loaded series was re-keyed in place, keeping its data...
    expect(mockGraphSeriesArray.value).toHaveLength(1)
    expect(mockGraphSeriesArray.value[0].id).toBe('mgd')
    expect(mockGraphSeriesArray.value[0].name).toBe('Raw (QC)')
    expect(mockGraphSeriesArray.value[0].data).toEqual(sourceData)
    // ...and the working copy was reused, not re-fetched (managed is empty).
    expect(mockFetchGraphSeries).not.toHaveBeenCalled()
    expect(mockFetchObservationsInRange).not.toHaveBeenCalled()
  })
})

describe('useDataVisStore.releaseManagedDatastream', () => {
  const withHistory = (store: any) => {
    store.qcHistories = [
      { id: 'h-1', managedDatastreamId: 'mgd', sourceDatastreamId: 'src' },
    ] as any
    store.datastreams = [
      makeDs({ id: 'src', name: 'Raw' }),
      makeDs({ id: 'mgd', name: 'Raw (QC)' }),
    ] as any
  }

  // Managed datastreams are hidden from the catalog table, so leaving the
  // editor with one plotted shows a plot with no row selected.
  it('swaps the managed datastream back to its source and refetches its data', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withHistory(store)
    const working = { tag: 'uncommitted-edits' }
    store.plottedDatastreams = [makeDs({ id: 'mgd', name: 'Raw (QC)' })] as any
    store.qcDatastreamId = 'mgd'
    mockGraphSeriesArray.value = [
      { id: 'mgd', name: 'Raw (QC)', data: working, color: '#1', yAxisLabel: 'T' },
    ]

    await store.releaseManagedDatastream()

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual(['src'])
    expect(store.qcDatastreamId).toBe('src')
    // The editor's working copy carries uncommitted edits, so it is dropped
    // and the source's stored data fetched instead.
    expect(
      mockGraphSeriesArray.value.some((s: any) => s.data === working)
    ).toBe(false)
    expect(mockFetchGraphSeries).toHaveBeenCalled()
    expect(mockFetchGraphSeries.mock.calls[0][0].id).toBe('src')
  })

  it('is a no-op when the plotted datastream is not a managed one', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withHistory(store)
    store.plottedDatastreams = [makeDs({ id: 'src', name: 'Raw' })] as any
    store.qcDatastreamId = 'src'

    await store.releaseManagedDatastream()

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual(['src'])
    expect(store.qcDatastreamId).toBe('src')
  })

  it('leaves the plot alone when the source is missing from the catalog', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.qcHistories = [
      { id: 'h-1', managedDatastreamId: 'mgd', sourceDatastreamId: 'gone' },
    ] as any
    store.datastreams = [makeDs({ id: 'mgd', name: 'Raw (QC)' })] as any
    store.plottedDatastreams = [makeDs({ id: 'mgd', name: 'Raw (QC)' })] as any
    store.qcDatastreamId = 'mgd'

    await store.releaseManagedDatastream()

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual(['mgd'])
    expect(store.qcDatastreamId).toBe('mgd')
  })
})

describe('useDataVisStore snapshot series', () => {
  const meta = {
    sessionId: 'sess-1',
    sessionLabel: 'March backfill',
    opIndex: 0,
    opCount: 2,
    opName: 'Fill Gaps',
    createdAt: '2026-01-01T00:00:00Z',
  }

  it('keeps a snapshot series across a refresh without fetching it', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    const record = { history: [], isLoading: false } as any

    await store.addSnapshotSeries('snap:sess-1:0', record, meta as any)
    await store.refreshGraphSeriesArray()

    const series = mockGraphSeriesArray.value.find(
      (s: any) => s.id === 'snap:sess-1:0'
    )
    expect(series).toBeDefined()
    // Reactive wrapping means this is a proxy of `record`, not `record` itself.
    expect(series.data).toEqual(record)
    expect(series.snapshot).toEqual(meta)
    expect(mockFetchObservationsInRange).not.toHaveBeenCalled()
    expect(mockFetchGraphSeries).not.toHaveBeenCalled()
  })

  it('removes a snapshot from both the plotted list and the series array', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()

    await store.addSnapshotSeries('snap:sess-1:0', { history: [] } as any, meta as any)
    await store.removeSnapshotSeries('snap:sess-1:0')

    expect(store.plottedDatastreams.some((d: any) => d.id === 'snap:sess-1:0')).toBe(
      false
    )
    expect(
      mockGraphSeriesArray.value.some((s: any) => s.id === 'snap:sess-1:0')
    ).toBe(false)
  })

  it('never promotes a snapshot to the QC target', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.qcDatastreamId = null

    await store.addSnapshotSeries('snap:sess-1:0', { history: [] } as any, meta as any)

    expect(store.qcDatastreamId).toBeNull()
  })

  // Snapshots belong to the editor. The Select view lists real datastreams
  // and lets the user pick a QC target, neither of which a snapshot can be.
  it('drops snapshots when the editor releases the managed datastream', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.qcHistories = [
      { id: 'h-1', managedDatastreamId: 'mgd', sourceDatastreamId: 'src' },
    ] as any
    store.datastreams = [makeDs({ id: 'src', name: 'Raw' })] as any
    store.plottedDatastreams = [makeDs({ id: 'mgd', name: 'Raw (QC)' })] as any
    store.qcDatastreamId = 'mgd'

    await store.addSnapshotSeries('snap:sess-1:0', { history: [] } as any, meta as any)
    await store.releaseManagedDatastream()

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual(['src'])
    expect(
      mockGraphSeriesArray.value.some((s: any) => s.id === 'snap:sess-1:0')
    ).toBe(false)
  })

  it('drops snapshots even when there is no managed datastream to release', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'src', name: 'Raw' })] as any
    store.qcDatastreamId = 'src'

    await store.addSnapshotSeries('snap:sess-1:0', { history: [] } as any, meta as any)
    await store.releaseManagedDatastream()

    expect(
      store.plottedDatastreams.some((d: any) => d.id === 'snap:sess-1:0')
    ).toBe(false)
  })
})

describe('useDataVisStore.sourceGroupIds', () => {
  it('returns the source plus every managed datastream derived from it', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.qcHistories = [
      { id: 'h-1', managedDatastreamId: 'mgd-1', sourceDatastreamId: 'src' },
      { id: 'h-2', managedDatastreamId: 'mgd-2', sourceDatastreamId: 'src' },
      { id: 'h-3', managedDatastreamId: 'mgd-3', sourceDatastreamId: 'other' },
    ] as any

    expect(store.sourceGroupIds('src')).toEqual(['src', 'mgd-1', 'mgd-2'])
    expect(store.sourceGroupIds('lonely')).toEqual(['lonely'])
  })
})

describe('useDataVisStore.plotSourceSelection', () => {
  const withGroup = (store: any) => {
    store.qcHistories = [
      { id: 'h-1', managedDatastreamId: 'mgd-1', sourceDatastreamId: 'src' },
      { id: 'h-2', managedDatastreamId: 'mgd-2', sourceDatastreamId: 'src' },
    ] as any
    store.datastreams = [
      makeDs({ id: 'src', name: 'Raw' }),
      makeDs({ id: 'mgd-1', name: 'Raw (QC)' }),
      makeDs({ id: 'mgd-2', name: 'Raw (QC2)' }),
      makeDs({ id: 'other', name: 'Other' }),
    ] as any
  }

  it('plots the chosen series and promotes the first as QC target', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)

    await store.plotSourceSelection('src', ['src', 'mgd-1'])

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual([
      'src',
      'mgd-1',
    ])
    expect(store.qcDatastreamId).toBe('src')
  })

  it('makes a managed datastream the QC target when the raw one is not picked', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)

    await store.plotSourceSelection('src', ['mgd-2'])

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual(['mgd-2'])
    expect(store.qcDatastreamId).toBe('mgd-2')
  })

  it('adds and removes within the group in a single call', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)
    store.plottedDatastreams = [
      makeDs({ id: 'src', name: 'Raw' }),
      makeDs({ id: 'mgd-1', name: 'Raw (QC)' }),
    ] as any
    store.qcDatastreamId = 'src'

    await store.plotSourceSelection('src', ['mgd-1', 'mgd-2'])

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual([
      'mgd-1',
      'mgd-2',
    ])
  })

  it('leaves datastreams from other sources untouched', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)
    store.plottedDatastreams = [makeDs({ id: 'other', name: 'Other' })] as any
    store.qcDatastreamId = 'other'

    await store.plotSourceSelection('src', ['mgd-1'])

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual([
      'other',
      'mgd-1',
    ])
    expect(store.qcDatastreamId).toBe('other')
  })

  it('promotes a new QC target when the current one is deselected', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)
    store.plottedDatastreams = [
      makeDs({ id: 'other', name: 'Other' }),
      makeDs({ id: 'src', name: 'Raw' }),
    ] as any
    store.qcDatastreamId = 'src'

    await store.plotSourceSelection('src', ['mgd-1'])

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual([
      'other',
      'mgd-1',
    ])
    expect(store.qcDatastreamId).toBe('other')
  })

  it('clears the QC target when nothing is left plotted', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)
    store.plottedDatastreams = [makeDs({ id: 'mgd-1', name: 'Raw (QC)' })] as any
    store.qcDatastreamId = 'mgd-1'

    await store.plotSourceSelection('src', [])

    expect(store.plottedDatastreams).toEqual([])
    expect(store.qcDatastreamId).toBeNull()
  })

  it('ignores ids that do not belong to the source group', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)

    await store.plotSourceSelection('src', ['other', 'mgd-1'])

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual(['mgd-1'])
  })

  // Looping plot/unplot would rebuild once per change; the batched action
  // settles the whole selection against one rebuild.
  it('rebuilds the plot once for the whole selection', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)

    await store.plotSourceSelection('src', ['src', 'mgd-1', 'mgd-2'])

    expect(mockUpdateOptions).toHaveBeenCalledTimes(1)
  })

  it('does nothing when the selection already matches', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)
    store.plottedDatastreams = [makeDs({ id: 'src', name: 'Raw' })] as any
    store.qcDatastreamId = 'src'

    await store.plotSourceSelection('src', ['src'])

    expect(mockUpdateOptions).not.toHaveBeenCalled()
  })
})

// Both the source and a managed datastream can be plotted at once now, so
// leaving the editor must not re-add a source that is already there.
describe('useDataVisStore.releaseManagedDatastream with the source plotted', () => {
  it('drops the managed datastream instead of duplicating the source', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.qcHistories = [
      { id: 'h-1', managedDatastreamId: 'mgd', sourceDatastreamId: 'src' },
    ] as any
    store.datastreams = [
      makeDs({ id: 'src', name: 'Raw' }),
      makeDs({ id: 'mgd', name: 'Raw (QC)' }),
    ] as any
    store.plottedDatastreams = [
      makeDs({ id: 'src', name: 'Raw' }),
      makeDs({ id: 'mgd', name: 'Raw (QC)' }),
    ] as any
    store.qcDatastreamId = 'mgd'

    await store.releaseManagedDatastream()

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual(['src'])
    expect(store.qcDatastreamId).toBe('src')
  })
})
