/**
 * Build the ObservationRecord for a history snapshot: a session's state after
 * its operation `opIndex` (or its baseline, at -1).
 *
 * The window is always the session chain's own window, never the plot's
 * current time range. Operations replay against array indices, so a different
 * base window would corrupt the replay.
 */

import type { Datastream, QualityControlSession } from '@hydroserver/client'
import type {
  HistoryItem,
  ObservationRecord,
  QcHistory,
  QcHistoryOperation,
} from '@uwrl/qc-utils'
import { loadLatestBase } from './session'
import {
  reconstructCommittedSession,
  type ReconstructSessionDeps,
} from './reconstructSession'
import { SNAPSHOT_BASELINE_INDEX } from '@/utils/snapshotId'

export interface BuildSnapshotParams {
  historyId: string
  session: QualityControlSession
  source: Datastream
  managed: Datastream
  opIndex: number
  /** Live draft history, required when the session is in progress. */
  liveHistory?: HistoryItem[]
}

/** Live history entry -> replayable operation, dropping runtime-only fields. */
function toSerialized(item: HistoryItem): QcHistoryOperation {
  const op: QcHistoryOperation = { method: item.method, args: item.args ?? [] }
  if (item.comment) op.comment = item.comment
  if (item.performedBy) op.performedBy = item.performedBy
  return op
}

export async function buildSnapshotRecord(
  deps: ReconstructSessionDeps,
  params: BuildSnapshotParams
): Promise<ObservationRecord> {
  const { historyId, session, source, managed, opIndex, liveHistory } = params

  if (session.status === 'committed') {
    const { record } = await reconstructCommittedSession(
      deps,
      source,
      historyId,
      session.id,
      opIndex + 1
    )
    return record
  }

  const record = await loadLatestBase(
    deps.fetchInRange,
    managed,
    source,
    new Date(session.phenomenonTimeStart),
    new Date(session.phenomenonTimeEnd)
  )

  const operations =
    opIndex <= SNAPSHOT_BASELINE_INDEX
      ? []
      : (liveHistory ?? []).slice(0, opIndex + 1).map(toSerialized)

  const history: QcHistory = {
    version: '1',
    createdAt: session.createdAt,
    window: {
      startDate: session.phenomenonTimeStart,
      endDate: session.phenomenonTimeEnd,
    },
    operations,
  }

  await deps.applyHistory(record, history)
  return record
}
