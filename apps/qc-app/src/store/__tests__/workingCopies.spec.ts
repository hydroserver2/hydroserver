import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import { makeQcFake } from '@/services/qualityControl/__tests__/qcServiceFake'
import { unwrap } from '@/services/qualityControl/unwrap'

const hs = ref<any>(null)
vi.mock('@/store/hydroserver', () => ({ useHydroServer: () => ({ hs }) }))

const fetchObservationsInRange = vi.fn()
vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({ fetchObservationsInRange }),
}))

const applyHistory = vi.fn(async () => ({ applied: 0, failed: [] }))
vi.mock('@uwrl/qc-utils', () => ({
  applyHistory: (...args: any[]) => applyHistory(...(args as [])),
  ObservationRecord: class {
    dataX: number[]
    dataY: number[]
    history: any[] = []
    redoStack: any[] = []
    constructor(d: { datetimes: ArrayLike<number>; dataValues: ArrayLike<number> }) {
      this.dataX = Array.from(d.datetimes)
      this.dataY = Array.from(d.dataValues)
    }
    async reload() {}
  },
}))

const managed = { id: 'm-1' } as any
const source = { id: 's-1' } as any
const rec = (xs: number[]) => ({ dataX: xs, dataY: xs.map(() => 1), history: [] })

let qc: ReturnType<typeof makeQcFake>
let historyId: string

beforeEach(async () => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  qc = makeQcFake()
  hs.value = {
    qualityControlSessions: qc.sessions,
    qualityControlOperations: qc.operations,
  }
  historyId = unwrap(
    await qc.histories.create({ managedDatastreamId: 'm-1', sourceDatastreamId: 's-1' })
  ).id
  // Managed datastream empty, source has data.
  fetchObservationsInRange.mockImplementation(async (ds: any) =>
    ds.id === 'm-1' ? rec([]) : rec([1, 2, 3])
  )
})

const startSession = () =>
  qc.sessions.create(historyId, {
    phenomenonTimeStart: '2025-01-01T00:00:00Z',
    phenomenonTimeEnd: '2025-02-01T00:00:00Z',
  })

describe('useWorkingCopiesStore', () => {
  it('returns null and caches nothing without an in-progress session', async () => {
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()
    expect(await store.load(managed, source, historyId)).toBeNull()
    expect(store.get('m-1')).toBeUndefined()
  })

  it('builds the working copy from the session window and replays its operations', async () => {
    const session = unwrap(await startSession())
    await qc.operations.create(historyId, session.id, [
      { operationType: 'SELECTION' as any, order: 0 },
    ])
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const copy = await store.load(managed, source, historyId)

    expect(copy?.sessionId).toBe(session.id)
    expect(copy?.begin.toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect(copy?.end.toISOString()).toBe('2025-02-01T00:00:00.000Z')
    expect(Array.from(copy!.record.dataX)).toEqual([1, 2, 3])
    expect(applyHistory).toHaveBeenCalledTimes(1)
    expect((applyHistory.mock.calls[0] as any[])[0]).toBe(copy!.record)
    expect(store.get('m-1')).toBe(copy)
  })

  it('reuses the cached copy for the same session', async () => {
    await startSession()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const first = await store.load(managed, source, historyId)
    const second = await store.load(managed, source, historyId)

    expect(second).toBe(first)
    expect(applyHistory).toHaveBeenCalledTimes(1)
  })

  it('drops a cached copy once its session is no longer in progress', async () => {
    const session = unwrap(await startSession())
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()
    await store.load(managed, source, historyId)

    await qc.sessions.commit(historyId, session.id)

    expect(await store.load(managed, source, historyId)).toBeNull()
    expect(store.get('m-1')).toBeUndefined()
  })

  it('rebuild always reconstructs, even for a cached session', async () => {
    const session = unwrap(await startSession())
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()
    const first = await store.load(managed, source, historyId)

    const rebuilt = await store.rebuild(managed, source, historyId, session)

    expect(rebuilt).not.toBe(first)
    expect(store.get('m-1')).toBe(rebuilt)
    expect(applyHistory).toHaveBeenCalledTimes(2)
  })

  it('set, invalidate and extents manage entries by managed id', async () => {
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()
    const record = rec([1]) as any
    store.set('m-1', 's-9', record, new Date('2024-03-01T00:00:00Z'), new Date('2024-04-01T00:00:00Z'))

    expect(store.get('m-1')?.record).toBe(record)
    expect(store.extents(['m-1', 'other'])).toEqual([
      {
        phenomenonBeginTime: '2024-03-01T00:00:00.000Z',
        phenomenonEndTime: '2024-04-01T00:00:00.000Z',
      },
    ])

    store.invalidate('m-1')
    expect(store.get('m-1')).toBeUndefined()
    expect(store.extents(['m-1'])).toEqual([])
  })
})
