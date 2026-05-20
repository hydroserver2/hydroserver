# API Reference — `@uwrl/qc-utils`

Every public symbol exported from the package, with signatures and the
shortest useful description. For conceptual context see
[ARCHITECTURE.md](./ARCHITECTURE.md). For the QC script wire format see
[HISTORY_SCRIPT.md](./HISTORY_SCRIPT.md). For worker dispatch see
[CALIBRATION.md](./CALIBRATION.md).

## API design principles

- **Single state container.** All mutation goes through
  `ObservationRecord`. There is no parallel set of functions that
  bypass the history.
- **Enum + args.** Operations are dispatched by `(EnumX, ...args)` tuples
  so the same call shape works at runtime, replay, and in tests.
- **History is the contract.** Every dispatch appends a `HistoryItem`.
  Anything that doesn't append (low-level array reads, calibration
  queries) is named accordingly.
- **Workers are an implementation detail.** Consumers don't import
  worker files. The dispatcher routes per call.
- **No DOM, no framework dependencies in the engine.** Vue / React /
  Node — all valid hosts. The only DOM-touching export is
  `Snackbar` (browser-only notification helper); everything else
  is headless.

## Module map

```
@uwrl/qc-utils
├─ state            ObservationRecord, INCREASE_AMOUNT
├─ operation enums  EnumEditOperations, EnumFilterOperations, Operator,
│                   FilterOperation, TimeUnit, timeUnitMultipliers
├─ types            HistoryItem, GraphSeries, DataPoint, …
├─ scripts          serializeHistory, parseScript, applyScript,
│                   QcScript, QcScriptOperation, QcScriptWindow,
│                   QC_SCRIPT_VERSION, ApplyScriptReport
├─ calibration      shouldUseWorker, ensureCalibration, runBenchmarks,
│                   getCalibration, onCalibrationChange,
│                   clearCalibration, DeviceProfile, DispatchSignals,
│                   DispatchDecision
├─ helpers          findFirstGreaterOrEqual, findLastLessOrEqual,
│                   formatDate, formatDuration, measureEllapsedTime
└─ Snackbar         browser-only notification helper (DOM-dependent)
```

For HydroServer REST calls, use `@hydroserver/client` directly. An
earlier `services/` REST client lived in this package; it was
removed in `0.1.0` because the consumer (qc-app) moved to the
dedicated client.

## State container

### `class ObservationRecord`

The single state holder. Owns `dataX` (Float64), `dataY` (Float32),
`history`, and `redoStack`. All mutation goes through it.

**Construction**

```ts
new ObservationRecord({
  datetimes: number[] | Float64Array,    // epoch ms
  dataValues: number[] | Float32Array,
})
```

`datetimes` and `dataValues` must be parallel and the same length. The
record copies the inputs into SAB-backed buffers if available, plain
`ArrayBuffer` otherwise. Construction does not yet build any history;
call `reload()` once construction is done to initialize.

**Properties**

| Name        | Type                            | Notes                                                             |
|-------------|---------------------------------|-------------------------------------------------------------------|
| `dataX`     | `Float64Array`                  | Timestamps, ms epoch.                                             |
| `dataY`     | `Float32Array`                  | Values.                                                           |
| `history`   | `HistoryItem[]`                 | Append-only log since the last `reload()`.                        |
| `redoStack` | `HistoryItem[]`                 | Items popped by `undo()`, available to `redo()`.                  |

**Methods**

| Method                                       | Returns          | Effect                                                                                     |
|----------------------------------------------|------------------|--------------------------------------------------------------------------------------------|
| `dispatch(ops: Array<[Enum, ...args]>)`      | `Promise<void>`  | Run a chain of operations atomically. Each op appends a `HistoryItem`.                     |
| `dispatchAction(op: EnumEditOperations, ...args)` | `Promise<void>` | Run one edit op.                                                                      |
| `dispatchFilter(op: EnumFilterOperations, ...args)` | `Promise<void>` | Run one filter op. Produces a selection.                                             |
| `undo()`                                     | `Promise<void>`  | Pop the last history entry; replay the rest from a fresh `reload()`.                       |
| `redo()`                                     | `Promise<void>`  | Replay the most recently undone entry.                                                     |
| `reload()`                                   | `Promise<void>`  | Re-initialize the typed arrays from the original constructor inputs; clear history.        |
| `reloadHistory()`                            | `Promise<void>`  | Replay current history against a fresh `reload()`.                                         |
| `removeHistoryItem(index: number)`           | `Promise<void>`  | Drop a specific entry; replay the rest.                                                    |

The op handlers themselves are private — dispatch by enum.

### `const INCREASE_AMOUNT: number`

The growth headroom in slots (default `20_000`) reserved on initial
buffer allocation so Add Points / Fill Gaps don't trigger a
reallocation on every batch. Tunable per-consumer if memory pressure
matters; lower means smaller idle memory, more frequent grow / copy.

## Operation enums

### `enum EnumEditOperations`

| Value                  | Args                                                                         |
|------------------------|------------------------------------------------------------------------------|
| `ADD_POINTS`           | `(datetimes: number[], values: number[])` — parallel arrays.                 |
| `CHANGE_VALUES`        | `(operator: Operator, value: number, [range?])` — applies at prior selection.|
| `ASSIGN_VALUES_BULK`   | `(indices: number[], values: number[])` — parallel arrays. No workers.       |
| `ASSIGN_DATETIMES_BULK`| `(indices: number[], datetimes: number[])` — combined delete + add.          |
| `DELETE_POINTS`        | `(indices?: number[])` — defaults to the prior selection.                    |
| `INTERPOLATE`          | `()` — linear interpolation per consecutive group in the prior selection.    |
| `SHIFT_DATETIMES`      | `(amount: number, unit: TimeUnit)`                                           |
| `DRIFT_CORRECTION`     | `(value: number)` — linear drift across each consecutive group.              |
| `FILL_GAPS`            | `(gapThreshold: [amount, unit], fillCadence: [amount, unit], fillValue?: number)` |

### `enum EnumFilterOperations`

| Value             | Args                                                            |
|-------------------|-----------------------------------------------------------------|
| `VALUE_THRESHOLD` | `({ 'Greater than'?: n, 'Less than'?: n, ... }, [range?])`      |
| `DATETIME_RANGE`  | `(fromTs?: number, toTs?: number)` — epoch ms.                   |
| `CHANGE`          | `(comparator: FilterOperation, value: number, [range?])`         |
| `RATE_OF_CHANGE`  | `(comparator: FilterOperation, fraction: number, [range?])`      |
| `FIND_GAPS`       | `(amount: number, unit: TimeUnit, [range?])`                     |
| `PERSISTENCE`     | `(times: number, [range?])` — minimum run length.                |
| `SELECTION`       | `(indices: number[])` — explicit user selection.                 |

Filter `range?` is the optional trailing `[startTs, endTs]` window
in epoch ms.

### `enum Operator`

`ADD`, `SUB`, `MULT`, `DIV`, `ASSIGN`. Used by `CHANGE_VALUES`.

### `enum FilterOperation`

`LT`, `LTE`, `GT`, `GTE`, `E`. Used by `CHANGE` / `RATE_OF_CHANGE`.
Values match the display strings: `'Less than'`, `'Less than or equal to'`, etc.

### `enum TimeUnit`

`SECOND`, `MINUTE`, `HOUR`, `DAY`, `WEEK`, `MONTH`, `YEAR`. Values are
the single-char codes: `s`, `m`, `h`, `D`, `W`, `M`, `Y`.

### `const timeUnitMultipliers: Record<TimeUnit, number>`

Multiplier from each `TimeUnit` to milliseconds.

## History script API

### `function serializeHistory(record, window): QcScript`

```ts
serializeHistory(record: ObservationRecord, window: { startDate: string; endDate: string }): QcScript
```

Convert the current history into a JSON-portable `QcScript`. ISO-8601
strings round-trip cleanly through `JSON.stringify`.

### `function parseScript(raw: unknown): QcScript`

Validate a parsed JSON object against the script schema. Throws on
shape / version mismatch. Use after `JSON.parse`.

### `function applyScript(record, script): Promise<ApplyScriptReport>`

Replay every op in `script.operations` against `record`. Per-op failures
are captured in the report but do not abort.

### `interface QcScript`

```ts
{
  version: '1',
  createdAt: string,                   // ISO-8601
  window: { startDate: string; endDate: string },
  operations: QcScriptOperation[],
}
```

### `interface QcScriptOperation`

```ts
{
  method: EnumEditOperations | EnumFilterOperations,
  args: any[],
  execution?: QcScriptExecution,
}
```

### `interface QcScriptExecution`

```ts
{
  startedAt?: number,                  // epoch-ms when the op was first dispatched
  status?: 'success' | 'failed',
  durationMs?: number,
  mode?: 'worker' | 'inline',
  datasetSize?: number,                // observation count at dispatch time
  selectionSize?: number,              // indices the op acted on
}
```

Every field is optional so pre-v0.1.x scripts (which had no
`execution` field) still load. The replay path stamps fresh runtime
values onto `HistoryItem.execution`; the persisted record survives
verbatim for audit. `parseScript` rejects non-finite numbers and
unknown enum values on any present field.

### `interface QcScriptWindow`

```ts
{ startDate: string; endDate: string }  // ISO-8601
```

### `interface ApplyScriptReport`

```ts
{
  applied: number,
  failed: Array<{ index: number; method: string; error: string }>,
}
```

### `const QC_SCRIPT_VERSION: '1'`

The current wire-format version. Bumped on incompatible schema changes;
`parseScript` rejects mismatches.

See [HISTORY_SCRIPT.md](./HISTORY_SCRIPT.md) for versioning rules,
loader workflow, and per-op arg shape examples.

## Calibration API

### `function shouldUseWorker(op, signals): DispatchDecision`

```ts
shouldUseWorker(
  op: EnumEditOperations | EnumFilterOperations,
  signals: DispatchSignals,
): DispatchDecision
```

`DispatchSignals = { datasetSize: number; selectionSize: number }`.

Decide per call whether `op` should run inline or on a worker, given
the current dataset size and selection size. Reads the cached device
profile. Always-inline ops short-circuit before any measurement is
read.

### `function ensureCalibration(): Promise<DeviceProfile>`

Idempotent: returns the cached profile if fresh (<30 days), otherwise
runs the benchmark suite once and stores the result. Call on idle.

### `function runBenchmarks(): Promise<BenchmarkDetail>`

Run the benchmark suite unconditionally. Returns the full sample
breakdown alongside the saved profile. Used by the calibration UI's
"Re-benchmark" button.

### `function getCalibration(): DeviceProfile | null`

Read the cached profile without running anything. `null` if never run.

### `function onCalibrationChange(cb): () => void`

Subscribe to calibration changes; returns an unsubscribe function.
Fires after `runBenchmarks` writes a new profile and after
`clearCalibration` removes one.

### `function clearCalibration(): void`

Drop the cached profile. The next dispatch will use the conservative
fallback until `ensureCalibration` runs again.

### `interface DeviceProfile`

```ts
{
  spawnOverheadMs: number,            // wall-clock for one worker roundtrip
  inlineThroughput: number,           // elements/ms on reference O(n) kernel
  workerThroughput: number,           // same, on worker
  hwConcurrency: number,
  measuredAt: number,                 // epoch ms
  userAgent: string,
}
```

### `interface DispatchSignals`

```ts
{ datasetSize: number; selectionSize: number }
```

### `interface DispatchDecision`

```ts
{
  useWorker: boolean,
  predictedInlineMs: number,
  predictedWorkerMs: number,
  reason: string,                     // human-readable explanation
}
```

See [CALIBRATION.md](./CALIBRATION.md) for the methodology and the
fallback profile.

## Helpers

### Binary search

```ts
findFirstGreaterOrEqual(arr: Float64Array | number[], target: number): number
findLastLessOrEqual(arr: Float64Array | number[], target: number): number
```

Used by `DATETIME_RANGE` / `FIND_GAPS` for sub-O(n) windowing.

### Formatting

```ts
formatDate(ts: number): string         // human-readable date
formatDuration(ms: number): string     // "1d 2h 3m 4s"
```

### `measureEllapsedTime<T>(fn: () => Promise<T> | T): Promise<{ result: T; duration: number }>`

Wrap any thunk with wall-clock measurement. Used by dispatch to fill
`HistoryItem.execution.durationMs`.

## Types

### `interface HistoryItem`

```ts
{
  method: EnumEditOperations | EnumFilterOperations,
  args?: any[],
  selected?: number[],
  execution: HistoryExecution,
}
```

`execution` is always present and carries every per-dispatch
runtime fact. See below for the field-by-field contract.

### `interface HistoryExecution`

```ts
{
  startedAt: number,                   // wall-clock epoch-ms stamped at push time
  inFlight: boolean,                   // true until the dispatch resolves
  status?: 'success' | 'failed',       // undefined while inFlight
  durationMs?: number,                 // undefined while inFlight
  mode?: 'worker' | 'inline',          // routing decision the calibration layer made
  datasetSize?: number,                // observation count at dispatch time
  selectionSize?: number,              // indices the op acted on
}
```

`execution` populates in two phases:

- **Push time** (synchronous, before the handler runs): `startedAt`,
  `inFlight: true`, `datasetSize`, and (for selection-consuming
  edits) `selectionSize`.
- **Resolve time** (after the handler returns or throws): `status`,
  `durationMs`, `mode`, `inFlight: false`, and (for filters)
  `selectionSize` (populated from the produced selection).

The qc-app reads this object to drive the EditHistory UI (per-row
spinner via `inFlight`, failure badge via `status`, duration text
via `durationMs`, dev-only worker/inline chip via `mode`).

`startedAt` is re-stamped on every replay (`undo` / `redo` /
`applyScript`) so the in-memory value always reflects the current
session's execution. `serializeHistory` persists the runtime
record into the script's per-op `execution` field for audit;
`applyScript` does NOT forward the persisted record onto the new
`HistoryItem.execution` — dispatch builds a fresh one. Saved
scripts hold "originally ran like this at this size on this mode";
the live `HistoryItem.execution` holds "ran in this session at
this size on this mode."

### `interface GraphSeries`

Wrapper around an `ObservationRecord` carrying display metadata. Used
by consumers to label a series for plotting.

```ts
{
  id: string,
  name: string,
  data: ObservationRecord,
  yAxisLabel: string,
  seriesOption: any,
}
```

### `type DataPoint`

```ts
{ date: Date; value: number }
```

### `type DataArray`

```ts
Array<[string, number]>    // legacy CSV-style row, retained for some serializers
```

### Other domain models

`Thing`, `Datastream`, `DatastreamExtended`, `Unit`, `Sensor`,
`ObservedProperty`, `ProcessingLevel`, `ResultQualifier`, `Workspace`,
`User`, `Tag`, `Frequency`, `Permission`, `PermissionAction`,
`PermissionResource`, `CollaboratorRole`, `Collaborator`, `ApiKey`,
`Organization`, `HydroShareArchive`, `PostHydroShareArchive`,
`Location`, `UserInfo`, `OAuthProvider`, `WorkspaceData`,
`ThingWithColor`, `Photo`, `ApiError`, `EnumDictionary`,
`LogicalOperation`, `Tag`, `TimeSpacingUnit`.

These mirror HydroServer's domain shapes. For new code, treat
`@hydroserver/client` as the canonical source of truth; the
qc-utils copies are kept because the QC engine references them
internally.

## `Snackbar` (browser-only notification helper)

A small DOM-based notification helper used by the qc-app and kept
here for that consumer. Independent of the QC engine; it depends
on `document` / `window` and is not usable from Node or Pyodide.

```ts
import { Snackbar } from '@uwrl/qc-utils'

Snackbar.success('Saved')
Snackbar.error('Network error. Please check your connection.')
```

## Browser requirements

- ES2022 / native `import`. Bundled as ESM with a CJS shim.
- `SharedArrayBuffer` for the worker fast-path (graceful inline
  fallback when unavailable).
- Typed-array `resize()` / `SharedArrayBuffer.grow()` —
  Chrome 111+ / Firefox 119+ / Safari 16.4+.

## See also

- [README](../README.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [HISTORY_SCRIPT.md](./HISTORY_SCRIPT.md)
- [CALIBRATION.md](./CALIBRATION.md)
- [PERFORMANCE.md](./PERFORMANCE.md)
- [QUALITY.md](./QUALITY.md)
