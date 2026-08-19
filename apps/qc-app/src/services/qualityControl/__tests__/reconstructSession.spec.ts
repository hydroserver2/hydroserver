import { describe, it, expect, vi } from 'vitest'
import type { Datastream } from '@hydroserver/client'
import type { ObservationRecord, QcHistory } from '@uwrl/qc-utils'
import { makeQcFake } from './qcServiceFake'
import { reconstructSession } from '../reconstructSession'
import { unwrap } from '../unwrap'

const win = (start: string, end: string) => ({
  phenomenonTimeStart: start,
  phenomenonTimeEnd: end,
})

// `redoStack` and `reload` exist on every real record; `loadLatestBase`
// uses them to reset a cached one back to its stored state.
const rec = (dataX: number[]) =>
  ({
    dataX,
    dataY: dataX.map(() => 0),
    history: [],
    redoStack: [],
    reload: vi.fn(async () => {}),
  }) as unknown as ObservationRecord

const newHistory = async (qc: ReturnType<typeof makeQcFake>) =>
  unwrap(
    await qc.histories.create({
      managedDatastreamId: 'm-1',
      sourceDatastreamId: 's-1',
    })
  ).id

const managed = { id: 'm-1' } as unknown as Datastream
const source = { id: 's-1' } as unknown as Datastream

describe('reconstructSession', () => {
  it('uses the managed datastream as the base and replays only this session ops', async () => {
    const qc = makeQcFake()
    const historyId = await newHistory(qc)
    const range = win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    const s = unwrap(await qc.sessions.create(historyId, range))
    await qc.operations.create(historyId, s.id, [
      { operationType: 'SELECTION' as any, order: 0 },
      { operationType: 'INTERPOLATE' as any, order: 1 },
    ])

    const managedBase = rec([Date.UTC(2025, 0, 1)])
    const fetchInRange = vi.fn().mockResolvedValue(managedBase)
    let captured: QcHistory | undefined
    const applyHistory = vi.fn(
      async (_rec: ObservationRecord, history: QcHistory) => {
        captured = history
        return { applied: history.operations.length, failed: [] }
      }
    )

    const result = await reconstructSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      managed,
      source,
      historyId,
      s.id
    )

    // Base comes from the managed datastream (latest committed state).
    const [ds, begin, end] = fetchInRange.mock.calls[0]
    expect(ds).toBe(managed)
    expect((begin as Date).toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect((end as Date).toISOString()).toBe('2025-02-01T00:00:00.000Z')

    // Only this session's own ops are replayed (ancestors are baked into
    // the managed datastream).
    expect(captured?.window).toEqual({
      startDate: range.phenomenonTimeStart,
      endDate: range.phenomenonTimeEnd,
    })
    expect(captured?.operations.map((o) => o.method)).toEqual([
      'SELECTION',
      'INTERPOLATE',
    ])
    expect(result.record).toBe(managedBase)
    expect(result.report.applied).toBe(2)
  })

  it('falls back to the source when the managed datastream has no committed data', async () => {
    const qc = makeQcFake()
    const historyId = await newHistory(qc)
    const s = unwrap(
      await qc.sessions.create(
        historyId,
        win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
      )
    )

    const sourceRec = rec([Date.UTC(2025, 0, 1)])
    const fetchInRange = vi
      .fn()
      .mockResolvedValueOnce(rec([])) // managed: nothing committed yet
      .mockResolvedValueOnce(sourceRec) // source fallback
    const applyHistory = vi.fn(async () => ({ applied: 0, failed: [] }))

    const result = await reconstructSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      managed,
      source,
      historyId,
      s.id
    )

    expect(fetchInRange).toHaveBeenCalledTimes(2)
    expect(fetchInRange.mock.calls[0][0]).toBe(managed)
    expect(fetchInRange.mock.calls[1][0]).toBe(source)
    expect(result.record).toBe(sourceRec)
  })
})

describe('reconstructCommittedSession', () => {
  /** Two committed sessions over the same window, the second chained to the first. */
  const chainOf = async (
    qc: ReturnType<typeof makeQcFake>,
    firstRange = win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z'),
    secondRange = win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
  ) => {
    const historyId = await newHistory(qc)
    const first = unwrap(await qc.sessions.create(historyId, firstRange))
    await qc.operations.create(historyId, first.id, [
      { operationType: 'SELECTION' as any, order: 0 },
    ])
    await qc.sessions.commit(historyId, first.id)

    const second = unwrap(await qc.sessions.create(historyId, secondRange))
    await qc.operations.create(historyId, second.id, [
      { operationType: 'DELETE_POINTS' as any, order: 0 },
      { operationType: 'INTERPOLATE' as any, order: 1 },
    ])
    await qc.sessions.commit(historyId, second.id)
    return { historyId, first, second }
  }

  const spies = () => {
    const base = rec([Date.UTC(2025, 0, 1)])
    const fetchInRange = vi.fn().mockResolvedValue(base)
    let captured: QcHistory | undefined
    const applyHistory = vi.fn(
      async (record: ObservationRecord, history: QcHistory) => {
        captured = history
        // Stand in for the engine: one history entry per replayed op.
        history.operations.forEach((op) =>
          (record.history as any[]).push({ method: op.method })
        )
        return { applied: history.operations.length, failed: [] }
      }
    )
    return { base, fetchInRange, applyHistory, captured: () => captured }
  }

  it('replays the ancestor chain from the raw source, not the managed datastream', async () => {
    const qc = makeQcFake()
    const { historyId, second } = await chainOf(qc)
    const { fetchInRange, applyHistory, captured } = spies()
    const { reconstructCommittedSession } = await import('../reconstructSession')

    await reconstructCommittedSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      source,
      historyId,
      second.id
    )

    // The managed datastream already carries every commit, so the base has
    // to be the raw source or the replay reproduces the final state.
    expect(fetchInRange).toHaveBeenCalledTimes(1)
    expect(fetchInRange.mock.calls[0][0]).toBe(source)
    // Ancestor first, then the viewed session's own operations.
    expect(captured()!.operations.map((o) => o.method)).toEqual([
      'SELECTION',
      'DELETE_POINTS',
      'INTERPOLATE',
    ])
  })

  it('loads the union window so a wider ancestor replays in alignment', async () => {
    const qc = makeQcFake()
    const { historyId, second } = await chainOf(
      qc,
      win('2024-12-01T00:00:00Z', '2025-03-01T00:00:00Z'),
      win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    )
    const { fetchInRange, applyHistory } = spies()
    const { reconstructCommittedSession } = await import('../reconstructSession')

    await reconstructCommittedSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      source,
      historyId,
      second.id
    )

    const [, begin, end] = fetchInRange.mock.calls[0]
    expect((begin as Date).toISOString()).toBe('2024-12-01T00:00:00.000Z')
    expect((end as Date).toISOString()).toBe('2025-03-01T00:00:00.000Z')
  })

  it('leaves only the viewed session operations on display', async () => {
    const qc = makeQcFake()
    const { historyId, second } = await chainOf(qc)
    const { fetchInRange, applyHistory } = spies()
    const { reconstructCommittedSession } = await import('../reconstructSession')

    const { record } = await reconstructCommittedSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      source,
      historyId,
      second.id
    )

    // Three ops were replayed to build the data; only this session's two show.
    expect((record.history as any[]).map((h) => h.method)).toEqual([
      'DELETE_POINTS',
      'INTERPOLATE',
    ])
  })

  it('reconstructs the first session without its later commits applied', async () => {
    const qc = makeQcFake()
    const { historyId, first } = await chainOf(qc)
    const { fetchInRange, applyHistory, captured } = spies()
    const { reconstructCommittedSession } = await import('../reconstructSession')

    const { record } = await reconstructCommittedSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      source,
      historyId,
      first.id
    )

    // The later session is a dependent, not an ancestor, so it stays out.
    expect(captured()!.operations.map((o) => o.method)).toEqual(['SELECTION'])
    expect((record.history as any[]).map((h) => h.method)).toEqual(['SELECTION'])
  })

  it('truncates the viewed session operations to opLimit', async () => {
    const qc = makeQcFake()
    const { historyId, second } = await chainOf(qc)
    const { fetchInRange, applyHistory, captured } = spies()
    const { reconstructCommittedSession } = await import('../reconstructSession')

    const { record } = await reconstructCommittedSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      source,
      historyId,
      second.id,
      1
    )

    // Ancestors are never truncated; only this session stops early.
    expect(captured()!.operations.map((o) => o.method)).toEqual([
      'SELECTION',
      'DELETE_POINTS',
    ])
    expect((record.history as any[]).map((h) => h.method)).toEqual([
      'DELETE_POINTS',
    ])
  })

  it('replays ancestors only when opLimit is 0', async () => {
    const qc = makeQcFake()
    const { historyId, second } = await chainOf(qc)
    const { fetchInRange, applyHistory, captured } = spies()
    const { reconstructCommittedSession } = await import('../reconstructSession')

    const { record } = await reconstructCommittedSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      source,
      historyId,
      second.id,
      0
    )

    expect(captured()!.operations.map((o) => o.method)).toEqual(['SELECTION'])
    expect(record.history as any[]).toEqual([])
  })

  it('replays every operation when opLimit is omitted', async () => {
    const qc = makeQcFake()
    const { historyId, second } = await chainOf(qc)
    const { fetchInRange, applyHistory, captured } = spies()
    const { reconstructCommittedSession } = await import('../reconstructSession')

    await reconstructCommittedSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      source,
      historyId,
      second.id
    )

    expect(captured()!.operations.map((o) => o.method)).toEqual([
      'SELECTION',
      'DELETE_POINTS',
      'INTERPOLATE',
    ])
  })
})

describe('reconstructCommittedSession — chain order', () => {
  // The fake allows only one in-progress session at a time, so creation
  // order always matches commit order there. Stub the services directly to
  // build the case where they disagree.
  const ok = (data: unknown) => ({ ok: true, data, status: 200, message: '' })
  const session = (
    id: string,
    createdAt: string,
    committedAt: string | null
  ) => ({
    id,
    createdAt,
    committedAt,
    phenomenonTimeStart: '2025-01-01T00:00:00Z',
    phenomenonTimeEnd: '2025-02-01T00:00:00Z',
  })

  it('orders by commit time, not creation time', async () => {
    // `early` is authored last but committed first, so its operation has to
    // replay first: committing is what wrote its data for the next session.
    const early = session('early', '2099-01-01T00:00:00Z', '2025-06-01T00:00:00Z')
    const viewed = session('viewed', '2025-01-01T00:00:00Z', '2025-06-02T00:00:00Z')

    const qcSessions = {
      get: vi.fn(async () => ok(viewed)),
      list: vi.fn(async () => ok([early])),
    } as any
    const opsById: Record<string, unknown[]> = {
      early: [{ operationType: 'SELECTION', arguments: [] }],
      viewed: [{ operationType: 'DELETE_POINTS', arguments: [] }],
    }
    const qcOperations = {
      list: vi.fn(async (_h: string, id: string) => ok(opsById[id])),
    } as any

    let captured: QcHistory | undefined
    const applyHistory = vi.fn(async (_r: ObservationRecord, h: QcHistory) => {
      captured = h
      return { applied: h.operations.length, failed: [] }
    })
    const { reconstructCommittedSession } = await import('../reconstructSession')

    await reconstructCommittedSession(
      {
        qcSessions,
        qcOperations,
        fetchInRange: vi.fn().mockResolvedValue(rec([Date.UTC(2025, 0, 1)])),
        applyHistory,
      },
      source,
      'h-1',
      'viewed'
    )

    expect(captured!.operations.map((o) => o.method)).toEqual([
      'SELECTION',
      'DELETE_POINTS',
    ])
  })

  it('falls back to creation time when a session is not committed', async () => {
    const uncommitted = session('draft', '2025-01-01T00:00:00Z', null)
    const viewed = session('viewed', '2025-02-01T00:00:00Z', '2025-06-01T00:00:00Z')
    const qcSessions = {
      get: vi.fn(async () => ok(viewed)),
      list: vi.fn(async () => ok([uncommitted])),
    } as any
    const opsById: Record<string, unknown[]> = {
      draft: [{ operationType: 'SELECTION', arguments: [] }],
      viewed: [{ operationType: 'DELETE_POINTS', arguments: [] }],
    }
    const qcOperations = {
      list: vi.fn(async (_h: string, id: string) => ok(opsById[id])),
    } as any

    let captured: QcHistory | undefined
    const applyHistory = vi.fn(async (_r: ObservationRecord, h: QcHistory) => {
      captured = h
      return { applied: h.operations.length, failed: [] }
    })
    const { reconstructCommittedSession } = await import('../reconstructSession')

    await reconstructCommittedSession(
      {
        qcSessions,
        qcOperations,
        fetchInRange: vi.fn().mockResolvedValue(rec([Date.UTC(2025, 0, 1)])),
        applyHistory,
      },
      source,
      'h-1',
      'viewed'
    )

    expect(captured!.operations.map((o) => o.method)).toEqual([
      'SELECTION',
      'DELETE_POINTS',
    ])
  })
})

describe('reconstructCommittedSession — attribution', () => {
  const ok = (data: unknown) => ({ ok: true, data, status: 200, message: '' })

  it('carries the operation performer through to the replayed history', async () => {
    const viewed = {
      id: 'viewed',
      createdAt: '2025-01-01T00:00:00Z',
      committedAt: '2025-06-01T00:00:00Z',
      phenomenonTimeStart: '2025-01-01T00:00:00Z',
      phenomenonTimeEnd: '2025-02-01T00:00:00Z',
    }
    const qcSessions = {
      get: vi.fn(async () => ok(viewed)),
      list: vi.fn(async () => ok([])),
    } as any
    const qcOperations = {
      list: vi.fn(async () =>
        ok([
          {
            operationType: 'SELECTION',
            arguments: [],
            createdBy: { name: 'Ada Lovelace', email: 'ada@example.org' },
          },
          // A contact without a name still attributes, via the email.
          {
            operationType: 'DELETE_POINTS',
            arguments: [],
            createdBy: { name: '', email: 'grace@example.org' },
          },
        ])
      ),
    } as any

    let captured: QcHistory | undefined
    const applyHistory = vi.fn(async (_r: ObservationRecord, h: QcHistory) => {
      captured = h
      return { applied: h.operations.length, failed: [] }
    })
    const { reconstructCommittedSession } = await import('../reconstructSession')

    await reconstructCommittedSession(
      {
        qcSessions,
        qcOperations,
        fetchInRange: vi.fn().mockResolvedValue(rec([Date.UTC(2025, 0, 1)])),
        applyHistory,
      },
      source,
      'h-1',
      'viewed'
    )

    expect(captured!.operations.map((o) => o.performedBy)).toEqual([
      'Ada Lovelace',
      'grace@example.org',
    ])
  })
})
