import { describe, it, expect, afterAll, vi } from 'vitest'

// Pinned so the labels are known values, not recomputed the way the code
// computes them.
const previousTz = vi.hoisted(() => {
  const tz = process.env.TZ
  process.env.TZ = 'America/Denver'
  return tz
})
afterAll(() => {
  if (previousTz === undefined) delete process.env.TZ
  else process.env.TZ = previousTz
})

const { timeZoneAbbreviation, timeZoneDescription } = await import('../time')

describe('time zone labels', () => {
  const winter = new Date('2026-01-15T19:00:00Z')
  const summer = new Date('2026-07-15T18:00:00Z')

  it('abbreviates the zone on the given date, tracking daylight saving', () => {
    expect(timeZoneAbbreviation(winter)).toBe('MST')
    expect(timeZoneAbbreviation(summer)).toBe('MDT')
  })

  it('names the zone and its UTC offset on the given date', () => {
    expect(timeZoneDescription(winter)).toBe('America/Denver, UTC-07:00')
    expect(timeZoneDescription(summer)).toBe('America/Denver, UTC-06:00')
  })
})
