/**
 * The time zone the app shows and takes dates in, chosen by the user the way
 * a data connection's zone is: UTC, a fixed UTC offset, or an IANA zone. It
 * defaults to the browser's own zone.
 *
 * Instants stay epoch ms everywhere. A "wall" value is an instant moved by
 * the zone's offset, so its UTC fields read as the zone's clock. Formatting,
 * pickers and the plot work on wall values; everything stored stays real.
 * The offset math lives in qc-utils.
 */

import { ref } from 'vue'
import {
  fromWall as zoneFromWall,
  fromWallArray as zoneFromWallArray,
  offsetMs as zoneOffsetMs,
  toWall as zoneToWall,
  toWallArray as zoneToWallArray,
} from '@uwrl/qc-utils'

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

/** The zone as qc-utils takes it: `UTC`, a fixed offset, or an IANA name.
 *  Shift operations save it, so their calendar replays the same anywhere. */
export function zoneId(z: DisplayZone = displayZone.value): string {
  return z.mode === 'utc' ? 'UTC' : z.zone
}

/** The zone's offset from UTC at instant `ms`, in ms. */
export const offsetMs = (ms: number, z: DisplayZone = displayZone.value): number =>
  zoneOffsetMs(ms, zoneId(z))

export const toWall = (ms: number, z: DisplayZone = displayZone.value): number =>
  zoneToWall(ms, zoneId(z))

/** The instant a wall value names. A clock time that a daylight saving
 *  change skips or repeats has no single instant; it maps to one beside it. */
export const fromWall = (wall: number, z: DisplayZone = displayZone.value): number =>
  zoneFromWall(wall, zoneId(z))

/** Every value of an ascending array moved to wall time. The input itself
 *  comes back when nothing moves (UTC). */
export const toWallArray = <T extends ArrayLike<number>>(
  xs: T,
  z: DisplayZone = displayZone.value
): T | Float64Array => zoneToWallArray(xs, zoneId(z))

/** `fromWall` over an ascending array. The input itself comes back when
 *  nothing moves (UTC). */
export const fromWallArray = <T extends ArrayLike<number>>(
  walls: T,
  z: DisplayZone = displayZone.value
): T | Float64Array => zoneFromWallArray(walls, zoneId(z))

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
