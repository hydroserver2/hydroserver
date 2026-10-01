/**
 * Time zone math on epoch ms. A zone is `UTC`, a fixed UTC offset like
 * `-0700` (the `FIXED_OFFSET_TIMEZONES` values), or an IANA name.
 *
 * A "wall" value is an instant moved by the zone's offset, so its UTC
 * fields read as the zone's clock.
 */

const MINUTE = 60_000
const DAY = 86_400_000

const FIXED_OFFSET = /^([+-])(\d{2}):?(\d{2})$/

const partFormatters = new Map<string, Intl.DateTimeFormat>()

function partFormatter(timeZone: string): Intl.DateTimeFormat {
  let fmt = partFormatters.get(timeZone)
  if (!fmt) {
    fmt = new Intl.DateTimeFormat('en-US', {
      timeZone,
      hourCycle: 'h23',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      second: 'numeric',
    })
    partFormatters.set(timeZone, fmt)
  }
  return fmt
}

/** Whether `zone` is `UTC`, a fixed offset, or an IANA zone this runtime knows. */
export function isValidTimeZone(zone: unknown): zone is string {
  if (typeof zone !== 'string' || !zone) return false
  if (zone === 'UTC' || FIXED_OFFSET.test(zone)) return true
  try {
    partFormatter(zone)
    return true
  } catch {
    return false
  }
}

function ianaOffsetMs(ms: number, timeZone: string): number {
  const parts = partFormatter(timeZone).formatToParts(ms)
  const get = (type: string) => Number(parts.find((p) => p.type === type)?.value)
  const wall = Date.UTC(
    get('year'),
    get('month') - 1,
    get('day'),
    get('hour'),
    get('minute'),
    get('second')
  )
  return wall - (ms - (((ms % 1000) + 1000) % 1000))
}

/** An offset that holds from `from` until `until`. */
interface Segment {
  from: number
  until: number
  offset: number
}

// Per zone, per UTC day: one segment, or two around a transition.
const segmentCache = new Map<string, Map<number, Segment[]>>()

function ianaSegment(ms: number, timeZone: string): Segment {
  let days = segmentCache.get(timeZone)
  if (!days) segmentCache.set(timeZone, (days = new Map()))
  const day = Math.floor(ms / DAY)
  let segments = days.get(day)
  if (!segments) {
    const start = day * DAY
    const end = start + DAY
    const first = ianaOffsetMs(start, timeZone)
    const last = ianaOffsetMs(end - MINUTE, timeZone)
    if (first === last) {
      segments = [{ from: start, until: end, offset: first }]
    } else {
      // Zones change offset on a minute boundary at most once a day.
      let lo = start
      let hi = end - MINUTE
      while (hi - lo > MINUTE) {
        const mid = lo + Math.floor((hi - lo) / 2 / MINUTE) * MINUTE
        if (ianaOffsetMs(mid, timeZone) === first) lo = mid
        else hi = mid
      }
      segments = [
        { from: start, until: hi, offset: first },
        { from: hi, until: end, offset: last },
      ]
    }
    days.set(day, segments)
  }
  return segments.find((s) => ms < s.until) ?? segments[segments.length - 1]!
}

function segmentAt(ms: number, zone: string): Segment {
  if (zone === 'UTC') return { from: -Infinity, until: Infinity, offset: 0 }
  const m = FIXED_OFFSET.exec(zone)
  if (m) {
    const minutes = Number(m[2]) * 60 + Number(m[3])
    const offset = (m[1] === '-' ? -minutes : minutes) * MINUTE
    return { from: -Infinity, until: Infinity, offset }
  }
  return ianaSegment(ms, zone)
}

/** The zone's offset from UTC at instant `ms`, in ms. */
export function offsetMs(ms: number, zone: string): number {
  return segmentAt(ms, zone).offset
}

export function toWall(ms: number, zone: string): number {
  return ms + offsetMs(ms, zone)
}

/** The instant a wall value names. A clock time that a daylight saving
 *  change skips or repeats has no single instant; it maps to one beside it. */
export function fromWall(wall: number, zone: string): number {
  const guess = wall - offsetMs(wall, zone)
  return wall - offsetMs(guess, zone)
}

/** Every value of an ascending array moved to wall time, walking the offset
 *  segments rather than looking each point up. The input itself comes back
 *  when nothing moves (UTC), so it is copied only when it has to be. */
export function toWallArray<T extends ArrayLike<number>>(
  xs: T,
  zone: string
): T | Float64Array {
  let out: Float64Array | null = null
  let seg: Segment | null = null
  for (let i = 0; i < xs.length; i++) {
    const x = xs[i]!
    if (!seg || x < seg.from || x >= seg.until) seg = segmentAt(x, zone)
    if (seg.offset !== 0 && !out) {
      out = new Float64Array(xs.length)
      for (let j = 0; j < i; j++) out[j] = xs[j]!
    }
    if (out) out[i] = x + seg.offset
  }
  return out ?? xs
}

/** `ms` moved by whole calendar months on the zone's clock, keeping the
 *  clock time. A day past the end of the target month clamps to its last
 *  day, so Jan 31 plus a month is Feb 28 (29 in a leap year). */
export function addCalendarMonths(ms: number, months: number, zone: string): number {
  const d = new Date(toWall(ms, zone))
  const total = d.getUTCFullYear() * 12 + d.getUTCMonth() + months
  const year = Math.floor(total / 12)
  const month = total - year * 12
  const lastDay = new Date(Date.UTC(year, month + 1, 0)).getUTCDate()
  const wall = Date.UTC(
    year,
    month,
    Math.min(d.getUTCDate(), lastDay),
    d.getUTCHours(),
    d.getUTCMinutes(),
    d.getUTCSeconds(),
    d.getUTCMilliseconds()
  )
  return fromWall(wall, zone)
}
