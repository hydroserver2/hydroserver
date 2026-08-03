import { describe, it, expect } from 'vitest'
import { formatDateInput, formatDateRange } from '../time'

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
  it('joins both bounds with "to"', () => {
    expect(
      formatDateRange('2025-01-05T00:00:00', '2025-01-15T09:05:00')
    ).toBe('01/05/2025 00:00 to 01/15/2025 09:05')
  })
})
