/**
 * Rules for a new edit session's window (history spec 7.2.3 and 7.2.4):
 * inside the source's observed extent, and never leaving a gap before or
 * after the committed history. Overlapping committed sessions is allowed.
 */

import { dataExtent, type TimeWindow } from '@/utils/timeRangePresets'

export interface SourceExtent {
  phenomenonBeginTime?: string | null
  phenomenonEndTime?: string | null
}

export interface SessionRange {
  status: string
  phenomenonTimeStart: string
  phenomenonTimeEnd: string
}

const formatMs = (ms: number) => new Date(ms).toLocaleString()

export function committedExtent(
  sessions: readonly SessionRange[]
): TimeWindow | null {
  let begin = Infinity
  let end = -Infinity
  for (const s of sessions) {
    if (s.status !== 'committed') continue
    begin = Math.min(begin, Date.parse(s.phenomenonTimeStart))
    end = Math.max(end, Date.parse(s.phenomenonTimeEnd))
  }
  if (!Number.isFinite(begin) || !Number.isFinite(end)) return null
  return { begin: new Date(begin), end: new Date(end) }
}

export function defaultSessionWindow(
  source: SourceExtent,
  sessions: readonly SessionRange[]
): TimeWindow | null {
  const extent = dataExtent([source])
  if (!extent) return null
  const history = committedExtent(sessions)
  if (history && history.end.getTime() < extent.end.getTime()) {
    return { begin: new Date(history.end), end: extent.end }
  }
  return extent
}

export function validateSessionWindow(
  window: TimeWindow,
  source: SourceExtent,
  sessions: readonly SessionRange[]
): string | null {
  const extent = dataExtent([source])
  if (!extent) return 'The source datastream has no observations to edit.'
  const begin = window.begin.getTime()
  const end = window.end.getTime()
  if (!(begin < end)) return 'The start must be before the end.'
  if (begin < extent.begin.getTime() || end > extent.end.getTime()) {
    return `The window must be within the source data (${formatMs(extent.begin.getTime())} to ${formatMs(extent.end.getTime())}).`
  }
  const history = committedExtent(sessions)
  if (history) {
    if (begin > history.end.getTime()) {
      return `This leaves a gap after the committed history, which ends ${formatMs(history.end.getTime())}. Start on or before that.`
    }
    if (end < history.begin.getTime()) {
      return `This leaves a gap before the committed history, which starts ${formatMs(history.begin.getTime())}. End on or after that.`
    }
  }
  return null
}
