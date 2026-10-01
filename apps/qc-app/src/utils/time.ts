/**
 * Date formatting for display, in the zone the user chose (`timeZone.ts`).
 * Each formatter runs in UTC over the instant's wall value, which reads as
 * that zone's clock whatever kind of zone it is.
 */

import {
  displayZone,
  toWall,
  wallParts,
  zoneAbbreviation,
  zoneDescription,
  zoneName,
} from '@/utils/timeZone'

const utc = (options: Intl.DateTimeFormatOptions, locale = 'en-US') =>
  new Intl.DateTimeFormat(locale, { ...options, timeZone: 'UTC' })

const LONG = utc({
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  hour12: true,
})
const MONTH_DAY = utc({ month: 'short', day: 'numeric' })
const MONTH_DAY_YEAR = utc({ month: 'short', day: 'numeric', year: 'numeric' })
const CLOCK = utc({ hour: 'numeric', minute: '2-digit', hour12: true })
// The browser's locale, 24-hour clock with seconds: data point timestamps.
const POINT = utc(
  {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    hour12: false,
    minute: '2-digit',
    second: '2-digit',
  },
  undefined
)

const wall = (ms: number) => new Date(toWall(ms))

const formatTime = (time?: string | null): string => {
  if (!time) return '–'
  const parts = LONG.formatToParts(wall(new Date(time).getTime()))
  const get = (type: string) => parts.find((p) => p.type === type)?.value
  return `${get('day')} ${get('month')} ${get('year')}, ${get('hour')}:${get('minute')} ${get('dayPeriod')}`
}

const toDate = (iso?: string | null): Date | null => {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d
}

/** A data point's timestamp, to the second. */
export function formatDateTime(ms: number): string {
  return Number.isFinite(ms) ? POINT.format(wall(ms)) : '–'
}

/** `Mar 14, 2026`. Day precision, for timestamps shown alongside other text. */
export function formatDayStamp(iso?: string | null): string {
  const d = toDate(iso)
  if (!d) return iso || '–'
  return MONTH_DAY_YEAR.format(wall(d.getTime()))
}

/** A whole-day boundary, where showing the clock adds nothing. */
const isMidnight = (d: Date) => {
  const p = wallParts(d.getTime())
  return p.hours === 0 && p.minutes === 0 && p.seconds === 0
}

/** One boundary: `Mar 14, 2026`, or `Mar 14, 2026, 2:30 PM` off midnight. */
export function formatStamp(when: Date): string {
  if (Number.isNaN(when.getTime())) return '–'
  const w = wall(when.getTime())
  const day = MONTH_DAY_YEAR.format(w)
  return isMidnight(when) ? day : `${day}, ${CLOCK.format(w)}`
}

/**
 * A session's phenomenon-time window, readable at a glance:
 *   `Jan 5 – Feb 1, 2025`                    whole days in one year
 *   `Dec 1, 2024 – Jan 15, 2025`             whole days across years
 *   `Jan 5, 2025, 9:00 AM – 2:30 PM`         within a single day
 *   `Jan 5, 9:00 AM – Feb 1, 2025, 2:30 PM`  partial days
 * The year is stated once when both bounds share it, and clock times are
 * dropped when the window sits on midnight at both ends.
 */
export function formatDateRange(
  start?: string | null,
  end?: string | null
): string {
  const from = toDate(start)
  const to = toDate(end)
  if (!from || !to) return '–'

  const wholeDays = isMidnight(from) && isMidnight(to)
  const a = wallParts(from.getTime())
  const b = wallParts(to.getTime())
  const wf = wall(from.getTime())
  const wt = wall(to.getTime())

  if (a.year === b.year && a.month === b.month && a.day === b.day) {
    const day = MONTH_DAY_YEAR.format(wf)
    return wholeDays ? day : `${day}, ${CLOCK.format(wf)} – ${CLOCK.format(wt)}`
  }

  const left = a.year === b.year ? MONTH_DAY.format(wf) : MONTH_DAY_YEAR.format(wf)
  const right = MONTH_DAY_YEAR.format(wt)
  return wholeDays
    ? `${left} – ${right}`
    : `${left}, ${CLOCK.format(wf)} – ${right}, ${CLOCK.format(wt)}`
}

/** The zone's short name on `date` (`MDT`, `MST`, `UTC`), which tracks
 *  daylight saving. Every date the app shows or takes is in that zone. */
export function timeZoneAbbreviation(date: Date): string {
  return zoneAbbreviation(date.getTime())
}

/** `America/Denver, UTC-06:00` for `date`. */
export function timeZoneDescription(date: Date): string {
  return zoneDescription(date.getTime())
}

export function formatTimeWithZone(time?: string | null) {
  if (!time) return '–'
  return `${formatTime(time)} (${zoneName(displayZone.value)})`
}
