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
  const RANGE = win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
  const noOps = vi.fn(async (_record: ObservationRecord, _history: QcHistory) => ({
    applied: 0,
    failed: [],
  }))

  it('bases a window a commit covered on the managed datastream and replays only this session ops', async () => {
    const qc = makeQcFake()
    const historyId = await newHistory(qc)
    const earlier = unwrap(await qc.sessions.create(historyId, RANGE))
    await qc.sessions.commit(historyId, earlier.id)
    const s = unwrap(await qc.sessions.create(historyId, RANGE))
    await qc.operations.create(historyId, s.id, [
      { operationType: 'SELECTION' as any, order: 0 },
      { operationType: 'INTERPOLATE' as any, order: 1 },
    ])

    const fetchInRange = vi.fn().mockResolvedValue(rec([Date.UTC(2025, 0, 1)]))
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

    expect(fetchInRange).toHaveBeenCalledTimes(1)
    const [ds, begin, end] = fetchInRange.mock.calls[0]
    expect(ds).toBe(managed)
    expect((begin as Date).toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect((end as Date).toISOString()).toBe('2025-02-01T00:00:00.000Z')
    // Ancestors are already in the managed datastream.
    expect(captured?.operations.map((o) => o.method)).toEqual([
      'SELECTION',
      'INTERPOLATE',
    ])
    expect(Array.from(result.record.dataX)).toEqual([Date.UTC(2025, 0, 1)])
    expect(result.report.applied).toBe(2)
  })

  it('bases an uncommitted window on the source', async () => {
    const qc = makeQcFake()
    const historyId = await newHistory(qc)
    const s = unwrap(await qc.sessions.create(historyId, RANGE))
    const fetchInRange = vi.fn().mockResolvedValue(rec([Date.UTC(2025, 0, 1)]))

    await reconstructSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory: noOps },
      managed,
      source,
      historyId,
      s.id
    )

    expect(fetchInRange).toHaveBeenCalledTimes(1)
    expect(fetchInRange.mock.calls[0][0]).toBe(source)
  })

  it('replays onto a copy, not the fetched record', async () => {
    const qc = makeQcFake()
    const historyId = await newHistory(qc)
    const s = unwrap(await qc.sessions.create(historyId, RANGE))
    const fetched = rec([Date.UTC(2025, 0, 1)])

    const result = await reconstructSession(
      {
        qcSessions: qc.sessions,
        qcOperations: qc.operations,
        fetchInRange: vi.fn().mockResolvedValue(fetched),
        applyHistory: noOps,
      },
      managed,
      source,
      historyId,
      s.id
    )

    expect(result.record).not.toBe(fetched)
    expect(noOps.mock.calls.at(-1)?.[0]).toBe(result.record)
  })
})

describe('reconstructCommittedSession', () => {
  const day = (d: number) => Date.UTC(2025, 0, d)
  const iso = (d: number) => new Date(day(d)).toISOString()
  const DAYS = Array.from({ length: 10 }, (_, i) => i + 1)
  // Deletes the first point of the session's own window.
  const DELETE_FIRST = [
    { operationType: 'SELECTION', arguments: [[0]], order: 0 },
    { operationType: 'DELETE_POINTS', arguments: [], order: 1 },
  ]

  const setup = async () => {
    const { ObservationRecord: Record, applyHistory } = await import('@uwrl/qc-utils')
    const sourceRecord = new Record({
      datetimes: DAYS.map(day),
      dataValues: DAYS,
    })
    await sourceRecord.reload()
    const qc = makeQcFake()
    const historyId = await newHistory(qc)
    const commit = async (from: number, to: number, ops = DELETE_FIRST) => {
      const s = unwrap(await qc.sessions.create(historyId, win(iso(from), iso(to))))
      await qc.operations.create(historyId, s.id, ops as any)
      await qc.sessions.commit(historyId, s.id)
      return s
    }
    const fetchInRange = vi.fn(async () => sourceRecord)
    const view = async (sessionId: string, opLimit?: number) => {
      const { reconstructCommittedSession } = await import('../reconstructSession')
      return reconstructCommittedSession(
        { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
        source,
        historyId,
        sessionId,
        opLimit
      )
    }
    return { commit, view, fetchInRange, sourceRecord }
  }
  const days = (record: ObservationRecord) =>
    Array.from(record.dataX).map((t) => new Date(t).getUTCDate())

  it('rebuilds a later session on its own window', async () => {
    const { commit, view } = await setup()
    await commit(1, 10)
    const later = await commit(5, 10)

    const { record } = await view(later.id)

    expect(days(record)).toEqual([6, 7, 8, 9, 10])
    expect(record.history.map((h) => h.method)).toEqual(['SELECTION', 'DELETE_POINTS'])
  })

  it('takes the part of a window past earlier commits from the source', async () => {
    const { commit, view } = await setup()
    await commit(1, 5)
    const later = await commit(3, 10)

    const { record } = await view(later.id)

    expect(days(record)).toEqual([4, 5, 6, 7, 8, 9, 10])
  })

  it('leaves out sessions committed after the viewed one', async () => {
    const { commit, view } = await setup()
    const first = await commit(1, 10)
    await commit(5, 10)

    const { record } = await view(first.id)

    expect(days(record)).toEqual([2, 3, 4, 5, 6, 7, 8, 9, 10])
  })

  it('stops the viewed session at opLimit, never its ancestors', async () => {
    const { commit, view } = await setup()
    await commit(1, 10)
    const later = await commit(5, 10)

    const partway = await view(later.id, 1)
    const baseline = await view(later.id, 0)

    expect(days(partway.record)).toEqual([5, 6, 7, 8, 9, 10])
    expect(partway.record.history.map((h) => h.method)).toEqual(['SELECTION'])
    expect(days(baseline.record)).toEqual([5, 6, 7, 8, 9, 10])
    expect(baseline.record.history).toHaveLength(0)
  })

  it('fetches the source once over the chain, never the managed datastream', async () => {
    const { commit, view, fetchInRange } = await setup()
    await commit(1, 5)
    const later = await commit(3, 10)

    await view(later.id)

    expect(fetchInRange).toHaveBeenCalledTimes(1)
    const [ds, begin, end] = fetchInRange.mock.calls[0] as unknown as [Datastream, Date, Date]
    expect(ds).toBe(source)
    expect(begin.getTime()).toBe(day(1))
    expect(end.getTime()).toBe(day(10))
  })

  it('never edits the fetched source record', async () => {
    const { commit, view, sourceRecord } = await setup()
    const first = await commit(1, 10)

    await view(first.id)

    expect(days(sourceRecord)).toEqual(DAYS)
    expect(sourceRecord.history).toHaveLength(0)
  })
})

describe('reconstructCommittedSession: chain order', () => {
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

    const replayed: string[][] = []
    const applyHistory = vi.fn(async (_r: ObservationRecord, h: QcHistory) => {
      replayed.push(h.operations.map((o) => o.method))
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

    expect(replayed).toEqual([['SELECTION'], ['DELETE_POINTS']])
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

    const replayed: string[][] = []
    const applyHistory = vi.fn(async (_r: ObservationRecord, h: QcHistory) => {
      replayed.push(h.operations.map((o) => o.method))
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

    expect(replayed).toEqual([['SELECTION'], ['DELETE_POINTS']])
  })
})

describe('reconstructCommittedSession: attribution', () => {
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

describe('reconstructSession with a real ObservationRecord', () => {
  // Pins the persisted shape of a delete (also seeded by
  // e2e/managed-preview.spec.ts): the SELECTION it consumes, then DELETE_POINTS.
  it('replays a saved SELECTION and DELETE_POINTS onto a copy of the base', async () => {
    const { ObservationRecord: Record, applyHistory, serializeHistory } =
      await import('@uwrl/qc-utils')
    const qc = makeQcFake()
    const historyId = await newHistory(qc)
    const range = win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    const s = unwrap(await qc.sessions.create(historyId, range))
    const persisted = [
      { operationType: 'SELECTION', arguments: [[1, 2, 3]], order: 0 },
      { operationType: 'DELETE_POINTS', arguments: [], order: 1 },
    ]
    await qc.operations.create(historyId, s.id, persisted as any)

    const days = [1, 2, 3, 4, 5, 6].map((d) => Date.UTC(2025, 0, d))
    const sourceRec = new Record({
      datetimes: days,
      dataValues: [10, 20, 30, 40, 50, 60],
    })
    await sourceRec.reload()
    const fetchInRange = vi.fn(async (ds: Datastream) =>
      ds.id === managed.id ? ({ dataX: [] } as unknown as ObservationRecord) : sourceRec
    )

    const { record, report } = await reconstructSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      managed,
      source,
      historyId,
      s.id
    )

    expect(report).toEqual({ applied: 2, failed: [] })
    expect(Array.from(record.dataX)).toEqual([days[0], days[4], days[5]])
    expect(Array.from(record.dataY)).toEqual([10, 50, 60])
    expect(Array.from(sourceRec.dataX)).toEqual(days)
    // Saving the replayed history yields the same operations back.
    const resaved = serializeHistory(record, {
      startDate: range.phenomenonTimeStart,
      endDate: range.phenomenonTimeEnd,
    }).operations.map((op) => [op.method, op.args])
    expect(resaved).toEqual(persisted.map((p) => [p.operationType, p.arguments]))
  })
})
