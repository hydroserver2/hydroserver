# @uwrl/qc-utils

Worker-parallelized quality-control primitives for hydrological time-series.
Powers the QC pipeline in
[hydroserver-qc-app](https://github.com/hydroserver2/hydroserver-qc-app),
but the runtime has no Vue / app dependencies — anywhere you can run a
modern browser bundle is fair game.

The package wraps a paired `Float64Array` (timestamps, ms epoch) and
`Float32Array` (values) in an `ObservationRecord` and exposes a single
history-driven dispatch surface. Every edit and filter is logged as a
`HistoryItem` you can replay, undo / redo, calibrate against the host
machine, and serialize to disk as a JSON "QC history".

## Install

```sh
npm install @uwrl/qc-utils
```

## Quick start

```ts
import {
  ObservationRecord,
  EnumFilterOperations,
  EnumEditOperations,
  Operator,
} from '@uwrl/qc-utils'

// Build a record from parallel datetime + value arrays.
const record = new ObservationRecord({
  datetimes: [1704067200000, 1704067260000, 1704067320000, 1704067380000],
  dataValues: [10.0, 11.5, 999.9, 12.3],
})
await record.reload()

// Find the spike, replace it with the previous value.
await record.dispatch([
  [EnumFilterOperations.VALUE_THRESHOLD, { 'Greater than': 100 }],
  [EnumEditOperations.CHANGE_VALUES, Operator.ASSIGN, 11.5],
])

record.dataY[2] // 11.5
record.history.length // 2
await record.undo()  // replays without CHANGE_VALUES
record.dataY[2] // 999.9
```

The dispatch chain is the canonical pattern: a filter (or explicit
`SELECTION`) seeds an index list, the next selection-consuming edit
reads it off `history[length - 2].selected`. See
[`docs/QC_HISTORY.md`](./docs/QC_HISTORY.md) for the full
operation-by-operation contract and the JSON wire format.

## Concepts

### `ObservationRecord`

The single state container. Holds:

- `dataX` / `dataY` — typed-array views into a (possibly shared) buffer.
- `history` — every committed `HistoryItem` since the last `reload()`.
- `redoStack` — items popped by `undo()`, ready for `redo()`.

Mutations only happen through `dispatch` / `dispatchAction` /
`dispatchFilter` / `undo` / `redo` / `reload` / `reloadHistory` /
`removeHistoryItem`. The handlers themselves are private — operations
are driven by enum + args so the same call shape works at runtime, on
replay from a saved QC history, and in unit tests.

### Edit operations (`EnumEditOperations`)

| Op                      | Purpose                                                  |
|-------------------------|----------------------------------------------------------|
| `ADD_POINTS`            | Insert (datetime, value) tuples; reindex + sort by date. |
| `CHANGE_VALUES`         | Apply `Operator` (ADD / SUB / MULT / DIV / ASSIGN) at the prior selection's indices. |
| `ASSIGN_VALUES_BULK`    | Write parallel `values[i] → dataY[selection[i]]`. Table-driven edits. |
| `ASSIGN_DATETIMES_BULK` | Write parallel datetimes; runs as one combined delete + add. |
| `DELETE_POINTS`         | Drop the selection from x / y in a single skip-on-delete pass. |
| `INTERPOLATE`           | Linear interpolation across each consecutive group in the selection. |
| `SHIFT_DATETIMES`       | Offset the selection's timestamps by `(amount, TimeUnit)`. |
| `DRIFT_CORRECTION`      | Apply linear drift `value` to every consecutive group in the selection. |
| `FILL_GAPS`             | Detect gaps over `gapThreshold`; insert points at `fillCadence` (interpolated or constant `fillValue`). |

### Filter operations (`EnumFilterOperations`)

All scan-style filters accept an optional trailing `[startTs, endTs]`
window in epoch ms; `DATETIME_RANGE`'s args ARE the window.

| Op                | Args                                                       |
|-------------------|------------------------------------------------------------|
| `VALUE_THRESHOLD` | `[{ 'Greater than': n, 'Less than': n, ... }, range?]`     |
| `DATETIME_RANGE`  | `[fromTs?, toTs?]`                                         |
| `CHANGE`          | `[comparator, value, range?]` — Δ between adjacent points  |
| `RATE_OF_CHANGE`  | `[comparator, value, range?]` — value is a fraction (0.5 = 50%) |
| `FIND_GAPS`       | `[amount, unit, range?]`                                   |
| `PERSISTENCE`     | `[times, range?]` — runs of identical repeated values      |
| `SELECTION`       | `[indices[]]` — explicit user selection                    |

### Worker dispatch + calibration

Every long-running kernel ships in two flavours: an inline core
(`changeValuesCore`, `fillGapsCore`, …) and a worker pool that scans
shared `Float64Array` / `Float32Array` views in parallel.
[`shouldUseWorker`](./src/utils/plotting/calibration.ts) picks per
call:

```ts
import { ensureCalibration, shouldUseWorker, EnumEditOperations } from '@uwrl/qc-utils'

await ensureCalibration() // benchmark once per device, cached in localStorage

shouldUseWorker(EnumEditOperations.FILL_GAPS, {
  datasetSize: record.dataX.length,
  selectionSize: 0,
})
// → { useWorker: false, predictedInlineMs: 12.4, predictedWorkerMs: 53.0,
//     reason: 'inline faster (12.4 vs 53.0 ms)' }
```

Workers require `SharedArrayBuffer`, which means the host page must
serve `Cross-Origin-Opener-Policy: same-origin` +
`Cross-Origin-Embedder-Policy: require-corp`. When SAB is unavailable
the dispatch transparently falls back to inline kernels. See
[`docs/CALIBRATION.md`](./docs/CALIBRATION.md) for the benchmark
methodology and the per-op cost table.

### QC History (save / load)

Every `ObservationRecord` history is round-trippable as JSON. The
on-disk shape IS the wire format used by the HydroServer API:

```ts
import { serializeHistory, parseHistory, applyHistory } from '@uwrl/qc-utils'

const history = serializeHistory(record, {
  startDate: '2024-01-01T00:00:00.000Z',
  endDate:   '2024-06-30T23:59:59.999Z',
})
// → { version: '1', createdAt, window, operations: [{ method, args }, ...] }

// On a fresh ObservationRecord with the same window's data loaded:
const fresh = new ObservationRecord(rawObservations)
await fresh.reload()
const report = await applyHistory(fresh, parseHistory(history))
report.applied // 12
report.failed  // [{ index, method, error }]  — per-op failures don't abort replay
```

QC histories are reusable across datastreams: they don't pin a datastream id,
they store the wall-clock window and the `[method, ...args]` tuples.
See [`docs/QC_HISTORY.md`](./docs/QC_HISTORY.md) for versioning,
loader workflow, and per-op arg shape.

## Public API surface

```ts
// State container
import { ObservationRecord, INCREASE_AMOUNT } from '@uwrl/qc-utils'

// Operation enums
import {
  EnumEditOperations,
  EnumFilterOperations,
  Operator,
  FilterOperation,
  TimeUnit,
  timeUnitMultipliers,
} from '@uwrl/qc-utils'

// QC history (save / load)
import {
  serializeHistory,
  parseHistory,
  applyHistory,
  QcHistory,
  QcHistoryOperation,
  QcHistoryWindow,
  QC_HISTORY_VERSION,
  ApplyHistoryReport,
} from '@uwrl/qc-utils'

// Calibration
import {
  shouldUseWorker,
  ensureCalibration,
  runBenchmarks,
  getCalibration,
  onCalibrationChange,
  clearCalibration,
  DeviceProfile,
  DispatchSignals,
  DispatchDecision,
} from '@uwrl/qc-utils'

// Helpers
import {
  findFirstGreaterOrEqual,
  findLastLessOrEqual,
  formatDate,
  formatDuration,
  measureEllapsedTime,
} from '@uwrl/qc-utils'
```

A `Snackbar` notification helper is also exported for browser
consumers. It's the package's only DOM-touching symbol — the QC
engine itself is headless.

```ts
import { Snackbar } from '@uwrl/qc-utils'
Snackbar.success('Saved')
```

For HydroServer REST calls, use `@hydroserver/client` directly. An
earlier `services/` REST client lived in this package and was
removed in `0.1.0` when the qc-app finished its migration to the
dedicated client.

## Browser requirements

- ES2022 / native `import`. Built as ESM with a CJS shim
  (`dist/index.js` + `dist/index.cjs`).
- `SharedArrayBuffer` for the worker fast path (graceful inline fallback
  when unavailable; see Calibration above).
- `Float64Array` / `Float32Array` typed-array `resize()` /
  `SharedArrayBuffer.grow()` — Chrome 111+, Firefox 119+, Safari 16.4+.

## Contributing

Clone the HydroServer repo, run `npm install` from the root, then `cd`
into `packages/qc-utils` before running package scripts. When working
inside this package, `npm run dev` rebuilds `dist/` on every source
change. The watch build skips `.d.ts` emit; run `npm run build` when you
need to verify published package artifacts. CI runs
`tsc --noEmit → coverage → lint → build` on every push and PR to main.

| Script              | Purpose                                                |
|---------------------|--------------------------------------------------------|
| `npm run dev`       | Watch-mode bundler for local package development.      |
| `npm run build`     | Production build — bundle + emit `.d.ts` declarations. |
| `npm run test`      | Vitest suite.                                          |
| `npm run coverage`  | Vitest with v8 coverage and the 80 % threshold.        |
| `npm run lint`      | ESLint over `src/`.                                    |

Using local changes in the QC app:

From `apps/qc-app`:

```sh
npm run dev
```

The QC app dev server aliases `@uwrl/qc-utils` directly to
`packages/qc-utils/src`, so local source edits do not require a
`qc-utils` build.

## License

[BSD 3-Clause](./LICENSE).
