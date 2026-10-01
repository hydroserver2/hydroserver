import { describe, it, expect, vi } from 'vitest'
import type { QcHistoryOperation } from '@uwrl/qc-utils'
import { makeQcFake } from './qcServiceFake'
import {
  persistSessionOperations,
} from '../persistOperations'
import { unwrap } from '../unwrap'

const op = (
  method: string,
  args: unknown[] = [],
  comment?: string
): QcHistoryOperation =>
  ({ method, args, ...(comment ? { comment } : {}) }) as unknown as QcHistoryOperation

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

describe('persistSessionOperations: wire shape', () => {
  it('sends method/args as operationType/arguments in order, without execution', async () => {
    const qc = makeQcFake()
    const { historyId, sessionId } = await sessionWith(qc)
    const create = vi.spyOn(qc.operations, 'create')
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      { method: 'VALUE_THRESHOLD', args: [{ min: 0 }], execution: { status: 'success' } },
      { method: 'DELETE_POINTS', args: [] },
    ] as unknown as QcHistoryOperation[])
    expect(create.mock.calls[0]![2]).toEqual([
      { operationType: 'VALUE_THRESHOLD', arguments: [{ min: 0 }], order: 0 },
      { operationType: 'DELETE_POINTS', arguments: [], order: 1 },
    ])
  })
})

describe('persistSessionOperations: comments', () => {
  it('sends a comment with a newly-appended operation', async () => {
    const qc = makeQcFake()
    const { historyId, sessionId } = await sessionWith(qc)
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('VALUE_THRESHOLD', [{ min: 0 }], 'sensor fouling'),
    ])
    const [saved] = await listOps(qc, historyId, sessionId)
    expect(saved.comment).toBe('sensor fouling')
  })

  it('patches a comment written onto an already-persisted operation', async () => {
    const qc = makeQcFake()
    const { historyId, sessionId } = await sessionWith(qc)
    const ops = [op('VALUE_THRESHOLD', [{ min: 0 }])]
    await persistSessionOperations(qc.operations, historyId, sessionId, ops)
    expect((await listOps(qc, historyId, sessionId))[0].comment).toBeNull()

    // Same operation, annotated after the fact.
    const annotated = [op('VALUE_THRESHOLD', [{ min: 0 }], 'sensor fouling')]
    await persistSessionOperations(qc.operations, historyId, sessionId, annotated)
    const saved = await listOps(qc, historyId, sessionId)
    expect(saved).toHaveLength(1)
    expect(saved[0].comment).toBe('sensor fouling')
  })

  it('clears a comment that was removed, treating blank as none', async () => {
    const qc = makeQcFake()
    const { historyId, sessionId } = await sessionWith(qc)
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('VALUE_THRESHOLD', [], 'sensor fouling'),
    ])
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('VALUE_THRESHOLD', [], '   '),
    ])
    expect((await listOps(qc, historyId, sessionId))[0].comment).toBeNull()
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

  it('replaces an undone operation with the one applied after it', async () => {
    const qc = makeQcFake()
    const { historyId, sessionId } = await sessionWith(qc)
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('SELECTION'),
      op('DELETE_POINTS'),
      op('CHANGE'),
    ])
    const keptIds = (await listOps(qc, historyId, sessionId))
      .slice(0, 2)
      .map((o) => o.id)

    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('SELECTION'),
      op('DELETE_POINTS'),
      op('INTERPOLATE'),
    ])
    const ops = await listOps(qc, historyId, sessionId)

    expect(ops.map((o) => o.operationType)).toEqual([
      'SELECTION',
      'DELETE_POINTS',
      'INTERPOLATE',
    ])
    expect(ops.map((o) => o.order)).toEqual([0, 1, 2])
    expect(ops.slice(0, 2).map((o) => o.id)).toEqual(keptIds)
  })

  it('replaces an operation whose arguments changed', async () => {
    const qc = makeQcFake()
    const { historyId, sessionId } = await sessionWith(qc)
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('VALUE_THRESHOLD', [{ min: 0 }]),
      op('DELETE_POINTS'),
    ])
    await persistSessionOperations(qc.operations, historyId, sessionId, [
      op('VALUE_THRESHOLD', [{ min: 5 }]),
      op('DELETE_POINTS'),
    ])
    const ops = await listOps(qc, historyId, sessionId)

    expect(ops.map((o) => o.arguments)).toEqual([[{ min: 5 }], []])
    expect(ops.map((o) => o.order)).toEqual([0, 1])
  })

  it('keeps an operation whose arguments only differ in wire form', async () => {
    const qc = makeQcFake()
    const { historyId, sessionId } = await sessionWith(qc)
    const ops = [op('SHIFT_DATETIMES', [new Date('2025-01-05T00:00:00Z'), { b: 1, a: 2 }])]
    await persistSessionOperations(qc.operations, historyId, sessionId, ops)
    const [first] = await listOps(qc, historyId, sessionId)

    await persistSessionOperations(qc.operations, historyId, sessionId, ops)
    const [second] = await listOps(qc, historyId, sessionId)

    expect(second.id).toBe(first.id)
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
