/**
 * Pure date-arithmetic helpers used by the time-range presets. JS's
 * native `new Date(y, m, d)` silently rolls overflow (`Feb 31` →
 * `Mar 3`), which made `subtractMonths(Aug 31, 6)` land three days
 * into March instead of on the Feb/Mar boundary. Clone the input,
 * subtract, and clamp the day-of-month back to the target month's
 * last day — matching the arithmetic Plotly's `rangeselector`
 * performs internally.
 */

export const subtractDays = (d: Date, days: number): Date => {
  const r = new Date(d)
  r.setDate(r.getDate() - days)
  return r
}

export const subtractMonths = (d: Date, months: number): Date => {
  const r = new Date(d)
  const day = r.getDate()
  // Move to day 1 before shifting the month so the shift can't
  // overflow (e.g. shifting `Aug 31` by −6 never becomes `Feb 31`
  // and then `Mar 3` via rollover).
  r.setDate(1)
  r.setMonth(r.getMonth() - months)
  const lastDayOfTarget = new Date(
    r.getFullYear(),
    r.getMonth() + 1,
    0
  ).getDate()
  r.setDate(Math.min(day, lastDayOfTarget))
  return r
}

export const subtractYears = (d: Date, years: number): Date => {
  const r = new Date(d)
  const day = r.getDate()
  r.setDate(1)
  r.setFullYear(r.getFullYear() - years)
  const lastDayOfTarget = new Date(
    r.getFullYear(),
    r.getMonth() + 1,
    0
  ).getDate()
  r.setDate(Math.min(day, lastDayOfTarget))
  return r
}
