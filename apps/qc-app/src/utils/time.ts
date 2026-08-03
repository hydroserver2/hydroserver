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

/** A session's phenomenon-time window, formatted like the date inputs. */
export function formatDateRange(
  start?: string | null,
  end?: string | null
): string {
  return `${formatDateInput(start)} to ${formatDateInput(end)}`
}

function getLocalTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || '–'
}

export function formatTimeWithZone(time?: string | null) {
  if (!time) return '–'
  return `${formatTime(time)} (${getLocalTimeZone()})`
}
