/**
 * Reconstruct the datastream state "as of" a session for resume/read-only
 * viewing (spec section 4 / 7.3).
 *
 * Fetch the source window, then replay the session's operations preceded
 * by its ancestors' operations (chronological order) via qc-utils
 * `applyHistory`. `fetchInRange` and `applyHistory` are injected so this
 * unit-tests without a real ObservationRecord.
 *
 * Operations are read from the operations endpoint, not off the session: a
 * session GET can return the summary shape (no embedded `operations`).
 *
 * Caveat (deferred): operations are index-coupled to the exact dataset
 * they were authored against, so reconstructing across sessions authored
 * over different windows can mis-target. This loads the target session's
 * window only; full multi-window reconstruction is a later task.
 */

import type {
  Datastream,
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
import type { FetchObservationsInRange } from './session'

/** API operation -> qc-utils replayable operation (rename operationType/arguments). */
const toSerialized = (op: QualityControlOperation): QcHistoryOperation =>
  ({
    method: op.operationType as unknown as QcHistoryOperation['method'],
    args: Array.isArray(op.arguments) ? op.arguments : [],
  }) as QcHistoryOperation

/**
 * The ordered operations needed to reconstruct a session: every ancestor's
 * operations (oldest first) followed by the target session's operations.
 */
export async function collectSessionOperations(
  qcSessions: QualityControlSessionService,
  qcOperations: QualityControlOperationService,
  historyId: string,
  sessionId: string
): Promise<QcHistoryOperation[]> {
  const ancestors = unwrap(
    await qcSessions.list(historyId, {
      ancestor_of: sessionId,
      fetch_all: true,
    })
  )
  const ordered = [...ancestors].sort(
    (a, b) =>
      new Date(a.phenomenonTimeStart).getTime() -
      new Date(b.phenomenonTimeStart).getTime()
  )

  const operations: QcHistoryOperation[] = []
  for (const ancestor of ordered) {
    const ops = unwrap(
      await qcOperations.list(historyId, ancestor.id, { fetch_all: true })
    )
    operations.push(...ops.map(toSerialized))
  }
  const sessionOps = unwrap(
    await qcOperations.list(historyId, sessionId, { fetch_all: true })
  )
  operations.push(...sessionOps.map(toSerialized))
  return operations
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

export async function reconstructSession(
  deps: ReconstructSessionDeps,
  source: Datastream,
  historyId: string,
  sessionId: string
): Promise<ReconstructSessionResult> {
  const { qcSessions, qcOperations, fetchInRange, applyHistory } = deps

  // The session GET supplies the window; operations come from the
  // operations endpoint (the GET may omit them in the summary shape).
  const session = unwrap(await qcSessions.get(historyId, sessionId))
  const operations = await collectSessionOperations(
    qcSessions,
    qcOperations,
    historyId,
    sessionId
  )

  const record = await fetchInRange(
    source,
    new Date(session.phenomenonTimeStart),
    new Date(session.phenomenonTimeEnd)
  )

  const history: QcHistory = {
    version: '1',
    createdAt: session.createdAt,
    window: {
      startDate: session.phenomenonTimeStart,
      endDate: session.phenomenonTimeEnd,
    },
    operations,
  }

  const report = await applyHistory(record, history)
  return { record, report }
}
