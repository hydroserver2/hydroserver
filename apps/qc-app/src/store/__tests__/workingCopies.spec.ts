import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import { makeQcFake } from '@/services/qualityControl/__tests__/qcServiceFake'
import { unwrap } from '@/services/qualityControl/unwrap'

const hs = ref<any>(null)
vi.mock('@/store/hydroserver', () => ({ useHydroServer: () => ({ hs }) }))

const fetchDetachedRecord = vi.fn()
vi.mock('@/store/observations', () => ({
  useObservationStore: () => ({ fetchDetachedRecord }),
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

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })
  return { promise, resolve }
}

/**
 * Gates every `fetchDetachedRecord` call behind `gate`, and resolves
 * `started` the first time a call is made, so a test can wait for a
 * build to have actually begun (past its generation bump) before racing
 * another store call against it.
 */
function gateFetch() {
  const gate = deferred<void>()
  const started = deferred<void>()
  fetchDetachedRecord.mockImplementation(async (ds: any) => {
    started.resolve()
    await gate.promise
    return ds.id === 'm-1' ? rec([]) : rec([1, 2, 3])
  })
  return { gate, started }
}

/**
 * Gates one `applyHistory` call (the last step of a rebuild's
 * reconstruction) so a test can hold a specific rebuild() call in flight
 * without gating the others sharing the same mocked fetch.
 */
function gateOneApplyHistory() {
  const gate = deferred<{ applied: number; failed: never[] }>()
  applyHistory.mockImplementationOnce(() => gate.promise)
  return gate
}

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
  fetchDetachedRecord.mockImplementation(async (ds: any) =>
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

  it('dedupes concurrent load() calls into a single reconstruction', async () => {
    await startSession()
    const { gate } = gateFetch()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const first = store.load(managed, source, historyId)
    const second = store.load(managed, source, historyId)
    gate.resolve()

    const [a, b] = await Promise.all([first, second])
    expect(a).toBe(b)
    expect(applyHistory).toHaveBeenCalledTimes(1)
    expect(store.get('m-1')).toBe(a)
  })

  it('invalidate() during an in-flight load() leaves no cached entry and the load does not resurrect it', async () => {
    await startSession()
    const { gate, started } = gateFetch()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const pending = store.load(managed, source, historyId)
    await started.promise
    store.invalidate('m-1')
    gate.resolve()

    expect(await pending).toBeNull()
    expect(store.get('m-1')).toBeUndefined()
  })

  it('set() during an in-flight load() keeps the set record', async () => {
    await startSession()
    const { gate, started } = gateFetch()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()
    const setRecord = rec([9]) as any
    const setBegin = new Date('2024-03-01T00:00:00Z')
    const setEnd = new Date('2024-04-01T00:00:00Z')

    const pending = store.load(managed, source, historyId)
    await started.promise
    store.set('m-1', 's-9', setRecord, setBegin, setEnd)
    gate.resolve()

    expect(await pending).toEqual({
      sessionId: 's-9',
      record: setRecord,
      begin: setBegin,
      end: setEnd,
    })
    expect(store.get('m-1')?.record).toBe(setRecord)
  })

  it('invalidate() during an in-flight rebuild() resolves it to null and leaves nothing cached', async () => {
    const session = unwrap(await startSession())
    const { gate, started } = gateFetch()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const pending = store.rebuild(managed, source, historyId, session)
    await started.promise
    store.invalidate('m-1')
    gate.resolve()

    expect(await pending).toBeNull()
    expect(store.get('m-1')).toBeUndefined()
  })

  it('set() during an in-flight rebuild() resolves it to the set record', async () => {
    const session = unwrap(await startSession())
    const { gate, started } = gateFetch()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()
    const setRecord = rec([9]) as any
    const setBegin = new Date('2024-03-01T00:00:00Z')
    const setEnd = new Date('2024-04-01T00:00:00Z')

    const pending = store.rebuild(managed, source, historyId, session)
    await started.promise
    store.set('m-1', 's-9', setRecord, setBegin, setEnd)
    gate.resolve()

    expect(await pending).toEqual({
      sessionId: 's-9',
      record: setRecord,
      begin: setBegin,
      end: setEnd,
    })
    expect(store.get('m-1')?.record).toBe(setRecord)
  })

  it('a second rebuild() supersedes the first, which resolves to the same cached copy regardless of which fetch finishes first', async () => {
    const session = unwrap(await startSession())
    const gate1 = gateOneApplyHistory()
    const gate2 = gateOneApplyHistory()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const first = store.rebuild(managed, source, historyId, session)
    const second = store.rebuild(managed, source, historyId, session)

    // The first call's own fetch settles before the second's, even
    // though the second call is the one that supersedes it: `first`
    // must still chain onto `second`'s result rather than returning its
    // own (discarded) build.
    gate1.resolve({ applied: 0, failed: [] })
    gate2.resolve({ applied: 0, failed: [] })

    const [firstResult, secondResult] = await Promise.all([first, second])
    expect(firstResult).toBe(secondResult)
    expect(store.get('m-1')).toBe(secondResult)
    expect(applyHistory).toHaveBeenCalledTimes(2)
  })

  it('load() during an in-flight rebuild() joins it, so both resolve to the same cached copy', async () => {
    const session = unwrap(await startSession())
    const { gate, started } = gateFetch()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const rebuilding = store.rebuild(managed, source, historyId, session)
    await started.promise
    const loading = store.load(managed, source, historyId)
    gate.resolve()

    const [rebuilt, loaded] = await Promise.all([rebuilding, loading])
    expect(rebuilt).not.toBeNull()
    expect(loaded).toBe(rebuilt)
    expect(store.get('m-1')).toBe(rebuilt)
    expect(applyHistory).toHaveBeenCalledTimes(1)
  })

  it('a load() still listing sessions when a rebuild() starts joins that rebuild', async () => {
    const session = unwrap(await startSession())
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const loading = store.load(managed, source, historyId)
    const rebuilding = store.rebuild(managed, source, historyId, session)

    const [loaded, rebuilt] = await Promise.all([loading, rebuilding])
    expect(rebuilt).not.toBeNull()
    expect(loaded).toBe(rebuilt)
    expect(applyHistory).toHaveBeenCalledTimes(1)
  })

  it('invalidate() drops an in-flight load(), so the next load() builds afresh', async () => {
    await startSession()
    const { gate, started } = gateFetch()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const stale = store.load(managed, source, historyId)
    await started.promise
    store.invalidate('m-1')
    const fresh = store.load(managed, source, historyId)
    gate.resolve()
    await stale

    const copy = await fresh
    expect(copy).not.toBeNull()
    expect(store.get('m-1')).toBe(copy)
  })

  it('clear() drops every cached copy', async () => {
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()
    const begin = new Date('2024-03-01T00:00:00Z')
    const end = new Date('2024-04-01T00:00:00Z')
    store.set('m-1', 's-1', rec([1]) as any, begin, end)
    store.set('m-2', 's-2', rec([2]) as any, begin, end)

    store.clear()

    expect(store.get('m-1')).toBeUndefined()
    expect(store.get('m-2')).toBeUndefined()
    expect(store.extents(['m-1', 'm-2'])).toEqual([])
  })

  it('clear() during an in-flight rebuild() resolves it to null and caches nothing', async () => {
    const session = unwrap(await startSession())
    const { gate, started } = gateFetch()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const pending = store.rebuild(managed, source, historyId, session)
    await started.promise
    store.clear()
    gate.resolve()

    expect(await pending).toBeNull()
    expect(store.get('m-1')).toBeUndefined()
  })

  it('clear() during an in-flight load() build resolves it to null and caches nothing', async () => {
    await startSession()
    const { gate, started } = gateFetch()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const pending = store.load(managed, source, historyId)
    await started.promise
    store.clear()
    gate.resolve()

    expect(await pending).toBeNull()
    expect(store.get('m-1')).toBeUndefined()
  })

  it('clear() while a load() is still listing sessions stops it from building', async () => {
    await startSession()
    const { useWorkingCopiesStore } = await import('@/store/workingCopies')
    const store = useWorkingCopiesStore()

    const pending = store.load(managed, source, historyId)
    store.clear()

    expect(await pending).toBeNull()
    expect(store.get('m-1')).toBeUndefined()
    expect(applyHistory).not.toHaveBeenCalled()
  })
})
