import { describe, it, expect } from 'vitest'
import type { QcHistoryOperation } from '@uwrl/qc-utils'
import { makeQcFake } from './qcServiceFake'
import {
  sessionOperationsFromSerialized,
  persistSessionOperations,
} from '../persistOperations'
import { unwrap } from '../unwrap'

const op = (method: string, args: unknown[] = []): QcHistoryOperation =>
  ({ method, args }) as unknown as QcHistoryOperation

const WIN = {
  phenomenonTimeStart: '2025-01-01T00:00:00Z',
  phenomenonTimeEnd: '2025-02-01T00:00:00Z',
}

const sessionWith = async (qc: ReturnType<typeof makeQcFake>) => {
  const h = unwrap(
    await qc.histories.create({
      managedDatastreamId: 'm-1',
      sourceDatastreamId: 's-1',
    })
  )
  const s = unwrap(await qc.sessions.create(h.id, WIN))
  return { historyId: h.id, sessionId: s.id }
}

const listOps = async (
  qc: ReturnType<typeof makeQcFake>,
  historyId: string,
  sessionId: string
) => unwrap(await qc.operations.list(historyId, sessionId))

describe('sessionOperationsFromSerialized', () => {
  it('maps method/args to operationType/arguments, assigns order, drops execution', () => {
    const serialized = [
      { method: 'VALUE_THRESHOLD', args: [{ min: 0 }], execution: { status: 'success' } },
      { method: 'DELETE_POINTS', args: [] },
    ] as unknown as QcHistoryOperation[]
    expect(sessionOperationsFromSerialized(serialized)).toEqual([
      { operationType: 'VALUE_THRESHOLD', arguments: [{ min: 0 }], order: 0 },
      { operationType: 'DELETE_POINTS', arguments: [], order: 1 },
    ])
  })
})

describe('persistSessionOperations', () => {
  it('appends newly-added operations, leaving existing ones in place', async () => {
    const qc = makeQcFake()
    const { historyId, sessionId } = await sessionWith(qc)
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('SELECTION'),
      op('DELETE_POINTS'),
    ])
    const firstIds = (await listOps(qc, historyId, sessionId)).map((o) => o.id)

    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('SELECTION'),
      op('DELETE_POINTS'),
      op('CHANGE'),
    ])
    const ops = await listOps(qc, historyId, sessionId)

    expect(ops.map((o) => o.operationType)).toEqual([
      'SELECTION',
      'DELETE_POINTS',
      'CHANGE',
    ])
    expect(ops.map((o) => o.order)).toEqual([0, 1, 2])
    // The first two are the same records, not recreated.
    expect(ops.slice(0, 2).map((o) => o.id)).toEqual(firstIds)
  })

  it('removes operations undone since the last save (trailing delete)', async () => {
    const qc = makeQcFake()
    const { historyId, sessionId } = await sessionWith(qc)
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('SELECTION'),
      op('DELETE_POINTS'),
      op('CHANGE'),
    ])
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('SELECTION'),
      op('DELETE_POINTS'),
    ])
    const ops = await listOps(qc, historyId, sessionId)
    expect(ops.map((o) => o.operationType)).toEqual(['SELECTION', 'DELETE_POINTS'])
  })

  it('clears operations when given an empty set', async () => {
    const qc = makeQcFake()
    const { historyId, sessionId } = await sessionWith(qc)
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('SELECTION'),
    ])
    await persistSessionOperations(qc.operations, historyId, sessionId, [])
    expect(await listOps(qc, historyId, sessionId)).toHaveLength(0)
  })
})
