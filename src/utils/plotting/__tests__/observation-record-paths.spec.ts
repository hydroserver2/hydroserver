/**
 * Coverage-focused tests for `observation-record.ts` that exercise
 * paths the baseline spec skips:
 *
 *   1. **Worker fan-out paths** — every `_operation` routes through
 *      `shouldUseWorker()` and falls back to an inline core for small
 *      inputs. The existing `observation-record.spec.ts` uses tiny
 *      datasets, so only the inline branches run. Here we mock
 *      `../calibration` so callers can flip `forceWorker = true` and
 *      drive the worker branches without needing multi-MB fixtures.
 *   2. **Bulk assignment ops** — `ASSIGN_VALUES_BULK` and
 *      `ASSIGN_DATETIMES_BULK` aren't touched by the baseline spec.
 *   3. **Undo / redo** — `undo()` / `redo()` have their own state
 *      machines that aren't driven by the `dispatch()` tests.
 *   4. **DATETIME_RANGE, SELECTION pop** — the remaining filter ops.
 *
 * Mocks are hoisted via `vi.mock`; the real calibration module is
 * wrapped so non-mocked helpers (getCalibration, etc.) still work if
 * anything reaches for them.
 */

import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

// Controls whether the mocked `shouldUseWorker` returns useWorker=true.
// Toggle per-test via `forceWorker = <bool>` before calling dispatch.
let forceWorker = false

vi.mock('../calibration', async (importOriginal) => {
  const real = await importOriginal<typeof import('../calibration')>()
  return {
    ...real,
    shouldUseWorker: () => ({
      useWorker: forceWorker,
      predictedInlineMs: forceWorker ? 100 : 0,
      predictedWorkerMs: forceWorker ? 1 : 50,
      reason: forceWorker ? 'forced worker (test)' : 'forced inline (test)',
    }),
  }
})

// Worker mocks — reuse the same shims as `observation-record.spec.ts`.
vi.mock('../delete-data.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockDeleteDataWorker }))
)
vi.mock('../fill-gaps.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockFillGapsWorker }))
)
vi.mock('../interpolate.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockInterpolateWorker }))
)
vi.mock('../drift-correction.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockDriftCorrectionWorker }))
)
vi.mock('../add-data.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockAddDataWorker }))
)
vi.mock('../shift-datetimes.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockShiftDatetimesWorker }))
)
vi.mock('../find-gaps.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockFindGapsWorker }))
)
vi.mock('../persistence.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockPersistenceWorker }))
)
vi.mock('../change.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockChangeWorker }))
)
vi.mock('../rate-of-change.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockRateOfChangeWorker }))
)
vi.mock('../value-threshold.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockValueThresholdWorker }))
)
vi.mock('../change-values.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockChangeValuesWorker }))
)

import { ObservationRecord } from '../observation-record'
import {
  EnumEditOperations,
  EnumFilterOperations,
  FilterOperation,
  Operator,
  TimeUnit,
} from '@/types'

/**
 * Some edit ops skip `await Promise.all(promises)` when `import.meta.env.MODE
 * === "test"`. The mock workers post results via `queueMicrotask`, so we
 * give the microtask queue one extra turn to drain before asserting on
 * mutated buffers.
 */
async function flushMicrotasks() {
  await new Promise((resolve) => setTimeout(resolve, 0))
}

/** Build a uniform-grid dataset. */
function uniform(size: number, y0 = 0, step = 1) {
  const spacingMs = 15 * 60 * 1000
  const startMs = Date.UTC(2023, 0, 1)
  const datetimes = new Array<number>(size)
  const dataValues = new Array<number>(size)
  for (let i = 0; i < size; i++) {
    datetimes[i] = startMs + i * spacingMs
    dataValues[i] = y0 + i * step
  }
  return { datetimes, dataValues }
}

describe('ObservationRecord — worker paths', () => {
  let rec: ObservationRecord

  beforeEach(async () => {
    forceWorker = true
    rec = new ObservationRecord(uniform(40, 0, 10))
    await rec.reload()
  })

  afterEach(() => {
    forceWorker = false
  })

  it('CHANGE_VALUES fans out when N >= threshold and useWorker=true', async () => {
    // Need N >= CHANGE_VALUES_WORKER_THRESHOLD (1024). Build a tall dataset
    // and select every index — the internal threshold gate is what we're
    // exercising, not the arithmetic correctness.
    const big = uniform(2000, 5, 0)
    const tall = new ObservationRecord(big)
    await tall.reload()
    const selection = Array.from({ length: 2000 }, (_, i) => i)
    await tall.dispatch([
      [EnumFilterOperations.SELECTION, selection],
      [EnumEditOperations.CHANGE_VALUES, Operator.ADD, 1],
    ])
    await flushMicrotasks()
    const last = tall.history[tall.history.length - 1]
    expect(last.method).toBe(EnumEditOperations.CHANGE_VALUES)
    expect(last.executionMode).toBe('worker')
    expect(tall.dataY[0]).toBe(6)
  })

  it('CHANGE_VALUES falls back to inline when N is below the threshold', async () => {
    // Even with forceWorker=true, the static N<1024 gate keeps this inline.
    await rec.dispatch([
      [EnumFilterOperations.SELECTION, [0, 1, 2]],
      [EnumEditOperations.CHANGE_VALUES, Operator.ADD, 100],
    ])
    const last = rec.history[rec.history.length - 1]
    expect(last.executionMode).toBe('inline')
    expect(rec.dataY[0]).toBe(100)
  })

  it('INTERPOLATE fans out to workers', async () => {
    // Overwrite middle values so we can check interp recovers the line.
    rec.dataY[10] = 999
    rec.dataY[11] = 999
    await rec.dispatch(EnumEditOperations.INTERPOLATE, [10, 11])
    await flushMicrotasks()
    const last = rec.history[rec.history.length - 1]
    expect(last.executionMode).toBe('worker')
  })

  it('SHIFT_DATETIMES fans out to workers', async () => {
    const originalLen = rec.dataX.length
    await rec.dispatch(
      EnumEditOperations.SHIFT_DATETIMES,
      [5, 6, 7],
      1,
      TimeUnit.HOUR
    )
    await flushMicrotasks()
    const last = rec.history[rec.history.length - 1]
    expect(last.executionMode).toBe('worker')
    expect(rec.dataX.length).toBe(originalLen)
  })

  it('DELETE_POINTS fans out to workers', async () => {
    const originalLen = rec.dataX.length
    await rec.dispatch(EnumEditOperations.DELETE_POINTS, [0, 5, 10])
    await flushMicrotasks()
    const last = rec.history[rec.history.length - 1]
    expect(last.executionMode).toBe('worker')
    expect(rec.dataX.length).toBe(originalLen - 3)
  })

  it('ADD_POINTS fans out to workers', async () => {
    const before = rec.dataX.length
    const pts: [number, number][] = [
      [rec.dataX[2] + 1, 99],
      [rec.dataX[20] + 1, 77],
    ]
    await rec.dispatch(EnumEditOperations.ADD_POINTS, pts)
    await flushMicrotasks()
    const last = rec.history[rec.history.length - 1]
    expect(last.executionMode).toBe('worker')
    expect(rec.dataX.length).toBe(before + 2)
  })

  it('DRIFT_CORRECTION fans out to workers', async () => {
    const baseline = Array.from(rec.dataY)
    await rec.dispatch(EnumEditOperations.DRIFT_CORRECTION, [[0, 20, 10]])
    await flushMicrotasks()
    const last = rec.history[rec.history.length - 1]
    expect(last.executionMode).toBe('worker')
    // Interior points should have shifted from their baseline.
    expect(rec.dataY[5]).not.toBe(baseline[5])
  })

  it('FILL_GAPS fans out to workers', async () => {
    // Build a dataset with a single large gap.
    const spacingMs = 15 * 60 * 1000
    const startMs = Date.UTC(2023, 0, 1)
    const datetimes = [
      startMs,
      startMs + spacingMs,
      startMs + spacingMs + 4 * 60 * 60 * 1000, // ~4-hour gap
      startMs + spacingMs + 4 * 60 * 60 * 1000 + spacingMs,
    ]
    const dataValues = [0, 1, 2, 3]
    const local = new ObservationRecord({ datetimes, dataValues })
    await local.reload()
    const before = local.dataX.length
    await local.dispatch(
      EnumEditOperations.FILL_GAPS,
      [30, TimeUnit.MINUTE],
      [1, TimeUnit.HOUR],
      true,
      -9999
    )
    await flushMicrotasks()
    const last = local.history[local.history.length - 1]
    expect(last.executionMode).toBe('worker')
    expect(local.dataX.length).toBeGreaterThan(before)
  })

  it('VALUE_THRESHOLD fans out to workers', async () => {
    const selection = await rec.dispatch(
      EnumFilterOperations.VALUE_THRESHOLD,
      { [FilterOperation.GTE]: 200 }
    )
    expect(rec.history[rec.history.length - 1].executionMode).toBe('worker')
    // dataY = [0, 10, 20, ...], so indexes 20..39 have y >= 200.
    expect(selection[0]).toBe(20)
    expect(selection[selection.length - 1]).toBe(39)
  })

  it('CHANGE fans out to workers', async () => {
    const selection = await rec.dispatch(
      EnumFilterOperations.CHANGE,
      FilterOperation.GTE,
      10
    )
    expect(rec.history[rec.history.length - 1].executionMode).toBe('worker')
    // Uniform step = 10, so every adjacent Δ matches.
    expect(selection.length).toBe(rec.dataY.length - 1)
  })

  it('RATE_OF_CHANGE fans out to workers', async () => {
    const selection = await rec.dispatch(
      EnumFilterOperations.RATE_OF_CHANGE,
      FilterOperation.GT,
      0.5
    )
    expect(rec.history[rec.history.length - 1].executionMode).toBe('worker')
    // (10-0)/0 is Infinity → matches; (20-10)/10 = 1 > 0.5 → matches.
    expect(selection.length).toBeGreaterThan(0)
  })

  it('FIND_GAPS fans out to workers', async () => {
    // Insert one large gap in a uniform dataset.
    const spacingMs = 15 * 60 * 1000
    const startMs = Date.UTC(2023, 0, 1)
    const datetimes = [
      startMs,
      startMs + spacingMs,
      startMs + spacingMs + 4 * 60 * 60 * 1000,
      startMs + spacingMs + 4 * 60 * 60 * 1000 + spacingMs,
    ]
    const dataValues = [0, 1, 2, 3]
    const local = new ObservationRecord({ datetimes, dataValues })
    await local.reload()
    forceWorker = true
    const selection = await local.dispatch(
      EnumFilterOperations.FIND_GAPS,
      30,
      TimeUnit.MINUTE
    )
    expect(local.history[local.history.length - 1].executionMode).toBe('worker')
    expect(selection.sort((a, b) => a - b)).toEqual([1, 2])
  })

  it('PERSISTENCE fans out to workers and stitches boundary runs', async () => {
    // Build a dataset dominated by a single long run so boundary stitching
    // is exercised when the run crosses chunk edges.
    const datetimes = Array.from({ length: 60 }, (_, i) => i * 1000)
    const dataValues = Array(60).fill(7)
    const local = new ObservationRecord({ datetimes, dataValues })
    await local.reload()
    const selection = await local.dispatch(
      EnumFilterOperations.PERSISTENCE,
      20
    )
    expect(local.history[local.history.length - 1].executionMode).toBe('worker')
    expect(selection.length).toBe(60)
  })
})

describe('ObservationRecord — bulk ops', () => {
  let rec: ObservationRecord
  beforeEach(async () => {
    forceWorker = false
    rec = new ObservationRecord(uniform(20, 0, 10))
    await rec.reload()
  })

  it('ASSIGN_VALUES_BULK writes parallel values at the selected indexes', async () => {
    await rec.dispatch([
      [EnumFilterOperations.SELECTION, [2, 5, 8]],
      [EnumEditOperations.ASSIGN_VALUES_BULK, [111, 222, 333]],
    ])
    expect(rec.dataY[2]).toBe(111)
    expect(rec.dataY[5]).toBe(222)
    expect(rec.dataY[8]).toBe(333)
  })

  it('ASSIGN_VALUES_BULK is a no-op without a prior selection', async () => {
    const before = Array.from(rec.dataY)
    await rec.dispatch(EnumEditOperations.ASSIGN_VALUES_BULK, [1, 2, 3])
    expect(Array.from(rec.dataY)).toEqual(before)
  })

  it('ASSIGN_VALUES_BULK is a no-op for empty values array', async () => {
    const before = Array.from(rec.dataY)
    await rec.dispatch([
      [EnumFilterOperations.SELECTION, [0, 1]],
      [EnumEditOperations.ASSIGN_VALUES_BULK, []],
    ])
    expect(Array.from(rec.dataY)).toEqual(before)
  })

  it('ASSIGN_DATETIMES_BULK moves rows to the new datetimes (delete+add)', async () => {
    const originalLen = rec.dataX.length
    const newDatetime = rec.dataX[rec.dataX.length - 1] + 60_000
    await rec.dispatch([
      [EnumFilterOperations.SELECTION, [3]],
      [EnumEditOperations.ASSIGN_DATETIMES_BULK, [newDatetime]],
    ])
    expect(rec.dataX.length).toBe(originalLen)
    // Row count unchanged; the moved row should now sit at the end.
    expect(rec.dataX[rec.dataX.length - 1]).toBe(newDatetime)
  })

  it('ASSIGN_DATETIMES_BULK is a no-op without selection or datetimes', async () => {
    const before = Array.from(rec.dataX)
    await rec.dispatch(EnumEditOperations.ASSIGN_DATETIMES_BULK, [1])
    expect(Array.from(rec.dataX)).toEqual(before)
    await rec.dispatch([
      [EnumFilterOperations.SELECTION, [0, 1]],
      [EnumEditOperations.ASSIGN_DATETIMES_BULK, []],
    ])
    expect(Array.from(rec.dataX)).toEqual(before)
  })
})

describe('ObservationRecord — undo / redo', () => {
  let rec: ObservationRecord
  beforeEach(async () => {
    forceWorker = false
    rec = new ObservationRecord(uniform(15, 0, 10))
    await rec.reload()
  })

  it('undo() on empty history returns []', async () => {
    expect(await rec.undo()).toEqual([])
  })

  it('redo() on empty stack returns []', async () => {
    expect(await rec.redo()).toEqual([])
  })

  it('undo then redo round-trips an edit', async () => {
    const originalLen = rec.dataX.length
    await rec.dispatch(EnumEditOperations.DELETE_POINTS, [0, 1])
    expect(rec.dataX.length).toBe(originalLen - 2)

    await rec.undo()
    expect(rec.dataX.length).toBe(originalLen)
    expect(rec.history.length).toBe(0)

    await rec.redo()
    expect(rec.dataX.length).toBe(originalLen - 2)
    expect(rec.history.length).toBe(1)
  })

  it('a fresh dispatch clears the redo stack (Word-style)', async () => {
    await rec.dispatch(EnumEditOperations.DELETE_POINTS, [0])
    await rec.undo()
    // Redo stack has one entry.
    await rec.dispatch(EnumEditOperations.DELETE_POINTS, [1])
    // The new dispatch should have wiped the redo stack.
    expect(await rec.redo()).toEqual([])
  })
})

describe('ObservationRecord — miscellaneous filters', () => {
  let rec: ObservationRecord
  beforeEach(async () => {
    forceWorker = false
    rec = new ObservationRecord(uniform(10, 0, 10))
    await rec.reload()
  })

  it('DATETIME_RANGE selects all indexes inside [from, to]', async () => {
    const from = rec.dataX[3]
    const to = rec.dataX[6]
    const selection = await rec.dispatch(
      EnumFilterOperations.DATETIME_RANGE,
      from,
      to
    )
    expect(selection).toEqual([3, 4, 5, 6])
  })

  it('DATETIME_RANGE with both bounds omitted selects the full series', async () => {
    const selection = await rec.dispatch(EnumFilterOperations.DATETIME_RANGE)
    expect(selection.length).toBe(rec.dataX.length)
  })

  it('DATETIME_RANGE returns [] on empty datasets', async () => {
    const empty = new ObservationRecord({ datetimes: [], dataValues: [] })
    await empty.reload()
    expect(
      await empty.dispatch(EnumFilterOperations.DATETIME_RANGE, 0, 100)
    ).toEqual([])
  })

  it('DATETIME_RANGE returns [] when from > to on the grid', async () => {
    const from = rec.dataX[7]
    const to = rec.dataX[2]
    expect(
      await rec.dispatch(EnumFilterOperations.DATETIME_RANGE, from, to)
    ).toEqual([])
  })
})
