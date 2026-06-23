import { describe, it, expect, vi } from 'vitest'
import type { Datastream } from '@hydroserver/client'
import type { ObservationRecord, QcHistory } from '@uwrl/qc-utils'
import { makeQcFake } from './qcServiceFake'
import {
  collectSessionOperations,
  reconstructSession,
} from '../reconstructSession'
import { unwrap } from '../unwrap'

const win = (start: string, end: string) => ({
  phenomenonTimeStart: start,
  phenomenonTimeEnd: end,
})

/** Create a committed session with the given operations. */
const committedSession = async (
  qc: ReturnType<typeof makeQcFake>,
  historyId: string,
  range: { phenomenonTimeStart: string; phenomenonTimeEnd: string },
  ops: string[]
) => {
  const s = unwrap(await qc.sessions.create(historyId, range))
  if (ops.length) {
    await qc.operations.create(
      historyId,
      s.id,
      ops.map((operationType, i) => ({
        operationType: operationType as any,
        order: i,
      }))
    )
  }
  await qc.sessions.commit(historyId, s.id)
  return s
}

const newHistory = async (qc: ReturnType<typeof makeQcFake>) =>
  unwrap(
    await qc.histories.create({
      managedDatastreamId: 'm-1',
      sourceDatastreamId: 's-1',
    })
  ).id

describe('collectSessionOperations', () => {
  it('returns just the session ops when there are no ancestors', async () => {
    const qc = makeQcFake()
    const historyId = await newHistory(qc)
    const s = await committedSession(
      qc,
      historyId,
      win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z'),
      ['SELECTION', 'DELETE_POINTS']
    )
    const ops = await collectSessionOperations(
      qc.sessions,
      qc.operations,
      historyId,
      s.id
    )
    expect(ops.map((o) => o.method)).toEqual(['SELECTION', 'DELETE_POINTS'])
  })

  it('prepends ancestor ops (oldest first) before the target session ops', async () => {
    const qc = makeQcFake()
    const historyId = await newHistory(qc)
    // A (Jan-Mar) then B (Feb-Apr) overlaps A -> B depends on A
    await committedSession(
      qc,
      historyId,
      win('2025-01-01T00:00:00Z', '2025-03-01T00:00:00Z'),
      ['VALUE_THRESHOLD']
    )
    const b = await committedSession(
      qc,
      historyId,
      win('2025-02-01T00:00:00Z', '2025-04-01T00:00:00Z'),
      ['CHANGE_VALUES']
    )

    const ops = await collectSessionOperations(
      qc.sessions,
      qc.operations,
      historyId,
      b.id
    )
    expect(ops.map((o) => o.method)).toEqual(['VALUE_THRESHOLD', 'CHANGE_VALUES'])
  })
})

describe('reconstructSession', () => {
  it('fetches the source window and replays the ordered operations via applyHistory', async () => {
    const qc = makeQcFake()
    const historyId = await newHistory(qc)
    const range = win('2025-01-01T00:00:00Z', '2025-02-01T00:00:00Z')
    const s = await committedSession(qc, historyId, range, [
      'SELECTION',
      'INTERPOLATE',
    ])

    const record = {} as ObservationRecord
    const fetchInRange = vi.fn().mockResolvedValue(record)
    let captured: QcHistory | undefined
    const applyHistory = vi.fn(async (_rec: ObservationRecord, history: QcHistory) => {
      captured = history
      return { applied: history.operations.length, failed: [] }
    })
    const source = { id: 's-1' } as unknown as Datastream

    const result = await reconstructSession(
      { qcSessions: qc.sessions, qcOperations: qc.operations, fetchInRange, applyHistory },
      source,
      historyId,
      s.id
    )

    // fetched the source over the session window
    const [ds, begin, end] = fetchInRange.mock.calls[0]
    expect(ds).toBe(source)
    expect((begin as Date).toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect((end as Date).toISOString()).toBe('2025-02-01T00:00:00.000Z')

    // replayed the ordered ops over that window
    expect(captured?.version).toBe('1')
    expect(captured?.window).toEqual({
      startDate: range.phenomenonTimeStart,
      endDate: range.phenomenonTimeEnd,
    })
    expect(captured?.operations.map((o) => o.method)).toEqual([
      'SELECTION',
      'INTERPOLATE',
    ])
    expect(result.record).toBe(record)
    expect(result.report.applied).toBe(2)
  })
})
