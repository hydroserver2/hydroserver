/**
 * The time zone the app shows and takes dates in, chosen by the user the way
 * a data connection's zone is: UTC, a fixed UTC offset, or an IANA zone. It
 * defaults to the browser's own zone.
 *
 * Instants stay epoch ms everywhere. A "wall" value is an instant moved by
 * the zone's offset, so its UTC fields read as the zone's clock. Formatting,
 * pickers and the plot work on wall values; everything stored stays real.
 */

import { ref } from 'vue'

export type ZoneMode = 'utc' | 'fixedOffset' | 'iana'

export interface DisplayZone {
  mode: ZoneMode
  /** A fixed offset like `-0700`, or an IANA zone. Unused for UTC. */
  zone: string
}

export const browserZone = (): DisplayZone => ({
  mode: 'iana',
  zone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
})

/** The zone in use. `qcPreferences` persists it. */
export const displayZone = ref<DisplayZone>(browserZone())

const MINUTE = 60_000
const DAY = 86_400_000

/** `-0700` to minutes east of UTC. */
function fixedOffsetMinutes(zone: string): number {
  const m = /^([+-])(\d{2}):?(\d{2})$/.exec(zone)
  if (!m) return 0
  const minutes = Number(m[2]) * 60 + Number(m[3])
  return m[1] === '-' ? -minutes : minutes
}

const partFormatters = new Map<string, Intl.DateTimeFormat>()

function ianaOffsetMs(ms: number, timeZone: string): number {
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
  const get = (parts: Intl.DateTimeFormatPart[], type: string) =>
    Number(parts.find((p) => p.type === type)?.value)
  const parts = fmt.formatToParts(ms)
  const wall = Date.UTC(
    get(parts, 'year'),
    get(parts, 'month') - 1,
    get(parts, 'day'),
    get(parts, 'hour'),
    get(parts, 'minute'),
    get(parts, 'second')
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

function segmentAt(ms: number, z: DisplayZone): Segment {
  if (z.mode === 'iana') return ianaSegment(ms, z.zone)
  const offset = z.mode === 'fixedOffset' ? fixedOffsetMinutes(z.zone) * MINUTE : 0
  return { from: -Infinity, until: Infinity, offset }
}

/** The zone's offset from UTC at instant `ms`, in ms. */
export function offsetMs(ms: number, z: DisplayZone = displayZone.value): number {
  return segmentAt(ms, z).offset
}

export function toWall(ms: number, z: DisplayZone = displayZone.value): number {
  return ms + offsetMs(ms, z)
}

/** The instant a wall value names. A clock time that a daylight saving
 *  change skips or repeats has no single instant; it maps to one beside it. */
export function fromWall(wall: number, z: DisplayZone = displayZone.value): number {
  const guess = wall - offsetMs(wall, z)
  return wall - offsetMs(guess, z)
}

/** Every value of an ascending array moved to wall time, walking the offset
 *  segments rather than looking each point up. The input itself comes back
 *  when nothing moves (UTC), so it is copied only when it has to be. */
export function toWallArray<T extends ArrayLike<number>>(
  xs: T,
  z: DisplayZone = displayZone.value
): T | Float64Array {
  let out: Float64Array | null = null
  let seg: Segment | null = null
  for (let i = 0; i < xs.length; i++) {
    const x = xs[i]!
    if (!seg || x < seg.from || x >= seg.until) seg = segmentAt(x, z)
    if (seg.offset !== 0 && !out) {
      out = new Float64Array(xs.length)
      for (let j = 0; j < i; j++) out[j] = xs[j]!
    }
    if (out) out[i] = x + seg.offset
  }
  return out ?? xs
}

/** The zone's clock at `ms`, with a 0-based month. */
export function wallParts(ms: number, z: DisplayZone = displayZone.value) {
  const d = new Date(toWall(ms, z))
  return {
    year: d.getUTCFullYear(),
    month: d.getUTCMonth(),
    day: d.getUTCDate(),
    hours: d.getUTCHours(),
    minutes: d.getUTCMinutes(),
    seconds: d.getUTCSeconds(),
  }
}

/** The instant the zone's clock reads the given fields. */
export function fromWallParts(
  year: number,
  month: number,
  day: number,
  hours = 0,
  minutes = 0,
  seconds = 0,
  z: DisplayZone = displayZone.value
): number {
  return fromWall(Date.UTC(year, month, day, hours, minutes, seconds), z)
}

function formatOffset(ms: number): string {
  const minutes = Math.round(ms / MINUTE)
  const sign = minutes < 0 ? '-' : '+'
  const hh = String(Math.floor(Math.abs(minutes) / 60)).padStart(2, '0')
  const mm = String(Math.abs(minutes) % 60).padStart(2, '0')
  return `UTC${sign}${hh}:${mm}`
}

const shortNames = new Map<string, Intl.DateTimeFormat>()

/** The zone's short name at `ms` (`MDT`, `MST`, `UTC`, `UTC+05:30`), which
 *  tracks daylight saving. */
export function zoneAbbreviation(
  ms: number,
  z: DisplayZone = displayZone.value
): string {
  if (z.mode === 'utc') return 'UTC'
  if (z.mode === 'fixedOffset') return formatOffset(offsetMs(ms, z))
  let fmt = shortNames.get(z.zone)
  if (!fmt) {
    fmt = new Intl.DateTimeFormat('en-US', {
      timeZone: z.zone,
      timeZoneName: 'short',
    })
    shortNames.set(z.zone, fmt)
  }
  return fmt.formatToParts(ms).find((p) => p.type === 'timeZoneName')?.value ?? ''
}

/** `America/Denver, UTC-06:00` at `ms`. */
export function zoneDescription(
  ms: number,
  z: DisplayZone = displayZone.value
): string {
  const offset = formatOffset(offsetMs(ms, z))
  if (z.mode === 'utc') return 'UTC'
  if (z.mode === 'fixedOffset') return `Fixed offset, ${offset}`
  return `${z.zone}, ${offset}`
}

/** The zone's name without a date: the IANA name, `UTC`, or the offset. */
export function zoneName(z: DisplayZone = displayZone.value): string {
  if (z.mode === 'utc') return 'UTC'
  if (z.mode === 'fixedOffset') return formatOffset(offsetMs(0, z))
  return z.zone
}
