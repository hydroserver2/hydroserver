import { describe, it, expect } from 'vitest'
import { estimateFillCount, fillFanout, fillLimit } from '../fillGaps'

const HOUR = 60 * 60 * 1000
const gap = (leftTs: number, rightTs: number, leftY = 0, rightY = 10) => ({
  leftTs,
  rightTs,
  leftY,
  rightY,
})

describe('fillGaps', () => {
  it('builds the fill points strictly inside each gap', () => {
    const { xs, ys, count } = fillFanout([gap(0, 4 * HOUR)], HOUR)
    expect(xs).toEqual([HOUR, 2 * HOUR, 3 * HOUR])
    expect(ys).toEqual([2.5, 5, 7.5])
    expect(count).toBe(3)
  })

  it('estimates the count without building the points', () => {
    const plans = [gap(0, 4 * HOUR), gap(10 * HOUR, 10.5 * HOUR)]
    expect(estimateFillCount(plans, HOUR)).toBe(3)
    expect(estimateFillCount(plans, HOUR)).toBe(fillFanout(plans, HOUR).count)
    // A year-long gap at a one-second cadence.
    expect(estimateFillCount([gap(0, 365 * 24 * HOUR)], 1000)).toBe(
      365 * 24 * 3600 - 1
    )
  })

  it('allows twice the loaded points, and never fewer than 10,000', () => {
    expect(fillLimit(1_000_000)).toBe(2_000_000)
    expect(fillLimit(100)).toBe(10_000)
  })
})
