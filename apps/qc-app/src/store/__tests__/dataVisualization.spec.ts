import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { createApp, nextTick, ref, shallowRef } from 'vue'
import { subtractDays, subtractMonths } from '@/utils/dateMath'

// Shared mutable stub state so each test can reset between runs.
const mockPlotlyRef = ref<any>(null)
// shallowRef: pushed objects keep their identity (not deep-reactive-wrapped),
// so tests can assert `data` is the exact working-copy record reference.
const mockGraphSeriesArray = shallowRef<any[]>([])
const mockUpdateOptions = vi.fn()
const mockClearChartState = vi.fn()
const mockClearZoomHistory = vi.fn()
const mockFetchGraphSeries = vi.fn(
  async (ds: any, _start?: Date, _end?: Date, _exclude?: unknown, _fetchAs?: any) => ({ id: ds.id, name: ds.name, data: {} })
)
const mockBuildGraphSeries = vi.fn((ds: any, data: any) => ({ id: ds.id, name: ds.name, data }))
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
    buildGraphSeries: mockBuildGraphSeries,
    assignSeriesColors: mockAssignSeriesColors,
    redraw: mockRedraw,
  }),
}))

vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({
    fetchObservationsInRange: mockFetchObservationsInRange,
  }),
}))

const mockWorkingCopies = new Map<string, any>()
const mockLoadWorkingCopy = vi.fn(async (managed: any) => mockWorkingCopies.get(managed.id) ?? null)
const mockInvalidateWorkingCopy = vi.fn((id: string) => mockWorkingCopies.delete(id))
const mockClearWorkingCopies = vi.fn(() => mockWorkingCopies.clear())
vi.mock('@/store/workingCopies', () => ({
  useWorkingCopiesStore: () => ({
    get: (id: string) => mockWorkingCopies.get(id),
    load: mockLoadWorkingCopy,
    invalidate: mockInvalidateWorkingCopy,
    clear: mockClearWorkingCopies,
    extents: (ids: string[]) =>
      ids.flatMap((id) => {
        const c = mockWorkingCopies.get(id)
        return c
          ? [{ phenomenonBeginTime: c.begin.toISOString(), phenomenonEndTime: c.end.toISOString() }]
          : []
      }),
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
  mockWorkingCopies.clear()
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

describe('useDataVisStore.plotDatastream', () => {
  it('adds a second datastream alongside the first', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.plotDatastream(makeDs({ id: 'a' }) as any)
    await store.plotDatastream(makeDs({ id: 'b' }) as any)
    expect(store.plottedDatastreams.map((d) => d.id)).toEqual(['a', 'b'])
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
  it('removes only the given datastream', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.plotDatastream(makeDs({ id: 'a' }) as any)
    await store.plotDatastream(makeDs({ id: 'b' }) as any)
    await store.unplotDatastream('a')
    expect(store.plottedDatastreams.map((d) => d.id)).toEqual(['b'])
  })

  it('is a no-op when the id is not present', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.unplotDatastream('ghost')
    expect(store.plottedDatastreams).toEqual([])
  })
})

describe('useDataVisStore.setPlottedDatastreams', () => {
  it('replaces the plotted list and rebuilds', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.setPlottedDatastreams([
      makeDs({ id: 'a' }),
      makeDs({ id: 'b' }),
    ] as any)
    expect(store.plottedDatastreams.map((d) => d.id)).toEqual(['a', 'b'])
  })
})

const managedPair = async () => {
  const { useDataVisStore } = await import('@/store/dataVisualization')
  const store = useDataVisStore()
  const source = makeDs({ id: 'src', phenomenonBeginTime: '2025-01-01T00:00:00Z', phenomenonEndTime: '2025-12-31T00:00:00Z' })
  const managed = makeDs({ id: 'mgd' })
  const other = makeDs({ id: 'other', phenomenonBeginTime: '2025-01-01T00:00:00Z', phenomenonEndTime: '2025-12-31T00:00:00Z' })
  store.datastreams = [source, managed, other] as any
  store.qcHistories = [
    { id: 'h1', sourceDatastreamId: 'src', managedDatastreamId: 'mgd' },
  ] as any
  return { store, source, managed, other }
}

const WIN_START = '2025-06-01T00:00:00Z'
const WIN_END = '2025-06-10T00:00:00Z'
const WINDOW = { begin: new Date(WIN_START), end: new Date(WIN_END) }

/** Load an in-progress session over `WINDOW` for the edit target. */
async function loadSession() {
  const { useQcSessionStore } = await import('@/store/qcSession')
  useQcSessionStore().applySessions('h1', [
    {
      id: 's1',
      status: 'in_progress',
      phenomenonTimeStart: WIN_START,
      phenomenonTimeEnd: WIN_END,
    },
  ] as any)
  await nextTick()
}

const settle = () => new Promise((r) => setTimeout(r, 0))

/** Edit `mgd` with its session window known and the context loaded. */
async function editWithWindow(store: any) {
  await store.setEditTarget('mgd')
  await loadSession()
  await settle()
}

describe('useDataVisStore edit target', () => {
  it('plotting never picks an edit target', async () => {
    const { store, other } = await managedPair()
    await store.plotDatastream(other as any)
    expect(store.qcDatastreamId).toBeNull()
    expect(store.seriesDatastreams.map((d) => d.id)).toEqual(['other'])
  })

  it('resolves the edit target from the catalog without plotting it', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    expect(store.qcDatastream?.id).toBe('mgd')
    expect(store.plottedDatastreams).toEqual([])
  })

  it('orders series as edit target, source, then plotted', async () => {
    const { store, other } = await managedPair()
    await store.plotDatastream(other as any)
    await store.setEditTarget('mgd')
    // The grey context has an id of its own; it reads the source's data.
    expect(store.sourceContextDatastream?.id).toBe('ctx:src')
    expect(store.seriesDatastreams.map((d) => d.id)).toEqual(['mgd', 'ctx:src', 'other'])
  })

  it('keeps the grey context beside a source the user plotted', async () => {
    const { store, source, other } = await managedPair()
    await store.plotDatastream(other as any)
    await store.plotDatastream(source as any)
    await store.setEditTarget('mgd')
    expect(store.editSourceDatastream?.id).toBe('src')
    expect(store.seriesDatastreams.map((d) => d.id)).toEqual([
      'mgd',
      'ctx:src',
      'other',
      'src',
    ])
  })

  it('fills the context series with the source data', async () => {
    const { store } = await managedPair()
    await editWithWindow(store)
    const call = mockFetchGraphSeries.mock.calls.find((c) => c[0].id === 'ctx:src')
    expect(call?.[4]?.id).toBe('src')
  })

  it('drops the source context when it is switched off', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    await store.setShowSourceContext(false)
    expect(store.sourceContextDatastream).toBeNull()
    expect(store.seriesDatastreams.map((d) => d.id)).toEqual(['mgd'])
    await store.setShowSourceContext(true)
    expect(store.seriesDatastreams.map((d) => d.id)).toEqual(['mgd', 'ctx:src'])
  })

  it('fetches a source the user plotted whole, without waiting for the window', async () => {
    const { store, source } = await managedPair()
    await store.plotDatastream(source as any)
    mockFetchGraphSeries.mockClear()
    mockFetchObservationsInRange.mockClear()
    await store.setEditTarget('mgd')
    await store.refreshGraphSeriesArray()
    const calls = [
      ...mockFetchGraphSeries.mock.calls,
      ...mockFetchObservationsInRange.mock.calls,
    ].filter((c) => c[0].id === 'src')
    expect(calls.length).toBeGreaterThan(0)
    expect(calls.every((c) => c[3] === undefined)).toBe(true)
  })

  it('never fetches the edit target when refreshing', async () => {
    const { store } = await managedPair()
    await editWithWindow(store)
    // The source is already loaded as context, so this refresh updates it
    // in place via `fetchObservationsInRange`, not a fresh fetch.
    mockFetchGraphSeries.mockClear()
    mockFetchObservationsInRange.mockClear()
    await store.refreshGraphSeriesArray()
    expect(mockFetchObservationsInRange.mock.calls.map((c) => c[0].id)).toEqual(['src'])
    expect(mockFetchGraphSeries).not.toHaveBeenCalled()
  })

  it('waits for the session window before fetching the source', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    expect(mockFetchGraphSeries).not.toHaveBeenCalled()

    await loadSession()
    await settle()

    expect(
      mockFetchGraphSeries.mock.calls.map((c) => [c[0].id, c[3], c[4]?.id])
    ).toEqual([['ctx:src', WINDOW, 'src']])
  })

  it('never fetches the session window for the source', async () => {
    const { store } = await managedPair()
    await editWithWindow(store)
    mockFetchObservationsInRange.mockClear()
    await store.refreshGraphSeriesArray()
    expect(mockFetchObservationsInRange.mock.calls[0]?.[3]).toEqual(WINDOW)
  })

  it('fetches other plotted datastreams whole', async () => {
    const { store, other } = await managedPair()
    await store.plotDatastream(other as any)
    await editWithWindow(store)
    mockFetchObservationsInRange.mockClear()
    await store.refreshGraphSeriesArray()
    const call = mockFetchObservationsInRange.mock.calls.find((c) => c[0].id === 'other')
    expect(call?.[3]).toBeUndefined()
  })

  it('unplotting the last plotted datastream while editing keeps the edit series', async () => {
    const { store, other } = await managedPair()
    await store.plotDatastream(other as any)
    await store.setEditTarget('mgd')
    await store.setEditRecord({ dataX: [1], history: [] } as any)
    mockClearChartState.mockClear()

    await store.unplotDatastream('other')

    expect(mockGraphSeriesArray.value.some((s) => s.id === 'mgd')).toBe(true)
    expect(mockClearChartState).not.toHaveBeenCalled()
  })

  it('setEditRecord adds the edit series, then updates it in place', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    const first = { dataX: [1], history: [] } as any
    const second = { dataX: [2], history: [] } as any
    await store.setEditRecord(first)
    expect(mockGraphSeriesArray.value.find((s) => s.id === 'mgd')?.data).toBe(first)
    await store.setEditRecord(second)
    const edits = mockGraphSeriesArray.value.filter((s) => s.id === 'mgd')
    expect(edits).toHaveLength(1)
    expect(edits[0].data).toBe(second)
  })

  it('clearEditTarget keeps the plotted datastreams and drops edit series', async () => {
    const { store, other } = await managedPair()
    await store.plotDatastream(other as any)
    await store.setEditTarget('mgd')
    await store.setEditRecord({ dataX: [1], history: [] } as any)
    await store.clearEditTarget()
    expect(store.qcDatastreamId).toBeNull()
    expect(store.plottedDatastreams.map((d) => d.id)).toEqual(['other'])
    expect(store.seriesDatastreams.map((d) => d.id)).toEqual(['other'])
    expect(mockGraphSeriesArray.value.some((s) => s.id === 'mgd')).toBe(false)
    expect(mockInvalidateWorkingCopy).toHaveBeenCalledWith('mgd')
  })

  it('unplotting never touches the edit target', async () => {
    const { store, other } = await managedPair()
    await store.plotDatastream(other as any)
    await store.setEditTarget('mgd')
    await store.unplotDatastream('other')
    expect(store.qcDatastreamId).toBe('mgd')
  })

  it('rebuilding while editing keeps the zoom', async () => {
    const { store, other } = await managedPair()
    await store.plotDatastream(other as any)
    await store.setEditTarget('mgd')
    mockPlotlyRef.value = {}
    const { handleNewPlot } = await import('@/utils/plotting/plotly')
    vi.mocked(handleNewPlot).mockClear()
    mockClearZoomHistory.mockClear()

    await store.unplotDatastream('other')

    expect(handleNewPlot).toHaveBeenCalledWith(undefined, { preserveZoom: true })
    expect(mockClearZoomHistory).not.toHaveBeenCalled()
  })

  it('rebuilding in Select drops the zoom', async () => {
    const { store, other, source } = await managedPair()
    await store.plotDatastream(other as any)
    await store.plotDatastream(source as any)
    mockPlotlyRef.value = {}
    const { handleNewPlot } = await import('@/utils/plotting/plotly')
    vi.mocked(handleNewPlot).mockClear()
    mockClearZoomHistory.mockClear()

    await store.unplotDatastream('other')

    expect(handleNewPlot).toHaveBeenCalledWith(undefined, { preserveZoom: false })
    expect(mockClearZoomHistory).toHaveBeenCalled()
  })

  it('a new edit target starts from an empty session store', async () => {
    const { store } = await managedPair()
    const { useQcSessionStore } = await import('@/store/qcSession')
    const sessions = useQcSessionStore()
    await store.setEditTarget('mgd')
    sessions.historyId = 'h1'
    sessions.sessions = [{ id: 's1', status: 'in_progress' }] as any
    sessions.currentSessionId = 's1'
    sessions.viewedSessionId = 's1'
    sessions.resumeDatastreamId = 'mgd'
    await store.clearEditTarget()

    await store.setEditTarget('other')

    expect(sessions.historyId).toBeNull()
    expect(sessions.sessions).toEqual([])
    expect(sessions.viewedSession).toBeNull()
    // The resume pointer is the entry flow's to set.
    expect(sessions.resumeDatastreamId).toBe('mgd')
  })

  it('entering the editor drops the Select zoom history', async () => {
    const { store, other } = await managedPair()
    await store.plotDatastream(other as any)
    mockClearZoomHistory.mockClear()

    await store.setEditTarget('mgd')

    expect(mockClearZoomHistory).toHaveBeenCalled()
  })

  it('setting the same edit target keeps the zoom history', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    mockClearZoomHistory.mockClear()

    await store.setEditTarget('mgd')

    expect(mockClearZoomHistory).not.toHaveBeenCalled()
  })

  it('setting the same edit target keeps its sessions', async () => {
    const { store } = await managedPair()
    const { useQcSessionStore } = await import('@/store/qcSession')
    const sessions = useQcSessionStore()
    await store.setEditTarget('mgd')
    sessions.historyId = 'h1'

    await store.setEditTarget('mgd')

    expect(sessions.historyId).toBe('h1')
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

  it('refreshes context when only the edit target is set, nothing plotted', async () => {
    const { store } = await managedPair()
    await editWithWindow(store)
    // The source is already loaded as context, so the date change updates
    // it in place via `fetchObservationsInRange`.
    mockFetchObservationsInRange.mockClear()
    mockRedraw.mockClear()
    mockClearZoomHistory.mockClear()

    await store.setDateRange({
      begin: new Date('2025-02-01T00:00:00Z'),
      end: new Date('2025-03-01T00:00:00Z'),
    })

    expect(mockFetchObservationsInRange.mock.calls.map((c) => c[0].id)).toContain('src')
    expect(mockRedraw).toHaveBeenCalledWith(false, true)
    expect(mockClearZoomHistory).not.toHaveBeenCalled()
  })
})

describe('useDataVisStore overlapping plot loads', () => {
  const deferred = <T>() => {
    let resolve!: (v: T) => void
    const promise = new Promise<T>((r) => (resolve = r))
    return { promise, resolve }
  }
  const flush = () => new Promise((r) => setTimeout(r, 0))
  const FEB = new Date('2025-02-01T00:00:00Z')
  const MAR = new Date('2025-03-01T00:00:00Z')
  const APR = new Date('2025-04-01T00:00:00Z')
  const MAY = new Date('2025-05-01T00:00:00Z')

  it('drops a context response whose range was superseded', async () => {
    const { store } = await managedPair()
    await editWithWindow(store)
    mockRedraw.mockClear()
    const first = deferred<any>()
    const second = deferred<any>()
    mockFetchObservationsInRange
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    const older = store.setDateRange({ begin: FEB, end: MAR })
    const newer = store.setDateRange({ begin: APR, end: MAY })
    first.resolve({ id: 'feb' })
    await flush()
    second.resolve({ id: 'apr' })
    await Promise.all([older, newer])

    const src = mockGraphSeriesArray.value.find((s) => s.id === 'ctx:src')
    expect(src.data).toEqual({ id: 'apr' })
    expect(store.loadingStates.get('ctx:src')).toBe(false)
    expect(mockRedraw).toHaveBeenCalledTimes(1)
  })

  it('a rebuild whose range moves while loading draws the new range once', async () => {
    const { store } = await managedPair()
    await editWithWindow(store)
    mockPlotlyRef.value = {}
    const { handleNewPlot } = await import('@/utils/plotting/plotly')
    const drawn: unknown[] = []
    vi.mocked(handleNewPlot).mockImplementationOnce(async () => {
      drawn.push(mockGraphSeriesArray.value.find((s) => s.id === 'ctx:src')?.data)
    })
    mockFetchObservationsInRange.mockClear()
    mockRedraw.mockClear()
    const first = deferred<any>()
    const second = deferred<any>()
    mockFetchObservationsInRange
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    const rebuild = store.rebuildPlot()
    await flush()
    const reload = store.setDateRange({ begin: APR, end: MAY })
    first.resolve({ id: 'old' })
    await flush()
    second.resolve({ id: 'new' })
    await Promise.all([rebuild, reload])

    expect(drawn).toEqual([{ id: 'new' }])
    expect(mockFetchObservationsInRange.mock.calls.map((c) => c[1])).toEqual([
      expect.any(Date),
      APR,
    ])
    expect(mockRedraw).not.toHaveBeenCalled()
  })

  it('a rebuild requested while a context reload loads waits for it', async () => {
    const { store, other } = await managedPair()
    await editWithWindow(store)
    mockFetchObservationsInRange.mockClear()
    mockFetchGraphSeries.mockClear()
    const pending = deferred<any>()
    mockFetchObservationsInRange.mockImplementationOnce(() => pending.promise)

    const reload = store.setDateRange({ begin: APR, end: MAY })
    const rebuild = store.plotDatastream(other as any)
    await flush()

    expect(mockFetchObservationsInRange).toHaveBeenCalledTimes(1)
    expect(mockFetchGraphSeries).not.toHaveBeenCalled()

    pending.resolve({ id: 'apr' })
    await Promise.all([reload, rebuild])
    expect(mockFetchGraphSeries.mock.calls.map((c: any[]) => [c[0].id, c[1]])).toEqual([
      ['other', APR],
    ])
  })

  it('a context reload requested while a rebuild is queued joins it', async () => {
    const { store } = await managedPair()
    await editWithWindow(store)
    mockPlotlyRef.value = {}
    mockRedraw.mockClear()
    const pending = deferred<any>()
    mockFetchObservationsInRange.mockClear()
    mockFetchObservationsInRange.mockImplementationOnce(() => pending.promise)

    const inFlight = store.rebuildPlot()
    await flush()
    const queued = store.rebuildPlot()
    const reload = store.setDateRange({ begin: APR, end: MAY })
    pending.resolve({ id: 'old' })
    await Promise.all([inFlight, queued, reload])

    const starts = mockFetchObservationsInRange.mock.calls.map((c) => c[1])
    expect(starts.filter((d) => d === APR)).toHaveLength(2)
    expect(starts).toHaveLength(3)
    expect(mockRedraw).not.toHaveBeenCalled()
  })

  // A load requested in the microtasks between one finishing and its queued
  // follow-up starting must join the follow-up, not start a load beside it.
  // The exact hop count is an implementation detail, so sweep the window.
  it('does not start a second load when one is requested as a load settles', async () => {
    const runScenario = async (hops: number) => {
      const { store } = await managedPair()
      await editWithWindow(store)
      mockPlotlyRef.value = {}
      let active = 0
      let maxActive = 0
      let firstFetch: Promise<unknown> | null = null
      mockFetchObservationsInRange.mockClear()
      mockFetchObservationsInRange.mockImplementation(() => {
        const fetched = (async () => {
          active++
          maxActive = Math.max(maxActive, active)
          await flush()
          active--
          return { id: 'x' }
        })()
        firstFetch ??= fetched
        return fetched
      })

      const inFlight = store.rebuildPlot()
      await flush()
      const queued = store.rebuildPlot()
      // Count hops from the first load's own fetch, so the request lands in
      // the microtasks where that load is settling.
      const late = firstFetch!.then(async () => {
        for (let i = 0; i < hops; i++) await Promise.resolve()
        return store.rebuildPlot()
      })
      await Promise.all([inFlight, queued, late])
      mockFetchObservationsInRange.mockResolvedValue({ id: 'stub', data: {} })
      return maxActive
    }

    for (let hops = 0; hops <= 24; hops++) {
      expect([hops, await runScenario(hops)]).toEqual([hops, 1])
    }
  })

  it('does not add a series from a superseded range', async () => {
    const { store, other } = await managedPair()
    const first = deferred<any>()
    const second = deferred<any>()
    mockFetchGraphSeries
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    const rebuild = store.plotDatastream(other as any)
    await flush()
    const reload = store.setDateRange({ begin: APR, end: MAY })
    first.resolve({ id: 'other', data: 'old range' })
    await flush()
    second.resolve({ id: 'other', data: 'new range' })
    await Promise.all([rebuild, reload])

    expect(mockGraphSeriesArray.value.map((s) => s.data)).toEqual(['new range'])
  })

  it('a rebuild requested while another runs resolves only after the follow-up rebuild', async () => {
    const { store, other } = await managedPair()
    const extra = makeDs({ id: 'extra', phenomenonBeginTime: '2025-01-01T00:00:00Z', phenomenonEndTime: '2025-12-31T00:00:00Z' })
    store.datastreams = [...store.datastreams, extra] as any
    const first = deferred<any>()
    const second = deferred<any>()
    mockFetchGraphSeries
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)

    const inFlight = store.plotDatastream(other as any)
    await flush()
    let queuedDone = false
    const queued = store.plotDatastream(extra as any).then(() => {
      queuedDone = true
    })
    first.resolve({ id: 'other', data: {} })
    await flush()

    expect(queuedDone).toBe(false)
    second.resolve({ id: 'extra', data: {} })
    await Promise.all([inFlight, queued])
    expect(mockGraphSeriesArray.value.map((s) => s.id)).toEqual(['other', 'extra'])
  })
})

describe('useDataVisStore context range around the session window', () => {

  it('keeps the Context preset apart from the Select view Time range', async () => {
    const { store } = await managedPair()
    store.selectedDateBtnId = 2
    await store.setEditTarget('mgd')
    await loadSession()
    await settle()

    await store.onDateBtnClick(0)
    expect(store.contextPresetId).toBe(0)
    expect(store.selectedDateBtnId).toBe(2)

    await store.clearEditTarget()
    expect(store.activePresetId).toBe(2)
  })

  it('records a custom range on the preset in use', async () => {
    const { store } = await managedPair()
    store.selectedDateBtnId = 2
    await store.setEditTarget('mgd')
    await store.setDateRange({ begin: new Date('2025-02-01T00:00:00Z'), end: new Date('2025-03-01T00:00:00Z') })
    expect(store.contextPresetId).toBe(-1)
    expect(store.selectedDateBtnId).toBe(2)
  })

  it('the editor counts presets out from the session window', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    await loadSession()
    await settle()

    await store.onDateBtnClick(0)

    expect(store.beginDate.getTime()).toBe(subtractDays(new Date(WIN_START), 7).getTime())
    expect(store.endDate.getTime()).toBe(subtractDays(new Date(WIN_END), -7).getTime())
  })

  it('YTD resolves like All around the session window', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    await loadSession()
    await settle()

    await store.onDateBtnClick(3)

    expect(store.beginDate.toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect(store.endDate.toISOString()).toBe('2025-12-31T00:00:00.000Z')
  })

  it('the editor counts back from the data end until a session window is known', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')

    await store.onDateBtnClick(0)

    expect(store.endDate.toISOString()).toBe('2025-12-31T00:00:00.000Z')
    expect(store.endDate.getTime() - store.beginDate.getTime()).toBe(7 * 24 * 60 * 60 * 1000)
  })

  it('the Select view ignores a leftover session window', async () => {
    const { store, other } = await managedPair()
    await loadSession()
    await store.plotDatastream(other as any)

    await store.onDateBtnClick(0)

    expect(store.endDate.toISOString()).toBe('2025-12-31T00:00:00.000Z')
  })

  it('re-resolves the context once the session window loads, keeping zoom', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    expect(store.endDate.toISOString()).toBe('2025-12-31T00:00:00.000Z')
    mockPlotlyRef.value = {}
    const { handleNewPlot } = await import('@/utils/plotting/plotly')
    vi.mocked(handleNewPlot).mockClear()
    mockFetchGraphSeries.mockClear()
    mockClearZoomHistory.mockClear()

    await loadSession()
    await settle()

    expect(store.beginDate.getTime()).toBe(subtractMonths(new Date(WIN_START), 1).getTime())
    expect(store.endDate.getTime()).toBe(subtractMonths(new Date(WIN_END), -1).getTime())
    // The source's traces first appear now, so it is a rebuild.
    expect(mockFetchGraphSeries.mock.calls.map((c) => c[0].id)).toEqual(['ctx:src'])
    expect(handleNewPlot).toHaveBeenCalledTimes(1)
    expect(handleNewPlot).toHaveBeenCalledWith(undefined, { preserveZoom: true })
    expect(mockClearZoomHistory).not.toHaveBeenCalled()
  })

  it('reports the editor ready only once the range around the session window has loaded', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    await store.setEditRecord({ dataX: [1], history: [] } as any)
    expect(store.isEditorReady).toBe(false)
    let resolveFetch!: (v: unknown) => void
    mockFetchGraphSeries.mockImplementationOnce(
      () => new Promise((r) => (resolveFetch = r)) as any
    )

    await loadSession()
    await settle()
    expect(store.beginDate.getTime()).toBe(subtractMonths(new Date(WIN_START), 1).getTime())
    expect(store.isEditorReady).toBe(false)

    resolveFetch({ id: 'src', data: {} })
    await settle()
    expect(store.isEditorReady).toBe(true)
  })

  it('reports the editor ready when the session window leaves the range unchanged', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    await store.setEditRecord({ dataX: [1], history: [] } as any)
    await store.setDateRange({ begin: new Date('2025-03-01T00:00:00Z'), end: new Date('2025-04-01T00:00:00Z') })

    await loadSession()
    await settle()

    expect(store.isEditorReady).toBe(true)
  })

  it('does not report the editor ready while a plot load is still drawing', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    await store.setEditRecord({ dataX: [1], history: [] } as any)
    await loadSession()
    await settle()
    expect(store.isEditorReady).toBe(true)
    mockPlotlyRef.value = {}
    const { handleNewPlot } = await import('@/utils/plotting/plotly')
    let finishDraw!: () => void
    vi.mocked(handleNewPlot).mockImplementationOnce(
      () => new Promise<void>((r) => (finishDraw = r))
    )

    const rebuild = store.rebuildPlot()
    await settle()
    expect(store.isEditorReady).toBe(false)

    finishDraw()
    await rebuild
    expect(store.isEditorReady).toBe(true)
  })

  it('does not report the editor ready until the edit record is drawn', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    await loadSession()
    await settle()
    expect(store.isEditorReady).toBe(false)
    mockPlotlyRef.value = {}
    const { handleNewPlot } = await import('@/utils/plotting/plotly')
    let finishDraw!: () => void
    vi.mocked(handleNewPlot).mockImplementationOnce(
      () => new Promise<void>((r) => (finishDraw = r))
    )

    const placing = store.setEditRecord({ dataX: [1], history: [] } as any)
    await settle()
    expect(store.isEditorReady).toBe(false)

    finishDraw()
    await placing
    expect(store.isEditorReady).toBe(true)
  })

  it('does not report the editor ready while another session is opening', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    await store.setEditRecord({ dataX: [1], history: [] } as any)
    await loadSession()
    await settle()
    const { useQcSessionStore } = await import('@/store/qcSession')

    useQcSessionStore().isSwitchingSession = true

    expect(store.isEditorReady).toBe(false)
  })

  it('keeps a custom context range when the session window loads', async () => {
    const { store } = await managedPair()
    await store.setEditTarget('mgd')
    const begin = new Date('2025-03-01T00:00:00Z')
    const end = new Date('2025-04-01T00:00:00Z')
    await store.setDateRange({ begin, end })
    mockFetchObservationsInRange.mockClear()

    await loadSession()
    await settle()

    expect(store.beginDate.getTime()).toBe(begin.getTime())
    expect(store.endDate.getTime()).toBe(end.getTime())
    expect(mockFetchObservationsInRange).not.toHaveBeenCalled()
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

  it('clears every working copy, which belongs to the workspace being left', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.resetState()
    expect(mockClearWorkingCopies).toHaveBeenCalled()
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
      store.endDate,
      undefined,
      expect.objectContaining({ id: 'old' })
    )
  })

  it('re-anchors when the newest datastream is unplotted', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [oldDs(), newerDs()] as any
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

  it('restores a persisted Custom id (-1) as the default preset', async () => {
    localStorage.setItem(
      'dataVisualization',
      JSON.stringify({ selectedDateBtnId: -1 })
    )
    installPinia()
    const { useDataVisStore } = await import('@/store/dataVisualization')
    expect(useDataVisStore().selectedDateBtnId).toBe(1)
  })

  it('restores an unknown persisted id as the default preset', async () => {
    localStorage.setItem(
      'dataVisualization',
      JSON.stringify({ selectedDateBtnId: 9 })
    )
    installPinia()
    const { useDataVisStore } = await import('@/store/dataVisualization')
    expect(useDataVisStore().selectedDateBtnId).toBe(1)
  })
})

describe('useDataVisStore.clearPlottedDatastreams + toggleDatastream', () => {
  it('clearPlottedDatastreams empties the list', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    await store.plotDatastream(makeDs({ id: 'a' }) as any)
    await store.plotDatastream(makeDs({ id: 'b' }) as any)
    await store.clearPlottedDatastreams()
    expect(store.plottedDatastreams).toEqual([])
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

  // Snapshots belong to the editor. Leaving the edit target must not leave
  // a replay line stranded on the plot.
  it('drops snapshots when the editor clears the edit target', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.datastreams = [makeDs({ id: 'mgd', name: 'Raw (QC)' })] as any
    store.qcDatastreamId = 'mgd'

    await store.addSnapshotSeries('snap:sess-1:0', { history: [] } as any, meta as any)
    await store.clearEditTarget()

    expect(store.qcDatastreamId).toBeNull()
    expect(
      mockGraphSeriesArray.value.some((s: any) => s.id === 'snap:sess-1:0')
    ).toBe(false)
  })

  it('drops snapshots even when there is no edit target set', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.plottedDatastreams = [makeDs({ id: 'src', name: 'Raw' })] as any

    await store.addSnapshotSeries('snap:sess-1:0', { history: [] } as any, meta as any)
    await store.clearEditTarget()

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

  it('adds and removes within the group in a single call', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)
    store.plottedDatastreams = [
      makeDs({ id: 'src', name: 'Raw' }),
      makeDs({ id: 'mgd-1', name: 'Raw (QC)' }),
    ] as any

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

    await store.plotSourceSelection('src', ['mgd-1'])

    expect(store.plottedDatastreams.map((d: any) => d.id)).toEqual([
      'other',
      'mgd-1',
    ])
  })

  it('empties the group when nothing is selected', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withGroup(store)
    store.plottedDatastreams = [makeDs({ id: 'mgd-1', name: 'Raw (QC)' })] as any

    await store.plotSourceSelection('src', [])

    expect(store.plottedDatastreams).toEqual([])
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

    await store.plotSourceSelection('src', ['src'])

    expect(mockUpdateOptions).not.toHaveBeenCalled()
  })
})

describe('useDataVisStore managed datastream working copy', () => {
  const withManaged = (store: any) => {
    store.qcHistories = [
      { id: 'h-1', managedDatastreamId: 'mgd', sourceDatastreamId: 'src' },
    ] as any
    store.datastreams = [
      makeDs({ id: 'src', name: 'Raw', phenomenonBeginTime: '2020-01-01T00:00:00Z', phenomenonEndTime: '2022-01-01T00:00:00Z' }),
      makeDs({ id: 'mgd', name: 'Raw (QC)', phenomenonBeginTime: null, phenomenonEndTime: null }),
    ] as any
  }
  const copy = { sessionId: 's-1', record: { dataX: [1], history: [] }, begin: new Date('2021-03-08T00:00:00Z'), end: new Date('2021-08-18T00:00:00Z') }

  it('plots the working copy instead of fetching the empty managed datastream', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withManaged(store)
    mockWorkingCopies.set('mgd', copy)

    await store.plotDatastream(store.datastreams[1] as any)

    expect(mockLoadWorkingCopy).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'mgd' }),
      expect.objectContaining({ id: 'src' }),
      'h-1'
    )
    expect(mockFetchGraphSeries).not.toHaveBeenCalled()
    expect(mockGraphSeriesArray.value.find((s: any) => s.id === 'mgd')?.data).toBe(copy.record)
  })

  it('anchors presets to the working copy session window', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withManaged(store)
    mockWorkingCopies.set('mgd', copy)

    await store.plotDatastream(store.datastreams[1] as any)

    expect(store.endDate.toISOString()).toBe('2021-08-18T00:00:00.000Z')
  })

  it('fetches as before when there is no session in progress', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withManaged(store)

    await store.plotDatastream(store.datastreams[1] as any)

    expect(mockFetchGraphSeries).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'mgd' }),
      expect.any(Date),
      expect.any(Date),
      undefined,
      expect.objectContaining({ id: 'mgd' })
    )
  })

  it('keeps the working copy record on a refresh of an existing series', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withManaged(store)
    mockWorkingCopies.set('mgd', copy)
    await store.plotDatastream(store.datastreams[1] as any)

    await store.setDateRange({
      begin: new Date('2021-01-01T00:00:00Z'),
      end: new Date('2021-02-01T00:00:00Z'),
    })

    expect(mockFetchObservationsInRange).not.toHaveBeenCalledWith(
      expect.objectContaining({ id: 'mgd' }),
      expect.anything(),
      expect.anything()
    )
    expect(mockGraphSeriesArray.value.find((s: any) => s.id === 'mgd')?.data).toBe(copy.record)
  })

  it('falls back to fetching when loading the working copy fails', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withManaged(store)
    mockLoadWorkingCopy.mockRejectedValueOnce(new Error('network'))

    await store.plotDatastream(store.datastreams[1] as any)

    expect(mockFetchGraphSeries).toHaveBeenCalled()
  })

  it('drops the working copy of a managed datastream that is unplotted', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withManaged(store)
    mockWorkingCopies.set('mgd', copy)
    await store.plotDatastream(store.datastreams[0] as any)
    await store.plotDatastream(store.datastreams[1] as any)
    expect(mockInvalidateWorkingCopy).not.toHaveBeenCalled()

    await store.unplotDatastream('mgd')

    expect(mockInvalidateWorkingCopy).toHaveBeenCalledWith('mgd')
  })

  it('drops working copies when the whole plot is cleared', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withManaged(store)
    mockWorkingCopies.set('mgd', copy)
    await store.plotDatastream(store.datastreams[1] as any)

    await store.clearPlottedDatastreams()

    expect(mockInvalidateWorkingCopy).toHaveBeenCalledWith('mgd')
  })

  it('keeps the QC target working copy even when it is not plotted', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    withManaged(store)
    mockWorkingCopies.set('mgd', copy)
    store.qcDatastreamId = 'mgd'
    // Seed the series so `invalidateUnplottedWorkingCopies`'s loop actually
    // has an 'mgd' entry to skip, not an empty array the skip is vacuous over.
    mockGraphSeriesArray.value = [
      { id: 'mgd', name: 'Raw (QC)', data: copy.record, color: '#1', yAxisLabel: 'T' },
    ]

    await store.refreshGraphSeriesArray()

    expect(mockInvalidateWorkingCopy).not.toHaveBeenCalledWith('mgd')
    expect(mockFetchGraphSeries.mock.calls.map((c) => c[0].id)).not.toContain('mgd')
  })
})

describe('useDataVisStore.replaceDatastream', () => {
  it('swaps the datastream in the catalog and the plotted set', async () => {
    const { useDataVisStore } = await import('@/store/dataVisualization')
    const store = useDataVisStore()
    store.datastreams = [
      makeDs({ id: 'a' }),
      makeDs({ id: 'm', phenomenonEndTime: null }),
    ] as any
    store.plottedDatastreams = [makeDs({ id: 'm', phenomenonEndTime: null })] as any
    store.qcDatastreamId = 'm'

    store.replaceDatastream(
      makeDs({ id: 'm', phenomenonEndTime: '2021-06-30T12:00:00Z' }) as any
    )

    expect(store.datastreams.map((d) => d.id)).toEqual(['a', 'm'])
    expect(store.datastreams[1]?.phenomenonEndTime).toBe('2021-06-30T12:00:00Z')
    expect(store.qcDatastream?.phenomenonEndTime).toBe('2021-06-30T12:00:00Z')
  })
})
