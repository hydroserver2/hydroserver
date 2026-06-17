/**
 * Direct unit tests for the pure kernels in `operation-cores.ts`. These
 * functions are the shared source of truth for every `*.worker.ts` with an
 * inline equivalent, so once they pass here the worker wrappers only need a
 * thin "message in / message out" check (see `workers.spec.ts`).
 *
 * Cores are deliberately framework-free and accept plain typed arrays, so
 * these tests build buffers from raw `Float32Array` / `Float64Array` rather
 * than `SharedArrayBuffer`. Semantics are identical and happy-dom doesn't
 * require the cross-origin-isolation headers SAB would.
 */

import { describe, expect, it } from 'vitest'
import {
  ThresholdOp,
  addDataPointsCore,
  changeCore,
  changeValuesCore,
  deleteDataPointsCore,
  driftCorrectionCore,
  fillGapsCore,
  findGapsCore,
  interpolateCore,
  persistenceCore,
  rateOfChangeCore,
  shiftDatetimesCollection,
  valueThresholdCore,
} from '../operation-cores'

const f32 = (v: number[]) => Float32Array.from(v)
const f64 = (v: number[]) => Float64Array.from(v)

// =====================================================================

describe('valueThresholdCore', () => {
  const y = f32([1, 5, 10, 15, 20])

  it('supports every opcode variant', () => {
    const cases: Array<[ThresholdOp, number, number[]]> = [
      [ThresholdOp.LT, 10, [0, 1]],
      [ThresholdOp.LTE, 10, [0, 1, 2]],
      [ThresholdOp.GT, 10, [3, 4]],
      [ThresholdOp.GTE, 10, [2, 3, 4]],
      [ThresholdOp.E, 10, [2]],
    ]
    for (const [op, v, expected] of cases) {
      expect(valueThresholdCore(y, 0, y.length, [op], [v])).toEqual(expected)
    }
  })

  it('falls through to equality for unknown opcodes', () => {
    expect(valueThresholdCore(y, 0, y.length, [99], [5])).toEqual([1])
  })

  it('short-circuits on the first matching opcode per element', () => {
    // ops: LT(5) matches index 0, GT(18) matches index 4.
    expect(
      valueThresholdCore(
        y,
        0,
        y.length,
        [ThresholdOp.LT, ThresholdOp.GT],
        [5, 18]
      )
    ).toEqual([0, 4])
  })

  it('honors the [start, end) range', () => {
    expect(valueThresholdCore(y, 1, 4, [ThresholdOp.GTE], [5])).toEqual([1, 2, 3])
  })
})

// =====================================================================

describe('changeCore', () => {
  // y = [10, 20, 21, 10]; Δ at i=1..3 = 10, 1, -11
  const y = f32([10, 20, 21, 10])

  it('handles every comparator', () => {
    const cases: Array<[string, number, number[]]> = [
      ['Less than', 0, [3]],
      ['Less than or equal to', 1, [2, 3]],
      ['Greater than', 1, [1]],
      ['Greater than or equal to', 10, [1]],
      ['Equal', 10, [1]],
    ]
    for (const [comp, val, expected] of cases) {
      expect(changeCore(y, 1, y.length, comp, val)).toEqual(expected)
    }
  })

  it('returns [] for unknown comparator', () => {
    expect(changeCore(y, 1, y.length, 'Bogus', 0)).toEqual([])
  })
})

// =====================================================================

describe('rateOfChangeCore', () => {
  // y = [10, 20, 15] → rates at i=1..2: (20-10)/10=1.0, (15-20)/20=-0.25
  const y = f32([10, 20, 15])

  it('selects indexes by every comparator', () => {
    expect(rateOfChangeCore(y, 1, y.length, 'Greater than', 0.5)).toEqual([1])
    expect(rateOfChangeCore(y, 1, y.length, 'Less than', 0)).toEqual([2])
    expect(rateOfChangeCore(y, 1, y.length, 'Less than or equal to', -0.25)).toEqual([2])
    expect(rateOfChangeCore(y, 1, y.length, 'Greater than or equal to', 1)).toEqual([1])
    expect(rateOfChangeCore(y, 1, y.length, 'Equal', 1)).toEqual([1])
  })

  it('returns [] for unknown comparator', () => {
    expect(rateOfChangeCore(y, 1, y.length, 'Bogus', 0)).toEqual([])
  })
})

// =====================================================================

describe('findGapsCore', () => {
  it('emits [left, right] pairs where Δx exceeds threshold', () => {
    // Δx: 1000, 5000, 1000 — threshold 2000 flags only the middle pair.
    const x = f64([0, 1000, 6000, 7000])
    expect(findGapsCore(x, 0, 3, 2000)).toEqual([1, 2])
  })

  it('returns [] when no gap exceeds the threshold', () => {
    const x = f64([0, 1000, 2000, 3000])
    expect(findGapsCore(x, 0, 3, 10_000)).toEqual([])
  })

  it('scans `[start, endInclusive]` inclusively', () => {
    // With endInclusive=2 we only examine indices 1..2; gap at (3,4) is ignored.
    const x = f64([0, 1, 2, 100, 101])
    expect(findGapsCore(x, 0, 2, 10)).toEqual([])
  })
})

// =====================================================================

describe('persistenceCore', () => {
  it('emits (startIndex, length, value) triplets per run of equal y', () => {
    const y = f32([1, 1, 2, 3, 3, 3])
    expect(persistenceCore(y, 0, y.length)).toEqual([0, 2, 1, 2, 1, 2, 3, 3, 3])
  })

  it('returns [] when start >= end', () => {
    expect(persistenceCore(f32([1, 2, 3]), 2, 2)).toEqual([])
  })

  it('emits a single run when every value is identical', () => {
    expect(persistenceCore(f32([7, 7, 7, 7]), 0, 4)).toEqual([0, 4, 7])
  })
})

// =====================================================================

describe('fillGapsCore', () => {
  it('inserts linearly-interpolated fill points inside gaps', () => {
    // x=[0, 1000, 11000] y=[0, 10, 110]. Gap at (1,2), fillDelta=2000.
    // Expected fills at 3000, 5000, 7000, 9000 with y = 30, 50, 70, 90.
    const sourceX = f64([0, 1000, 11000])
    const sourceY = f32([0, 10, 110])
    const outX = new Float64Array(7)
    const outY = new Float32Array(7)
    const written = fillGapsCore(
      sourceX,
      sourceY,
      [[1, 2]],
      outX,
      outY,
      0,
      2,
      0,
      2000,
      true,
      -9999
    )
    expect(written).toBe(7)
    expect(Array.from(outX)).toEqual([0, 1000, 3000, 5000, 7000, 9000, 11000])
    expect(Array.from(outY)).toEqual([0, 10, 30, 50, 70, 90, 110])
  })

  it('uses fillValue when interpolate is false', () => {
    const sourceX = f64([0, 10_000])
    const sourceY = f32([1, 2])
    const outX = new Float64Array(4)
    const outY = new Float32Array(4)
    fillGapsCore(
      sourceX,
      sourceY,
      [[0, 1]],
      outX,
      outY,
      0,
      1,
      0,
      3000,
      false,
      -9999
    )
    expect(Array.from(outY)).toEqual([1, -9999, -9999, -9999])
  })

  it('emits no fill when the gap is narrower than fillDelta', () => {
    const sourceX = f64([0, 500])
    const sourceY = f32([1, 2])
    const outX = new Float64Array(2)
    const outY = new Float32Array(2)
    const written = fillGapsCore(
      sourceX,
      sourceY,
      [[0, 1]],
      outX,
      outY,
      0,
      1,
      0,
      1000,
      true,
      -9999
    )
    expect(written).toBe(2)
    expect(Array.from(outX)).toEqual([0, 500])
  })
})

// =====================================================================

describe('addDataPointsCore', () => {
  it('merges originals with sorted insertions preserving datetime order', () => {
    const sourceX = f64([10, 20, 30])
    const sourceY = f32([1, 2, 3])
    const outX = new Float64Array(5)
    const outY = new Float32Array(5)
    const written = addDataPointsCore(
      sourceX,
      sourceY,
      [
        [15, 1.5],
        [25, 2.5],
      ],
      outX,
      outY,
      0,
      3,
      0
    )
    expect(written).toBe(5)
    expect(Array.from(outX)).toEqual([10, 15, 20, 25, 30])
    expect(Array.from(outY)).toEqual([1, 1.5, 2, 2.5, 3])
  })

  it('breaks datetime ties in favor of the original (findLastLessOrEqual)', () => {
    const sourceX = f64([10, 20])
    const sourceY = f32([1, 2])
    const outX = new Float64Array(3)
    const outY = new Float32Array(3)
    addDataPointsCore(sourceX, sourceY, [[20, 99]], outX, outY, 0, 2, 0)
    expect(Array.from(outX)).toEqual([10, 20, 20])
    expect(Array.from(outY)).toEqual([1, 2, 99])
  })

  it('appends trailing insertions when originals are exhausted', () => {
    const sourceX = f64([10])
    const sourceY = f32([1])
    const outX = new Float64Array(3)
    const outY = new Float32Array(3)
    addDataPointsCore(
      sourceX,
      sourceY,
      [
        [20, 2],
        [30, 3],
      ],
      outX,
      outY,
      0,
      1,
      0
    )
    expect(Array.from(outX)).toEqual([10, 20, 30])
    expect(Array.from(outY)).toEqual([1, 2, 3])
  })

  it('honors outStart so multiple segments can share an output buffer', () => {
    const sourceX = f64([10, 20])
    const sourceY = f32([1, 2])
    const outX = new Float64Array(4)
    const outY = new Float32Array(4)
    addDataPointsCore(sourceX, sourceY, [], outX, outY, 0, 2, 2)
    expect(Array.from(outX)).toEqual([0, 0, 10, 20])
    expect(Array.from(outY)).toEqual([0, 0, 1, 2])
  })
})

// =====================================================================

describe('deleteDataPointsCore', () => {
  it('copies [readStart, readEnd] skipping deleted indexes', () => {
    const sourceX = f64([10, 20, 30, 40, 50])
    const sourceY = f32([1, 2, 3, 4, 5])
    const outX = new Float64Array(3)
    const outY = new Float32Array(3)
    const written = deleteDataPointsCore(
      sourceX,
      sourceY,
      [1, 3],
      outX,
      outY,
      0,
      4,
      0
    )
    expect(written).toBe(3)
    expect(Array.from(outX)).toEqual([10, 30, 50])
    expect(Array.from(outY)).toEqual([1, 3, 5])
  })

  it('honors outStart so multiple segments can share an output buffer', () => {
    const sourceX = f64([10, 20, 30])
    const sourceY = f32([1, 2, 3])
    const outX = new Float64Array(5)
    const outY = new Float32Array(5)
    deleteDataPointsCore(sourceX, sourceY, [], outX, outY, 0, 2, 2)
    expect(Array.from(outX)).toEqual([0, 0, 10, 20, 30])
    expect(Array.from(outY)).toEqual([0, 0, 1, 2, 3])
  })
})

// =====================================================================

describe('shiftDatetimesCollection', () => {
  it('shifts by a precomputed deltaMs when unit is not month/year', () => {
    const x = f64([1_000_000, 2_000_000, 3_000_000])
    const y = f32([1, 2, 3])
    const out = shiftDatetimesCollection(x, y, [0, 2], {
      amount: 1,
      isMonth: false,
      isYear: false,
      deltaMs: 500_000,
    })
    expect(out).toEqual([
      [1_500_000, 1],
      [3_500_000, 3],
    ])
  })

  it('shifts by calendar months when isMonth is true', () => {
    const base = Date.UTC(2024, 0, 15)
    const [shifted] = shiftDatetimesCollection(f64([base]), f32([42]), [0], {
      amount: 2,
      isMonth: true,
      isYear: false,
      deltaMs: 0,
    })
    const a = new Date(base)
    const b = new Date(shifted[0])
    const monthDelta =
      (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth())
    expect(monthDelta).toBe(2)
    expect(shifted[1]).toBe(42)
  })

  it('shifts by calendar years when isYear is true', () => {
    const base = Date.UTC(2024, 5, 10)
    const [shifted] = shiftDatetimesCollection(f64([base]), f32([7]), [0], {
      amount: 3,
      isMonth: false,
      isYear: true,
      deltaMs: 0,
    })
    expect(new Date(shifted[0]).getFullYear() - new Date(base).getFullYear()).toBe(3)
  })

  it('returns an empty array for empty index list', () => {
    expect(
      shiftDatetimesCollection(f64([1]), f32([1]), [], {
        amount: 1,
        isMonth: false,
        isYear: false,
        deltaMs: 0,
      })
    ).toEqual([])
  })
})

// =====================================================================

describe('interpolateCore', () => {
  it('linearly interpolates group indexes between their anchors', () => {
    // Uniform x [0..4]. y=[0,10,?,?,40]. Group [2,3] anchored on 1 and 4 → 20, 30.
    const x = f64([0, 1, 2, 3, 4])
    const y = f32([0, 10, 999, 999, 40])
    interpolateCore(x, y, [{ indexes: [2, 3], lowerIdx: 1, upperIdx: 4 }])
    expect(+y[2].toFixed(3)).toBe(20)
    expect(+y[3].toFixed(3)).toBe(30)
  })

  it('collapses to the lower anchor when xSpan is zero', () => {
    const x = f64([5, 5, 5])
    const y = f32([1, 999, 3])
    interpolateCore(x, y, [{ indexes: [1], lowerIdx: 0, upperIdx: 2 }])
    expect(y[1]).toBe(1)
  })

  it('is a no-op for an empty group list', () => {
    const y = f32([1, 2, 3])
    const before = Array.from(y)
    interpolateCore(f64([0, 1, 2]), y, [])
    expect(Array.from(y)).toEqual(before)
  })
})

// =====================================================================

describe('driftCorrectionCore', () => {
  it('applies y_n += value * (x - startDatetime) / extent over each range', () => {
    const x = f64([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    const y = f32(Array(x.length).fill(0))
    // range [start=0, end=9, value=9] → extent = x[9]-x[0] = 9, so per-point
    // offset = 9 * (i - 0) / 9 = i. End index is exclusive in the write loop.
    driftCorrectionCore(x, y, [[0, 9, 9]])
    expect(Array.from(y).slice(0, 9)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8])
    expect(y[9]).toBe(0)
  })

  it('skips ranges with non-positive extent', () => {
    const x = f64([0, 0, 0])
    const y = f32([1, 2, 3])
    driftCorrectionCore(x, y, [[0, 2, 10]]) // extent = 0
    expect(Array.from(y)).toEqual([1, 2, 3])
  })

  it('skips ranges where end <= start', () => {
    const x = f64([0, 1, 2])
    const y = f32([1, 2, 3])
    driftCorrectionCore(x, y, [[2, 2, 10]])
    expect(Array.from(y)).toEqual([1, 2, 3])
  })
})

// =====================================================================

describe('changeValuesCore', () => {
  const y0 = [10, 20, 30, 40]

  it('applies ADD / SUB / MULT / DIV / ASSIGN to indexed elements', () => {
    const cases: Array<[string, number, number[]]> = [
      ['ADD', 5, [15, 25, 30, 40]],
      ['SUB', 5, [5, 15, 30, 40]],
      ['MULT', 2, [20, 40, 30, 40]],
      ['DIV', 2, [5, 10, 30, 40]],
      ['ASSIGN', 99, [99, 99, 30, 40]],
    ]
    for (const [op, v, expected] of cases) {
      const y = f32(y0)
      changeValuesCore(y, [0, 1], op, v)
      expect(Array.from(y)).toEqual(expected)
    }
  })

  it('is a no-op for an unknown operator', () => {
    const y = f32(y0)
    changeValuesCore(y, [0, 1], 'XYZ', 99)
    expect(Array.from(y)).toEqual(y0)
  })

  it('is a no-op for an empty index list', () => {
    const y = f32(y0)
    changeValuesCore(y, [], 'ADD', 5)
    expect(Array.from(y)).toEqual(y0)
  })
})
