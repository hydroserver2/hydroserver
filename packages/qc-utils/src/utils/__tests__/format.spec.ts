import { describe, expect, it } from 'vitest'
import { formatDate, formatDuration } from '../format'

describe('Format', () => {
  it('formats date', () => {
    const someDate = new Date(2025, 0, 1)
    const expected = "Jan 01, 2025, 00:00:00"
    const formatted = formatDate(someDate)
    expect(formatted).toBe(expected)
  })

  it('formats duration', () => {
    // Milliseconds
    let someDuration = 525
    let formatted = formatDuration(someDuration)
    expect(formatted).toBe("525 ms")

    // Seconds
    someDuration = 1244
    formatted = formatDuration(someDuration)
    expect(formatted).toBe("1.24 s")

    // Minutes
    someDuration = 81525
    formatted = formatDuration(someDuration)
    expect(formatted).toBe("1.36 m")
  })
})