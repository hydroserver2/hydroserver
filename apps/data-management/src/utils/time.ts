export const formatTime = (time?: string | null): string => {
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

export function getLocalTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || '–'
}

export function formatTimeWithZone(time?: string | null) {
  if (!time) return '–'
  return `${formatTime(time)} (${getLocalTimeZone()})`
}
