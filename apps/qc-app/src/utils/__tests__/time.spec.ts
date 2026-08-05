import { describe, it, expect } from 'vitest'
import { formatDateInput, formatDateRange, formatDayStamp } from '../time'

// Datetime strings without a timezone offset are parsed as local time, so
// these assertions are stable regardless of the test runner's zone.
describe('formatDateInput', () => {
  it('formats as MM/DD/YYYY HH:MM (date-input style)', () => {
    expect(formatDateInput('2025-01-05T14:30:00')).toBe('01/05/2025 14:30')
  })

  it('zero-pads month, day, hour, and minute', () => {
    expect(formatDateInput('2025-09-08T04:07:00')).toBe('09/08/2025 04:07')
  })

  it('returns a dash for nullish input', () => {
    expect(formatDateInput(null)).toBe('–')
    expect(formatDateInput(undefined)).toBe('–')
  })

  it('returns the raw string when unparseable', () => {
    expect(formatDateInput('not-a-date')).toBe('not-a-date')
  })
})

describe('formatDateRange', () => {
  it('states the year once when both bounds share it', () => {
    expect(formatDateRange('2025-01-05T00:00:00', '2025-02-01T00:00:00')).toBe(
      'Jan 5 – Feb 1, 2025'
    )
  })

  it('states both years when the window crosses one', () => {
    expect(formatDateRange('2024-12-01T00:00:00', '2025-01-15T00:00:00')).toBe(
      'Dec 1, 2024 – Jan 15, 2025'
    )
  })

  it('collapses a single day to one date with a time span', () => {
    expect(formatDateRange('2025-01-05T09:00:00', '2025-01-05T14:30:00')).toBe(
      'Jan 5, 2025, 9:00 AM – 2:30 PM'
    )
  })

  it('keeps clock times when the bounds are not whole days', () => {
    expect(formatDateRange('2025-01-05T09:00:00', '2025-02-01T14:30:00')).toBe(
      'Jan 5, 9:00 AM – Feb 1, 2025, 2:30 PM'
    )
  })

  it('drops the clock when the window sits on midnight at both ends', () => {
    expect(formatDateRange('2025-01-05T00:00:00', '2025-01-06T00:00:00')).toBe(
      'Jan 5 – Jan 6, 2025'
    )
  })

  it('returns a dash for nullish or unparseable bounds', () => {
    expect(formatDateRange(null, '2025-01-05T00:00:00')).toBe('–')
    expect(formatDateRange('2025-01-05T00:00:00', undefined)).toBe('–')
    expect(formatDateRange('not-a-date', '2025-01-05T00:00:00')).toBe('–')
  })
})

describe('formatDayStamp', () => {
  it('formats an ISO timestamp to day precision', () => {
    expect(formatDayStamp('2026-03-14T12:00:00')).toBe('Mar 14, 2026')
  })

  it('falls back for nullish and unparseable input', () => {
    expect(formatDayStamp(null)).toBe('–')
    expect(formatDayStamp('nonsense')).toBe('nonsense')
  })
})
