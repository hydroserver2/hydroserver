import { describe, it, expect } from 'vitest'
import {
  fromWall,
  fromWallParts,
  offsetMs,
  toWall,
  toWallArray,
  wallParts,
  zoneAbbreviation,
  zoneDescription,
  type DisplayZone,
} from '../timeZone'
import { fromPlot, plotCoord, toPlotDate } from '../plotting/plotTime'

const HOUR = 3_600_000
const denver: DisplayZone = { mode: 'iana', zone: 'America/Denver' }
const india: DisplayZone = { mode: 'fixedOffset', zone: '+0530' }
const utc: DisplayZone = { mode: 'utc', zone: '' }

// 2026-03-08 09:00Z is 2 AM MST, when Denver springs forward to MDT.
const SPRING = Date.UTC(2026, 2, 8, 9)

describe('display zone offsets', () => {
  it('reads an IANA zone, tracking daylight saving', () => {
    expect(offsetMs(Date.UTC(2026, 0, 15, 12), denver)).toBe(-7 * HOUR)
    expect(offsetMs(Date.UTC(2026, 6, 15, 12), denver)).toBe(-6 * HOUR)
  })

  it('changes offset at the transition minute, not the day', () => {
    expect(offsetMs(SPRING - 60_000, denver)).toBe(-7 * HOUR)
    expect(offsetMs(SPRING, denver)).toBe(-6 * HOUR)
  })

  it('reads a fixed offset and UTC', () => {
    expect(offsetMs(0, india)).toBe(5.5 * HOUR)
    expect(offsetMs(0, utc)).toBe(0)
  })

  // Outside the hour that falling back repeats, which has two instants.
  it('round-trips an instant through its wall value', () => {
    for (const ms of [SPRING - HOUR, SPRING, SPRING + HOUR, Date.UTC(2026, 10, 1, 10)]) {
      expect(fromWall(toWall(ms, denver), denver)).toBe(ms)
    }
  })

  it('reads and builds the zone clock', () => {
    const ms = Date.UTC(2026, 6, 15, 18, 30)
    expect(wallParts(ms, denver)).toEqual({
      year: 2026,
      month: 6,
      day: 15,
      hours: 12,
      minutes: 30,
      seconds: 0,
    })
    expect(fromWallParts(2026, 6, 15, 12, 30, 0, denver)).toBe(ms)
  })

  it('moves an array across a transition, and leaves UTC uncopied', () => {
    const xs = new Float64Array([SPRING - HOUR, SPRING + HOUR])
    expect(Array.from(toWallArray(xs, denver))).toEqual([
      SPRING - 8 * HOUR,
      SPRING - 5 * HOUR,
    ])
    expect(toWallArray(xs, utc)).toBe(xs)
  })

  it('names the zone', () => {
    expect(zoneAbbreviation(Date.UTC(2026, 0, 15), denver)).toBe('MST')
    expect(zoneAbbreviation(0, india)).toBe('UTC+05:30')
    expect(zoneDescription(Date.UTC(2026, 6, 15), denver)).toBe(
      'America/Denver, UTC-06:00'
    )
    expect(zoneAbbreviation(0, utc)).toBe('UTC')
  })
})

describe('plot time', () => {
  // The test run's zone is UTC (vite.config), so the browser zone adds nothing.
  it('writes Plotly date strings and reads them back', () => {
    const ms = Date.UTC(2026, 0, 2, 3, 4, 5, 6)
    expect(toPlotDate(ms)).toBe('2026-01-02 03:04:05.006')
    expect(fromPlot('2026-01-02 03:04:05.006')).toBe(ms)
    expect(plotCoord('2026-01-02')).toBe(Date.UTC(2026, 0, 2))
    expect(plotCoord(42)).toBe(42)
  })
})
