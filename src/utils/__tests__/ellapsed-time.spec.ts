import { describe, expect, it, vi } from 'vitest'
import { measureEllapsedTime } from '../ellapsed-time'

/** Async function that yields `value` after `delay` ms. */
const after = <T>(value: T, delay: number): (() => Promise<T>) =>
  () => new Promise<T>((resolve) => setTimeout(() => resolve(value), delay))

describe('measureEllapsedTime', () => {
  it('reports a duration that meets or exceeds the actual wait', async () => {
    const DELAY = 40
    const measurement = await measureEllapsedTime(after([], DELAY))
    // Use a slack of a few ms below `DELAY` so the assertion stays
    // robust against `setTimeout`'s "may fire slightly early" semantics
    // observed on some hosts; the bug being guarded against is
    // "duration captures real elapsed time," not exact equality.
    expect(measurement.duration).toBeGreaterThanOrEqual(DELAY - 5)
  })

  it('reports a finite numeric duration even for an instantly-resolving thunk', async () => {
    const measurement = await measureEllapsedTime(() => Promise.resolve('ok'))
    expect(typeof measurement.duration).toBe('number')
    expect(Number.isFinite(measurement.duration)).toBe(true)
    expect(measurement.duration).toBeGreaterThanOrEqual(0)
  })

  it('forwards the underlying function\'s resolved value verbatim', async () => {
    const arr: number[] = []
    const measurement = await measureEllapsedTime(after(arr, 5))
    // Identity is preserved — the wrapper does not copy the response.
    expect(measurement.response).toBe(arr)
  })

  it('returns the resolved value when it is an empty array (regression: toBe vs toEqual)', async () => {
    // Original spec asserted `expect(response).toBe([])`, which fails
    // because `[] === []` is `false`. Use `toEqual` for structural
    // equality.
    const measurement = await measureEllapsedTime(after([], 5))
    expect(measurement.response).toEqual([])
  })

  it('returns rich object values verbatim', async () => {
    const payload = { rows: 3, keys: ['a', 'b'] }
    const measurement = await measureEllapsedTime(() => Promise.resolve(payload))
    expect(measurement.response).toBe(payload)
  })

  it('supports synchronous (non-Promise) thunks via await', async () => {
    const measurement = await measureEllapsedTime(() => 42)
    expect(measurement.response).toBe(42)
    expect(measurement.duration).toBeGreaterThanOrEqual(0)
  })

  it('logs the provided message to console.info before measuring', async () => {
    const spy = vi.spyOn(console, 'info').mockImplementation(() => { })
    try {
      await measureEllapsedTime(() => Promise.resolve(null), 'starting work')
      expect(spy).toHaveBeenCalledWith('starting work')
    } finally {
      spy.mockRestore()
    }
  })

  it('does not log when no message is provided', async () => {
    const spy = vi.spyOn(console, 'info').mockImplementation(() => { })
    try {
      await measureEllapsedTime(() => Promise.resolve(null))
      expect(spy).not.toHaveBeenCalled()
    } finally {
      spy.mockRestore()
    }
  })

  it('propagates errors from the wrapped function', async () => {
    await expect(
      measureEllapsedTime(() => Promise.reject(new Error('inner boom')))
    ).rejects.toThrow('inner boom')
  })
})
