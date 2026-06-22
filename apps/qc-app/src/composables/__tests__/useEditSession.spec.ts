import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { makeQcFake } from '@/services/qualityControl/__tests__/qcServiceFake'
import { unwrap } from '@/services/qualityControl/unwrap'

const qcDatastream = ref<any>(null)
vi.mock('@/store/dataVisualization', () => ({
  useDataVisStore: () => ({ qcDatastream }),
}))

const selectedSeries = ref<any>(null)
vi.mock('@/store/plotly', () => ({
  usePlotlyStore: () => ({ selectedSeries }),
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
// imports types only), so stub serializeHistory/applyHistory here.
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
  applyHistory: vi.fn(async () => ({ applied: 0, failed: [] })),
}))

import { useQcSessionStore } from '@/store/qcSession'

const WIN = {
  phenomenonTimeStart: '2025-01-01T00:00:00Z',
  phenomenonTimeEnd: '2025-02-01T00:00:00Z',
}

const makeRecord = (history: any[] = []) => ({
  history,
  dataX: [Date.UTC(2025, 0, 1)],
  dataY: [10],
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
    const { useEditSession } = await import('@/composables/useEditSession')
    const qcUtils = await import('@uwrl/qc-utils')
    const { beginEditing, needsSession } = useEditSession()
    await beginEditing()
    expect(needsSession.value).toBe(false)
    expect(qcUtils.applyHistory).toHaveBeenCalled()
  })

  it('startSession creates a session and copies the source window', async () => {
    await seedHistory()
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession({ ...WIN, description: 'Jan' })
    expect(session.needsSession.value).toBe(false)
    expect(useQcSessionStore().inProgressSession?.description).toBe('Jan')
    expect(fetchObservationsInRange.mock.calls.at(-1)?.[0].id).toBe('s-1')
  })

  it('saveDraft persists the record operations to the session', async () => {
    await seedHistory()
    selectedSeries.value = {
      data: makeRecord([
        { method: 'VALUE_THRESHOLD', args: [] },
        { method: 'DELETE_POINTS', args: [] },
      ]),
    }
    const { useEditSession } = await import('@/composables/useEditSession')
    const session = useEditSession()
    await session.beginEditing()
    await session.startSession(WIN)
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
})
