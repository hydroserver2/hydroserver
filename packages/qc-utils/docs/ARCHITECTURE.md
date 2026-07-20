# Architecture &amp; Software Stack

This document covers the technology choices in `@uwrl/qc-utils`, why they
were made, and how the package is structured internally. For the public
API surface and quick-start, see the [README](../README.md). For the
QC history wire format, see [QC_HISTORY.md](./QC_HISTORY.md).
For worker dispatch, see [CALIBRATION.md](./CALIBRATION.md).

## What this package is

`@uwrl/qc-utils` is a **framework-agnostic, worker-parallelized QC
engine** for hydrological time series. It does not render anything, does
not depend on Vue / React / Angular, and does not require a DOM beyond
what a Web Worker host provides. It powers
[hydroserver-qc-app](https://github.com/hydroserver2/hydroserver-qc-app),
but any browser-shaped JavaScript environment can consume it.

The single state container is `ObservationRecord` — a paired
`Float64Array` (datetimes, ms epoch) + `Float32Array` (values) with a
replayable, undo / redo-able edit history.

## Stack and reasoning

| Layer            | Technology                          | Why this choice                                                                              |
|------------------|-------------------------------------|----------------------------------------------------------------------------------------------|
| Language         | TypeScript 5 (latest, strict)       | Mature type inference + readable build output. Strict mode catches the API drift between this package and `hydroserver-qc-app`. |
| Module format    | ESM with a CJS shim                 | Modern bundlers consume ESM natively; CJS shim keeps Node consumers working until they migrate. |
| Build            | Vite 8 (`build --mode prod`)        | Same tool as the consumer app; first-class worker bundling via `?worker&inline`.             |
| Type emit        | `vue-tsc --declaration --emitDeclarationOnly` | The package uses zero Vue runtime API but the Vue TS compiler tooling is stable; could be swapped for `tsc` with no behavior change. |
| Runtime          | None app-side; web workers per kernel | A pool of small, single-purpose workers parallelizes scans without copying through SAB.    |
| Reactive plumbing| `rxjs`                              | `Subject` for the calibration-changed event. Tiny use of the library — could be swapped for an `EventTarget` polyfill, but rxjs gives a typed surface. |
| Tests            | Vitest + happy-dom + `@vitest/web-worker` | Runs in-process; happy-dom is faster than jsdom for the small surface this package exercises; the web-worker plugin lets us test worker code paths inline. |
| Linting          | `eslint` (`eslint.config.js`, flat config) + `prettier` | Standard. CI gates on it.                                                |
| Coverage tool    | `@vitest/coverage-v8`               | Same v8 provider as the qc-app; coverage is gated at 80% in CI.                              |
| Bundle viz       | `rollup-plugin-visualizer`          | `stats.html` is emitted on build; useful for confirming the per-worker chunks are small.     |

### Database technology

**None.** `@uwrl/qc-utils` runs entirely in-process. Persistent state
exists in two places at the consumer's discretion:

1. **The calibration cache** in `localStorage` (key
   `qc-utils:calibration:v1`) — a small DeviceProfile blob, ~200 bytes,
   refreshed once every 30 days. See [CALIBRATION.md](./CALIBRATION.md).
2. **QC history JSON files** — written and read by the consumer
   wherever they keep files. The package serializes; the consumer
   decides where to put the bytes. See [QC_HISTORY.md](./QC_HISTORY.md).

The in-memory data path uses `SharedArrayBuffer`-backed
`Float64Array` / `Float32Array` when COOP / COEP are present, falling
back to plain `ArrayBuffer` otherwise. The worker code paths gracefully
degrade to inline kernels when SAB is unavailable, so consumers without
cross-origin isolation still get correct (just slower) results.

## High-level model

```
┌──────────────────────────────────────────────────────────┐
│ Consumer (e.g. hydroserver-qc-app, Node CLI)             │
│   - holds an ObservationRecord per series                │
│   - calls record.dispatch([...])                         │
└──────────────────────┬───────────────────────────────────┘
                       │
            ┌──────────▼───────────┐
            │  ObservationRecord    │  (state container)
            │  ────────────────     │
            │  dataX (Float64Array) │
            │  dataY (Float32Array) │
            │  history[]            │
            │  redoStack[]          │
            │  dispatch(...)        │
            └────────┬──────────────┘
                     │
       ┌─────────────┼─────────────────────────┐
       ▼             ▼                         ▼
 ┌──────────┐  ┌──────────────────────┐  ┌────────────────────┐
 │  Inline  │  │ Worker dispatch      │  │ QC History I/O     │
 │  cores   │  │  - per-op worker     │  │  - serializeHistory│
 │ (single  │  │  - SAB-backed views  │  │  - parseHistory     │
 │  thread) │  │  - calibration-routed│  │  - applyHistory     │
 └──────────┘  └──────────────────────┘  └────────────────────┘
```

`ObservationRecord.dispatch` is the **only** mutation surface. Every
filter, edit, and selection produces a `HistoryItem`. The handlers
themselves are private — operations are driven by enum + args so the
same call shape works at runtime, on replay from a saved QC history, and in
unit tests.

The record holds the full series in `rawData`, but `dataX` / `dataY` (the
operation surface) carry only the active **window**. `applyWindow(begin,
end)` slices `rawData` into `dataX` / `dataY`; `reload()` restores that
windowed baseline. A window change clears history — operations only ever see
data inside the current window, so a new window starts from a fresh QC
baseline.

## Source layout

```
src/
├─ index.ts                       Public barrel — re-exports types, models, utils.
├─ types/index.ts                 All enums + types (EnumEditOperations, EnumFilterOperations,
│                                 Operator, TimeUnit, HistoryItem, QcHistory, domain models).
├─ models/                        Plain-data domain models (DataSource, Payload, Settings,
│                                 Timestamp).
├─ utils/
│  ├─ index.ts                    Util barrel.
│  ├─ format.ts                   Duration / date formatting, timeUnitMultipliers.
│  ├─ ellapsed-time.ts            `measureEllapsedTime` — tiny wall-clock helper used by every dispatch.
│  ├─ observations.ts             `findFirstGreaterOrEqual` / `findLastLessOrEqual` — binary search helpers.
│  ├─ notifications.ts            Snackbar helper (carried for consumer convenience).
│  └─ plotting/
│     ├─ observation-record.ts    The state container + dispatch entry points.
│     ├─ operation-cores.ts       Inline kernels: changeValuesCore, fillGapsCore, etc.
│     ├─ calibration.ts           shouldUseWorker / ensureCalibration / runBenchmarks.
│     ├─ history.ts                serializeHistory / parseHistory / applyHistory.
│     ├─ value-threshold.worker.ts        ┐
│     ├─ change.worker.ts                 │
│     ├─ rate-of-change.worker.ts         │  one ?worker&inline file per
│     ├─ find-gaps.worker.ts              │  kernel — Vite inlines each
│     ├─ persistence.worker.ts            │  as a Blob URL at build time
│     ├─ change-values.worker.ts          │
│     ├─ interpolate.worker.ts            │
│     ├─ drift-correction.worker.ts       │
│     ├─ shift-datetimes.worker.ts        │
│     ├─ fill-gaps.worker.ts              │
│     ├─ add-data.worker.ts               │
│     └─ delete-data.worker.ts            ┘
└─ index.ts                       Public barrel re-exports.
```

HydroServer REST is the consumer's concern, not this package's.
Use `@hydroserver/client` directly. An earlier `services/` REST
client lived here for the qc-app's convenience; it was removed in
`0.1.0` when the consumer migrated to the dedicated client.

## Operation taxonomy

Two enums define the entire dispatch surface:

### `EnumEditOperations`

| Op                      | Purpose                                                                  | Worker? |
|-------------------------|--------------------------------------------------------------------------|---------|
| `ADD_POINTS`            | Insert (datetime, value) tuples; reindex + sort by date.                 | yes     |
| `CHANGE_VALUES`         | Apply `Operator` (ADD/SUB/MULT/DIV/ASSIGN) at the prior selection.       | yes     |
| `ASSIGN_VALUES_BULK`    | Parallel `values[i] → dataY[selection[i]]`. Table-driven edits.          | inline  |
| `ASSIGN_DATETIMES_BULK` | Parallel `datetimes[i] → dataX[selection[i]]` via combined delete+add.   | inline  |
| `DELETE_POINTS`         | Drop the selection in a single skip-on-delete pass.                       | yes     |
| `INTERPOLATE`           | Linear interpolation per consecutive group in the selection.              | yes     |
| `SHIFT_DATETIMES`       | Offset the selection's timestamps by `(amount, TimeUnit)`.                | yes     |
| `DRIFT_CORRECTION`      | Apply linear drift across each consecutive group in the selection.         | yes     |
| `FILL_GAPS`             | Detect gaps above threshold; insert points at fillCadence (interpolated). | yes     |

### `EnumFilterOperations`

Filters produce a selection; they don't mutate values.

| Op                | Args                                                            | Worker? |
|-------------------|-----------------------------------------------------------------|---------|
| `VALUE_THRESHOLD` | `[{ 'Greater than': n, 'Less than': n, ... }, range?]`          | yes     |
| `DATETIME_RANGE`  | `[fromTs?, toTs?]`                                              | inline  |
| `CHANGE`          | `[comparator, value, range?]` — Δ between adjacent points       | yes     |
| `RATE_OF_CHANGE`  | `[comparator, value, range?]` — fraction (0.5 = 50%)            | yes     |
| `FIND_GAPS`       | `[amount, unit, range?]`                                        | yes     |
| `PERSISTENCE`     | `[times, range?]` — runs of identical repeated values           | yes     |
| `SELECTION`       | `[indices[]]` — explicit user selection                         | inline  |

The trailing `[startTs, endTs]` window on most filter args is in epoch
ms. `DATETIME_RANGE`'s args ARE the window itself.

## The two-flavor kernel pattern

Every worker-eligible kernel ships in **two** forms:

1. **Inline core** in `operation-cores.ts` (`changeValuesCore`,
   `fillGapsCore`, …). Pure function over typed arrays.
2. **Worker variant** in `<op>.worker.ts`. Wraps the same core in a
   `self.onmessage` handler that reads SAB-backed views.

`ObservationRecord.dispatchAction` / `dispatchFilter` route per-call
via `shouldUseWorker(op, signals)`. The decision combines:

- Per-device measured primitives (spawn overhead, inline + worker
  throughput).
- Per-op complexity weights (universal, encoded as constants).
- The current dataset and selection size.

This is the heart of the package and is documented in detail in
[CALIBRATION.md](./CALIBRATION.md).

Always-inline ops (`SELECTION`, `DATETIME_RANGE`, `ASSIGN_VALUES_BULK`,
`ASSIGN_DATETIMES_BULK`) short-circuit before reading any measured
primitives, so a missing calibration never blocks dispatch.

## SharedArrayBuffer + cross-origin isolation

Workers are useful only when they can scan the same memory the main
thread is reading. `ObservationRecord` allocates buffers via
`makeBuffer()`:

```ts
// observation-record.ts
const SAB_AVAILABLE = typeof SharedArrayBuffer !== "undefined";
function makeBuffer(byteLength, maxByteLength?) {
  if (SAB_AVAILABLE)
    return new SharedArrayBuffer(byteLength, maxByteLength ? { maxByteLength } : undefined);
  return new ArrayBuffer(byteLength, maxByteLength ? { maxByteLength } : undefined);
}
```

When SAB is unavailable:

- The buffer is a plain `ArrayBuffer`.
- `shouldUseWorker` returns `useWorker: false` because the workers
  would need a structured-clone copy, which negates the benefit.
- Everything runs inline. Identical results, slower.

The grow strategy uses typed-array `resize()` + `SharedArrayBuffer.grow()`
when the constructor advertises `maxByteLength`. `INCREASE_AMOUNT = 20_000`
extra slots is reserved on initial allocation so Add Points / Fill Gaps
don't trigger a reallocation on every batch.

## History and replay

`history: HistoryItem[]` is the canonical record of edits since the
last `reload()`. Each `HistoryItem`:

```ts
{
  method: EnumEditOperations | EnumFilterOperations,
  args?: any[],
  selected?: number[],          // index list this op produced (filters) or consumed (edits)
  execution: {
    startedAt: number,          // wall-clock epoch-ms at push time
    inFlight: boolean,          // true until the handler resolves
    status?: 'success' | 'failed',
    durationMs?: number,        // wall-clock ms (set at resolve)
    mode?: 'worker' | 'inline', // calibration routing decision
    datasetSize?: number,       // observation count at dispatch time
    selectionSize?: number,     // indices the op acted on
  },
}
```

`undo()` truncates the last entry, pushes it onto `redoStack`, and
replays the remaining history from scratch against the freshly
`reload()`-ed dataset. `redo()` is the inverse. This is conservative
(every undo is O(history-length)) but correctness is straightforward —
no rollback / inverse-op machinery to maintain. For typical QC sessions
(<100 ops) it's instant.

`serializeHistory` writes a JSON-portable `[method, ...args]` per entry
plus the wall-clock window the session was authored against.
`applyHistory` runs them in order against a fresh `ObservationRecord`;
per-op failures are reported in the return value but do not abort the
replay.

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
  serializeHistory, parseHistory, applyHistory,
  QcHistory, QcHistoryOperation, QcHistoryWindow,
  QC_HISTORY_VERSION, ApplyHistoryReport,
} from '@uwrl/qc-utils'

// Calibration
import {
  shouldUseWorker, ensureCalibration, runBenchmarks,
  getCalibration, onCalibrationChange, clearCalibration,
  DeviceProfile, DispatchSignals, DispatchDecision,
} from '@uwrl/qc-utils'

// Helpers
import {
  findFirstGreaterOrEqual, findLastLessOrEqual,
  formatDate, formatDuration, measureEllapsedTime,
} from '@uwrl/qc-utils'
```

The full per-symbol API reference is in
[API_REFERENCE.md](./API_REFERENCE.md).

## See also

- [README](../README.md)
- [API_REFERENCE.md](./API_REFERENCE.md) — every exported symbol, signature
- [QC_HISTORY.md](./QC_HISTORY.md) — QC history wire format
- [CALIBRATION.md](./CALIBRATION.md) — worker / inline dispatch
- [ONBOARDING.md](./ONBOARDING.md) — developer setup
- [DEPLOYMENT.md](./DEPLOYMENT.md) — publishing + linked-dev workflow
- [PERFORMANCE.md](./PERFORMANCE.md) — scaling characteristics
- [QUALITY.md](./QUALITY.md) — testing posture, tech debt
