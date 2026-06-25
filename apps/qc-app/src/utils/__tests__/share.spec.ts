/**
 * Round-trip + edge-case coverage for the share URL encoder/decoder.
 *
 * The asserts here pin two properties:
 *   1. Encoding only emits keys whose value differs from the app's
 *      default. (URLs stay short.)
 *   2. Decoding produces the same state the encoder consumed. (No
 *      lossy compaction.)
 */

import { describe, it, expect } from 'vitest'
import {
  axisIndexFromName,
  axisNameFromIndex,
  base36SecondsToMs,
  bitmaskFromBoolList,
  boolListFromBitmask,
  compactFloat,
  decodeShareState,
  encodeShareState,
  tsToBase36Seconds,
  type ShareState,
} from '@/utils/share'

describe('share encoding primitives', () => {
  it('round-trips a base36-second timestamp', () => {
    const ms = Date.UTC(2026, 4, 13, 12, 0, 0)
    const enc = tsToBase36Seconds(ms)
    expect(enc).toMatch(/^[0-9a-z]+$/)
    expect(base36SecondsToMs(enc)).toBe(ms - (ms % 1000))
  })

  it('returns null for unparseable base36 timestamps', () => {
    expect(base36SecondsToMs('')).toBeNull()
    expect(base36SecondsToMs('!!!')).toBeNull()
  })

  it('round-trips a boolean bitmask', () => {
    const bits = [true, false, true, true, false]
    const hex = bitmaskFromBoolList(bits)
    expect(boolListFromBitmask(hex, bits.length)).toEqual(bits)
  })

  it('treats a zero-mask as all false', () => {
    expect(boolListFromBitmask('0', 4)).toEqual([false, false, false, false])
  })

  it('trims trailing zeros in compact floats', () => {
    expect(compactFloat(10)).toBe('10')
    expect(compactFloat(10.5)).toBe('10.5')
    expect(compactFloat(1.23456789)).toBe('1.2346')
  })

  it('maps datastream position to Plotly axis name and back', () => {
    expect(axisNameFromIndex(0)).toBe('y')
    expect(axisNameFromIndex(1)).toBe('y2')
    expect(axisNameFromIndex(4)).toBe('y5')
    expect(axisIndexFromName('y', 5)).toBe(0)
    expect(axisIndexFromName('y3', 5)).toBe(2)
    expect(axisIndexFromName('bogus', 5)).toBe(-1)
  })
})

describe('encodeShareState — omits defaults', () => {
  it('emits an empty query for the empty state', () => {
    expect(encodeShareState({})).toEqual({})
  })

  it('does not serialise Plot tab (default)', () => {
    const q = encodeShareState({ tableTab: false })
    expect(q.tab).toBeUndefined()
  })

  it('does not serialise Select view (default)', () => {
    const q = encodeShareState({ editView: false })
    expect(q.m).toBeUndefined()
  })

  it('serialises only short keys for the basic Edit case', () => {
    const q = encodeShareState({
      workspaceId: 'ws-1',
      editView: true,
      datastreamIds: ['a', 'b'],
      datePresetId: 0,
    })
    expect(q).toEqual({ ws: 'ws-1', m: 'e', ds: 'a,b', r: '0' })
    // Critically: no `qc`, no `mode`, no `begin`/`end`.
    expect(q.qc).toBeUndefined()
    expect(q.from).toBeUndefined()
    expect(q.to).toBeUndefined()
  })

  it('drops begin/end when a preset is active', () => {
    const q = encodeShareState({
      datastreamIds: ['a'],
      datePresetId: 2,
      beginMs: Date.now() - 1_000_000,
      endMs: Date.now(),
    })
    expect(q.r).toBe('2')
    expect(q.from).toBeUndefined()
    expect(q.to).toBeUndefined()
  })

  it('serialises begin/end (base36) when no preset is active', () => {
    const beginMs = Date.UTC(2026, 4, 13)
    const endMs = Date.UTC(2026, 4, 20)
    const q = encodeShareState({
      datastreamIds: ['a'],
      datePresetId: -1,
      beginMs,
      endMs,
    })
    expect(q.r).toBeUndefined()
    expect(q.from).toBe(tsToBase36Seconds(beginMs))
    expect(q.to).toBe(tsToBase36Seconds(endMs))
  })

  it('emits no visibility keys when every trace is visible', () => {
    const q = encodeShareState({
      datastreamIds: ['a', 'b', 'c'],
      traceVisibility: [true, true, true],
      axisVisibility: [true, true, true],
    })
    expect(q.h).toBeUndefined()
    expect(q.ya).toBeUndefined()
  })

  it('encodes hidden traces / axes as a hex bitmask', () => {
    const q = encodeShareState({
      datastreamIds: ['a', 'b', 'c', 'd'],
      // hidden: index 1 and 3 → bits 0b1010 → 0xa
      traceVisibility: [true, false, true, false],
      // hidden: index 2 → bits 0b100 → 0x4
      axisVisibility: [true, true, false, true],
    })
    expect(q.h).toBe('a')
    expect(q.ya).toBe('4')
  })

  it('encodes x-zoom as two base36 seconds joined by a dot', () => {
    const lo = Date.UTC(2026, 0, 1)
    const hi = Date.UTC(2026, 5, 1)
    const q = encodeShareState({
      datastreamIds: ['a'],
      zoom: { xRange: [lo, hi], yRanges: {} },
    })
    expect(q.z).toBe(`${tsToBase36Seconds(lo)}.${tsToBase36Seconds(hi)}`)
  })

  it('encodes per-y zoom by position in `ds`', () => {
    const q = encodeShareState({
      datastreamIds: ['a', 'b'],
      zoom: {
        xRange: null,
        yRanges: { y: [0, 10], y2: [-5, 5.123456] },
      },
    })
    // Two entries separated by `;`, each `<idx>:<lo>~<hi>`.
    expect(q.yz).toBe('0:0~10;1:-5~5.1235')
  })

  it('omits data points keys when the mode is auto and threshold is default', () => {
    const q = encodeShareState({
      dataPointsMode: 'auto',
      dataPointsThreshold: 10000,
    })
    expect(q.dp).toBeUndefined()
    expect(q.th).toBeUndefined()
  })

  it('encodes manual modes and non-default thresholds', () => {
    const q = encodeShareState({
      dataPointsMode: 'manualOff',
      dataPointsThreshold: 25000,
    })
    expect(q.dp).toBe('0')
    expect(q.th).toBe('25000')
  })
})

describe('decodeShareState', () => {
  it('returns an empty state for an empty query', () => {
    expect(decodeShareState({})).toEqual({})
  })

  it('decodes the basic Edit case', () => {
    const decoded = decodeShareState({ ws: 'ws-1', m: 'e', ds: 'a,b', r: '0' })
    expect(decoded.workspaceId).toBe('ws-1')
    expect(decoded.editView).toBe(true)
    expect(decoded.datastreamIds).toEqual(['a', 'b'])
    expect(decoded.datePresetId).toBe(0)
    expect(decoded.beginMs).toBeUndefined()
    expect(decoded.endMs).toBeUndefined()
  })

  it('sets datePresetId = -1 when only from/to are present', () => {
    const beginMs = Date.UTC(2026, 4, 13)
    const endMs = Date.UTC(2026, 4, 20)
    const decoded = decodeShareState({
      from: tsToBase36Seconds(beginMs),
      to: tsToBase36Seconds(endMs),
    })
    expect(decoded.datePresetId).toBe(-1)
    expect(decoded.beginMs).toBe(beginMs)
    expect(decoded.endMs).toBe(endMs)
  })

  it('inverts the visibility bitmask', () => {
    const decoded = decodeShareState({
      ds: 'a,b,c,d',
      h: 'a',
      ya: '4',
    })
    expect(decoded.traceVisibility).toEqual([true, false, true, false])
    expect(decoded.axisVisibility).toEqual([true, true, false, true])
  })

  it('decodes per-y zoom into Plotly axis names', () => {
    const decoded = decodeShareState({
      ds: 'a,b',
      yz: '0:0~10;1:-5~5.1235',
    })
    expect(decoded.zoom).toBeDefined()
    expect(decoded.zoom!.yRanges).toEqual({
      y: [0, 10],
      y2: [-5, 5.1235],
    })
  })

  it('skips malformed yz entries instead of throwing', () => {
    const decoded = decodeShareState({
      ds: 'a',
      yz: '0:0~10;not-a-number;1:foo~bar',
    })
    expect(decoded.zoom!.yRanges).toEqual({ y: [0, 10] })
  })

  it('decodes data points mode and threshold', () => {
    const decoded = decodeShareState({ dp: '0', th: '25000' })
    expect(decoded.dataPointsMode).toBe('manualOff')
    expect(decoded.dataPointsThreshold).toBe(25000)
  })
})

describe('round-trip', () => {
  it('preserves a maximal-coverage state through encode → decode', () => {
    const beginMs = Date.UTC(2026, 4, 13, 12, 0, 0)
    const endMs = Date.UTC(2026, 4, 20, 12, 0, 0)
    const original: ShareState = {
      workspaceId: '01a2b3c4-d5e6-7f89-0a1b-2c3d4e5f6789',
      editView: true,
      tableTab: true,
      datastreamIds: ['ds-1', 'ds-2', 'ds-3'],
      datePresetId: -1,
      beginMs,
      endMs,
      traceVisibility: [true, false, true],
      axisVisibility: [true, true, false],
      zoom: {
        xRange: [beginMs, endMs],
        yRanges: { y: [0, 100], y3: [-50, 50] },
      },
      dataPointsMode: 'manualOn',
      dataPointsThreshold: 5000,
    }
    const decoded = decodeShareState(encodeShareState(original))
    expect(decoded).toEqual(original)
  })

  it('round-trips a preset-driven state without timestamps', () => {
    const original: ShareState = {
      workspaceId: 'ws-1',
      datastreamIds: ['ds-1'],
      datePresetId: 5,
    }
    const decoded = decodeShareState(encodeShareState(original))
    expect(decoded).toEqual(original)
  })
})
