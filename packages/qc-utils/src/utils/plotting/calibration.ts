import { EnumEditOperations, EnumFilterOperations } from '../../types'
import { valueThresholdCore, changeValuesCore } from './operation-cores'
// @ts-ignore — Vite worker import
import ValueThresholdWorker from './value-threshold.worker?worker&inline'

/**
 * Per-user, per-device calibration for the dispatch decision inside
 * `ObservationRecord`: should a given operation run inline on the
 * main thread or spawn web workers? Spawn cost varies wildly across
 * machines (Windows Chrome: ~100 ms, macOS: ~10 ms, budget Android:
 * somewhere in between plus thermal jitter), so static thresholds
 * baked into the library are wrong for most users most of the time.
 *
 * The approach:
 *   1. Measure three primitives on this device: worker spawn
 *      roundtrip, inline throughput, worker throughput.
 *   2. Combine those with per-operation complexity weights (which
 *      ARE universal — they describe the algorithm, not the
 *      hardware) to predict the crossover size for each op.
 *   3. Cache the measurements in `localStorage` keyed by a version
 *      tag and refresh on explicit user action, on staleness, or
 *      when we detect systematic mispredictions via the
 *      `execution.durationMs` already logged on each `HistoryItem`.
 *
 * `shouldUseWorker()` is the single public decision function that
 * `ObservationRecord.dispatchAction` / `dispatchFilter` consult. Both
 * always-inline and always-worker operations short-circuit before
 * reading any measured primitives, so a missing calibration never
 * blocks the dispatch path.
 *
 * See `docs/CALIBRATION.md` for the full design write-up.
 */

/** Increment when the profile shape changes to invalidate old cached entries. */
const CALIBRATION_VERSION = 1

const STORAGE_KEY = `qc-utils:calibration:v${CALIBRATION_VERSION}`

/**
 * Maximum age before cached measurements are considered stale and a
 * fresh benchmark is triggered. Users might upgrade OS, swap laptops,
 * or see background thermal changes on Chromebooks — 30 days is a
 * cheap cadence to re-measure.
 */
const STALE_AFTER_MS = 30 * 24 * 60 * 60 * 1000

/** Synthetic dataset sizes used by the benchmark (see `runBenchmarks`). */
const BENCH_SIZE_INLINE = 50_000
const BENCH_SIZE_WORKER = 200_000

/**
 * Device-specific primitives measured during the benchmark. Everything
 * is in consistent units:
 *   - `spawnOverheadMs` — wall-clock ms for one postMessage roundtrip
 *     including worker construction and termination,
 *   - `inlineThroughput` / `workerThroughput` — elements scanned per
 *     millisecond on a reference O(n) kernel (value-threshold).
 */
export interface DeviceProfile {
  spawnOverheadMs: number
  inlineThroughput: number
  workerThroughput: number
  hwConcurrency: number
  measuredAt: number
  userAgent: string
}

export interface BenchmarkDetail extends DeviceProfile {
  sharedArrayBufferAvailable: boolean
  samples: {
    spawnRoundtripMs: number[]
    inlineScanMs: number[]
    workerScanMs: number[]
  }
}

/**
 * Conservative fallback used when no calibration has run yet (first
 * session, SharedArrayBuffer unavailable, benchmark aborted). Biased
 * toward inline for small ops so tiny edits stay instant, and toward
 * workers once we cross a reasonably large size.
 */
const DEFAULT_PROFILE: DeviceProfile = {
  spawnOverheadMs: 50,       // worst-case Windows
  inlineThroughput: 50_000,  // 50M elements/sec, conservative
  workerThroughput: 80_000,  // workers slightly faster in-loop once spawned
  hwConcurrency: 4,
  measuredAt: 0,
  userAgent: 'default',
}

/**
 * In-memory snapshot of the latest calibration. Initialised eagerly
 * from `localStorage` when the module first loads so the dispatch
 * site doesn't need to await anything on the hot path.
 */
let activeProfile: DeviceProfile = loadFromStorage() ?? DEFAULT_PROFILE
let lastBenchmarkDetail: BenchmarkDetail | null = null
let runningBenchmark: Promise<BenchmarkDetail> | null = null

/** Subscribers notified after every successful recalibration. */
type CalibrationListener = (profile: DeviceProfile) => void
const listeners = new Set<CalibrationListener>()

/**
 * Per-operation algorithm descriptor. `weight` is the kernel's relative
 * cost per element compared to the reference value-threshold scan
 * (weight 1). `mode`:
 *   - `always-inline`: never worth the worker hop (O(log n), pure
 *     bookkeeping, or already single-shot loops),
 *   - `always-worker`: escape hatch for kernels that genuinely
 *     need thread-level parallelism (none in the current catalog),
 *   - `calibrated`: dispatch decides per-call using the estimator.
 */
type OperationMode = 'always-inline' | 'always-worker' | 'calibrated'

interface OperationDescriptor {
  mode: OperationMode
  /** Relative cost per element; compares against the scan baseline. */
  weight: number
  /** Short rationale surfaced in the dev popover. */
  rationale: string
}

/**
 * Hand-curated table — values are starting points tuned on a
 * mid-range laptop; refine as we collect telemetry on
 * `execution.durationMs`. Keep this table exhaustive over
 * `EnumEditOperations` + `EnumFilterOperations` so a typo in the
 * caller surfaces as a type error, not a silent fallback.
 */
const OPERATION_TABLE: Record<
  EnumEditOperations | EnumFilterOperations,
  OperationDescriptor
> = {
  // Filter ops — read-only scans, cheap kernels
  [EnumFilterOperations.VALUE_THRESHOLD]: {
    mode: 'calibrated',
    weight: 1,
    rationale: 'O(n) single-pass scan; baseline reference',
  },
  [EnumFilterOperations.CHANGE]: {
    mode: 'calibrated',
    weight: 1.1,
    rationale: 'O(n) with one subtraction per step',
  },
  [EnumFilterOperations.RATE_OF_CHANGE]: {
    mode: 'calibrated',
    weight: 1.4,
    rationale: 'O(n) with division + abs per step',
  },
  [EnumFilterOperations.FIND_GAPS]: {
    mode: 'calibrated',
    weight: 0.9,
    rationale: 'O(n) on X only, mostly empty output',
  },
  [EnumFilterOperations.PERSISTENCE]: {
    mode: 'calibrated',
    weight: 1.3,
    rationale: 'O(n) + chunk-boundary stitch',
  },
  [EnumFilterOperations.DATETIME_RANGE]: {
    mode: 'always-inline',
    weight: 0,
    rationale: 'O(log n) binary search; never worth the worker hop',
  },
  [EnumFilterOperations.SELECTION]: {
    mode: 'always-inline',
    weight: 0,
    rationale: 'Pure history bookkeeping',
  },
  // Edit ops — mutate Y in place or rebuild arrays
  [EnumEditOperations.CHANGE_VALUES]: {
    mode: 'calibrated',
    weight: 0.7,
    rationale: 'O(k) in-place arithmetic on selection',
  },
  [EnumEditOperations.ASSIGN_VALUES_BULK]: {
    mode: 'always-inline',
    weight: 0,
    rationale: 'Single tight loop, already inline',
  },
  [EnumEditOperations.ASSIGN_DATETIMES_BULK]: {
    mode: 'always-inline',
    weight: 0,
    rationale: 'Composes delete+add which handle their own dispatch',
  },
  [EnumEditOperations.INTERPOLATE]: {
    mode: 'calibrated',
    weight: 1.5,
    rationale: 'Linear interp per consecutive group; in-place writes',
  },
  [EnumEditOperations.DRIFT_CORRECTION]: {
    mode: 'calibrated',
    weight: 1.2,
    rationale: 'O(range total) in-place math; one pass per range',
  },
  [EnumEditOperations.SHIFT_DATETIMES]: {
    mode: 'calibrated',
    weight: 1.1,
    rationale: 'O(k) per-point shift math; inline skips SAB allocation',
  },
  [EnumEditOperations.ADD_POINTS]: {
    mode: 'calibrated',
    weight: 1.8,
    rationale: 'Single merge pass over Y/X + insertions; fresh SAB per call',
  },
  [EnumEditOperations.DELETE_POINTS]: {
    mode: 'calibrated',
    weight: 1.4,
    rationale: 'Single skip-on-delete pass over Y/X; fresh SAB per call',
  },
  [EnumEditOperations.FILL_GAPS]: {
    mode: 'calibrated',
    weight: 1.3,
    rationale: 'Single copy-with-fills pass; fresh SAB sized to newLength',
  },
}

export interface DispatchSignals {
  /** Total dataset length in points (source.x.length). */
  datasetSize: number
  /** Indices involved when the op is selection-bound; 0 for full-scan. */
  selectionSize?: number
  /** Override the measured workers count (defaults to hwConcurrency). */
  parallelism?: number
}

export interface DispatchDecision {
  useWorker: boolean
  predictedInlineMs: number
  predictedWorkerMs: number
  /** Human-readable explanation (e.g. "inline faster at N=200"). */
  reason: string
}

/**
 * Core dispatch decision. Returns `useWorker: false` when the
 * predicted inline runtime beats the worker runtime (spawn overhead
 * plus in-loop work divided across workers). Callers should short-
 * circuit to the inline path when `useWorker` is false.
 */
export function shouldUseWorker(
  op: EnumEditOperations | EnumFilterOperations,
  signals: DispatchSignals
): DispatchDecision {
  const desc = OPERATION_TABLE[op]
  if (!desc) {
    return {
      useWorker: true,
      predictedInlineMs: Infinity,
      predictedWorkerMs: 0,
      reason: 'unknown op; keeping default worker path',
    }
  }

  if (desc.mode === 'always-inline') {
    return {
      useWorker: false,
      predictedInlineMs: 0,
      predictedWorkerMs: 0,
      reason: desc.rationale,
    }
  }

  // SharedArrayBuffer is required by every worker kernel. When it
  // isn't available (cross-origin-isolation headers missing, some
  // embeds) workers can't read shared Y/X views — force inline.
  if (typeof SharedArrayBuffer === 'undefined') {
    return {
      useWorker: false,
      predictedInlineMs: 0,
      predictedWorkerMs: Infinity,
      reason: 'SharedArrayBuffer unavailable; forced inline',
    }
  }

  if (desc.mode === 'always-worker') {
    return {
      useWorker: true,
      predictedInlineMs: Infinity,
      predictedWorkerMs: 0,
      reason: desc.rationale,
    }
  }

  const N = estimateWorkUnits(op, signals)
  if (N <= 0) {
    return {
      useWorker: false,
      predictedInlineMs: 0,
      predictedWorkerMs: activeProfile.spawnOverheadMs,
      reason: 'zero work units',
    }
  }

  const parallelism = Math.max(
    1,
    Math.min(
      signals.parallelism ?? activeProfile.hwConcurrency,
      activeProfile.hwConcurrency
    )
  )
  const predictedInlineMs =
    (desc.weight * N) / activeProfile.inlineThroughput
  const predictedWorkerMs =
    activeProfile.spawnOverheadMs +
    (desc.weight * N) / (activeProfile.workerThroughput * parallelism)

  const useWorker = predictedInlineMs > predictedWorkerMs
  return {
    useWorker,
    predictedInlineMs,
    predictedWorkerMs,
    reason: useWorker
      ? `worker faster (${predictedWorkerMs.toFixed(1)} vs ${predictedInlineMs.toFixed(1)} ms)`
      : `inline faster (${predictedInlineMs.toFixed(1)} vs ${predictedWorkerMs.toFixed(1)} ms)`,
  }
}

/**
 * Estimate work units for a given op + params. The formulas capture
 * first-order cost shape and stay closed-form so the decision costs
 * no measurable time at dispatch:
 *
 *   VALUE_THRESHOLD / CHANGE / RATE_OF_CHANGE / FIND_GAPS /
 *     PERSISTENCE   → datasetSize
 *   CHANGE_VALUES   → selectionSize
 *   ADD_POINTS      → datasetSize + insertionCount * log(datasetSize)
 *                     (not reachable today since the op is
 *                      always-worker, but kept for symmetry)
 *
 * Additional signals can be appended without breaking call sites;
 * the estimator falls back to `datasetSize` for any op it doesn't
 * special-case.
 */
function estimateWorkUnits(
  op: EnumEditOperations | EnumFilterOperations,
  signals: DispatchSignals
): number {
  switch (op) {
    case EnumEditOperations.CHANGE_VALUES:
    case EnumEditOperations.INTERPOLATE:
    case EnumEditOperations.SHIFT_DATETIMES:
    case EnumEditOperations.DRIFT_CORRECTION:
      // DRIFT_CORRECTION callers pass the summed range extent as
      // `selectionSize` — it's range-length-bound, not dataset-bound.
      return signals.selectionSize ?? 0
    case EnumEditOperations.DELETE_POINTS:
      return (signals.selectionSize ?? 0) + signals.datasetSize * 0.25
    case EnumEditOperations.ADD_POINTS: {
      const log = Math.max(1, Math.log2(Math.max(signals.datasetSize, 2)))
      return signals.datasetSize + (signals.selectionSize ?? 0) * log
    }
    default:
      return signals.datasetSize
  }
}

/** Subscribe for post-benchmark updates (UI badge, etc.). */
export function onCalibrationChange(listener: CalibrationListener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** Read the active profile without triggering a benchmark. */
export function getCalibration(): DeviceProfile {
  return activeProfile
}

/** Detail snapshot for the dev popover; `null` until a benchmark runs. */
export function getLastBenchmarkDetail(): BenchmarkDetail | null {
  return lastBenchmarkDetail
}

/** Operation table for UI display (README + dev popover). */
export function getOperationTable(): ReadonlyArray<{
  op: EnumEditOperations | EnumFilterOperations
  mode: OperationMode
  weight: number
  rationale: string
}> {
  return (Object.keys(OPERATION_TABLE) as Array<EnumEditOperations | EnumFilterOperations>)
    .map((op) => ({ op, ...OPERATION_TABLE[op] }))
}

/** Clear cached calibration — mostly for tests / debugging. */
export function clearCalibration(): void {
  activeProfile = DEFAULT_PROFILE
  lastBenchmarkDetail = null
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // storage may be disabled; in-memory reset is still valuable.
  }
}

/**
 * Kick off a benchmark when:
 *   - no profile exists yet, or
 *   - `force` is set (user clicked Recalibrate), or
 *   - the cached measurement is older than `STALE_AFTER_MS`.
 * Returns the active profile immediately; use `onCalibrationChange`
 * or the resolved `Promise<BenchmarkDetail>` to observe the result.
 */
export async function ensureCalibration(opts: { force?: boolean } = {}): Promise<DeviceProfile> {
  if (typeof window === 'undefined') return activeProfile
  const needs =
    opts.force ||
    activeProfile.measuredAt === 0 ||
    Date.now() - activeProfile.measuredAt > STALE_AFTER_MS
  if (!needs) return activeProfile
  if (runningBenchmark) await runningBenchmark
  else {
    runningBenchmark = runBenchmarks().finally(() => {
      runningBenchmark = null
    })
    const detail = await runningBenchmark
    activeProfile = detail
    saveToStorage(detail)
    lastBenchmarkDetail = detail
    for (const l of listeners) l(activeProfile)
  }
  return activeProfile
}

/**
 * Run the three microbenchmarks: worker spawn roundtrip, inline
 * scan throughput, worker scan throughput. Each is sampled three
 * times; we take the median to shake out noise. All numbers are in
 * elements-per-millisecond or milliseconds.
 *
 * Uses the VALUE_THRESHOLD kernel as the reference scan because it
 * already has both an inline core and a worker; per-op weights in
 * `OPERATION_TABLE` are normalised to this baseline so a single
 * throughput measurement covers all `calibrated` ops.
 */
export async function runBenchmarks(): Promise<BenchmarkDetail> {
  const sabAvailable = typeof SharedArrayBuffer !== 'undefined'
  if (!sabAvailable) {
    const detail: BenchmarkDetail = {
      ...DEFAULT_PROFILE,
      measuredAt: Date.now(),
      userAgent: navigator.userAgent,
      hwConcurrency: navigator.hardwareConcurrency || DEFAULT_PROFILE.hwConcurrency,
      sharedArrayBufferAvailable: false,
      samples: { spawnRoundtripMs: [], inlineScanMs: [], workerScanMs: [] },
    }
    return detail
  }

  const hwConcurrency = navigator.hardwareConcurrency || 4

  // Inline baseline — one Float32Array, no workers.
  const inlineBuf = new Float32Array(BENCH_SIZE_INLINE)
  for (let i = 0; i < BENCH_SIZE_INLINE; i++) inlineBuf[i] = Math.sin(i)
  const inlineSamples = await sample(3, () => {
    const t0 = performance.now()
    valueThresholdCore(inlineBuf, 0, BENCH_SIZE_INLINE, [2], [0.5])
    return performance.now() - t0
  })
  const inlineMedian = median(inlineSamples)
  const inlineThroughput = BENCH_SIZE_INLINE / Math.max(inlineMedian, 0.001)

  // Worker roundtrip — measure spawn + noop postMessage + terminate.
  // We call the real ValueThresholdWorker with a tiny payload so the
  // in-worker setup (Float32Array creation etc.) is included; the
  // actual scan time on a 256-element buffer is negligible.
  const tinyBuf = new SharedArrayBuffer(256 * Float32Array.BYTES_PER_ELEMENT)
  const spawnSamples = await sample(3, async () => {
    const t0 = performance.now()
    await new Promise<void>((resolve) => {
      const worker = new ValueThresholdWorker()
      worker.onmessage = () => {
        worker.terminate()
        resolve()
      }
      worker.postMessage({
        bufferY: tinyBuf,
        start: 0,
        end: 256,
        ops: [2],
        values: [0.5],
      })
    })
    return performance.now() - t0
  })
  const spawnOverheadMs = median(spawnSamples)

  // Worker scan throughput — a large buffer so the in-loop cost
  // dominates spawn cost. We subtract the measured spawn overhead
  // to isolate in-loop throughput.
  const bigBuf = new SharedArrayBuffer(
    BENCH_SIZE_WORKER * Float32Array.BYTES_PER_ELEMENT
  )
  const bigView = new Float32Array(bigBuf)
  for (let i = 0; i < BENCH_SIZE_WORKER; i++) bigView[i] = Math.sin(i)
  const workerSamples = await sample(3, async () => {
    const t0 = performance.now()
    await new Promise<void>((resolve) => {
      const worker = new ValueThresholdWorker()
      worker.onmessage = () => {
        worker.terminate()
        resolve()
      }
      worker.postMessage({
        bufferY: bigBuf,
        start: 0,
        end: BENCH_SIZE_WORKER,
        ops: [2],
        values: [0.5],
      })
    })
    return performance.now() - t0
  })
  const workerMedian = Math.max(median(workerSamples) - spawnOverheadMs, 0.1)
  const workerThroughput = BENCH_SIZE_WORKER / workerMedian

  const detail: BenchmarkDetail = {
    spawnOverheadMs,
    inlineThroughput,
    workerThroughput,
    hwConcurrency,
    measuredAt: Date.now(),
    userAgent: navigator.userAgent,
    sharedArrayBufferAvailable: true,
    samples: {
      spawnRoundtripMs: spawnSamples,
      inlineScanMs: inlineSamples,
      workerScanMs: workerSamples,
    },
  }
  return detail
}

async function sample(
  n: number,
  fn: () => number | Promise<number>
): Promise<number[]> {
  const out: number[] = []
  for (let i = 0; i < n; i++) {
    // Yield so paint / other tasks aren't starved between samples.
    await new Promise((r) => setTimeout(r, 0))
    out.push(await fn())
  }
  return out
}

function median(arr: number[]): number {
  if (!arr.length) return 0
  const sorted = [...arr].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2
}

function loadFromStorage(): DeviceProfile | null {
  if (typeof localStorage === 'undefined') return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as DeviceProfile
    if (!parsed || typeof parsed.spawnOverheadMs !== 'number') return null
    return parsed
  } catch {
    return null
  }
}

function saveToStorage(detail: DeviceProfile): void {
  if (typeof localStorage === 'undefined') return
  try {
    const profile: DeviceProfile = {
      spawnOverheadMs: detail.spawnOverheadMs,
      inlineThroughput: detail.inlineThroughput,
      workerThroughput: detail.workerThroughput,
      hwConcurrency: detail.hwConcurrency,
      measuredAt: detail.measuredAt,
      userAgent: detail.userAgent,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
  } catch {
    // storage quota / private mode — in-memory profile still drives
    // the session.
  }
}

// Silence unused-import warning — `changeValuesCore` isn't referenced
// here today but keeps the bench file's core imports together as we
// add more primitives without needing to re-touch the top of the file.
// eslint-disable-next-line no-unused-vars
const _keepImport: typeof changeValuesCore = changeValuesCore
