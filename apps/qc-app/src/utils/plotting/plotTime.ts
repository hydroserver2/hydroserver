/**
 * Plotly has no time zones: it reads epoch ms as UTC. So x values go in as
 * wall values (`timeZone.ts`), which makes its axis, ticks and hover read in
 * the chosen zone, and every x that comes back out goes through `fromPlot`.
 *
 * Ranges, shapes and tick values are written as Plotly date strings. Plotly
 * reads a bare number there as browser-local time, unlike trace data, which
 * would shift every zoom by the browser's UTC offset.
 */

import { fromWall, toWall, toWallArray } from '@/utils/timeZone'

/** Trace x values for Plotly, from epoch ms. */
export const toPlotX = <T extends ArrayLike<number>>(xs: T): T | Float64Array =>
  toWallArray(xs)

/** A Plotly date string (`YYYY-MM-DD HH:MM:SS.sss`) for an instant. */
export const toPlotDate = (ms: number): string => plotCoordToDate(toWall(ms))

/** A Plotly x as a number in Plotly's own frame, where trace values live:
 *  a range or shape string read as UTC, or a number as is. Compare it with
 *  trace values; take `fromPlot` to leave the plot. */
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
