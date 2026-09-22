/**
 * Rules for a new edit session's window (history spec 7.2.3 and 7.2.4):
 * inside the source's observed extent, and never leaving a gap before or
 * after the committed history. Overlapping committed sessions is allowed.
 */

import { formatStamp } from '@/utils/time'
import {
  ALL_PRESET_ID,
  TIME_RANGE_PRESETS,
  dataExtent,
  presetWindow,
  type TimeWindow,
} from '@/utils/timeRangePresets'

export interface SourceExtent {
  phenomenonBeginTime?: string | null
  phenomenonEndTime?: string | null
}

export interface SessionRange {
  status: string
  phenomenonTimeStart: string
  phenomenonTimeEnd: string
}

export type SessionWindowIssueKind =
  | 'no-data'
  | 'order'
  | 'starts-before-source'
  | 'ends-after-source'
  | 'outside-source'
  | 'gap-after-history'
  | 'gap-before-history'

/** A one-click correction. It carries only the endpoints at fault, so the
 *  one the user already got right is never moved. */
export interface SessionWindowFix {
  begin?: Date
  end?: Date
  /** Button copy, naming the date it sets. */
  label: string
}

export interface SessionWindowIssue {
  kind: SessionWindowIssueKind
  message: string
  /** Null when no correction of the offending endpoints would be valid. */
  fix: SessionWindowFix | null
}

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

/** The source's own extent, which the rules above always accept while the
 *  committed history lies inside it. */
export function defaultSessionWindow(source: SourceExtent): TimeWindow | null {
  return dataExtent([source])
}

export const NO_SOURCE_DATA_ISSUE: SessionWindowIssue = {
  kind: 'no-data',
  message: 'The source datastream has no observations to edit.',
  fix: null,
}

/** The first broken rule, with the correction it suggests. The correction is
 *  not yet checked against the other rules; `sessionWindowIssue` does that. */
function firstProblem(
  window: TimeWindow,
  source: SourceExtent,
  sessions: readonly SessionRange[]
): SessionWindowIssue | null {
  const extent = dataExtent([source])
  if (!extent) return NO_SOURCE_DATA_ISSUE

  const begin = window.begin.getTime()
  const end = window.end.getTime()
  if (!(begin < end)) {
    return { kind: 'order', message: 'The start must be before the end.', fix: null }
  }

  const early = begin < extent.begin.getTime()
  const late = end > extent.end.getTime()
  if (early && late) {
    return {
      kind: 'outside-source',
      message: `The window must be within the source data (${formatStamp(extent.begin)} to ${formatStamp(extent.end)}).`,
      fix: {
        begin: new Date(extent.begin),
        end: new Date(extent.end),
        label: `Use ${formatStamp(extent.begin)} to ${formatStamp(extent.end)}`,
      },
    }
  }
  if (early) {
    return {
      kind: 'starts-before-source',
      message: `The start is before the source data, which begins ${formatStamp(extent.begin)}.`,
      fix: {
        begin: new Date(extent.begin),
        label: `Start at ${formatStamp(extent.begin)}`,
      },
    }
  }
  if (late) {
    return {
      kind: 'ends-after-source',
      message: `The end is after the source data, which ends ${formatStamp(extent.end)}.`,
      fix: { end: new Date(extent.end), label: `End at ${formatStamp(extent.end)}` },
    }
  }

  const history = committedExtent(sessions)
  if (history) {
    if (begin > history.end.getTime()) {
      return {
        kind: 'gap-after-history',
        message: `This leaves a gap after the committed history, which ends ${formatStamp(history.end)}. Start on or before that.`,
        fix: {
          begin: new Date(history.end),
          label: `Start at ${formatStamp(history.end)}`,
        },
      }
    }
    if (end < history.begin.getTime()) {
      return {
        kind: 'gap-before-history',
        message: `This leaves a gap before the committed history, which starts ${formatStamp(history.begin)}. End on or after that.`,
        fix: {
          end: new Date(history.begin),
          label: `End at ${formatStamp(history.begin)}`,
        },
      }
    }
  }
  return null
}

/** `null` when `window` is valid, otherwise the broken rule and the fix for
 *  it. A fix is only offered when applying it leaves a valid window. */
export function sessionWindowIssue(
  window: TimeWindow,
  source: SourceExtent,
  sessions: readonly SessionRange[]
): SessionWindowIssue | null {
  const issue = firstProblem(window, source, sessions)
  if (!issue?.fix) return issue
  const fixed = {
    begin: issue.fix.begin ?? window.begin,
    end: issue.fix.end ?? window.end,
  }
  return firstProblem(fixed, source, sessions) ? { ...issue, fix: null } : issue
}

export interface SessionWindowPreset {
  id: string
  label: string
  /** Tooltip, or the reason when the preset is disabled. */
  title: string
  window: TimeWindow
  /** Short reason the preset breaks a rule, or `null` when it is usable. */
  disabledReason: string | null
}

const PRESET_REASONS: Record<SessionWindowIssueKind, string> = {
  'no-data': 'No observations',
  order: 'Empty window',
  'starts-before-source': 'Longer than the record',
  'ends-after-source': 'Past the end of the record',
  'outside-source': 'Longer than the record',
  'gap-after-history': 'Leaves a gap after the committed work',
  'gap-before-history': 'Leaves a gap before the committed work',
}

/** Whole record first, then shorter spans counting back from its end. */
const SPAN_PRESETS: readonly { id: string; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: '1y', label: '1y' },
  { id: '6m', label: '6m' },
  { id: '1m', label: '1m' },
]

function toPreset(
  id: string,
  label: string,
  title: string,
  window: TimeWindow,
  source: SourceExtent,
  sessions: readonly SessionRange[]
): SessionWindowPreset {
  const issue = firstProblem(window, source, sessions)
  return {
    id,
    label,
    title,
    window,
    disabledReason: issue ? PRESET_REASONS[issue.kind] : null,
  }
}

/**
 * One-click windows for the session-window step, each already checked
 * against the rules. Spans anchor to the source's last observation, and a
 * committed history adds the "continue where the commit ended" case.
 */
export function sessionWindowPresets(
  source: SourceExtent,
  sessions: readonly SessionRange[]
): SessionWindowPreset[] {
  const extent = dataExtent([source])
  if (!extent) return []

  const presets: SessionWindowPreset[] = []
  for (const span of SPAN_PRESETS) {
    const base = TIME_RANGE_PRESETS.find((p) => p.label === span.label)
    const window = base ? presetWindow(base.id, extent) : null
    if (!base || !window) continue
    const title = base.id === ALL_PRESET_ID ? 'The whole source record' : base.title
    presets.push(toPreset(span.id, span.label, title, window, source, sessions))
  }

  const history = committedExtent(sessions)
  if (history) {
    presets.push(
      toPreset(
        'since',
        'Since commit',
        'From the end of the committed work to the end of the record',
        { begin: new Date(history.end), end: new Date(extent.end) },
        source,
        sessions
      )
    )
  }
  return presets
}
