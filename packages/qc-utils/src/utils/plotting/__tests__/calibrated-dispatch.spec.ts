/**
 * Calibrated dispatch: small datasets run inline, large datasets run in workers.
 *
 * The dispatcher inside `ObservationRecord` consults `shouldUseWorker()`
 * (from `calibration.ts`) before every calibrated operation. The
 * decision depends on the device profile built by `runBenchmarks()`:
 * spawn overhead, inline throughput, worker throughput, hwConcurrency.
 *
 * This spec exercises that contract end-to-end:
 *   1. `beforeAll` runs the benchmark exactly once. Every test below
 *      reads the resulting profile via `shouldUseWorker()`.
 *   2. For each calibrated operation we binary-search the smallest
 *      dataset (or selection) size where the predictor flips to
 *      worker, then bracket comfortably below and above it.
 *   3. We dispatch the operation at both sizes through the real
 *      `ObservationRecord` and assert the recorded
 *      `HistoryItem.execution.mode` matches the predictor.
 *
 * Workers are the same `?worker&inline` modules `ObservationRecord`
 * imports in prod, stubbed by `workerMocks.ts` (which already powers
 * `observation-record.spec.ts`). The mocks flip
 * `_pendingExecutionMode` to "worker" the same way real workers do.
 *
 * If the benchmark on this machine produces a profile where some
 * operation's crossover falls outside `[CROSSOVER_FLOOR, MAX_TEST_SIZE]`,
 * the per-op pair is reported as skipped rather than silently passing —
 * a "workers never win" or "always win" calibration would otherwise
 * make the assertion vacuous.
 */

import { beforeAll, describe, expect, it, vi } from 'vitest'

// Worker mocks must register before `observation-record` / `calibration`
// load, since both import `?worker&inline` modules eagerly.
vi.mock('../delete-data.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockDeleteDataWorker })),
)
vi.mock('../fill-gaps.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockFillGapsWorker })),
)
vi.mock('../interpolate.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockInterpolateWorker })),
)
vi.mock('../drift-correction.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockDriftCorrectionWorker })),
)
vi.mock('../add-data.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockAddDataWorker })),
)
vi.mock('../shift-datetimes.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockShiftDatetimesWorker })),
)
vi.mock('../find-gaps.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockFindGapsWorker })),
)
vi.mock('../persistence.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockPersistenceWorker })),
)
vi.mock('../change.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockChangeWorker })),
)
vi.mock('../rate-of-change.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockRateOfChangeWorker })),
)
vi.mock('../value-threshold.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockValueThresholdWorker })),
)
vi.mock('../change-values.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockChangeValuesWorker })),
)

import { ObservationRecord } from '../observation-record'
import {
  ensureCalibration,
  shouldUseWorker,
  type DispatchSignals,
} from '../calibration'
import {
  EnumEditOperations,
  EnumFilterOperations,
  FilterOperation,
  Operator,
  TimeUnit,
} from '@/types'

/**
 * Memory ceiling for any dataset built in this spec. The largest test
 * size we'll ever ask for is `MAX_TEST_SIZE` points (two Float arrays
 * → ~5 MiB at 1M, fine for CI workers). Crossovers above this floor
 * mean the predictor judges worker dispatch unworthwhile up to the
 * test ceiling — we surface that as a skip rather than ramp the
 * fixture into the tens of millions.
 */
const MAX_TEST_SIZE = 1_000_000
const CROSSOVER_FLOOR = 8 // Below this, even the "small" bracket can't be inline-only.
const SAFETY_FACTOR = 4 // Bracket sizes 4× either side of the crossover.

/** Build a uniform-grid synthetic series, 15-minute spacing. */
function buildUniformInput(size: number) {
  const datetimes = new Array<number>(size)
  const dataValues = new Array<number>(size)
  const startMs = Date.UTC(2023, 0, 1)
  const spacingMs = 15 * 60 * 1000
  for (let i = 0; i < size; i++) {
    datetimes[i] = startMs + i * spacingMs
    // `y = i % 1000` keeps PERSISTENCE runnable on any size: runs of
    // identical values appear at length 1, which never matches the
    // default `>=3` threshold below — so we won't accidentally hit a
    // zero-work shortcut inside the kernel.
    dataValues[i] = (i % 1000) + 1
  }
  return { datetimes, dataValues, startMs, spacingMs }
}

/** Construct + reload an ObservationRecord, ready for dispatch. */
async function makeRecord(size: number): Promise<ObservationRecord> {
  const raw = buildUniformInput(size)
  const rec = new ObservationRecord({
    datetimes: raw.datetimes,
    dataValues: raw.dataValues,
  })
  await rec.reload()
  return rec
}

/**
 * Read the execution mode that `dispatch` recorded on the last
 * non-SELECTION history entry. Filters that are immediately followed
 * by an unrelated edit may have their SELECTION spliced out, so we
 * walk back to find the most recent calibrated entry.
 */
function lastCalibratedMode(
  rec: ObservationRecord,
): 'inline' | 'worker' | undefined {
  for (let i = rec.history.length - 1; i >= 0; i--) {
    const entry = rec.history[i]
    if (entry.method !== EnumFilterOperations.SELECTION) {
      return entry.execution?.mode
    }
  }
  return undefined
}

/**
 * Binary-search the smallest size value at which `shouldUseWorker`
 * flips to `useWorker: true`. The `axis` callback maps a candidate
 * value into the `DispatchSignals` shape the op expects — datasetSize
 * for full-scan ops, selectionSize for selection-bound ops.
 */
function findCrossover(
  op: EnumEditOperations | EnumFilterOperations,
  axis: (size: number) => DispatchSignals,
): number | null {
  const lo0 = 1
  const hi0 = MAX_TEST_SIZE * 4
  // Decide first if a flip exists at all in [lo0, hi0].
  if (shouldUseWorker(op, axis(lo0)).useWorker) return 1
  if (!shouldUseWorker(op, axis(hi0)).useWorker) return null
  let lo = lo0
  let hi = hi0
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2)
    if (shouldUseWorker(op, axis(mid)).useWorker) hi = mid
    else lo = mid + 1
  }
  return lo
}

/**
 * Each calibrated operation gets one entry below. `axis` decides
 * whether the size sweeps `datasetSize` (full-scan ops) or
 * `selectionSize` (selection-bound ops). `prepare` builds the
 * `ObservationRecord` and returns a thunk that runs the dispatch with
 * `targetSize` as the dispatched payload size; `selectionSize`-axis
 * cases keep `datasetSize` fixed at `SELECTION_AXIS_DATASET` so the
 * crossover prediction lines up with the call-site signal.
 */
const SELECTION_AXIS_DATASET = 4 * MAX_TEST_SIZE // big enough that any sane crossover lies below.

interface CalibratedCase {
  op: EnumEditOperations | EnumFilterOperations
  name: string
  axis: (size: number) => DispatchSignals
  run(targetSize: number): Promise<ObservationRecord>
}

const cases: CalibratedCase[] = [
  // --- Filter operations (datasetSize-driven) ---------------------------
  {
    op: EnumFilterOperations.VALUE_THRESHOLD,
    name: 'VALUE_THRESHOLD',
    axis: (datasetSize) => ({ datasetSize }),
    async run(size) {
      const rec = await makeRecord(size)
      await rec.dispatch(EnumFilterOperations.VALUE_THRESHOLD, {
        [FilterOperation.GTE]: 0,
      })
      return rec
    },
  },
  {
    op: EnumFilterOperations.CHANGE,
    name: 'CHANGE',
    axis: (datasetSize) => ({ datasetSize }),
    async run(size) {
      const rec = await makeRecord(size)
      await rec.dispatch(
        EnumFilterOperations.CHANGE,
        FilterOperation.GTE,
        0,
      )
      return rec
    },
  },
  {
    op: EnumFilterOperations.RATE_OF_CHANGE,
    name: 'RATE_OF_CHANGE',
    axis: (datasetSize) => ({ datasetSize }),
    async run(size) {
      const rec = await makeRecord(size)
      await rec.dispatch(
        EnumFilterOperations.RATE_OF_CHANGE,
        FilterOperation.GT,
        -Infinity,
      )
      return rec
    },
  },
  {
    op: EnumFilterOperations.FIND_GAPS,
    name: 'FIND_GAPS',
    axis: (datasetSize) => ({ datasetSize }),
    async run(size) {
      const rec = await makeRecord(size)
      // Threshold larger than the 15-minute fixture spacing so no
      // gaps are flagged — keeps the kernel's branch shape uniform
      // across small and large runs.
      await rec.dispatch(EnumFilterOperations.FIND_GAPS, 1, TimeUnit.HOUR)
      return rec
    },
  },
  {
    op: EnumFilterOperations.PERSISTENCE,
    name: 'PERSISTENCE',
    axis: (datasetSize) => ({ datasetSize }),
    async run(size) {
      const rec = await makeRecord(size)
      // Threshold of 5 never matches our `i % 1000` fixture (runs of 1).
      await rec.dispatch(EnumFilterOperations.PERSISTENCE, 5)
      return rec
    },
  },

  // --- Edit operations (selectionSize-driven) ---------------------------
  {
    op: EnumEditOperations.CHANGE_VALUES,
    name: 'CHANGE_VALUES',
    axis: (selectionSize) => ({
      datasetSize: SELECTION_AXIS_DATASET,
      selectionSize,
    }),
    async run(size) {
      const rec = await makeRecord(Math.max(size, 16))
      const selection = consecutiveIndexes(size, rec.dataX.length)
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, selection],
        [EnumEditOperations.CHANGE_VALUES, Operator.ADD, 1],
      ])
      return rec
    },
  },
  {
    op: EnumEditOperations.INTERPOLATE,
    name: 'INTERPOLATE',
    axis: (selectionSize) => ({
      datasetSize: SELECTION_AXIS_DATASET,
      selectionSize,
    }),
    async run(size) {
      // Interpolation needs anchor points on each side of the
      // selection; offset by 1 from the edges of the dataset.
      const rec = await makeRecord(Math.max(size + 4, 16))
      const selection = consecutiveIndexes(size, rec.dataX.length, 2)
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, selection],
        [EnumEditOperations.INTERPOLATE],
      ])
      return rec
    },
  },
  {
    op: EnumEditOperations.SHIFT_DATETIMES,
    name: 'SHIFT_DATETIMES',
    axis: (selectionSize) => ({
      datasetSize: SELECTION_AXIS_DATASET,
      selectionSize,
    }),
    async run(size) {
      const rec = await makeRecord(Math.max(size, 16))
      const selection = consecutiveIndexes(size, rec.dataX.length)
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, selection],
        [EnumEditOperations.SHIFT_DATETIMES, 1, TimeUnit.HOUR],
      ])
      return rec
    },
  },
  {
    op: EnumEditOperations.DRIFT_CORRECTION,
    name: 'DRIFT_CORRECTION',
    axis: (selectionSize) => ({
      datasetSize: SELECTION_AXIS_DATASET,
      selectionSize,
    }),
    async run(size) {
      const rec = await makeRecord(Math.max(size + 1, 16))
      const selection = consecutiveIndexes(size, rec.dataX.length)
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, selection],
        [EnumEditOperations.DRIFT_CORRECTION, 1],
      ])
      return rec
    },
  },

  // --- Edit operations (mixed sizing) -----------------------------------
  {
    op: EnumEditOperations.DELETE_POINTS,
    name: 'DELETE_POINTS',
    // Work units = selectionSize + datasetSize * 0.25. Fixing
    // selectionSize at 1 makes the crossover sweep cleanly through
    // `datasetSize`. The dispatch below scales the selection
    // proportionally so the actual call exercises the sized path.
    axis: (datasetSize) => ({
      datasetSize,
      selectionSize: Math.max(1, Math.floor(datasetSize / 8)),
    }),
    async run(size) {
      const rec = await makeRecord(Math.max(size, 16))
      const selection = consecutiveIndexes(
        Math.max(1, Math.floor(size / 8)),
        rec.dataX.length,
      )
      await rec.dispatch([
        [EnumFilterOperations.SELECTION, selection],
        [EnumEditOperations.DELETE_POINTS],
      ])
      return rec
    },
  },
  {
    op: EnumEditOperations.ADD_POINTS,
    name: 'ADD_POINTS',
    // Work units = datasetSize + selectionSize * log(datasetSize).
    // Sweep `datasetSize` with a tiny insertions list so the test
    // payload stays bounded.
    axis: (datasetSize) => ({ datasetSize, selectionSize: 1 }),
    async run(size) {
      const rec = await makeRecord(Math.max(size, 16))
      // Insert one point at the centre of the time window so the
      // datetimes stay sorted after dispatch.
      const center = rec.dataX[Math.floor(rec.dataX.length / 2)] + 1
      await rec.dispatch(EnumEditOperations.ADD_POINTS, [[center, 0]])
      return rec
    },
  },
  {
    op: EnumEditOperations.FILL_GAPS,
    name: 'FILL_GAPS',
    axis: (datasetSize) => ({ datasetSize }),
    async run(size) {
      // `_fillGaps` short-circuits when no gap exceeds the threshold,
      // so a uniform fixture would skip the dispatch entirely
      // regardless of size. Punch a single 4-hour gap into the series
      // by deleting one of the centre samples — the rest of the
      // dataset still drives the O(n) copy-with-fills pass that
      // dominates the calibrated prediction.
      const safeSize = Math.max(size, 16)
      const raw = buildUniformInput(safeSize + 1)
      const cut = Math.floor(raw.datetimes.length / 2)
      raw.datetimes.splice(cut, 1)
      raw.dataValues.splice(cut, 1)
      const rec = new ObservationRecord({
        datetimes: raw.datetimes,
        dataValues: raw.dataValues,
      })
      await rec.reload()
      // Threshold 20 min catches the new 30-min hole; one fill at 15
      // min keeps the inserted-points list tiny so the call's cost
      // stays dataset-bound (matching the predictor's work-units model).
      await rec.dispatch(
        EnumEditOperations.FILL_GAPS,
        [20, TimeUnit.MINUTE],
        [15, TimeUnit.MINUTE],
        false,
        -9999,
      )
      return rec
    },
  },
]

/** Return `count` ascending indices into a dataset of `datasetLen`. */
function consecutiveIndexes(
  count: number,
  datasetLen: number,
  offset = 0,
): number[] {
  const safe = Math.max(0, Math.min(count, datasetLen - offset))
  const out: number[] = new Array(safe)
  for (let i = 0; i < safe; i++) out[i] = i + offset
  return out
}

describe('Calibrated dispatch: inline below crossover, worker above', () => {
  // One benchmark for the whole spec. `ensureCalibration` short-
  // circuits subsequent calls when the profile is fresh.
  beforeAll(async () => {
    await ensureCalibration({ force: true })
  }, 30_000)

  for (const c of cases) {
    describe(c.name, () => {
      let crossover: number | null = null
      let smallSize = 0
      let largeSize = 0

      beforeAll(() => {
        crossover = findCrossover(c.op, c.axis)
        if (crossover != null) {
          smallSize = Math.max(1, Math.floor(crossover / SAFETY_FACTOR))
          largeSize = Math.min(MAX_TEST_SIZE, crossover * SAFETY_FACTOR)
        }
      })

      it('binary-search finds a usable crossover for this device', () => {
        expect(crossover).not.toBeNull()
        expect(crossover).toBeGreaterThanOrEqual(CROSSOVER_FLOOR)
        expect(crossover).toBeLessThanOrEqual(MAX_TEST_SIZE)
        // Bracket sanity: the predictor must actually flip across our
        // chosen sizes. Without this guard, a tight bracket near the
        // floor could leave both ends on the same side of the curve.
        expect(shouldUseWorker(c.op, c.axis(smallSize)).useWorker).toBe(false)
        expect(shouldUseWorker(c.op, c.axis(largeSize)).useWorker).toBe(true)
      })

      it('runs inline below the crossover', async () => {
        const rec = await c.run(smallSize)
        const mode = lastCalibratedMode(rec)
        expect(mode).toBe('inline')
      }, 30_000)

      it('runs in a worker above the crossover', async () => {
        const rec = await c.run(largeSize)
        const mode = lastCalibratedMode(rec)
        expect(mode).toBe('worker')
      }, 30_000)
    })
  }
})
