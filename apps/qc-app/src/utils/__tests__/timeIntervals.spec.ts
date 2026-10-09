import { describe, it, expect } from 'vitest'
import { mergeIntervals, subtractIntervals } from '../timeIntervals'

describe('mergeIntervals', () => {
  it('joins overlapping and touching intervals, in order', () => {
    expect(mergeIntervals([[20, 30], [0, 10], [11, 15], [5, 8]])).toEqual([
      [0, 15],
      [20, 30],
    ])
  })

  it('keeps separated intervals apart', () => {
    expect(mergeIntervals([[0, 10], [12, 20]])).toEqual([[0, 10], [12, 20]])
  })
})

describe('subtractIntervals', () => {
  it('cuts a hole out of an interval', () => {
    expect(subtractIntervals([[0, 100]], [[40, 60]])).toEqual([
      [0, 39],
      [61, 100],
    ])
  })

  it('trims either end and drops what is fully covered', () => {
    expect(subtractIntervals([[0, 10], [20, 30], [40, 50]], [[5, 25], [35, 60]])).toEqual([
      [0, 4],
      [26, 30],
    ])
  })

  it('returns the input when nothing is removed', () => {
    expect(subtractIntervals([[0, 10]], [])).toEqual([[0, 10]])
  })

  it('returns nothing when everything is removed', () => {
    expect(subtractIntervals([[0, 10]], [[0, 10]])).toEqual([])
  })
})
