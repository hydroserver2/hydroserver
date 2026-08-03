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
import { loadLatestBase, type FetchObservationsInRange } from './session'

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

/**
 * Rebuild the state a committed session left behind, for read-only viewing.
 * The managed datastream carries every commit, so the ancestor chain is
 * replayed from the raw source instead.
 *
 * Ordered by `committedAt`, since commit order is what a later session
 * built on. Loaded over the union of the chain's windows: operations replay
 * against array indices, so a narrower base misaligns a wider ancestor.
 */
export async function reconstructCommittedSession(
  deps: ReconstructSessionDeps,
  source: Datastream,
  historyId: string,
  sessionId: string
): Promise<ReconstructSessionResult> {
  const { qcSessions, qcOperations, fetchInRange, applyHistory } = deps

  const session = unwrap(await qcSessions.get(historyId, sessionId))
  const ancestors = unwrap(
    await qcSessions.list(historyId, {
      ancestor_of: sessionId,
      fetch_all: true,
    } as never)
  )

  const chainOrder = (s: QualityControlSession) => s.committedAt ?? s.createdAt
  const chain = [...ancestors, session].sort((a, b) =>
    chainOrder(a).localeCompare(chainOrder(b))
  )

  const startMs = Math.min(
    ...chain.map((s) => new Date(s.phenomenonTimeStart).getTime())
  )
  const endMs = Math.max(
    ...chain.map((s) => new Date(s.phenomenonTimeEnd).getTime())
  )

  const record = await fetchInRange(source, new Date(startMs), new Date(endMs))

  const perSession = await Promise.all(
    chain.map(async (s) =>
      unwrap(await qcOperations.list(historyId, s.id, { fetch_all: true }))
    )
  )

  const history: QcHistory = {
    version: '1',
    createdAt: session.createdAt,
    window: {
      startDate: new Date(startMs).toISOString(),
      endDate: new Date(endMs).toISOString(),
    },
    operations: perSession.flat().map(toSerialized),
  }

  const report = await applyHistory(record, history)

  const ownCount = perSession[chain.length - 1]?.length ?? 0
  record.history.splice(0, record.history.length - ownCount)

  return { record, report }
}
