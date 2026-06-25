import { describe, it, expect } from 'vitest'
import {
  subtractDays,
  subtractMonths,
  subtractYears,
} from '@/utils/dateMath'

// The helpers clone their input — these tests double as immutability
// assertions so callers don't need to defensively copy.

describe('dateMath.subtractDays', () => {
  it('subtracts whole days', () => {
    const result = subtractDays(new Date(2025, 0, 15), 5)
    expect(result.getFullYear()).toBe(2025)
    expect(result.getMonth()).toBe(0)
    expect(result.getDate()).toBe(10)
  })

  it('crosses a month boundary', () => {
    const result = subtractDays(new Date(2025, 2, 3), 5) // Mar 3 - 5d
    expect(result.getMonth()).toBe(1) // Feb
    expect(result.getDate()).toBe(26)
  })

  it('crosses a year boundary', () => {
    const result = subtractDays(new Date(2025, 0, 3), 10) // Jan 3 2025 - 10d
    expect(result.getFullYear()).toBe(2024)
    expect(result.getMonth()).toBe(11) // Dec
    expect(result.getDate()).toBe(24)
  })

  it('accepts zero as a no-op', () => {
    const input = new Date(2025, 5, 15)
    const result = subtractDays(input, 0)
    expect(result.getTime()).toBe(input.getTime())
  })

  it('does not mutate the input', () => {
    const input = new Date(2025, 0, 15)
    const originalTs = input.getTime()
    subtractDays(input, 30)
    expect(input.getTime()).toBe(originalTs)
  })
})

describe('dateMath.subtractMonths', () => {
  it('subtracts whole months on a mid-month day', () => {
    const result = subtractMonths(new Date(2025, 5, 15), 2) // Jun 15 - 2M
    expect(result.getMonth()).toBe(3) // Apr
    expect(result.getDate()).toBe(15)
  })

  it('clamps day-of-month when target month is shorter (Aug 31 - 6M → Feb 28)', () => {
    // The reason this helper exists — JS's native setMonth overflows
    // Feb 31 into March 3, which silently misrouted the 6-month preset.
    const result = subtractMonths(new Date(2025, 7, 31), 6) // Aug 31 - 6M
    expect(result.getFullYear()).toBe(2025)
    expect(result.getMonth()).toBe(1) // Feb
    expect(result.getDate()).toBe(28) // clamped (2025 is not a leap year)
  })

  it('lands on Feb 29 in a leap year', () => {
    const result = subtractMonths(new Date(2024, 7, 31), 6) // Aug 31 2024 - 6M
    expect(result.getFullYear()).toBe(2024)
    expect(result.getMonth()).toBe(1)
    expect(result.getDate()).toBe(29)
  })

  it('crosses a year boundary', () => {
    const result = subtractMonths(new Date(2025, 1, 10), 3) // Feb 10 - 3M
    expect(result.getFullYear()).toBe(2024)
    expect(result.getMonth()).toBe(10) // Nov
    expect(result.getDate()).toBe(10)
  })

  it('accepts zero as a no-op', () => {
    const input = new Date(2025, 5, 15)
    const result = subtractMonths(input, 0)
    expect(result.getTime()).toBe(input.getTime())
  })

  it('does not mutate the input', () => {
    const input = new Date(2025, 7, 31)
    const originalTs = input.getTime()
    subtractMonths(input, 6)
    expect(input.getTime()).toBe(originalTs)
  })
})

describe('dateMath.subtractYears', () => {
  it('subtracts whole years on a regular day', () => {
    const result = subtractYears(new Date(2025, 5, 15), 3)
    expect(result.getFullYear()).toBe(2022)
    expect(result.getMonth()).toBe(5)
    expect(result.getDate()).toBe(15)
  })

  it('clamps Feb 29 to Feb 28 when the target year is not a leap year', () => {
    const result = subtractYears(new Date(2024, 1, 29), 1) // Feb 29 2024 - 1y
    expect(result.getFullYear()).toBe(2023)
    expect(result.getMonth()).toBe(1)
    expect(result.getDate()).toBe(28)
  })

  it('preserves Feb 29 when the target year is also a leap year', () => {
    const result = subtractYears(new Date(2024, 1, 29), 4) // Feb 29 2024 - 4y → 2020
    expect(result.getFullYear()).toBe(2020)
    expect(result.getMonth()).toBe(1)
    expect(result.getDate()).toBe(29)
  })

  it('accepts zero as a no-op', () => {
    const input = new Date(2025, 5, 15)
    const result = subtractYears(input, 0)
    expect(result.getTime()).toBe(input.getTime())
  })

  it('does not mutate the input', () => {
    const input = new Date(2024, 1, 29)
    const originalTs = input.getTime()
    subtractYears(input, 1)
    expect(input.getTime()).toBe(originalTs)
  })
})
