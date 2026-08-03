const formatTime = (time?: string | null): string => {
  if (!time) return '–'

  const date = new Date(time)
  const parts = new Intl.DateTimeFormat('en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).formatToParts(date)

  const get = (type: string) => parts.find((p) => p.type === type)?.value
  const day = get('day')
  const month = get('month')
  const year = get('year')
  const hour = get('hour')
  const minute = get('minute')
  const period = get('dayPeriod')

  return `${day} ${month} ${year}, ${hour}:${minute} ${period}`
}

/** Local date+time matching the time-range date inputs: `MM/DD/YYYY HH:MM`. */
export function formatDateInput(iso?: string | null): string {
  if (!iso) return '–'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${mm}/${dd}/${d.getFullYear()} ${hh}:${min}`
}

const MONTH_DAY = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
})
const MONTH_DAY_YEAR = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})
const CLOCK = new Intl.DateTimeFormat('en-US', {
  hour: 'numeric',
  minute: '2-digit',
  hour12: true,
})

const toDate = (iso?: string | null): Date | null => {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d
}

/** A whole-day boundary, where showing the clock adds nothing. */
const isMidnight = (d: Date) =>
  d.getHours() === 0 && d.getMinutes() === 0 && d.getSeconds() === 0

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
  const sameYear = from.getFullYear() === to.getFullYear()

  if (from.toDateString() === to.toDateString()) {
    const day = MONTH_DAY_YEAR.format(from)
    return wholeDays
      ? day
      : `${day}, ${CLOCK.format(from)} – ${CLOCK.format(to)}`
  }

  const left = sameYear ? MONTH_DAY.format(from) : MONTH_DAY_YEAR.format(from)
  const right = MONTH_DAY_YEAR.format(to)
  return wholeDays
    ? `${left} – ${right}`
    : `${left}, ${CLOCK.format(from)} – ${right}, ${CLOCK.format(to)}`
}

function getLocalTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || '–'
}

export function formatTimeWithZone(time?: string | null) {
  if (!time) return '–'
  return `${formatTime(time)} (${getLocalTimeZone()})`
}
