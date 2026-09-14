/**
 * Time range presets. A preset resolves against a data extent rather than
 * the wall clock, so it always lands on observations.
 */

import { subtractDays, subtractMonths, subtractYears } from '@/utils/dateMath'

export interface TimeRangePreset {
  id: number
  icon: string
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
  { id: 0, icon: 'mdi-calendar-week', label: '1w', title: 'Last week of data' },
  { id: 1, icon: 'mdi-calendar-month', label: '1m', title: 'Last month of data' },
  { id: 2, icon: 'mdi-calendar-range', label: '6m', title: 'Last 6 months of data' },
  { id: 4, icon: 'mdi-calendar', label: '1y', title: 'Last year of data' },
  { id: 3, icon: 'mdi-calendar-today', label: 'YTD', title: 'Year to date' },
  { id: 5, icon: 'mdi-infinity', label: 'All', title: 'All data' },
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

/** The window a preset covers, counting back from the extent's end. */
export function presetWindow(id: number, extent: TimeWindow): TimeWindow | null {
  const preset = findPreset(id)
  if (!preset) return null
  const end = new Date(extent.end)
  switch (preset.label) {
    case '1w':
      return { begin: subtractDays(end, 7), end }
    case '1m':
      return { begin: subtractMonths(end, 1), end }
    case '6m':
      return { begin: subtractMonths(end, 6), end }
    case '1y':
      return { begin: subtractYears(end, 1), end }
    case 'YTD':
      return { begin: new Date(end.getFullYear(), 0, 1), end }
    case 'All':
      return { begin: new Date(extent.begin), end }
  }
}
