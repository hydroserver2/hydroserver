/**
 * Session lifecycle helpers: resume the in-progress session for a history or
 * start a new one, and load the data a session edits.
 */

import type {
  Datastream,
  QualityControlSessionService,
  QualityControlSessionContract,
} from '@hydroserver/client'
import type { ObservationRecord } from '@uwrl/qc-utils'
import { unwrap } from './unwrap'
import { recordFrom } from './recordFrom'
import { subtractIntervals, type Interval } from '@/utils/timeIntervals'

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
 * (with its operations) and whether it already existed. On resume the spec
 * is ignored and the existing session keeps its own window.
 */
export async function startOrResumeSession(
  qcSessions: QualityControlSessionService,
  historyId: string,
  spec: QcSessionPostBody
): Promise<{ session: QcSessionDetail; resumed: boolean }> {
  const existing = await getInProgressSession(qcSessions, historyId)
  if (existing) {
    // A single-resource GET returns the detail shape (with operations).
    const session = unwrap(await qcSessions.get(historyId, existing.id)) as QcSessionDetail
    return { session, resumed: true }
  }
  return { session: unwrap(await qcSessions.create(historyId, spec)), resumed: false }
}

/** Fetch signature matching `useObservationStore.fetchObservationsInRange`. */
export type FetchObservationsInRange = (
  datastream: Datastream,
  beginTime: Date,
  endTime: Date
) => Promise<ObservationRecord>

/** Observations as parallel time/value arrays, sorted by time. */
export interface Points {
  dataX: ArrayLike<number>
  dataY: ArrayLike<number>
}

/**
 * The latest committed state for a window, as a standalone record. The
 * managed datastream only holds the ranges committed sessions covered, so
 * those come from it and the rest of the window from the source.
 */
export async function loadLatestBase(
  fetchInRange: FetchObservationsInRange,
  managed: Datastream,
  source: Datastream,
  start: Date,
  end: Date,
  committed: readonly Interval[]
): Promise<ObservationRecord> {
  const window: Interval = [start.getTime(), end.getTime()]
  const fromSource = subtractIntervals([window], committed)
  const fromManaged = subtractIntervals([window], fromSource)
  const [managedRecord, sourceRecord] = await Promise.all([
    fromManaged.length ? fetchInRange(managed, start, end) : undefined,
    fromSource.length ? fetchInRange(source, start, end) : undefined,
  ])
  const base = composeBase(managedRecord, sourceRecord, window, committed)
  // Placeholders come from the source; managed datastreams copy its metadata.
  return recordFrom(base.dataX, base.dataY, source.noDataValue)
}

/**
 * A window's base: `managed` inside the committed intervals, `source`
 * everywhere else. Deleted points inside a committed range stay deleted.
 */
export function composeBase(
  managed: Points | undefined,
  source: Points | undefined,
  window: Interval,
  committed: readonly Interval[]
): { dataX: number[]; dataY: number[] } {
  const fromSource = subtractIntervals([window], committed)
  const fromManaged = subtractIntervals([window], fromSource)
  return mergeSorted(
    pointsWithin(managed, fromManaged),
    pointsWithin(source, fromSource)
  )
}

/** `managed` after a commit replaced `window` with `output`. */
export function replaceWindow(
  managed: Points,
  window: Interval,
  output: Points
): { dataX: number[]; dataY: number[] } {
  const outside = subtractIntervals([[-Infinity, Infinity]], [window])
  return mergeSorted(pointsWithin(managed, outside), output)
}

function pointsWithin(
  points: Points | undefined,
  parts: readonly Interval[]
): { dataX: number[]; dataY: number[] } {
  const dataX: number[] = []
  const dataY: number[] = []
  if (!points) return { dataX, dataY }
  for (let i = 0; i < points.dataX.length; i++) {
    const t = points.dataX[i]!
    if (parts.some(([a, b]) => t >= a && t <= b)) {
      dataX.push(t)
      dataY.push(points.dataY[i]!)
    }
  }
  return { dataX, dataY }
}

function mergeSorted(a: Points, b: Points): { dataX: number[]; dataY: number[] } {
  const dataX: number[] = []
  const dataY: number[] = []
  let i = 0
  let j = 0
  while (i < a.dataX.length || j < b.dataX.length) {
    if (j >= b.dataX.length || (i < a.dataX.length && a.dataX[i]! < b.dataX[j]!)) {
      dataX.push(a.dataX[i]!)
      dataY.push(a.dataY[i++]!)
    } else {
      dataX.push(b.dataX[j]!)
      dataY.push(b.dataY[j++]!)
    }
  }
  return { dataX, dataY }
}

/** The windows of the committed sessions in `sessions`. */
export function committedWindows(
  sessions: readonly Pick<
    QcSessionSummary,
    'status' | 'phenomenonTimeStart' | 'phenomenonTimeEnd'
  >[]
): Interval[] {
  return sessions
    .filter((s) => s.status === 'committed')
    .map((s) => [
      new Date(s.phenomenonTimeStart).getTime(),
      new Date(s.phenomenonTimeEnd).getTime(),
    ])
}
