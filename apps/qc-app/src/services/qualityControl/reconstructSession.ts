/**
 * Reconstruct a session's working state for resume/read-only viewing
 * (spec section 4 / 7.3).
 *
 * Base = the latest committed state (the managed datastream's observations,
 * which already carry every previously-committed session via commit's
 * in-range replace), then replay this session's own draft operations on top.
 * Previously-committed sessions are NOT replayed here; they are already baked
 * into the managed datastream. Falls back to the raw source only when nothing
 * has been committed yet. `fetchInRange` / `applyHistory` are injected so this
 * unit-tests without a real ObservationRecord.
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
import { loadLatestBase, type FetchObservationsInRange } from './session'

/** API operation -> qc-utils replayable operation (rename operationType/arguments). */
const toSerialized = (op: QualityControlOperation): QcHistoryOperation =>
  ({
    method: op.operationType as unknown as QcHistoryOperation['method'],
    args: Array.isArray(op.arguments) ? op.arguments : [],
  }) as QcHistoryOperation

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
  managed: Datastream,
  source: Datastream,
  historyId: string,
  sessionId: string
): Promise<ReconstructSessionResult> {
  const { qcSessions, qcOperations, fetchInRange, applyHistory } = deps

  const session = unwrap(await qcSessions.get(historyId, sessionId))
  const start = new Date(session.phenomenonTimeStart)
  const end = new Date(session.phenomenonTimeEnd)

  // Latest committed state as the base, then this session's own operations.
  const record = await loadLatestBase(fetchInRange, managed, source, start, end)
  const ops = unwrap(
    await qcOperations.list(historyId, sessionId, { fetch_all: true })
  )

  const history: QcHistory = {
    version: '1',
    createdAt: session.createdAt,
    window: {
      startDate: session.phenomenonTimeStart,
      endDate: session.phenomenonTimeEnd,
    },
    operations: ops.map(toSerialized),
  }

  const report = await applyHistory(record, history)
  return { record, report }
}
