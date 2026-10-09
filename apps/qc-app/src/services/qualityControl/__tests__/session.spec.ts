import { describe, it, expect, vi } from 'vitest'
import type { Datastream } from '@hydroserver/client'
import type { ObservationRecord } from '@uwrl/qc-utils'
import { createHistory, createSession, makeQcFake } from './qcServiceFake'
import {
  getInProgressSession,
  startOrResumeSession,
  loadLatestBase,
  withOperations,
} from '../session'
import { unwrap } from '../unwrap'

const WIN = {
  phenomenonTimeStart: '2025-01-01T00:00:00Z',
  phenomenonTimeEnd: '2025-02-01T00:00:00Z',
}

const historyWith = async (qc: ReturnType<typeof makeQcFake>) => {
  const h = await createHistory(qc, {
    managedDatastreamId: 'm-1',
    sourceDatastreamId: 's-1',
  })
  return h.id
}

describe('getInProgressSession', () => {
  it('returns null when no session is in progress', async () => {
    const qc = makeQcFake()
    expect(await getInProgressSession(qc.sessions, await historyWith(qc))).toBeNull()
  })

  it('returns the in-progress session when one exists', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const s = await createSession(qc, historyId, WIN)
    const found = await getInProgressSession(qc.sessions, historyId)
    expect(found?.id).toBe(s.id)
    expect(found?.status).toBe('in_progress')
  })
})

describe('startOrResumeSession', () => {
  it('starts a new session when none is in progress', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const { session, resumed } = await startOrResumeSession(qc.sessions, qc.operations, historyId, {
      ...WIN,
      description: 'Jan QC',
    })
    expect(resumed).toBe(false)
    expect(session.status).toBe('in_progress')
    expect(session.description).toBe('Jan QC')
    expect(unwrap(await qc.sessions.list(historyId))).toHaveLength(1)
  })

  it('resumes the existing session instead of creating another (spec ignored)', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const first = await createSession(qc, historyId, WIN)
    const { session, resumed } = await startOrResumeSession(qc.sessions, qc.operations, historyId, {
      phenomenonTimeStart: '2030-01-01T00:00:00Z',
      phenomenonTimeEnd: '2030-02-01T00:00:00Z',
    })
    expect(resumed).toBe(true)
    expect(session.id).toBe(first.id)
    expect(session.phenomenonTimeStart).toBe(WIN.phenomenonTimeStart)
    expect(unwrap(await qc.sessions.list(historyId))).toHaveLength(1)
  })
})

describe('withOperations', () => {
  const op = (order: number) => ({ operationType: 'SELECTION', arguments: {}, order })

  it('attaches each session its operations, in order', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const s = await createSession(qc, historyId, WIN)
    await qc.operations.create(historyId, s.id, [op(1), op(0)] as any)

    const [loaded] = await withOperations(qc.operations, historyId, [s])

    expect(loaded!.id).toBe(s.id)
    expect(loaded!.operations.map((o) => o.order)).toEqual([0, 1])
  })

  it('throws when a session operations fail to load', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const s = await createSession(qc, historyId, WIN)
    vi.spyOn(qc.operations, 'list').mockResolvedValue({
      ok: false,
      status: 500,
      message: 'Server error',
    } as any)

    await expect(withOperations(qc.operations, historyId, [s])).rejects.toThrow(
      'Server error'
    )
  })

  it('resumes a session with the operations it saved', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const s = await createSession(qc, historyId, WIN)
    await qc.operations.create(historyId, s.id, [op(0)] as any)

    const { session } = await startOrResumeSession(qc.sessions, qc.operations, historyId, WIN)

    expect(session.operations).toHaveLength(1)
  })
})

describe('loadLatestBase', () => {
  const managed = { id: 'm-1', noDataValue: -1 } as unknown as Datastream
  const source = { id: 's-1', noDataValue: -9999 } as unknown as Datastream
  const day = (m: number, d: number) => Date.UTC(2025, m, d)
  const rec = (points: [number, number][]) =>
    ({
      dataX: points.map(([t]) => t),
      dataY: points.map(([, v]) => v),
      history: [],
    }) as unknown as ObservationRecord
  const fetchFrom = (byId: Record<string, ObservationRecord>) =>
    vi.fn(async (ds: Datastream) => byId[ds.id]!)
  const points = (r: ObservationRecord) =>
    Array.from(r.dataX).map((t, i) => [t, r.dataY[i]])

  it('uses the managed datastream where sessions were committed', async () => {
    const fetchInRange = fetchFrom({ 'm-1': rec([[day(0, 10), 7]]) })

    const base = await loadLatestBase(
      fetchInRange,
      managed,
      source,
      new Date(day(0, 1)),
      new Date(day(0, 31)),
      [[day(0, 1), day(0, 31)]]
    )

    expect(points(base)).toEqual([[day(0, 10), 7]])
    expect(fetchInRange).toHaveBeenCalledTimes(1)
    expect(fetchInRange.mock.calls[0]![0]).toBe(managed)
  })

  it('uses the source where nothing is committed', async () => {
    const fetchInRange = fetchFrom({ 's-1': rec([[day(0, 10), 3]]) })

    const base = await loadLatestBase(
      fetchInRange,
      managed,
      source,
      new Date(day(0, 1)),
      new Date(day(0, 31)),
      []
    )

    expect(points(base)).toEqual([[day(0, 10), 3]])
    expect(fetchInRange).toHaveBeenCalledTimes(1)
    expect(fetchInRange.mock.calls[0]![0]).toBe(source)
  })

  it("takes the source's no-data value", async () => {
    const base = await loadLatestBase(
      fetchFrom({ 's-1': rec([]) }),
      managed,
      source,
      new Date(day(0, 1)),
      new Date(day(0, 31)),
      []
    )

    expect(base.noDataValue).toBe(-9999)
  })

  it('fills the uncommitted part of the window from the source', async () => {
    // January was committed with the Jan 25 point deleted.
    const fetchInRange = fetchFrom({
      'm-1': rec([[day(0, 20), 7]]),
      's-1': rec([
        [day(0, 20), 3],
        [day(0, 25), 4],
        [day(1, 10), 5],
      ]),
    })

    const base = await loadLatestBase(
      fetchInRange,
      managed,
      source,
      new Date(day(0, 15)),
      new Date(day(2, 1)),
      [[day(0, 1), day(0, 31)]]
    )

    expect(points(base)).toEqual([
      [day(0, 20), 7],
      [day(1, 10), 5],
    ])
  })

  // The store hands back its cached record; editing a copy is what keeps a
  // plotted raw line free of draft edits.
  it('never returns the fetched record itself', async () => {
    const sourceRec = rec([[day(0, 10), 3]])
    const fetchInRange = fetchFrom({ 's-1': sourceRec })

    const base = await loadLatestBase(
      fetchInRange,
      managed,
      source,
      new Date(day(0, 1)),
      new Date(day(0, 31)),
      []
    )

    expect(base).not.toBe(sourceRec)
  })
})
