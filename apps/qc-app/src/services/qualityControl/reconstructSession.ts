/**
 * Rebuild a session's data for editing (resume) or read-only viewing.
 * `fetchInRange` and `applyHistory` are injected for unit testing.
 */

import type {
  Datastream,
  QualityControlSession,
  QualityControlSessionService,
  QualityControlOperationService,
  QualityControlOperation,
} from '@hydroserver/client'
import type {
  ApplyHistoryReport,
  ObservationRecord,
  QcHistory,
  QcHistoryOperation,
} from '@uwrl/qc-utils'
import { unwrap } from './unwrap'
import {
  committedWindows,
  composeBase,
  loadLatestBase,
  replaceWindow,
  type FetchObservationsInRange,
  type Points,
} from './session'
import { recordFrom } from './recordFrom'
import type { Interval } from '@/utils/timeIntervals'
import { commitOrder } from '@/utils/sessionGraph'

/** API operation -> qc-utils replayable operation (rename operationType/arguments). */
const toSerialized = (op: QualityControlOperation): QcHistoryOperation => {
  const serialized = {
    method: op.operationType as unknown as QcHistoryOperation['method'],
    args: Array.isArray(op.arguments) ? op.arguments : [],
  } as QcHistoryOperation
  if (op.comment) serialized.comment = op.comment
  const performedBy = performerName(op)
  if (performedBy) serialized.performedBy = performedBy
  return serialized
}

function performerName(op: QualityControlOperation): string | undefined {
  const by = (op as { createdBy?: { name?: string; email?: string } }).createdBy
  return by?.name?.trim() || by?.email?.trim() || undefined
}

export interface ReconstructSessionDeps {
  qcSessions: QualityControlSessionService
  qcOperations: QualityControlOperationService
  fetchInRange: FetchObservationsInRange
  applyHistory: (
    record: ObservationRecord,
    history: QcHistory
  ) => Promise<ApplyHistoryReport>
}

export interface ReconstructSessionResult {
  record: ObservationRecord
  report: ApplyHistoryReport
}

/** An in-progress session's working copy: its window's latest committed
 *  base with the session's saved operations replayed on top. */
export async function reconstructSession(
  deps: ReconstructSessionDeps,
  managed: Datastream,
  source: Datastream,
  historyId: string,
  sessionId: string
): Promise<ReconstructSessionResult> {
  const { qcSessions, qcOperations, fetchInRange, applyHistory } = deps

  const session = unwrap(await qcSessions.get(historyId, sessionId))
  const start = new Date(session.phenomenonTimeStart)
  const end = new Date(session.phenomenonTimeEnd)

  const committed = unwrap(
    await qcSessions.list(historyId, { status: 'committed', fetch_all: true })
  )
  const record = await loadLatestBase(
    fetchInRange,
    managed,
    source,
    start,
    end,
    committedWindows(committed)
  )
  const ops = unwrap(
    await qcOperations.list(historyId, sessionId, { fetch_all: true })
  )

  const report = await applyHistory(record, historyOf(session, ops))
  return { record, report }
}

/**
 * Rebuild the state a committed session left behind, for read-only viewing.
 * The managed datastream now carries later commits too, so it is replayed
 * from the raw source instead: each session in the ancestor chain, in commit
 * order, on the base its own window had (committed data where an earlier
 * session covered it, source data elsewhere), just as it was edited.
 */
export async function reconstructCommittedSession(
  deps: ReconstructSessionDeps,
  source: Datastream,
  historyId: string,
  sessionId: string,
  opLimit?: number
): Promise<ReconstructSessionResult> {
  const { qcSessions, qcOperations, fetchInRange, applyHistory } = deps

  const session = unwrap(await qcSessions.get(historyId, sessionId))
  const ancestors = unwrap(
    await qcSessions.list(historyId, {
      ancestor_of: sessionId,
      fetch_all: true,
    })
  ).sort((a, b) => commitOrder(a).localeCompare(commitOrder(b)))
  const chain = [...ancestors, session]
  const windows = chain.map(windowOf)

  const [sourceRecord, operations] = await Promise.all([
    fetchInRange(
      source,
      new Date(Math.min(...windows.map(([start]) => start))),
      new Date(Math.max(...windows.map(([, end]) => end)))
    ),
    Promise.all(
      chain.map(async (s) =>
        unwrap(await qcOperations.list(historyId, s.id, { fetch_all: true }))
      )
    ),
  ])

  let managed: Points = { dataX: [], dataY: [] }
  const committed: Interval[] = []
  const replay = async (index: number, ops: QualityControlOperation[]) => {
    const base = composeBase(managed, sourceRecord, windows[index]!, committed)
    const record = await recordFrom(base.dataX, base.dataY, source.noDataValue)
    const report = await applyHistory(record, historyOf(chain[index]!, ops))
    return { record, report }
  }

  for (let i = 0; i < ancestors.length; i++) {
    const { record } = await replay(i, operations[i]!)
    managed = replaceWindow(managed, windows[i]!, record)
    committed.push(windows[i]!)
  }

  const own = operations[chain.length - 1]!
  return replay(chain.length - 1, opLimit == null ? own : own.slice(0, opLimit))
}

const windowOf = (s: QualityControlSession): Interval => [
  new Date(s.phenomenonTimeStart).getTime(),
  new Date(s.phenomenonTimeEnd).getTime(),
]

function historyOf(
  session: QualityControlSession,
  operations: QualityControlOperation[]
): QcHistory {
  return {
    version: '1',
    createdAt: session.createdAt,
    window: {
      startDate: session.phenomenonTimeStart,
      endDate: session.phenomenonTimeEnd,
    },
    operations: operations.map(toSerialized),
  }
}
