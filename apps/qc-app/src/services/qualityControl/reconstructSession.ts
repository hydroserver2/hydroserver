/**
 * Reconstruct the datastream state "as of" a committed session for
 * read-only viewing (spec section 4 / 7.3).
 *
 * Fetch the source window, then replay the session's operations preceded
 * by its ancestors' operations (chronological order) via qc-utils
 * `applyHistory`. `fetchInRange` and `applyHistory` are injected so this
 * unit-tests without a real ObservationRecord.
 *
 * Caveat (deferred): operations are index-coupled to the exact dataset
 * they were authored against, so reconstructing across sessions authored
 * over different windows can mis-target. This loads the target session's
 * window only; full multi-window reconstruction is a later task.
 */

import type {
  Datastream,
  QualityControlSessionService,
  QualityControlOperation,
  QualityControlSessionContract,
} from '@hydroserver/client'
import type {
  ApplyHistoryReport,
  ObservationRecord,
  QcHistory,
  QcHistoryOperation,
} from '@uwrl/qc-utils'
import { unwrap } from './unwrap'
import type { FetchObservationsInRange } from './session'

type QcSessionDetail = QualityControlSessionContract.DetailResponse

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
  historyId: string,
  sessionId: string
): Promise<QcHistoryOperation[]> {
  const session = unwrap(
    await qcSessions.get(historyId, sessionId)
  ) as QcSessionDetail
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
    const detail = unwrap(
      await qcSessions.get(historyId, ancestor.id)
    ) as QcSessionDetail
    operations.push(...detail.operations.map(toSerialized))
  }
  operations.push(...session.operations.map(toSerialized))
  return operations
}

export interface ReconstructSessionDeps {
  qcSessions: QualityControlSessionService
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
  const { qcSessions, fetchInRange, applyHistory } = deps

  const session = unwrap(
    await qcSessions.get(historyId, sessionId)
  ) as QcSessionDetail
  const operations = await collectSessionOperations(qcSessions, historyId, sessionId)

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
