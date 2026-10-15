/**
 * Plotly has no time zones. Its own frame on a date axis is a clock's
 * fields read as UTC, and the plot shows the chosen zone's clock, so that
 * frame holds wall values (`timeZone.ts`). Every x that leaves the plot
 * goes through `fromPlot`.
 *
 * Ranges, shapes and tick values are written as Plotly date strings, which
 * it reads as written. A trace's numeric x it reads as the browser's local
 * clock, so `toPlotX` hands it the instant whose browser-local clock shows
 * the wall time: in the browser's own zone, the instant itself. Code that
 * compares trace x with the view reads it back through `plotX`.
 *
 * A wall time the browser's clock skips (its daylight saving gap) has no
 * such instant, so with another zone chosen a point there draws beside it.
 */

import {
  browserZone,
  fromWall,
  fromWallArray,
  toWall,
  toWallArray,
  zoneId,
} from '@/utils/timeZone'

const BROWSER = browserZone()

/** Trace x values for Plotly, from epoch ms. */
export function toPlotX<T extends ArrayLike<number>>(xs: T): T | Float64Array {
  if (zoneId() === zoneId(BROWSER)) return xs
  return fromWallArray(toWallArray(xs), BROWSER)
}

/** Trace x as Plotly draws it, in its own frame (see `plotCoord`). */
export const plotX = <T extends ArrayLike<number>>(xs: T): T | Float64Array =>
  toWallArray(xs, BROWSER)

/** A Plotly date string (`YYYY-MM-DD HH:MM:SS.sss`) for an instant. */
export const toPlotDate = (ms: number): string => plotCoordToDate(toWall(ms))

/** A Plotly x as a number in Plotly's own frame: a range or shape string
 *  read as UTC, or a number as is. Compare it with `plotX` values; take
 *  `fromPlot` to leave the plot. */
export function plotCoord(v: number | string): number {
  if (typeof v === 'number') return v
  const [date, time = '00:00'] = v.trim().replace(/Z$/i, '').split(/[ T]/)
  return Date.parse(`${date}T${time}Z`)
}

/** The instant behind a Plotly x. */
export const fromPlot = (v: number | string): number => fromWall(plotCoord(v))

/** A Plotly date string for a number in Plotly's own frame. */
export const plotCoordToDate = (wall: number): string =>
  new Date(wall).toISOString().replace('T', ' ').replace('Z', '')
