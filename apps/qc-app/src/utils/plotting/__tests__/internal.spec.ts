import { describe, it, expect } from 'vitest'
import {
  traceXAsNumbers,
  DENSITY_HIDE_MARKERS,
  Y_AXIS_KEY_RE,
} from '../internal'

describe('internal helpers', () => {
  it('traceXAsNumbers returns [] for null gd', () => {
    expect(traceXAsNumbers(null, 0)).toEqual([])
  })
  it('traceXAsNumbers returns [] for undefined gd', () => {
    expect(traceXAsNumbers(undefined, 0)).toEqual([])
  })
  it('traceXAsNumbers returns [] for missing trace', () => {
    expect(traceXAsNumbers({ data: [] } as any, 0)).toEqual([])
  })
  it('traceXAsNumbers returns the x array when present', () => {
    const xs = [1, 2, 3]
    expect(traceXAsNumbers({ data: [{ x: xs }] } as any, 0)).toBe(xs)
  })
  it('DENSITY_HIDE_MARKERS is the documented threshold', () => {
    expect(DENSITY_HIDE_MARKERS).toBe(2000)
  })
  it('Y_AXIS_KEY_RE matches yaxis and yaxisN', () => {
    expect(Y_AXIS_KEY_RE.test('yaxis')).toBe(true)
    expect(Y_AXIS_KEY_RE.test('yaxis2')).toBe(true)
    expect(Y_AXIS_KEY_RE.test('xaxis')).toBe(false)
  })
})
