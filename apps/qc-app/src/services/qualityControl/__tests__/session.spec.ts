import { describe, it, expect, vi } from 'vitest'
import type { Datastream } from '@hydroserver/client'
import type { ObservationRecord } from '@uwrl/qc-utils'
import { makeQcFake } from './qcServiceFake'
import {
  getInProgressSession,
  startOrResumeSession,
  loadSourceWindow,
  loadLatestBase,
} from '../session'
import { unwrap } from '../unwrap'

const WIN = {
  phenomenonTimeStart: '2025-01-01T00:00:00Z',
  phenomenonTimeEnd: '2025-02-01T00:00:00Z',
}

const historyWith = async (qc: ReturnType<typeof makeQcFake>) => {
  const h = unwrap(
    await qc.histories.create({
      managedDatastreamId: 'm-1',
      sourceDatastreamId: 's-1',
    })
  )
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
    const s = unwrap(await qc.sessions.create(historyId, WIN))
    const found = await getInProgressSession(qc.sessions, historyId)
    expect(found?.id).toBe(s.id)
    expect(found?.status).toBe('in_progress')
  })
})

describe('startOrResumeSession', () => {
  it('starts a new session when none is in progress', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const session = await startOrResumeSession(qc.sessions, historyId, {
      ...WIN,
      description: 'Jan QC',
    })
    expect(session.status).toBe('in_progress')
    expect(session.description).toBe('Jan QC')
    expect(unwrap(await qc.sessions.list(historyId))).toHaveLength(1)
  })

  it('resumes the existing session instead of creating another (spec ignored)', async () => {
    const qc = makeQcFake()
    const historyId = await historyWith(qc)
    const first = unwrap(await qc.sessions.create(historyId, WIN))
    const resumed = await startOrResumeSession(qc.sessions, historyId, {
      phenomenonTimeStart: '2030-01-01T00:00:00Z',
      phenomenonTimeEnd: '2030-02-01T00:00:00Z',
    })
    expect(resumed.id).toBe(first.id)
    expect(resumed.phenomenonTimeStart).toBe(WIN.phenomenonTimeStart)
    expect(unwrap(await qc.sessions.list(historyId))).toHaveLength(1)
  })
})

describe('loadSourceWindow', () => {
  it('fetches the session window from the source datastream', async () => {
    const record = {} as ObservationRecord
    const fetchInRange = vi.fn().mockResolvedValue(record)
    const source = { id: 's-1' } as unknown as Datastream

    const result = await loadSourceWindow(fetchInRange, source, WIN)

    expect(result).toBe(record)
    expect(fetchInRange).toHaveBeenCalledTimes(1)
    const [ds, begin, end] = fetchInRange.mock.calls[0]
    expect(ds).toBe(source)
    expect((begin as Date).toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect((end as Date).toISOString()).toBe('2025-02-01T00:00:00.000Z')
  })
})

describe('loadLatestBase', () => {
  const managed = { id: 'm-1' } as unknown as Datastream
  const source = { id: 's-1' } as unknown as Datastream
  const start = new Date('2025-01-01T00:00:00Z')
  const end = new Date('2025-02-01T00:00:00Z')
  // Real records always carry `history`/`redoStack`; `loadLatestBase` clears
  // them, since the store hands back a cached instance.
  const recWith = (n: number) =>
    ({
      dataX: Array(n).fill(0),
      dataY: Array(n).fill(0),
      history: [],
      redoStack: [],
      reload: vi.fn(async () => {}),
    }) as unknown as ObservationRecord

  it('uses the managed datastream when it has committed data', async () => {
    const managedRec = recWith(3)
    const fetchInRange = vi.fn().mockResolvedValue(managedRec)
    const result = await loadLatestBase(fetchInRange, managed, source, start, end)
    expect(result).toBe(managedRec)
    expect(fetchInRange).toHaveBeenCalledTimes(1)
    expect(fetchInRange.mock.calls[0][0]).toBe(managed)
  })

  it('falls back to the source when the managed datastream is empty', async () => {
    const sourceRec = recWith(2)
    const fetchInRange = vi
      .fn()
      .mockResolvedValueOnce(recWith(0))
      .mockResolvedValueOnce(sourceRec)
    const result = await loadLatestBase(fetchInRange, managed, source, start, end)
    expect(result).toBe(sourceRec)
    expect(fetchInRange).toHaveBeenCalledTimes(2)
    expect(fetchInRange.mock.calls[1][0]).toBe(source)
  })
})

describe('loadLatestBase — cached record', () => {
  // The observation store keeps one record per datastream and returns the
  // same instance, so a new session's base can arrive carrying the previous
  // session's replayed operations.
  const makeRecord = (history: any[], dataX = [1, 2, 3]) => {
    const reload = vi.fn(async () => {})
    return {
      dataX,
      history,
      redoStack: [] as any[],
      reload,
    } as any
  }

  it('clears operations left on the cached record and reloads from raw', async () => {
    const cached = makeRecord([{ method: 'SELECTION' }, { method: 'DELETE_POINTS' }])
    const fetchInRange = vi.fn().mockResolvedValue(cached)

    const base = await loadLatestBase(
      fetchInRange,
      { id: 'm-1' } as any,
      { id: 's-1' } as any,
      new Date('2025-01-01T00:00:00Z'),
      new Date('2025-02-01T00:00:00Z')
    )

    expect(base.history).toHaveLength(0)
    expect(base.redoStack).toHaveLength(0)
    // Data was mutated by the previous session's replay, so raw is restored.
    expect(cached.reload).toHaveBeenCalled()
  })

  it('keeps the array reference so bound consumers stay connected', async () => {
    const history: any[] = [{ method: 'SELECTION' }]
    const cached = makeRecord(history)
    const fetchInRange = vi.fn().mockResolvedValue(cached)

    const base = await loadLatestBase(
      fetchInRange,
      { id: 'm-1' } as any,
      { id: 's-1' } as any,
      new Date('2025-01-01T00:00:00Z'),
      new Date('2025-02-01T00:00:00Z')
    )

    expect(base.history).toBe(history)
  })

  it('leaves a clean record untouched', async () => {
    const cached = makeRecord([])
    const fetchInRange = vi.fn().mockResolvedValue(cached)

    await loadLatestBase(
      fetchInRange,
      { id: 'm-1' } as any,
      { id: 's-1' } as any,
      new Date('2025-01-01T00:00:00Z'),
      new Date('2025-02-01T00:00:00Z')
    )

    expect(cached.reload).not.toHaveBeenCalled()
  })

  it('falls back to the source when the managed datastream is empty', async () => {
    const empty = makeRecord([], [])
    const sourceRecord = makeRecord([{ method: 'SELECTION' }])
    const fetchInRange = vi
      .fn()
      .mockResolvedValueOnce(empty)
      .mockResolvedValueOnce(sourceRecord)

    const base = await loadLatestBase(
      fetchInRange,
      { id: 'm-1' } as any,
      { id: 's-1' } as any,
      new Date('2025-01-01T00:00:00Z'),
      new Date('2025-02-01T00:00:00Z')
    )

    expect(base).toBe(sourceRecord)
    expect(base.history).toHaveLength(0)
  })
})
