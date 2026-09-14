import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, toRaw } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { makeQcFake } from '@/services/qualityControl/__tests__/qcServiceFake'
import { unwrap } from '@/services/qualityControl/unwrap'

const qcDatastream = ref<any>(null)
const replaceDatastream = vi.fn()
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ qcDatastream, replaceDatastream }),
}))

const selectedSeries = ref<any>(null)
const redraw = vi.fn()
vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ selectedSeries, redraw }),
}))

const getItem = vi.fn()
const createObservations = vi.fn()
const hs = ref<any>({ datastreams: { getItem, createObservations } })
vi.mock('@/store/hydroserver', () => ({
  useHydroServer: () => ({ hs }),
}))

const fetchObservationsInRange = vi.fn()
vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({ fetchObservationsInRange }),
}))

// qc-utils is only used at runtime by the composable (the service layer
// imports types only), so stub serializeHistory/applyHistory/Snackbar here.
// `vi.hoisted` keeps these safe to reference from the hoisted `vi.mock`
// factory below regardless of how it's shaped.
const { snackbarWarn, ObservationRecordDouble } = vi.hoisted(() => {
  // `loadLatestBase`'s default clone constructs a real `ObservationRecord`.
  // This test double exposes just enough surface for the session layer.
  class ObservationRecordDouble {
    dataX: number[]
    dataY: number[]
    history: any[] = []
    redoStack: any[] = []
    reload = vi.fn(async () => {})
    // `discardUnsavedEdits` calls this on the working copy; mirror the
    // truncate-in-place semantics the other test double in this file uses.
    reloadHistory = vi.fn(async function (this: ObservationRecordDouble, index: number) {
      this.history.splice(index + 1)
      return []
    })
    constructor({ datetimes, dataValues }: { datetimes: number[]; dataValues: number[] }) {
      this.dataX = datetimes
      this.dataY = dataValues
    }
  }
  return { snackbarWarn: vi.fn(), ObservationRecordDouble }
})

vi.mock('@uwrl/qc-utils', () => ({
  serializeHistory: vi.fn((record: any, window: any) => ({
    version: '1',
    createdAt: '2025-01-01T00:00:00Z',
    window,
    operations: (record.history ?? []).map((h: any) => ({
      method: h.method,
      args: h.args ?? [],
    })),
  })),
  applyHistory: vi.fn(async (_record?: unknown, _history?: unknown) => ({
    applied: 0,
    failed: [],
  })),
  Snackbar: { warn: snackbarWarn },
  ObservationRecord: ObservationRecordDouble,
}))

import { useQcSessionStore } from '@/store/qcSession'

const WIN = {
  phenomenonTimeStart: '2025-01-01T00:00:00Z',
  phenomenonTimeEnd: '2025-02-01T00:00:00Z',
}

// Mirrors a real ObservationRecord closely enough for the session layer:
// `redoStack` and `reload` exist on every record and are used when a cached
// one is reset back to its stored state.
const makeRecord = (history: any[] = []) => ({
  history,
  redoStack: [] as any[],
  dataX: [Date.UTC(2025, 0, 1)],
  dataY: [10],
  reload: vi.fn(async () => {}),
  // Stands in for qc-utils: truncate to `0..index` and hand back a selection.
  reloadHistory: vi.fn(async function (this: any, index: number) {
    history.splice(index + 1)
    return []
  }),
})

let qc: ReturnType<typeof makeQcFake>

const wireHs = () => {
  hs.value = {
    datastreams: { getItem, createObservations },
    qualityControlHistories: qc.histories,
    qualityControlSessions: qc.sessions,
    qualityControlOperations: qc.operations,
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  qc = makeQcFake()
  wireHs()
  qcDatastream.value = { id: 'm-1' }
  selectedSeries.value = { data: makeRecord() }
  getItem.mockResolvedValue({ id: 's-1', name: 'Source' })
  createObservations.mockResolvedValue(undefined)
  fetchObservationsInRange.mockResolvedValue(makeRecord())
})

const seedHistory = async () => {
  await qc.histories.create({
    managedDatastreamId: 'm-1',
    sourceDatastreamId: 's-1',
  })
}

describe('useEditSession', () => {
  it('beginEditing resolves the history and needs a session when none is in progress', async () => {
    await seedHistory()
    const { useEditSession } = await import('@/composables/useEditSession')
    const { beginEditing, needsSession, sourceDatastream } = useEditSession()
    await beginEditing()
    expect(sourceDatastream.value?.id).toBe('s-1')
    expect(needsSession.value).toBe(true)
    expect(useQcSessionStore().historyId).toBeTruthy()
  })

  it('beginEditing flags needsHistory when the datastream is not a managed one', async () => {
    const { useEditSession } = await import('@/composables/useEditSession')
    const { beginEditing, needsHistory, needsSession } = useEditSession()
    await beginEditing()
    expect(needsHistory.value).toBe(true)
    expect(needsSession.value).toBe(false)
  })

  it('beginEditing resumes an in-progress session (replays via applyHistory)', async () => {
    const h = unwrap(
      await qc.histories.create({
        managedDatastreamId: 'm-1',
        sourceDatastreamId: 's-1',
      })
    )
    await qc.sessions.create(h.id, WIN)
    // The reconstructed working copy that resume should wire into the series.
    const reconstructed = makeRecord([{ method: 'VALUE_THRESHOLD', args: [] }])
    fetchObservationsInRange.mockResolvedValue(reconstructed)
    const { useEditSession } = await import('@/composables/useEditSession')
    const qcUtils = await import('@uwrl/qc-utils')
    const { beginEditing, needsSession } = useEditSession()
    await beginEditing()
    expect(needsSession.value).toBe(false)
    // The QC-target series shows the reconstructed session's data, but on
    // its own copy: resume never hands out the fetched record itself, so
    // editing it can't mutate the store's cached one.
    const seriesRecord = selectedSeries.value.data
    expect(Array.from(seriesRecord.dataX)).toEqual(Array.from(reconstructed.dataX))
    expect(toRaw(seriesRecord)).not.toBe(reconstructed)
    // applyHistory replayed onto that same copy, not the fetched record.
    // `toRaw` unwraps the reactive proxy Vue puts on the assigned object,
    // since applyHistory was called with the pre-proxy instance.
    const applyHistoryMock = qcUtils.applyHistory as unknown as {
      mock: { calls: unknown[][] }
    }
    expect(applyHistoryMock.mock.calls[0]?.[0]).toBe(toRaw(seriesRecord))
    // Nothing watches for a swapped-in record, so resume has to rebuild the
    // plot itself or it keeps rendering the pre-reconstruction trace.
    expect(redraw).toHaveBeenCalled()
  })

  it('startSession loads the managed datastream as the working base', async () => {
    await seedHistory()
    const managedBase = makeRecord()
    fetchObservationsInRange.mockResolvedValue(managedBase)
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession({ ...WIN, description: 'Jan' })
    expect(session.needsSession.value).toBe(false)
    expect(useQcSessionStore().inProgressSession?.description).toBe('Jan')
    // Working copy comes from the managed datastream (latest committed state).
    expect(fetchObservationsInRange.mock.calls[0]?.[0].id).toBe('m-1')
    expect(Array.from(selectedSeries.value.data.dataX)).toEqual(
      Array.from(managedBase.dataX)
    )
    expect(selectedSeries.value.data).not.toBe(managedBase)
  })

  it('startSession clamps the window to the source datastream extent', async () => {
    await seedHistory()
    getItem.mockResolvedValue({
      id: 's-1',
      name: 'Source',
      phenomenonBeginTime: '2025-01-01T00:00:00Z',
      phenomenonEndTime: '2025-01-15T00:00:00Z',
    })
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    // Display window ends "now" (past the source's last observation).
    await session.startSession({
      phenomenonTimeStart: '2025-01-05T00:00:00Z',
      phenomenonTimeEnd: '2025-06-01T00:00:00Z',
    })
    const inProgress = useQcSessionStore().inProgressSession
    expect(inProgress?.phenomenonTimeEnd).toBe('2025-01-15T00:00:00.000Z')
    expect(inProgress?.phenomenonTimeStart).toBe('2025-01-05T00:00:00.000Z')
  })

  it('saveDraft persists the record operations to the session', async () => {
    await seedHistory()
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession(WIN)
    // A new session starts from a clean base, so the operations are the ones
    // the user applies afterwards.
    selectedSeries.value.data.history.push(
      { method: 'VALUE_THRESHOLD', args: [] },
      { method: 'DELETE_POINTS', args: [] }
    )
    await session.saveDraft()

    const store = useQcSessionStore()
    const ops = unwrap(
      await qc.operations.list(store.historyId!, store.inProgressSession!.id)
    )
    expect(ops.map((o) => o.operationType)).toEqual([
      'VALUE_THRESHOLD',
      'DELETE_POINTS',
    ])
  })

  it('commit pushes observations in replace mode and locks the session', async () => {
    await seedHistory()
    selectedSeries.value = { data: makeRecord([{ method: 'VALUE_THRESHOLD', args: [] }]) }
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession(WIN)
    await session.commit()

    expect(createObservations).toHaveBeenCalledWith(
      'm-1',
      expect.objectContaining({ fields: ['phenomenonTime', 'result'] }),
      { mode: 'replace' }
    )
    const store = useQcSessionStore()
    expect(store.committedSessions.length).toBe(1)
    expect(store.inProgressSession).toBeNull()
  })

  it('commit refreshes the managed datastream so its new extent is known', async () => {
    await seedHistory()
    const refreshed = { id: 'm-1', phenomenonEndTime: '2025-02-01T00:00:00Z' }
    getItem.mockImplementation(async (id: string) =>
      id === 'm-1' ? refreshed : { id: 's-1', name: 'Source' }
    )
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession(WIN)
    await session.commit()

    expect(getItem).toHaveBeenCalledWith('m-1', { expand_related: true })
    expect(replaceDatastream).toHaveBeenCalledWith(refreshed)
  })

  it('commit keeps the session locked even when the datastream refresh throws', async () => {
    await seedHistory()
    getItem.mockImplementation(async (id: string) => {
      if (id === 'm-1') throw new Error('Network error')
      return { id: 's-1', name: 'Source' }
    })
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession(WIN)
    await session.commit()

    const store = useQcSessionStore()
    expect(store.committedSessions.length).toBe(1)
    expect(store.inProgressSession).toBeNull()
    expect(replaceDatastream).not.toHaveBeenCalled()
    expect(snackbarWarn).toHaveBeenCalledWith(
      'Session committed, but the datastream details could not be refreshed. Reload to see its updated time range.'
    )
  })

  it('commit keeps the session locked when the datastream refresh returns null', async () => {
    await seedHistory()
    getItem.mockImplementation(async (id: string) => {
      if (id === 'm-1') return null
      return { id: 's-1', name: 'Source' }
    })
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession(WIN)
    await session.commit()

    const store = useQcSessionStore()
    expect(store.committedSessions.length).toBe(1)
    expect(store.inProgressSession).toBeNull()
    expect(replaceDatastream).not.toHaveBeenCalled()
    expect(snackbarWarn).toHaveBeenCalledWith(
      'Session committed, but the datastream details could not be refreshed. Reload to see its updated time range.'
    )
  })

  it('tracks unsaved edits against the last saved snapshot', async () => {
    await seedHistory()
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession(WIN)
    // Fresh session: working copy matches the saved baseline.
    expect(session.hasUnsavedChanges.value).toBe(false)
    expect(session.unsavedEditCount.value).toBe(0)
    // A new edit on the working copy is unsaved.
    selectedSeries.value.data.history.push({ method: 'DELETE_POINTS', args: [] })
    expect(session.hasUnsavedChanges.value).toBe(true)
    expect(session.unsavedEditCount.value).toBe(1)
    // Saving re-baselines.
    await session.saveDraft()
    expect(session.hasUnsavedChanges.value).toBe(false)
    expect(session.unsavedEditCount.value).toBe(0)
  })

  // A committed session cannot be edited, so nothing about it can be
  // unsaved. Stepping through its history replaces entries as it replays,
  // which an identity comparison would otherwise read as pending edits.
  it('reports no unsaved changes while viewing a read-only session', async () => {
    await seedHistory()
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession(WIN)

    selectedSeries.value.data.history.push({ method: 'DELETE_POINTS', args: [] })
    expect(session.hasUnsavedChanges.value).toBe(true)

    const store = useQcSessionStore()
    store.sessions = [
      { id: 'a', status: 'committed', createdAt: '2025-01-01T00:00:00Z' },
      { id: 'b', status: 'in_progress', createdAt: '2025-02-01T00:00:00Z' },
    ] as any
    store.currentSessionId = 'b'
    store.viewedSessionId = 'a'

    expect(store.isReadOnly).toBe(true)
    expect(session.hasUnsavedChanges.value).toBe(false)
    expect(session.unsavedEditCount.value).toBe(0)
  })

  it('resuming a session starts with no unsaved changes', async () => {
    const h = unwrap(
      await qc.histories.create({
        managedDatastreamId: 'm-1',
        sourceDatastreamId: 's-1',
      })
    )
    await qc.sessions.create(h.id, WIN)
    fetchObservationsInRange.mockResolvedValue(
      makeRecord([{ method: 'VALUE_THRESHOLD', args: [] }])
    )
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    expect(session.hasUnsavedChanges.value).toBe(false)
    expect(session.unsavedEditCount.value).toBe(0)
  })

  it('commit saves the description provided at commit time', async () => {
    await seedHistory()
    selectedSeries.value = {
      data: makeRecord([{ method: 'VALUE_THRESHOLD', args: [] }]),
    }
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession(WIN)
    await session.commit('Reviewed January spike')

    const store = useQcSessionStore()
    expect(store.committedSessions[0]?.description).toBe('Reviewed January spike')
  })
})

describe('useEditSession.discardUnsavedEdits', () => {
  it('drops edits added since the last save', async () => {
    await seedHistory()
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    const { discardUnsavedEdits, hasUnsavedChanges } = session
    await session.beginEditing()
    await session.startSession(WIN)

    const record = selectedSeries.value.data
    record.history.push({ method: 'DELETE_POINTS', args: [] })
    expect(hasUnsavedChanges.value).toBe(true)

    await discardUnsavedEdits()

    expect(record.history).toHaveLength(0)
    expect(hasUnsavedChanges.value).toBe(false)
  })

  it('puts a comment edited in place back to its saved text', async () => {
    await seedHistory()
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    const { saveDraft, discardUnsavedEdits, hasUnsavedChanges } = session
    await session.beginEditing()
    await session.startSession(WIN)

    const record = selectedSeries.value.data
    record.history.push({
      method: 'DELETE_POINTS',
      args: [],
      comment: 'the saved reason',
    })
    await saveDraft()
    expect(hasUnsavedChanges.value).toBe(false)

    record.history[0].comment = 'an unsaved rewrite'
    expect(hasUnsavedChanges.value).toBe(true)

    await discardUnsavedEdits()

    expect(record.history[0].comment).toBe('the saved reason')
    expect(hasUnsavedChanges.value).toBe(false)
  })
})

describe('useEditSession.viewSession', () => {
  it('loads a committed session and marks the editor read-only', async () => {
    const h = unwrap(
      await qc.histories.create({
        managedDatastreamId: 'm-1',
        sourceDatastreamId: 's-1',
      })
    )
    const committed = unwrap(await qc.sessions.create(h.id, WIN))
    await qc.operations.create(h.id, committed.id, [
      { operationType: 'SELECTION' as any, order: 0 },
    ])
    await qc.sessions.commit(h.id, committed.id)
    await qc.sessions.create(h.id, WIN)

    const viewed = makeRecord([])
    fetchObservationsInRange.mockResolvedValue(viewed)

    const { useEditSession } = await import('@/composables/useEditSession')
    const store = useQcSessionStore()
    const session = useEditSession()
    await session.beginEditing()

    await session.viewSession(committed.id)

    // The panel shows the viewed session's data, but on its own copy: a
    // read-only view must not replay onto the source's cached record.
    const seriesRecord = selectedSeries.value.data
    expect(Array.from(seriesRecord.dataX)).toEqual(Array.from(viewed.dataX))
    expect(toRaw(seriesRecord)).not.toBe(viewed)
    expect(store.viewedSessionId).toBe(committed.id)
    expect(store.isReadOnly).toBe(true)
    expect(redraw).toHaveBeenCalled()
  })

  it('moves the selection before loading, so the spinner sits on the new session', async () => {
    const h = unwrap(
      await qc.histories.create({
        managedDatastreamId: 'm-1',
        sourceDatastreamId: 's-1',
      })
    )
    const committed = unwrap(await qc.sessions.create(h.id, WIN))
    await qc.sessions.commit(h.id, committed.id)
    await qc.sessions.create(h.id, WIN)

    const store = useQcSessionStore()
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()

    const seen: Array<{ viewed: string | null; switching: boolean }> = []
    fetchObservationsInRange.mockImplementation(async () => {
      seen.push({
        viewed: store.viewedSessionId,
        switching: store.isSwitchingSession,
      })
      return makeRecord([])
    })

    await session.viewSession(committed.id)

    // While loading, the list already points at the incoming session.
    expect(seen[0]).toEqual({ viewed: committed.id, switching: true })
    expect(store.isSwitchingSession).toBe(false)
  })

  it('restores the previous selection when loading a session fails', async () => {
    const h = unwrap(
      await qc.histories.create({
        managedDatastreamId: 'm-1',
        sourceDatastreamId: 's-1',
      })
    )
    const committed = unwrap(await qc.sessions.create(h.id, WIN))
    await qc.sessions.commit(h.id, committed.id)
    const inProgress = unwrap(await qc.sessions.create(h.id, WIN))

    const store = useQcSessionStore()
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    expect(store.viewedSessionId).toBe(inProgress.id)

    fetchObservationsInRange.mockRejectedValueOnce(new Error('network'))
    await expect(session.viewSession(committed.id)).rejects.toThrow('network')

    expect(store.viewedSessionId).toBe(inProgress.id)
    expect(store.isSwitchingSession).toBe(false)
  })

  it('rejects before a managed datastream is loaded', async () => {
    const { useEditSession } = await import('@/composables/useEditSession')
    await expect(useEditSession().viewSession('s-1')).rejects.toThrow(
      /Load a managed datastream/
    )
  })
})
