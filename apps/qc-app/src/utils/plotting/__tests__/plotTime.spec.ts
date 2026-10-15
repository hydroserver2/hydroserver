import { afterEach, describe, expect, it } from 'vitest'
import { browserZone, displayZone, toWallArray, type DisplayZone } from '@/utils/timeZone'
import { plotX, toPlotX } from '../plotTime'

// What Plotly does with a trace's numeric x on a date axis: it reads the
// number's browser-local clock as UTC fields.
const plotlyReads = (xs: ArrayLike<number>) =>
  Array.from(xs, (v) => v - new Date(v).getTimezoneOffset() * 60_000)

// Mid-January and mid-July, clear of any daylight saving change.
const instants = [
  Date.UTC(2014, 0, 15, 7, 15),
  Date.UTC(2014, 0, 15, 7, 30),
  Date.UTC(2026, 6, 15, 18, 0),
]

const zones: DisplayZone[] = [
  { mode: 'utc', zone: '' },
  { mode: 'fixedOffset', zone: '-0300' },
  { mode: 'iana', zone: 'Asia/Tokyo' },
  browserZone(),
]

afterEach(() => {
  displayZone.value = browserZone()
})

describe('plot time', () => {
  it.each(zones)('draws each point at its wall time in $mode $zone', (zone) => {
    displayZone.value = zone
    const wall = Array.from(toWallArray(instants))
    expect(plotlyReads(toPlotX(instants))).toEqual(wall)
  })

  it.each(zones)('reads trace x back as Plotly draws it in $mode $zone', (zone) => {
    displayZone.value = zone
    const sent = toPlotX(instants)
    expect(Array.from(plotX(sent))).toEqual(plotlyReads(sent))
  })

  it("hands over the instants untouched in the browser's own zone", () => {
    displayZone.value = browserZone()
    const xs = new Float64Array(instants)
    expect(toPlotX(xs)).toBe(xs)
  })
})
