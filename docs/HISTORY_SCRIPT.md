# QC History Script — Save / Load Design

This document describes the JSON file format for serializing and
replaying an `ObservationRecord` history, plus the consumer-side
save/load workflow.

The format is intentionally designed to be the **foundation for the
HydroServer API** representation of a QC script — what the app saves
locally today is what the backend will accept and replay tomorrow.
The on-disk JSON IS the wire format.

---

## Goals

1. **Round-trip a session.** Save the executable record of every
   transformation a user applied to a `Datastream`, load it back, and
   replay it against the same raw data to reproduce the edited
   dataset bit-for-bit.
2. **Be the API foundation.** No app-specific state in the file.
   Consumer (UI) state and server state both stay out. Anything in the
   file is portable to a different consumer (CLI, Python notebook,
   backend replay worker).
3. **Stay reusable.** A script doesn't pin itself to a specific
   datastream id. The same script can be applied to any compatible
   datastream — useful for templating QC across stations, or for
   re-running a procedure after the source data is replaced.
4. **Stay forward-compatible.** A `version` field at the root lets us
   evolve the schema without breaking older files. Loaders refuse
   files they don't understand instead of silently mis-replaying.
5. **Window-aware.** Real QC happens incrementally as data is
   gathered. A script records the date window it was authored
   against; loading it into a growing dataset means fetching that
   exact window before replaying — the script does not assume the
   target dataset's full extent matches the author-time extent.
6. **Keep parameter args, not derived state.** The script captures
   "what the user told the operation to do," not "what the operation
   produced." Derived data (selection indices) is recomputed on
   replay; only inputs and a per-op `execution` audit record (timing,
   mode, dataset shape — kept verbatim) are persisted.

## Non-goals

- **Persisting the underlying observations.** The script applies to
  whatever raw data the consumer hands the `ObservationRecord` at
  load time. If the data changed shape (different point count, gaps
  appearing/disappearing) the script may not produce the same edited
  result — that's the consumer's concern, not the format's.
- **Persisting qualifiers in this version.** Result-qualifier flags
  (the per-index "missing" / "estimated" / etc. codes the Qualifying
  Comments panel attaches) are tracked in a separate Pinia store
  outside `ObservationRecord.history`. They need their own
  serialization story; bundling them in here would conflate two
  conceptually distinct edit streams.

---

## JSON schema (v1)

```json
{
  "version": "1",
  "createdAt": "2026-04-25T16:42:00.000Z",
  "window": {
    "startDate": "2024-01-01T00:00:00.000Z",
    "endDate":   "2024-06-30T23:59:59.999Z"
  },
  "operations": [
    {
      "method": "SELECTION",
      "args": [[127, 128, 129, 415, 416, 502]],
      "execution": {
        "startedAt": 1745597008000,
        "status": "success",
        "durationMs": 0.6,
        "mode": "inline",
        "datasetSize": 12000,
        "selectionSize": 6
      }
    },
    {
      "method": "DELETE_POINTS",
      "args": [],
      "execution": {
        "startedAt": 1745597015000,
        "status": "success",
        "durationMs": 4.1,
        "mode": "inline",
        "datasetSize": 12000,
        "selectionSize": 6
      }
    },
    {
      "method": "FILL_GAPS",
      "args": [[15, "m"], [5, "m"], true, -9999],
      "execution": {
        "startedAt": 1745597032000,
        "status": "success",
        "durationMs": 240,
        "mode": "worker",
        "datasetSize": 11994
      }
    },
    {
      "method": "ADD_POINTS",
      "args": [[[1737000000000, 12.4], [1737003600000, 12.5]]],
      "execution": {
        "startedAt": 1745597048000,
        "status": "success",
        "durationMs": 6.2,
        "mode": "inline",
        "datasetSize": 12012
      }
    }
  ]
}
```

`DELETE_POINTS` carries `args: []` because its target indices come
from the preceding `SELECTION` entry — see the per-method table
below and the "selection-coupling" note. The pattern is
intentional: index-typed args don't live on selection-consuming
edits, they live on the `SELECTION` (or the filter) immediately
before them so a single source of indices feeds every downstream
op without duplication. The five other selection-consuming
edits — `INTERPOLATE`, `SHIFT_DATETIMES`, `DRIFT_CORRECTION`,
`CHANGE_VALUES`, `ASSIGN_*_BULK` — follow the same contract: any
script that includes one must place a `SELECTION` (or a non-
SELECTION filter whose `selected` it should consume) immediately
before it.

### Top-level fields

| Field        | Type     | Required | Notes                                                                 |
|--------------|----------|----------|-----------------------------------------------------------------------|
| `version`    | string   | yes      | `"1"` for the current schema. Loaders reject unknown versions.        |
| `createdAt`  | ISO-8601 | yes      | When the script was saved. Used for sorting and audit display.        |
| `window`     | object   | yes      | The date range the script was authored against. The loader fetches this exact window before replaying. |
| `window.startDate` | ISO-8601 | yes | Inclusive lower bound of the data window.                          |
| `window.endDate`   | ISO-8601 | yes | Inclusive upper bound of the data window.                          |
| `operations` | object[] | yes      | The replayable operation list (see below).                            |


### Per-operation entry

| Field       | Type    | Required | Notes                                                              |
|-------------|---------|----------|--------------------------------------------------------------------|
| `method`    | string  | yes      | `EnumEditOperations` or `EnumFilterOperations` value (e.g. `"VALUE_THRESHOLD"`, `"FILL_GAPS"`). |
| `args`      | any[]   | yes      | Positional args forwarded to the operation handler. Per-method shape rules below. |
| `execution` | object  | no       | Per-dispatch audit record (timing, mode, dataset shape, status). See below. Omitted in pre-v0.1.x scripts and may be absent on hand-written JSON; the loader accepts both shapes. |

The shape mirrors `ObservationRecord.dispatch`'s tuple form:
`[method, ...args]`. A loaded script is replayed via
`record.dispatch(operations.map(o => [o.method, ...o.args]))`.

### `execution` sub-fields

| Field           | Type    | Notes                                                                       |
|-----------------|---------|-----------------------------------------------------------------------------|
| `startedAt`     | number  | Wall-clock epoch-milliseconds (UTC) when the dispatch site pushed the entry. |
| `status`        | string  | `"success"` or `"failed"`. Failure surfaces in the qc-app UI as a red badge. |
| `durationMs`    | number  | Wall-clock duration of the handler. Useful for retrospective perf review.   |
| `mode`          | string  | `"worker"` or `"inline"` — the calibration layer's routing decision.        |
| `datasetSize`   | number  | Observation count at dispatch time. Reflects the pre-edit shape.            |
| `selectionSize` | number  | Indices the op acted on (filter's produced selection, or preceding SELECTION for selection-consuming edits). |

Every sub-field is optional; the loader validates the type of any
present value (finite number / `"success"` \| `"failed"` /
`"worker"` \| `"inline"`) and rejects malformed shapes.

`execution` is **record-keeping, not replay input.** The loader does
not forward it to the dispatcher: `dispatchAction` /
`dispatchFilter` build a fresh `HistoryExecution` for the new run
so the in-memory record reflects the current session. The persisted
record survives in the saved script for later audit (and for any
consumer that wants to show "originally ran inline on a 50k record
in 240ms" alongside the replay's numbers).

---

## Per-method serialization rules

The runtime `HistoryItem` carries `selected` (the indices the op
produced) and `execution.inFlight` (true until the handler resolves)
that the script doesn't need: `selected` is recomputed on replay and
`inFlight` is meaningless for a serialized entry. Everything else on
`execution` (`startedAt`, `status`, `durationMs`, `mode`,
`datasetSize`, `selectionSize`) round-trips verbatim into the
`execution` audit object on the persisted op.

**Every method's `args` serializes verbatim.** No per-method elide
or re-inject machinery. The save layer is `JSON.stringify`-grade
trivial; the load layer is
`record.dispatch(operations.map(o => [o.method, ...o.args]))`.

The methods split along one **runtime** dimension: whether they
need a preceding SELECTION-producing entry in history at replay
time. That's a runtime contract — the script preserves the original
ordering, so the replay walks the operation list in sequence and
the SELECTION is in the right slot when the consuming op fires.

### Method table

All wall-clock args (timestamps, ranges) are epoch-milliseconds,
NOT dataset indices, so they survive data growth and are portable
across datasets. The `SELECTION` entry's `indices[]` is the lone
index-typed survivor — its indices ARE the operation's purpose, and
they replay against the same windowed dataset shape that the
script's `window` field guarantees the loader fetches before
replay.

**Trailing optional `[startTs, endTs]?` on filter ops.** Every
scan-style filter (`VALUE_THRESHOLD`, `CHANGE`, `RATE_OF_CHANGE`,
`FIND_GAPS`, `PERSISTENCE`) accepts an optional `[startTs, endTs]`
tuple as its last positional arg, sourced from the shared "Filter
range" toggle in the plot toolbar. Omit when the user has the
toggle off (the filter scans the full extent); include when the
user pinned the scan to a window. `DATETIME_RANGE` is the
exception — its from/to args ARE the window, so there is no
trailing range tuple.

| Method                  | `args` shape                                                                                        | Reads `history[-2].selected` at runtime? |
|-------------------------|-----------------------------------------------------------------------------------------------------|------------------------------------------|
| `VALUE_THRESHOLD`       | `[{ "Greater than": number, ... }, [startTs, endTs]?]`                                              | No                                       |
| `DATETIME_RANGE`        | `[fromTs?, toTs?]`                                                                                  | No                                       |
| `CHANGE`                | `[comparator, value, [startTs, endTs]?]`                                                            | No                                       |
| `RATE_OF_CHANGE`        | `[comparator, value, [startTs, endTs]?]` — value is a fraction (0.5 = 50%)                          | No                                       |
| `FIND_GAPS`             | `[amount, unit, [startTs, endTs]?]`                                                                 | No                                       |
| `PERSISTENCE`           | `[times, [startTs, endTs]?]`                                                                        | No                                       |
| `SELECTION`             | `[indices[]]`                                                                                       | No                                       |
| `ADD_POINTS`            | `[ [ [epochMs, value], ... ] ]`                                                                     | No                                       |
| `FILL_GAPS`             | `[ [gapAmount, gapUnit], [fillAmount, fillUnit], interpolateValues, fillValue, [startTs, endTs]? ]` | No                                       |
| `CHANGE_VALUES`         | `[operator, value]`                                                                                 | **Yes** (indices to mutate)              |
| `ASSIGN_VALUES_BULK`    | `[values[]]`                                                                                        | **Yes** (indices to assign at)           |
| `ASSIGN_DATETIMES_BULK` | `[datetimes[]]`                                                                                     | **Yes** (indices to assign at)           |
| `DELETE_POINTS`         | `[]`                                                                                                | **Yes** (indices to delete)              |
| `INTERPOLATE`           | `[]`                                                                                                | **Yes** (indices to interpolate)         |
| `SHIFT_DATETIMES`       | `[amount, unit]`                                                                                    | **Yes** (indices to shift)               |
| `DRIFT_CORRECTION`      | `[value]`                                                                                           | **Yes** (consecutive groups → ranges, per-group drift = `value`) |

### Note on the runtime selection-coupling column

Operations marked **Yes** have no selection-related args of their
own. They each route through a thin `*FromSelection` dispatch
wrapper inside qc-utils that reads the target indices off
`history[length - 2].selected`. Concretely:

- A script `[…, SELECTION([3,4,5]), DELETE_POINTS]` deletes
  indices 3, 4, and 5.
- A script `[…, VALUE_THRESHOLD({"Greater than": 100}), DELETE_POINTS]`
  is **also valid** — the filter's own `selected` array is what
  `DELETE_POINTS` reads.
- A script that has `DELETE_POINTS` at index 0 (no prior entry),
  or whose preceding entry is another selection-consuming edit
  rather than a filter or `SELECTION`, will throw at replay time
  because `history[-2].selected` is empty / undefined. The
  loader does not pre-validate this — it surfaces as a per-op
  failure in `ApplyScriptReport`.

---

## Replay semantics

Loading a script does:

```ts
record.history.length = 0
record.redoStack.length = 0
await record.reload()                // restore from rawData
await record.dispatch(operations.map(op => [op.method, ...op.args]))
```

`dispatch` (already implemented) iterates the array, routing each
entry through `dispatchFilter` or `dispatchAction` based on whether
the method is in `EnumFilterOperations`.

There is no per-method arg-expansion step at the loader. The
selection-coupled ops (`DELETE_POINTS`, `INTERPOLATE`,
`SHIFT_DATETIMES`, `DRIFT_CORRECTION`, plus the existing
`CHANGE_VALUES` / `ASSIGN_*_BULK` trio) all read indices off
`history[length - 2].selected` themselves, inside the
`*FromSelection` dispatch wrappers in
[`observation-record.ts`](../src/utils/plotting/observation-record.ts).
Replay just walks the operation list in order — when one of these
ops runs, the preceding SELECTION is already in history because the
script preserves the original ordering.

---

## Save / load API

### Save

```ts
function serializeHistory(
  record: ObservationRecord,
  window: { startDate: Date | string; endDate: Date | string }
): QcScript
```

- Walks `record.history`, applies the per-method elide rules, returns
  a `QcScript` object (matches the JSON schema above).
- Window dates are taken from the consumer because qc-utils itself
  has no notion of a "viewed time range" — only the consumer (the
  Vue layer with the date pickers / time-range chips) knows what
  window the technician was working in.

### Load

```ts
function parseScript(json: unknown): QcScript                       // throws on schema violation
async function applyScript(
  record: ObservationRecord,
  script: QcScript
): Promise<ApplyScriptReport>

interface ApplyScriptReport {
  applied: number
  failed: Array<{ index: number; method: string; error: string }>
}
```

- `parseScript` validates `version`, the array shape, and per-method
  arg arity. It does NOT validate that indices fit the current
  dataset — that's deferred to the dispatch handlers, which already
  bail on out-of-range arguments.
- `applyScript` assumes the consumer has already loaded the script's
  data window into the record (see "Load workflow" below). It clears
  history + redo, then dispatches the operations in order. Per-op
  failures are caught, marked on the resulting `HistoryItem` as
  `execution.status === "failed"`, and surfaced in the returned
  report — they never abort the remainder of the replay.

### Load workflow

`applyScript` is data-agnostic; the consumer drives the data fetch.
The full Vue-side flow:

```ts
async function importScript(file: File) {
  const json = JSON.parse(await file.text())
  const script = parseScript(json)
  // Fetch the script's window into the active record before replaying.
  // The data store call below may differ per consumer (REST, WebSocket,
  // local file) — keeping it outside qc-utils means the same script
  // format works for any of them.
  await observationStore.fetchObservationsInRange({
    datastreamId: qcDatastream.value.id,
    begin: script.window.startDate,
    end:   script.window.endDate,
  })
  const report = await applyScript(selectedSeries.value.data, script)
  if (report.failed.length) {
    Snackbar.warn(
      `${report.applied} operations applied; ${report.failed.length} failed (see history).`
    )
  }
}
```

The consumer is responsible for two things qc-utils can't do:

1. **Targeting** — picking which datastream the script applies to.
   No id-matching is enforced; the user (or the calling code) decides.
2. **Window provisioning** — fetching the `script.window` data range
   into the `ObservationRecord` before `applyScript`. Operations that
   reference indices are valid only against this window's shape, so
   the fetch is non-negotiable. If the target datastream has fewer
   points in that window than the script expects, individual ops
   fail and are reported in `ApplyScriptReport.failed`.

### Vue composable surface

`useQcScript` (in `hydroserver-qc-app/src/composables/`) wires the
above to file pickers / download links:

```ts
export function useQcScript() {
  const { selectedSeries } = storeToRefs(usePlotlyStore())
  const { beginDate, endDate } = storeToRefs(useDataVisStore())
  const observationStore = useObservationStore()

  async function exportScript(): Promise<void> {
    /* serialize with current window → blob → download */
  }

  async function importScript(file: File): Promise<ApplyScriptReport> {
    /* read → parseScript → fetch window → applyScript → return report */
  }

  return { exportScript, importScript }
}
```

---

## Failed-operation handling

Operations that throw during dispatch (whether at author time or
during a script replay) indicate failure through
`HistoryItem.execution.status`:

1. In `dispatchAction` and `dispatchFilter`'s `catch` blocks, set
   `stored.execution.status = "failed"` and `inFlight = false`.
2. Round-trip `execution.status` through `serializeHistory` /
   `parseScript` so a script saved with failed steps loads back
   with those steps still marked failed (no silent re-success on
   reload).
3. Surface the badge in `EditHistory.vue` — a small red `mdi-alert`
   chip next to the entry's duration.

`ApplyScriptReport.failed` is the programmatic surface for the same
information; the UI consumes it for the post-load Snackbar but the
authoritative state lives on the entries themselves.

---

## Versioning & migration

The single `version: "1"` string is the migration anchor. Future
changes:

- **Additive** (new optional fields, new methods): bump to `"1.x"`,
  loaders for `"1"` skip unknown fields and operations they don't
  recognize, with a warning.
- **Breaking** (changed arg shape for an existing method, removed
  field): bump to `"2"`. Loaders for `"1"` and `"2"` co-exist;
  `parseScript` dispatches on `version` to the right parser.

Don't reuse method names with different arg shapes inside a major
version. If `FILL_GAPS`'s argument list changes, either accept both
shapes during a deprecation window or rename the method
(`FILL_GAPS_V2`).
