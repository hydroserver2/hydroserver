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
  ({ dataX, dataY: dataX.map(() => 0), history: [] }) as unknown as ObservationRecord

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
