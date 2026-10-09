# API Reference — `@uwrl/qc-utils`

Every public symbol exported from the package, with signatures and the
shortest useful description. For conceptual context see
[ARCHITECTURE.md](./ARCHITECTURE.md). For the QC history wire format see
[QC_HISTORY.md](./QC_HISTORY.md). For worker dispatch see
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
├─ qc history       serializeHistory, parseHistory, applyHistory,
│                   QcHistory, QcHistoryOperation, QcHistoryWindow,
│                   QC_HISTORY_VERSION, ApplyHistoryReport
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

The single state holder. Owns `dataX` (Float64), `dataY` (Float64),
`history`, and `redoStack`. All mutation goes through it.

**Construction**

```ts
new ObservationRecord(
  {
    datetimes: number[] | Float64Array,    // epoch ms
    dataValues: number[] | Float64Array,
  },
  { noDataValue?: number | null },        // the datastream's missing-reading placeholder
)
```

`datetimes` and `dataValues` must be parallel and the same length. The
record copies the inputs into SAB-backed buffers if available, plain
`ArrayBuffer` otherwise. Construction does not yet build any history;
call `reload()` once construction is done to initialize.

`noDataValue` marks missing readings. `CHANGE_VALUES` (except `ASSIGN`) and
`DRIFT_CORRECTION` skip points holding it, `INTERPOLATE` never anchors on it,
and `FILL_GAPS` writes `fillValue` instead of interpolating across a gap edge
that holds it. Omitted or `null`, every value is treated as a measurement.

**Properties**

| Name        | Type                            | Notes                                                             |
|-------------|---------------------------------|-------------------------------------------------------------------|
| `dataX`     | `Float64Array`                  | Timestamps (ms epoch) of the **current window** (see `applyWindow`). |
| `dataY`     | `Float64Array`                  | Values of the current window.                                    |
| `rawData`   | `{ datetimes, dataValues }`     | The full series (source of truth); `dataX`/`dataY` are its windowed slice. |
| `windowBegin` / `windowEnd` | `number`          | Inclusive epoch-ms bounds materialized into `dataX`/`dataY`. `±Infinity` = full series. |
| `history`   | `HistoryItem[]`                 | Append-only log since the last `reload()` / window change.        |
| `redoStack` | `HistoryItem[]`                 | Items popped by `undo()`, available to `redo()`.                  |
| `revision`  | `number`                        | Bumped by every load (including undo, redo and preview) and every edit operation; filters and selections leave it. Index-keyed state is stale once it changes. |
| `noDataValue` | `number \| null`              | The datastream's missing-reading placeholder (see Construction).  |

**Methods**

| Method                                       | Returns          | Effect                                                                                     |
|----------------------------------------------|------------------|--------------------------------------------------------------------------------------------|
| `dispatch(ops: Array<[Enum, ...args]>)`      | `Promise<number[]>` | Run a chain of operations in order. Each op appends a `HistoryItem` (a filter can replace the one before it). Returns the last op's selection. |
| `dispatchStep(step)`                         | `Promise<number[]>` | Run one recorded step (`method`, `args`) and carry its `comment` and `performedBy` onto the entry it produces. Every replay goes through it, so these survive undo, redo, removal and `applyHistory` even when replay merges entries. |
| `dispatchAction(op: EnumEditOperations, ...args)` | `Promise<number[]>` | Run one edit op. Returns the selection it leaves.                                  |
| `dispatchFilter(op: EnumFilterOperations, ...args)` | `Promise<number[]>` | Run one filter op. Returns its selection.                                        |
| `undo()`                                     | `Promise<number[]>` | Pop the last history entry; replay the rest from a fresh `reload()`. Returns the selection left. |
| `redo()`                                     | `Promise<number[]>` | Replay the most recently undone entry. Returns its selection.                           |
| `applyWindow(begin, end, rawData?)`          | `Promise<void>`  | Materialize the inclusive epoch-ms window `[begin, end]` of `rawData` into `dataX`/`dataY`. A passed `rawData` replaces the full series first (e.g. after a cache filled a gap). Clears history on a real change; no-op when neither the window nor the data changed. |
| `reload()`                                   | `Promise<void>`  | Re-initialize the typed arrays from `rawData`, sliced to the current window; clear history. |
| `previewHistory(index)`                      | `Promise<number[]>` | Show the data as of step `index` (`-1` for the starting state) and keep every later step listed, unapplied. Sets `previewIndex`; edits throw `HistoryPreviewError` until `exitPreview`. Previewing the last step is `exitPreview`. Returns the shown step's selection. |
| `exitPreview()`                              | `Promise<number[]>` | Replay the whole history after a preview. A no-op when nothing is previewed. |
| `truncateHistory(index)`                     | `Promise<number[]>` | Drop every step after `index` for good, clear the redo stack and replay the rest. |
| `restoreHistory(steps)`                      | `Promise<number[]>` | Replace the history with `steps` (keeping their comment and attribution), clear the redo stack and replay from raw. For going back to a saved history that undo and new edits have diverged from. |
| `previewIndex`                               | `number \| null`    | The step being previewed, or null when the data reflects the whole history. `undo` ends a preview; `redo` ends it first, then redoes. |
| `removeHistoryItem(index: number)`           | `Promise<number[]>` | Drop a specific entry and clear the redo stack; replay the rest. Returns the selection left. |

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
| `DELETE_POINTS`        | `(indices?: number[])`, defaulting to the prior selection. Indices past the end and repeats are ignored. |
| `INTERPOLATE`          | `()` — linear interpolation per consecutive group in the prior selection.    |
| `SHIFT_DATETIMES`      | `(amount: number, unit: TimeUnit, timeZone: string)`; months and years follow `timeZone`'s calendar; see Time zones. |
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

## QC History API

### `function serializeHistory(record, window): QcHistory`

```ts
serializeHistory(record: ObservationRecord, window: { startDate: string; endDate: string }): QcHistory
```

Convert the current history into a JSON-portable `QcHistory`. ISO-8601
strings round-trip cleanly through `JSON.stringify`.

### `function parseHistory(raw: unknown): QcHistory`

Validate a parsed JSON object against the QC history schema. Throws on
shape / version mismatch. Use after `JSON.parse`.

### `function applyHistory(record, history): Promise<ApplyHistoryReport>`

Replay every op in `history.operations` against `record`. Per-op failures
are captured in the report but do not abort.

### `interface QcHistory`

```ts
{
  version: '1',
  createdAt: string,                   // ISO-8601
  window: { startDate: string; endDate: string },
  operations: QcHistoryOperation[],
}
```

### `interface QcHistoryOperation`

```ts
{
  method: EnumEditOperations | EnumFilterOperations,
  args: any[],
  comment?: string,                    // the operator's note, trimmed; absent when blank
  performedBy?: string,                // who applied it, for display; audit only
  execution?: QcHistoryExecution,
}
```

### `interface QcHistoryExecution`

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

Every field is optional so pre-v0.1.x QC histories (which had no
`execution` field) still load. The replay path stamps fresh runtime
values onto `HistoryItem.execution`; the persisted record survives
verbatim for audit. `parseHistory` rejects non-finite numbers and
unknown enum values on any present field.

### `interface QcHistoryWindow`

```ts
{ startDate: string; endDate: string }  // ISO-8601
```

### `interface ApplyHistoryReport`

```ts
{
  applied: number,
  failed: Array<{ index: number; method: string; error: string }>,
}
```

### `const QC_HISTORY_VERSION: '1'`

The current wire-format version. Bumped on incompatible schema changes;
`parseHistory` rejects mismatches.

See [QC_HISTORY.md](./QC_HISTORY.md) for versioning rules,
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

### Time zones

`FIXED_OFFSET_TIMEZONES` (`{ title, value }` with values like `-0700`) and
`DST_AWARE_TIMEZONES` (every IANA zone `Intl` knows, titled with its winter
and summer offsets), with their `FixedOffsetTimezone` and `DstAwareTimezone`
value types. The lists a data connection's timestamps choose from; the QC
app's time zone setting offers the same ones.

The math takes a zone as a string: `UTC`, a fixed offset like `-0700`, or
an IANA name.

```ts
isValidTimeZone(zone: unknown): boolean
offsetMs(ms: number, zone: string): number       // the zone's offset at ms
toWall(ms: number, zone: string): number         // ms moved to the zone's clock
fromWall(wall: number, zone: string): number     // back to an instant
toWallArray(xs, zone): typeof xs | Float64Array  // xs itself when nothing moves
fromWallArray(walls, zone): typeof walls | Float64Array  // fromWall over an array; walls itself when nothing moves
addCalendarMonths(ms: number, months: number, zone: string): number
```

A **wall** value is an instant moved by the zone's offset, so its UTC
fields read as the zone's clock. IANA offsets are cached per UTC day, with
the transition minute found on a day the offset changes. A clock time that
daylight saving skips or repeats maps to an instant beside it.

`addCalendarMonths` keeps the clock time on the zone's calendar, so Jan 15
at 9:00 in Denver plus six months is Jul 15 at 9:00 there, across the
change to daylight time. A day past the end of the target month clamps to
its last day: Jan 31 plus a month is Feb 28 (29 in a leap year).

`SHIFT_DATETIMES` saves its zone, so a month or year shift replays the
same on any machine. It fails (`execution.status: "failed"`) on a zone
`isValidTimeZone` rejects, or a month or year amount that isn't whole.
Other units are fixed spans and ignore the zone.

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
  comment?: string,                    // authored; survives every replay
  performedBy?: string,                // server provenance; survives every replay
  execution: HistoryExecution,
}
```

### `class HistoryPreviewError`

Thrown by any edit dispatched while `previewIndex` is set, that is while
`previewHistory` shows an earlier step. `exitPreview()` (or previewing the
last step) ends the preview.

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
  extent?: { begin: number, end: number }, // epoch-ms of the first / last point acted on
}
```

`execution` populates in two phases:

- **Push time** (synchronous, before the handler runs): `startedAt`,
  `inFlight: true`, `datasetSize`, and (for selection-consuming
  edits) `selectionSize` and `extent`, read from the preceding entry's
  selection (a SELECTION or a filter result) before the edit moves it.
- **Resolve time** (after the handler returns or throws): `status`,
  `durationMs`, `mode`, `inFlight: false`, and (for filters)
  `selectionSize` and `extent` from the produced selection. ADD_POINTS
  and FILL_GAPS get `extent` here from the points they inserted.

`extent` names the period a step touched in datetimes, which later edits
don't shift the way they shift indices. It is runtime-only, like
`selected`: replay recomputes it and `serializeHistory` leaves it out.

The qc-app reads this object to drive the EditHistory UI (per-row
spinner via `inFlight`, failure badge via `status`, duration text
via `durationMs`, dev-only worker/inline chip via `mode`).

`startedAt` is re-stamped on every replay (`undo` / `redo` /
`applyHistory`) so the in-memory value always reflects the current
session's execution. `serializeHistory` persists the runtime
record into the QC history's per-op `execution` field for audit;
`applyHistory` does NOT forward the persisted record onto the new
`HistoryItem.execution` — dispatch builds a fresh one. Saved
QC histories hold "originally ran like this at this size on this mode";
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

`MonitoringSite`, `Datastream`, `DatastreamExtended`, `Unit`, `Method`,
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
- [QC_HISTORY.md](./QC_HISTORY.md)
- [CALIBRATION.md](./CALIBRATION.md)
- [PERFORMANCE.md](./PERFORMANCE.md)
- [QUALITY.md](./QUALITY.md)
