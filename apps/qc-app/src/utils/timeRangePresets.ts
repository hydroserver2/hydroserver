/**
 * Time range presets. A preset resolves against a data extent rather than
 * the wall clock, so it always lands on observations.
 */

import { subtractDays, subtractMonths, subtractYears } from '@/utils/dateMath'

export interface TimeRangePreset {
  id: number
  label: '1w' | '1m' | '6m' | '1y' | 'YTD' | 'All'
  title: string
}

export interface TimeWindow {
  begin: Date
  end: Date
}

interface PhenomenonTimes {
  phenomenonBeginTime?: string | null
  phenomenonEndTime?: string | null
}

export const TIME_RANGE_PRESETS: readonly TimeRangePreset[] = [
  { id: 0, label: '1w', title: 'Last week of data' },
  { id: 1, label: '1m', title: 'Last month of data' },
  { id: 2, label: '6m', title: 'Last 6 months of data' },
  { id: 4, label: '1y', title: 'Last year of data' },
  { id: 3, label: 'YTD', title: 'Year of the last observation' },
  { id: 5, label: 'All', title: 'All data' },
]

export const DEFAULT_PRESET_ID = 1
export const ALL_PRESET_ID = 5
export const CUSTOM_PRESET_ID = -1

export const findPreset = (id: number) =>
  TIME_RANGE_PRESETS.find((p) => p.id === id)

/** Earliest first to latest last observation; null when none has data. */
export function dataExtent(
  datastreams: readonly PhenomenonTimes[]
): TimeWindow | null {
  let begin = Infinity
  let end = -Infinity
  for (const ds of datastreams) {
    if (!ds.phenomenonBeginTime || !ds.phenomenonEndTime) continue
    begin = Math.min(begin, Date.parse(ds.phenomenonBeginTime))
    end = Math.max(end, Date.parse(ds.phenomenonEndTime))
  }
  if (!Number.isFinite(begin) || !Number.isFinite(end)) return null
  return { begin: new Date(begin), end: new Date(end) }
}

type SpanLabel = '1w' | '1m' | '6m' | '1y'

/** `d` moved back by `times` of a preset span; a negative `times` moves forward. */
function shiftBySpan(label: SpanLabel, d: Date, times: 1 | -1): Date {
  switch (label) {
    case '1w':
      return subtractDays(d, 7 * times)
    case '1m':
      return subtractMonths(d, times)
    case '6m':
      return subtractMonths(d, 6 * times)
    case '1y':
      return subtractYears(d, times)
  }
}

/** The window a preset covers, counting back from the extent's end. */
export function presetWindow(id: number, extent: TimeWindow): TimeWindow | null {
  const preset = findPreset(id)
  if (!preset) return null
  const end = new Date(extent.end)
  switch (preset.label) {
    case 'YTD':
      return { begin: new Date(end.getFullYear(), 0, 1), end }
    case 'All':
      return { begin: new Date(extent.begin), end }
    default:
      return { begin: shiftBySpan(preset.label, end, 1), end }
  }
}

const EDITOR_TITLES: Partial<Record<TimeRangePreset['label'], string>> = {
  '1w': 'A week before and after the session',
  '1m': 'A month before and after the session',
  '6m': '6 months before and after the session',
  '1y': 'A year before and after the session',
}

/** The editor's presets, titled for the session window. YTD is left out: it
 *  has no meaning around a window. */
export const EDITOR_PRESETS: readonly TimeRangePreset[] = TIME_RANGE_PRESETS
  .filter((p) => p.label !== 'YTD')
  .map((p) => ({ ...p, title: EDITOR_TITLES[p.label] ?? p.title }))

/** The chip that shows `selectedId` among `presets`, or null for none. YTD
 *  shows as All where it is not offered, since it loads like All there. The
 *  selection itself is unchanged. */
export function shownPresetId(
  selectedId: number,
  presets: readonly TimeRangePreset[]
): number | null {
  if (presets.some((p) => p.id === selectedId)) return selectedId
  return findPreset(selectedId)?.label === 'YTD' ? ALL_PRESET_ID : null
}

/**
 * The window a preset covers around an edit session's window: the span on
 * each side. All (and YTD, not offered in the editor) is the data extent,
 * widened to cover the window. Spans are not clipped to the data; a fetch
 * past it just returns nothing.
 */
export function presetAroundWindow(
  id: number,
  window: TimeWindow,
  extent: TimeWindow | null
): TimeWindow | null {
  const preset = findPreset(id)
  if (!preset) return null
  switch (preset.label) {
    case 'YTD':
    case 'All': {
      const begin = window.begin.getTime()
      const end = window.end.getTime()
      return {
        begin: new Date(extent ? Math.min(extent.begin.getTime(), begin) : begin),
        end: new Date(extent ? Math.max(extent.end.getTime(), end) : end),
      }
    }
    default:
      return {
        begin: shiftBySpan(preset.label, window.begin, 1),
        end: shiftBySpan(preset.label, window.end, -1),
      }
  }
}
