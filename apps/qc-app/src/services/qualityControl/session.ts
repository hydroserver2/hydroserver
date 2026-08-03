/**
 * Session lifecycle helpers (spec section 5): resume the in-progress
 * session for a history or start a new one, and load the source-data
 * window for editing ("Copy data from source").
 *
 * Pure (deps injected) for unit testing; a composable wires these to the
 * QC client and the observation store.
 */

import type {
  Datastream,
  QualityControlSessionService,
  QualityControlSessionContract,
} from '@hydroserver/client'
import type { ObservationRecord } from '@uwrl/qc-utils'
import { unwrap } from './unwrap'

type QcSessionDetail = QualityControlSessionContract.DetailResponse
type QcSessionSummary = QualityControlSessionContract.SummaryResponse
type QcSessionPostBody = QualityControlSessionContract.PostBody

/** The history's single in-progress session, or null. */
export async function getInProgressSession(
  qcSessions: QualityControlSessionService,
  historyId: string
): Promise<QcSessionSummary | null> {
  const list = unwrap(await qcSessions.list(historyId, { status: 'in_progress' }))
  return (list[0] as QcSessionSummary | undefined) ?? null
}

/**
 * Resume the history's in-progress session if one exists, otherwise start
 * a new one with the given window/description. Returns the session detail
 * (with its operations) either way. On resume the spec is ignored — the
 * existing session keeps its own window.
 */
export async function startOrResumeSession(
  qcSessions: QualityControlSessionService,
  historyId: string,
  spec: QcSessionPostBody
): Promise<QcSessionDetail> {
  const existing = await getInProgressSession(qcSessions, historyId)
  if (existing) {
    // A single-resource GET returns the detail shape (with operations).
    return unwrap(await qcSessions.get(historyId, existing.id)) as QcSessionDetail
  }
  return unwrap(await qcSessions.create(historyId, spec))
}

/** Fetch signature matching `useObservationStore.fetchObservationsInRange`. */
export type FetchObservationsInRange = (
  datastream: Datastream,
  beginTime: Date,
  endTime: Date
) => Promise<ObservationRecord>

/**
 * "Copy data from source": fetch the session's phenomenon-time window from
 * the source datastream into an ObservationRecord for editing. The mixed
 * managed+source fetch (windows overlapping committed sessions) is
 * deferred; this loads source-only.
 */
export async function loadSourceWindow(
  fetchInRange: FetchObservationsInRange,
  source: Datastream,
  session: Pick<QcSessionDetail, 'phenomenonTimeStart' | 'phenomenonTimeEnd'>
): Promise<ObservationRecord> {
  return fetchInRange(
    source,
    new Date(session.phenomenonTimeStart),
    new Date(session.phenomenonTimeEnd)
  )
}

/**
 * The latest committed state for a window. Every commit replays its session
 * into the managed datastream (in-range replace), so the managed datastream's
 * observations already carry all previously-committed sessions. Falls back to
 * the raw source when nothing has been committed yet (the first session).
 */
export async function loadLatestBase(
  fetchInRange: FetchObservationsInRange,
  managed: Datastream,
  source: Datastream,
  start: Date,
  end: Date
): Promise<ObservationRecord> {
  const base = await fetchInRange(managed, start, end)
  const record =
    (base.dataX?.length ?? 0) > 0 ? base : await fetchInRange(source, start, end)
  return resetToStoredState(record)
}

/**
 * The observation store keeps one `ObservationRecord` per datastream and
 * hands back the same instance, so this may be the one a previous session
 * was editing. Truncated in place to keep bound references.
 */
async function resetToStoredState(
  record: ObservationRecord
): Promise<ObservationRecord> {
  if (!record.history.length && !record.redoStack.length) return record
  record.history.length = 0
  record.redoStack.length = 0
  await record.reload()
  return record
}
