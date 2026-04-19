/**
 * Pure, framework-free primitive kernels for each QC operation whose
 * worker has a one-to-one inline equivalent. Shared by both the
 * `?worker&inline` Vite workers and `ObservationRecord`'s non-worker
 * fast paths so there's a single source of truth for each algorithm —
 * if the worker's hot loop drifts from the main-thread loop we get
 * silently wrong selections, which the calibration feature would make
 * far easier to trigger.
 *
 * Keep these functions:
 *   - allocation-frugal (no unnecessary intermediate arrays),
 *   - free of module-level `self` / `postMessage` references (callable
 *     in either context),
 *   - deterministic given identical inputs (so worker output can be
 *     diffed against inline output when debugging drift).
 */

/** Opcode encoding used by `valueThresholdCore` (matches the worker). */
export const enum ThresholdOp {
  LT = 0,
  LTE = 1,
  GT = 2,
  GTE = 3,
  E = 4,
}

/**
 * Scan `[start, end)` of `arrayY` and collect every index where the
 * value matches ANY of the supplied comparator/threshold pairs. Short-
 * circuits on first match per element (matches worker semantics).
 */
export function valueThresholdCore(
  arrayY: Float32Array | Float32Array<SharedArrayBuffer>,
  start: number,
  end: number,
  ops: number[],
  values: number[]
): number[] {
  const indexes: number[] = []
  const nFilters = ops.length
  for (let i = start; i < end; i++) {
    const v = arrayY[i]
    let match = false
    for (let k = 0; k < nFilters; k++) {
      const op = ops[k]
      const t = values[k]
      if (op === ThresholdOp.LT) {
        if (v < t) { match = true; break }
      } else if (op === ThresholdOp.LTE) {
        if (v <= t) { match = true; break }
      } else if (op === ThresholdOp.GT) {
        if (v > t) { match = true; break }
      } else if (op === ThresholdOp.GTE) {
        if (v >= t) { match = true; break }
      } else {
        if (v == t) { match = true; break }
      }
    }
    if (match) indexes.push(i)
  }
  return indexes
}

/**
 * First-difference filter: collect indexes in `[start, end)` where
 * `Y[i] - Y[i-1]` satisfies the comparator. Comparator strings match
 * the worker exactly (FilterOperation enum values).
 */
export function changeCore(
  arrayY: Float32Array | Float32Array<SharedArrayBuffer>,
  start: number,
  end: number,
  comparator: string,
  value: number
): number[] {
  const indexes: number[] = []
  if (comparator === 'Less than') {
    for (let i = start; i < end; i++) {
      if (arrayY[i] - arrayY[i - 1] < value) indexes.push(i)
    }
  } else if (comparator === 'Less than or equal to') {
    for (let i = start; i < end; i++) {
      if (arrayY[i] - arrayY[i - 1] <= value) indexes.push(i)
    }
  } else if (comparator === 'Greater than') {
    for (let i = start; i < end; i++) {
      if (arrayY[i] - arrayY[i - 1] > value) indexes.push(i)
    }
  } else if (comparator === 'Greater than or equal to') {
    for (let i = start; i < end; i++) {
      if (arrayY[i] - arrayY[i - 1] >= value) indexes.push(i)
    }
  } else if (comparator === 'Equal') {
    for (let i = start; i < end; i++) {
      if (arrayY[i] - arrayY[i - 1] == value) indexes.push(i)
    }
  }
  return indexes
}

/**
 * Relative rate-of-change: `(Y[i] - Y[i-1]) / |Y[i-1]|`. Same
 * comparator semantics as `changeCore`.
 */
export function rateOfChangeCore(
  arrayY: Float32Array | Float32Array<SharedArrayBuffer>,
  start: number,
  end: number,
  comparator: string,
  value: number
): number[] {
  const indexes: number[] = []
  if (comparator === 'Less than') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1]
      if ((arrayY[i] - prev) / Math.abs(prev) < value) indexes.push(i)
    }
  } else if (comparator === 'Less than or equal to') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1]
      if ((arrayY[i] - prev) / Math.abs(prev) <= value) indexes.push(i)
    }
  } else if (comparator === 'Greater than') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1]
      if ((arrayY[i] - prev) / Math.abs(prev) > value) indexes.push(i)
    }
  } else if (comparator === 'Greater than or equal to') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1]
      if ((arrayY[i] - prev) / Math.abs(prev) >= value) indexes.push(i)
    }
  } else if (comparator === 'Equal') {
    for (let i = start; i < end; i++) {
      const prev = arrayY[i - 1]
      if ((arrayY[i] - prev) / Math.abs(prev) == value) indexes.push(i)
    }
  }
  return indexes
}

/**
 * Detect datetime gaps: returns a flat `[leftIdx, rightIdx, ...]`
 * list for every pair whose datetime delta exceeds `threshold` ms.
 * Scan covers `[start, endInclusive]`.
 */
export function findGapsCore(
  arrayX: Float64Array | Float64Array<SharedArrayBuffer>,
  start: number,
  endInclusive: number,
  threshold: number
): number[] {
  const pairs: number[] = []
  let prev = arrayX[start]
  for (let i = start + 1; i <= endInclusive; i++) {
    const curr = arrayX[i]
    if (curr - prev > threshold) pairs.push(i - 1, i)
    prev = curr
  }
  return pairs
}

/**
 * Emit maximal runs of equal Y values in `[start, end)` as flat
 * `[startIndex, length, value, ...]` triplets. Downstream stitches
 * adjacent chunk triplets before applying the min-run-length filter.
 */
export function persistenceCore(
  arrayY: Float32Array | Float32Array<SharedArrayBuffer>,
  start: number,
  end: number
): number[] {
  const runs: number[] = []
  if (start >= end) return runs
  let runStart = start
  let runValue = arrayY[start]
  for (let i = start + 1; i < end; i++) {
    const v = arrayY[i]
    if (v !== runValue) {
      runs.push(runStart, i - runStart, runValue)
      runStart = i
      runValue = v
    }
  }
  runs.push(runStart, end - runStart, runValue)
  return runs
}

/**
 * Apply linear drift correction over one or more `[start, end, value]`
 * ranges in place on `arrayY`, using `arrayX` only to compute each
 * range's time anchors. Per-point formula:
 *
 *     y_i += value * (x_i - startDatetime) / extent
 *
 * where `startDatetime = x[start]` and `extent = x[end] - x[start]`.
 * Ranges with non-positive extent are skipped to match the worker's
 * behaviour. The whole operation is O(total range length) — no
 * chunking or spawning, suitable for the inline calibration path.
 */
export function driftCorrectionCore(
  arrayX: Float64Array | Float64Array<SharedArrayBuffer>,
  arrayY: Float32Array | Float32Array<SharedArrayBuffer>,
  ranges: [number, number, number][]
): void {
  for (let r = 0; r < ranges.length; r++) {
    const start = ranges[r][0]
    const end = ranges[r][1]
    const value = ranges[r][2]
    if (end <= start) continue
    const startDatetime = arrayX[start]
    const extent = arrayX[end] - startDatetime
    if (extent === 0) continue
    for (let i = start; i < end; i++) {
      arrayY[i] = arrayY[i] + value * ((arrayX[i] - startDatetime) / extent)
    }
  }
}

/**
 * Apply an arithmetic operator to `arrayY` at each index in
 * `indexes`. Operator strings match `Operator` enum values.
 */
export function changeValuesCore(
  arrayY: Float32Array | Float32Array<SharedArrayBuffer>,
  indexes: ArrayLike<number>,
  operator: string,
  value: number
): void {
  const n = indexes.length
  if (operator === 'ADD') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] + value
  } else if (operator === 'SUB') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] - value
  } else if (operator === 'MULT') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] * value
  } else if (operator === 'DIV') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = arrayY[indexes[i]] / value
  } else if (operator === 'ASSIGN') {
    for (let i = 0; i < n; i++) arrayY[indexes[i]] = value
  }
}
