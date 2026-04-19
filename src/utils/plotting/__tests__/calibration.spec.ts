/**
 * Unit tests for the public surface of `calibration.ts`.
 *
 * The module imports `value-threshold.worker?worker&inline` eagerly, which
 * Vite transforms in the app build but not in Vitest + happy-dom — so we
 * substitute the same `MockValueThresholdWorker` used by
 * `observation-record.spec.ts` to give `runBenchmarks()` a working worker
 * constructor. The mock round-trips via `queueMicrotask`, which is enough
 * for `ensureCalibration()` to complete synchronously-ish in tests.
 *
 * Module state (`activeProfile`, `lastBenchmarkDetail`, `listeners`,
 * `localStorage`) lives at import scope, so every test begins with a
 * `clearCalibration()` and a `localStorage.clear()` to avoid cross-
 * pollination.
 */

import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

vi.mock('../value-threshold.worker?worker&inline', () =>
  import('./workerMocks').then((m) => ({ default: m.MockValueThresholdWorker }))
)

import {
  clearCalibration,
  ensureCalibration,
  getCalibration,
  getLastBenchmarkDetail,
  getOperationTable,
  onCalibrationChange,
  runBenchmarks,
  shouldUseWorker,
} from '../calibration'
import { EnumEditOperations, EnumFilterOperations } from '@/types'

// Matches the `DEFAULT_PROFILE` shape; used when asserting fallbacks.
const DEFAULT_SPAWN_MS = 50

describe('calibration', () => {
  beforeEach(() => {
    try {
      localStorage.clear()
    } catch {
      /* ignore */
    }
    clearCalibration()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('shouldUseWorker', () => {
    it('returns useWorker=false for always-inline ops', () => {
      for (const op of [
        EnumFilterOperations.DATETIME_RANGE,
        EnumFilterOperations.SELECTION,
        EnumEditOperations.ASSIGN_VALUES_BULK,
        EnumEditOperations.ASSIGN_DATETIMES_BULK,
      ]) {
        const d = shouldUseWorker(op, { datasetSize: 10_000_000 })
        expect(d.useWorker).toBe(false)
        expect(d.predictedInlineMs).toBe(0)
        expect(d.predictedWorkerMs).toBe(0)
      }
    })

    it('returns useWorker=true with a rationale for unknown ops', () => {
      const d = shouldUseWorker('NOPE' as any, { datasetSize: 100 })
      expect(d.useWorker).toBe(true)
      expect(d.predictedInlineMs).toBe(Infinity)
      expect(d.reason).toMatch(/unknown op/i)
    })

    it('forces inline when SharedArrayBuffer is unavailable', () => {
      vi.stubGlobal('SharedArrayBuffer', undefined)
      const d = shouldUseWorker(EnumFilterOperations.VALUE_THRESHOLD, {
        datasetSize: 10_000_000,
      })
      expect(d.useWorker).toBe(false)
      expect(d.predictedWorkerMs).toBe(Infinity)
      expect(d.reason).toMatch(/SharedArrayBuffer unavailable/)
    })

    it('picks inline for zero work units', () => {
      const d = shouldUseWorker(EnumEditOperations.CHANGE_VALUES, {
        datasetSize: 1_000_000,
        selectionSize: 0,
      })
      expect(d.useWorker).toBe(false)
      expect(d.reason).toBe('zero work units')
      // The decision still reports the spawn cost it would have paid.
      expect(d.predictedWorkerMs).toBe(DEFAULT_SPAWN_MS)
    })

    it('picks inline for small datasets and worker for large ones', () => {
      // Defaults: spawnOverheadMs=50, inlineThroughput=50k/ms, workerThroughput=80k/ms.
      // For VALUE_THRESHOLD (weight 1, parallelism=hwConcurrency=4), the crossover is
      // where `N/50k === 50 + N/(80k*4)` → N ≈ ~2.67M. 500 and 10M bracket that.
      const small = shouldUseWorker(EnumFilterOperations.VALUE_THRESHOLD, {
        datasetSize: 500,
      })
      expect(small.useWorker).toBe(false)
      expect(small.reason).toMatch(/inline faster/)

      const huge = shouldUseWorker(EnumFilterOperations.VALUE_THRESHOLD, {
        datasetSize: 10_000_000,
      })
      expect(huge.useWorker).toBe(true)
      expect(huge.reason).toMatch(/worker faster/)
    })

    it('parallelism is clamped to [1, hwConcurrency]', () => {
      // Asking for 9999 parallelism should not outperform hwConcurrency=4.
      const capped = shouldUseWorker(EnumFilterOperations.VALUE_THRESHOLD, {
        datasetSize: 10_000_000,
        parallelism: 9999,
      })
      const natural = shouldUseWorker(EnumFilterOperations.VALUE_THRESHOLD, {
        datasetSize: 10_000_000,
      })
      expect(capped.predictedWorkerMs).toBeCloseTo(natural.predictedWorkerMs, 5)

      // Asking for 0 should be treated as 1 worker — which makes worker path
      // slower than the uncapped default, so the ratio should move.
      const single = shouldUseWorker(EnumFilterOperations.VALUE_THRESHOLD, {
        datasetSize: 10_000_000,
        parallelism: 0,
      })
      expect(single.predictedWorkerMs).toBeGreaterThan(natural.predictedWorkerMs)
    })
  })

  describe('getOperationTable', () => {
    it('includes every edit and filter enum value', () => {
      const rows = getOperationTable()
      const ops = new Set(rows.map((r) => r.op))
      for (const op of Object.values(EnumEditOperations)) expect(ops.has(op)).toBe(true)
      for (const op of Object.values(EnumFilterOperations)) expect(ops.has(op)).toBe(true)
    })

    it('each entry carries a mode, weight, and rationale', () => {
      for (const row of getOperationTable()) {
        expect(['always-inline', 'always-worker', 'calibrated']).toContain(row.mode)
        expect(typeof row.weight).toBe('number')
        expect(typeof row.rationale).toBe('string')
        expect(row.rationale.length).toBeGreaterThan(0)
      }
    })
  })

  describe('profile state', () => {
    it('starts with a default profile and no benchmark detail', () => {
      const p = getCalibration()
      expect(p.measuredAt).toBe(0)
      expect(p.userAgent).toBe('default')
      expect(getLastBenchmarkDetail()).toBeNull()
    })

    it('clearCalibration resets profile + storage', () => {
      localStorage.setItem('qc-utils:calibration:v1', JSON.stringify({ foo: 'bar' }))
      clearCalibration()
      expect(localStorage.getItem('qc-utils:calibration:v1')).toBeNull()
      expect(getCalibration().measuredAt).toBe(0)
    })
  })

  describe('onCalibrationChange', () => {
    it('notifies subscribers after a benchmark runs', async () => {
      const listener = vi.fn()
      const unsubscribe = onCalibrationChange(listener)
      await ensureCalibration({ force: true })
      expect(listener).toHaveBeenCalledTimes(1)
      expect(listener.mock.calls[0][0].measuredAt).toBeGreaterThan(0)
      unsubscribe()
    })

    it('unsubscribed listeners stop receiving updates', async () => {
      const listener = vi.fn()
      const unsubscribe = onCalibrationChange(listener)
      unsubscribe()
      await ensureCalibration({ force: true })
      expect(listener).not.toHaveBeenCalled()
    })
  })

  describe('ensureCalibration', () => {
    it('triggers a benchmark on first run and populates getLastBenchmarkDetail', async () => {
      expect(getLastBenchmarkDetail()).toBeNull()
      const profile = await ensureCalibration()
      expect(profile.measuredAt).toBeGreaterThan(0)
      const detail = getLastBenchmarkDetail()
      expect(detail).not.toBeNull()
      expect(detail!.samples.inlineScanMs.length).toBe(3)
    })

    it('is a no-op when a fresh profile already exists', async () => {
      // Seed a "just measured" profile directly into storage so the module
      // picks it up as non-stale — but since the module only loads storage
      // at import time, we force one benchmark first and then assert a
      // second call doesn't re-measure.
      await ensureCalibration({ force: true })
      const firstMeasuredAt = getCalibration().measuredAt
      await new Promise((r) => setTimeout(r, 5))
      await ensureCalibration()
      expect(getCalibration().measuredAt).toBe(firstMeasuredAt)
    })

    it('force=true re-measures even when a fresh profile exists', async () => {
      await ensureCalibration({ force: true })
      const first = getCalibration().measuredAt
      await new Promise((r) => setTimeout(r, 5))
      await ensureCalibration({ force: true })
      expect(getCalibration().measuredAt).toBeGreaterThan(first)
    })
  })

  describe('runBenchmarks', () => {
    it('returns the conservative default profile when SAB is unavailable', async () => {
      vi.stubGlobal('SharedArrayBuffer', undefined)
      const detail = await runBenchmarks()
      expect(detail.sharedArrayBufferAvailable).toBe(false)
      expect(detail.samples.inlineScanMs).toEqual([])
      expect(detail.samples.workerScanMs).toEqual([])
      expect(detail.spawnOverheadMs).toBe(DEFAULT_SPAWN_MS)
    })

    it('collects three samples per primitive when SAB is available', async () => {
      const detail = await runBenchmarks()
      expect(detail.sharedArrayBufferAvailable).toBe(true)
      expect(detail.samples.spawnRoundtripMs.length).toBe(3)
      expect(detail.samples.inlineScanMs.length).toBe(3)
      expect(detail.samples.workerScanMs.length).toBe(3)
      expect(detail.inlineThroughput).toBeGreaterThan(0)
      expect(detail.workerThroughput).toBeGreaterThan(0)
    })
  })
})
