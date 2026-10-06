/**
 * Calendar arithmetic for the time-range presets, on the chosen zone's
 * clock (`timeZone.ts`), so a month back from 9 AM lands on 9 AM. JS's
 * date setters silently roll overflow (`Feb 31` → `Mar 3`), which made
 * `subtractMonths(Aug 31, 6)` land three days into March instead of on the
 * Feb/Mar boundary. Shift from day 1, then clamp the day-of-month back to
 * the target month's last day, matching the arithmetic Plotly's
 * `rangeselector` performs internally.
 */

import { fromWall, toWall } from '@/utils/timeZone'

/** Apply `shift` to `d`'s wall value, read with UTC setters. */
const onWall = (d: Date, shift: (w: Date) => void): Date => {
  const w = new Date(toWall(d.getTime()))
  shift(w)
  return new Date(fromWall(w.getTime()))
}

const daysIn = (year: number, month: number) =>
  new Date(Date.UTC(year, month + 1, 0)).getUTCDate()

export const subtractDays = (d: Date, days: number): Date =>
  onWall(d, (w) => w.setUTCDate(w.getUTCDate() - days))

export const subtractMonths = (d: Date, months: number): Date =>
  onWall(d, (w) => {
    const day = w.getUTCDate()
    w.setUTCDate(1)
    w.setUTCMonth(w.getUTCMonth() - months)
    w.setUTCDate(Math.min(day, daysIn(w.getUTCFullYear(), w.getUTCMonth())))
  })

export const subtractYears = (d: Date, years: number): Date =>
  onWall(d, (w) => {
    const day = w.getUTCDate()
    w.setUTCDate(1)
    w.setUTCFullYear(w.getUTCFullYear() - years)
    w.setUTCDate(Math.min(day, daysIn(w.getUTCFullYear(), w.getUTCMonth())))
  })
