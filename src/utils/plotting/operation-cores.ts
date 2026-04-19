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
 * Copy `[start, end]` of `sourceX` / `sourceY` into `outX` / `outY`
 * starting at `outStart`, inserting synthesized fill points after each
 * gap whose left index falls in the read range. `gaps` is a list of
 * `[leftIdx, rightIdx]` pairs, sorted by left index. `fillDelta` is
 * the spacing between inserted points in the same unit as `sourceX`.
 * When `interpolate` is true the filled Y values are linearly
 * interpolated between the gap's endpoints; otherwise `fillValue` is
 * written (used for "sentinel" -9999 fills).
 *
 * Shared by the `FillGapsWorker`'s per-segment write and the inline
 * full-array path. Returns the number of elements written so callers
 * can double-check contiguity against their pre-computed fill totals.
 */
export function fillGapsCore(
  sourceX: Float64Array | Float64Array<SharedArrayBuffer>,
  sourceY: Float32Array | Float32Array<SharedArrayBuffer>,
  gaps: ReadonlyArray<[number, number]>,
  outX: Float64Array | Float64Array<SharedArrayBuffer>,
  outY: Float32Array | Float32Array<SharedArrayBuffer>,
  start: number,
  end: number,
  outStart: number,
  fillDelta: number,
  interpolate: boolean,
  fillValue: number
): number {
  let gapPtr = 0
  let writePtr = outStart
  for (let readPtr = start; readPtr <= end; readPtr++) {
    outX[writePtr] = sourceX[readPtr]
    outY[writePtr] = sourceY[readPtr]
    writePtr++

    if (gapPtr < gaps.length && readPtr === gaps[gapPtr][0]) {
      const leftIdx = gaps[gapPtr][0]
      const rightIdx = gaps[gapPtr][1]
      const leftDatetime = sourceX[leftIdx]
      const rightDatetime = sourceX[rightIdx]
      const leftValue = sourceY[leftIdx]
      const rightValue = sourceY[rightIdx]
      const span = rightDatetime - leftDatetime
      const valueSpan = rightValue - leftValue

      let nextFillDatetime = leftDatetime + fillDelta
      while (nextFillDatetime < rightDatetime) {
        outX[writePtr] = nextFillDatetime
        outY[writePtr] = interpolate
          ? leftValue + ((nextFillDatetime - leftDatetime) * valueSpan) / span
          : fillValue
        writePtr++
        nextFillDatetime += fillDelta
      }
      gapPtr++
    }
  }
  return writePtr - outStart
}

/**
 * Merge a slice `[origStart, origEnd)` of `sourceX` / `sourceY` with
 * a pre-sorted list of `(x, y)` insertions into `outX` / `outY`
 * starting at `outStart`. Originals win on datetime ties so the
 * merged order matches `findLastLessOrEqual` semantics (insertion
 * lands after equal-valued originals). Writes in order; caller is
 * responsible for pre-allocating output buffers sized to
 * `origEnd - origStart + insertions.length`.
 *
 * Shared by the `AddDataWorker`'s segment merge and the inline
 * full-array path. Returns the number of elements written so callers
 * can double-check contiguity.
 */
export function addDataPointsCore(
  sourceX: Float64Array | Float64Array<SharedArrayBuffer>,
  sourceY: Float32Array | Float32Array<SharedArrayBuffer>,
  insertions: ReadonlyArray<[number, number]>,
  outX: Float64Array | Float64Array<SharedArrayBuffer>,
  outY: Float32Array | Float32Array<SharedArrayBuffer>,
  origStart: number,
  origEnd: number,
  outStart: number
): number {
  let origPtr = origStart
  let insPtr = 0
  let writePtr = outStart
  const insLen = insertions.length

  while (origPtr < origEnd && insPtr < insLen) {
    const insX = insertions[insPtr][0]
    if (sourceX[origPtr] <= insX) {
      outX[writePtr] = sourceX[origPtr]
      outY[writePtr] = sourceY[origPtr]
      origPtr++
    } else {
      outX[writePtr] = insX
      outY[writePtr] = insertions[insPtr][1]
      insPtr++
    }
    writePtr++
  }
  while (origPtr < origEnd) {
    outX[writePtr] = sourceX[origPtr]
    outY[writePtr] = sourceY[origPtr]
    origPtr++
    writePtr++
  }
  while (insPtr < insLen) {
    outX[writePtr] = insertions[insPtr][0]
    outY[writePtr] = insertions[insPtr][1]
    insPtr++
    writePtr++
  }
  return writePtr - outStart
}

/**
 * Copy `[readStart, readEnd]` of `sourceX` / `sourceY` into
 * `outX` / `outY` starting at `outStart`, skipping any index that
 * appears in `deleteIndices` (which must be sorted ascending and
 * bounded to the read range). Shared by the worker's per-segment
 * write path and the inline full-array path. Returns the number of
 * elements written so callers can double-check contiguity.
 */
export function deleteDataPointsCore(
  sourceX: Float64Array | Float64Array<SharedArrayBuffer>,
  sourceY: Float32Array | Float32Array<SharedArrayBuffer>,
  deleteIndices: ArrayLike<number>,
  outX: Float64Array | Float64Array<SharedArrayBuffer>,
  outY: Float32Array | Float32Array<SharedArrayBuffer>,
  readStart: number,
  readEnd: number,
  outStart: number
): number {
  let deletePtr = 0
  let writePtr = outStart
  for (let readPtr = readStart; readPtr <= readEnd; readPtr++) {
    if (
      deletePtr < deleteIndices.length &&
      readPtr === deleteIndices[deletePtr]
    ) {
      deletePtr++
    } else {
      outX[writePtr] = sourceX[readPtr]
      outY[writePtr] = sourceY[readPtr]
      writePtr++
    }
  }
  return writePtr - outStart
}

/** Params for `shiftDatetimesCollection`; mirrors the worker payload. */
export interface ShiftDatetimesParams {
  amount: number
  isMonth: boolean
  isYear: boolean
  /** Precomputed scalar ms offset; unused when `isMonth || isYear`. */
  deltaMs: number
}

/**
 * Compute shifted `(x, y)` pairs for each index in `indexes` without
 * allocating a `SharedArrayBuffer`. Mirrors the shift worker's branches
 * for month / year / scalar units. Returned in the same order as
 * `indexes` so the caller can hand the collection straight to
 * `_addDataPoints` after a `_deleteDataPoints(indexes)`.
 */
export function shiftDatetimesCollection(
  arrayX: Float64Array | Float64Array<SharedArrayBuffer>,
  arrayY: Float32Array | Float32Array<SharedArrayBuffer>,
  indexes: ArrayLike<number>,
  params: ShiftDatetimesParams
): [number, number][] {
  const n = indexes.length
  const out: [number, number][] = new Array(n)
  if (params.isMonth) {
    for (let i = 0; i < n; i++) {
      const idx = indexes[i]
      const d = new Date(arrayX[idx])
      d.setMonth(d.getMonth() + params.amount)
      out[i] = [d.getTime(), arrayY[idx]]
    }
  } else if (params.isYear) {
    for (let i = 0; i < n; i++) {
      const idx = indexes[i]
      const d = new Date(arrayX[idx])
      d.setFullYear(d.getFullYear() + params.amount)
      out[i] = [d.getTime(), arrayY[idx]]
    }
  } else {
    for (let i = 0; i < n; i++) {
      const idx = indexes[i]
      out[i] = [arrayX[idx] + params.deltaMs, arrayY[idx]]
    }
  }
  return out
}

/** Prepared group shape shared by `_interpolate` and its worker. */
export interface InterpolateGroup {
  indexes: number[]
  lowerIdx: number
  upperIdx: number
}

/**
 * Linear-interpolate Y-values at each group's `indexes` between the
 * anchor points at `lowerIdx` / `upperIdx`. Writes in place. Matches
 * the worker's degenerate-span semantics: if `lowerIdx === upperIdx`
 * (group sits at a buffer edge with no valid anchor on one side) we
 * paste the lone anchor value for every point in the group.
 */
export function interpolateCore(
  arrayX: Float64Array | Float64Array<SharedArrayBuffer>,
  arrayY: Float32Array | Float32Array<SharedArrayBuffer>,
  groups: InterpolateGroup[]
): void {
  for (let gi = 0; gi < groups.length; gi++) {
    const { indexes, lowerIdx, upperIdx } = groups[gi]
    const lowerX = arrayX[lowerIdx]
    const lowerY = arrayY[lowerIdx]
    const upperX = arrayX[upperIdx]
    const upperY = arrayY[upperIdx]
    const xSpan = upperX - lowerX
    const ySpan = upperY - lowerY
    if (xSpan === 0) {
      for (let i = 0; i < indexes.length; i++) arrayY[indexes[i]] = lowerY
      continue
    }
    for (let i = 0; i < indexes.length; i++) {
      const idx = indexes[i]
      arrayY[idx] = lowerY + ((arrayX[idx] - lowerX) * ySpan) / xSpan
    }
  }
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
