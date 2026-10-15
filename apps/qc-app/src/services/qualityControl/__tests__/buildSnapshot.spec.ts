/**
 * The builder picks its base and replay source from the session's status:
 * committed sessions replay the server-side ancestor chain, the in-progress
 * session replays the live record so unsaved drafts are included.
 */

import { describe, it, expect, vi } from 'vitest'
import type { Datastream, QualityControlSession } from '@hydroserver/client'
import type { HistoryItem, ObservationRecord, QcHistory } from '@uwrl/qc-utils'
import { buildSnapshotRecord } from '../buildSnapshot'
import type { ReconstructSessionDeps } from '../reconstructSession'
import { SNAPSHOT_BASELINE_INDEX } from '@/utils/snapshotId'

const managed = { id: 'm-1' } as unknown as Datastream
const source = { id: 's-1' } as unknown as Datastream

const rec = () =>
  ({
    dataX: [Date.UTC(2025, 0, 1)],
    dataY: [0],
    history: [],
    redoStack: [],
    reload: vi.fn(async () => {}),
  }) as unknown as ObservationRecord

const inProgressSession = {
  id: 'sess-p',
  status: 'in_progress',
  createdAt: '2025-01-01T00:00:00Z',
  phenomenonTimeStart: '2025-01-01T00:00:00Z',
  phenomenonTimeEnd: '2025-02-01T00:00:00Z',
} as unknown as QualityControlSession

const committedSession = {
  ...inProgressSession,
  id: 'sess-c',
  status: 'committed',
  committedAt: '2025-06-01T00:00:00Z',
} as unknown as QualityControlSession

const ops = (methods: string[]) =>
  methods.map((operationType) => ({ operationType, arguments: [] }))

function makeDeps(base = rec(), committed: QualityControlSession[] = []) {
  let captured: QcHistory | undefined
  const fetchInRange = vi.fn().mockResolvedValue(base)
  const deps = {
    qcSessions: {
      get: vi.fn(async () => ({ ok: true, data: committedSession })),
      list: vi.fn(async () => ({ ok: true, data: committed })),
    },
    qcOperations: {
      list: vi.fn(async () => ({
        ok: true,
        data: ops(['DELETE_POINTS', 'INTERPOLATE']),
      })),
    },
    fetchInRange,
    applyHistory: vi.fn(async (_r: ObservationRecord, h: QcHistory) => {
      captured = h
      return { applied: h.operations.length, failed: [] }
    }),
  } as unknown as ReconstructSessionDeps

  return { base, captured: () => captured, deps, fetchInRange }
}

const history = (methods: string[]): HistoryItem[] =>
  methods.map((method) => ({ method, args: [] })) as unknown as HistoryItem[]

describe('buildSnapshotRecord', () => {
  it('replays the live history up to opIndex for the in-progress session', async () => {
    const { deps, captured, base } = makeDeps()

    const out = await buildSnapshotRecord(deps, {
      historyId: 'h-1',
      session: inProgressSession,
      source,
      managed,
      opIndex: 1,
      liveHistory: history(['SELECTION', 'DELETE_POINTS', 'INTERPOLATE']),
    })

    expect(captured()!.operations.map((o) => o.method)).toEqual([
      'SELECTION',
      'DELETE_POINTS',
    ])
    expect(Array.from(out.dataX)).toEqual(Array.from(base.dataX))
  })

  it('serializes optional live-history fields and defaults missing args', async () => {
    const { deps, captured } = makeDeps()
    const item = {
      method: 'CHANGE_VALUES',
      args: undefined,
      comment: 'reviewed adjustment',
      performedBy: 'analyst',
    } as unknown as HistoryItem

    await buildSnapshotRecord(deps, {
      historyId: 'h-1',
      session: inProgressSession,
      source,
      managed,
      opIndex: 0,
      liveHistory: [item],
    })

    expect(captured()!.operations).toEqual([
      {
        method: 'CHANGE_VALUES',
        args: [],
        comment: 'reviewed adjustment',
        performedBy: 'analyst',
      },
    ])
  })

  it('defaults missing live history to an empty operation list', async () => {
    const { deps, captured } = makeDeps()

    await buildSnapshotRecord(deps, {
      historyId: 'h-1',
      session: inProgressSession,
      source,
      managed,
      opIndex: 0,
    })

    expect(captured()!.operations).toEqual([])
  })

  it('replays nothing for an in-progress baseline snapshot', async () => {
    const { deps, captured } = makeDeps()

    await buildSnapshotRecord(deps, {
      historyId: 'h-1',
      session: inProgressSession,
      source,
      managed,
      opIndex: SNAPSHOT_BASELINE_INDEX,
      liveHistory: history(['SELECTION']),
    })

    expect(captured()!.operations).toEqual([])
  })

  it('loads the in-progress base over the session window', async () => {
    // A commit over the same window, so the base comes from the managed datastream.
    const { deps, fetchInRange } = makeDeps(rec(), [committedSession])

    await buildSnapshotRecord(deps, {
      historyId: 'h-1',
      session: inProgressSession,
      source,
      managed,
      opIndex: 0,
      liveHistory: history(['SELECTION']),
    })

    const [ds, begin, end] = fetchInRange.mock.calls[0]!
    expect(ds).toBe(managed)
    expect(begin.toISOString()).toBe('2025-01-01T00:00:00.000Z')
    expect(end.toISOString()).toBe('2025-02-01T00:00:00.000Z')
  })

  it('delegates a committed session to the reconstruct service with opLimit', async () => {
    const { deps, captured } = makeDeps()

    await buildSnapshotRecord(deps, {
      historyId: 'h-1',
      session: committedSession,
      source,
      managed,
      opIndex: 0,
    })

    // opIndex 0 means "after the first operation", so opLimit is 1.
    expect(captured()!.operations.map((o) => o.method)).toEqual([
      'DELETE_POINTS',
    ])
  })
})
