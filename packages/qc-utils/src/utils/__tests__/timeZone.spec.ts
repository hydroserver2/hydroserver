import { describe, it, expect } from 'vitest'
import {
  addCalendarMonths,
  fromWall,
  isValidTimeZone,
  offsetMs,
  toWall,
  toWallArray,
} from '../timeZone'

const HOUR = 3_600_000
const DENVER = 'America/Denver'

// 2026-03-08 09:00Z is 2 AM MST, when Denver springs forward to MDT.
const SPRING = Date.UTC(2026, 2, 8, 9)

describe('time zone offsets', () => {
  it('reads an IANA zone, tracking daylight saving', () => {
    expect(offsetMs(Date.UTC(2026, 0, 15, 12), DENVER)).toBe(-7 * HOUR)
    expect(offsetMs(Date.UTC(2026, 6, 15, 12), DENVER)).toBe(-6 * HOUR)
  })

  it('changes offset at the transition minute, not the day', () => {
    expect(offsetMs(SPRING - 60_000, DENVER)).toBe(-7 * HOUR)
    expect(offsetMs(SPRING, DENVER)).toBe(-6 * HOUR)
  })

  it('reads a fixed offset and UTC', () => {
    expect(offsetMs(0, '+0530')).toBe(5.5 * HOUR)
    expect(offsetMs(0, '-07:00')).toBe(-7 * HOUR)
    expect(offsetMs(0, 'UTC')).toBe(0)
  })

  // Outside the hour that falling back repeats, which has two instants.
  it('round-trips an instant through its wall value', () => {
    for (const ms of [SPRING - HOUR, SPRING, SPRING + HOUR, Date.UTC(2026, 10, 1, 10)]) {
      expect(fromWall(toWall(ms, DENVER), DENVER)).toBe(ms)
    }
  })

  it('moves an array across a transition, and leaves UTC uncopied', () => {
    const xs = new Float64Array([SPRING - HOUR, SPRING + HOUR])
    expect(Array.from(toWallArray(xs, DENVER))).toEqual([
      SPRING - 8 * HOUR,
      SPRING - 5 * HOUR,
    ])
    expect(toWallArray(xs, 'UTC')).toBe(xs)
  })

  it('knows a zone from a typo', () => {
    expect(isValidTimeZone('UTC')).toBe(true)
    expect(isValidTimeZone('-0700')).toBe(true)
    expect(isValidTimeZone(DENVER)).toBe(true)
    expect(isValidTimeZone('Mars/Olympus')).toBe(false)
    expect(isValidTimeZone('')).toBe(false)
    expect(isValidTimeZone(undefined)).toBe(false)
  })
})

describe('addCalendarMonths', () => {
  it('keeps the clock time across daylight saving', () => {
    expect(addCalendarMonths(Date.UTC(2026, 0, 15, 16), 6, DENVER)).toBe(
      Date.UTC(2026, 6, 15, 15)
    )
  })

  it('crosses years both ways', () => {
    expect(addCalendarMonths(Date.UTC(2026, 10, 15), 3, 'UTC')).toBe(Date.UTC(2027, 1, 15))
    expect(addCalendarMonths(Date.UTC(2026, 1, 15), -3, 'UTC')).toBe(Date.UTC(2025, 10, 15))
  })

  it('clamps to the last day of a shorter month', () => {
    expect(addCalendarMonths(Date.UTC(2026, 0, 31), 1, 'UTC')).toBe(Date.UTC(2026, 1, 28))
    expect(addCalendarMonths(Date.UTC(2024, 1, 29), 12, 'UTC')).toBe(Date.UTC(2025, 1, 28))
  })
})
