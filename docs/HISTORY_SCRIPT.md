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
   produced." Derived data (selection indices, per-entry timing) is
   recomputed on replay; only inputs and per-op success/failure are
   persisted.

## Non-goals

- **Persisting the underlying observations.** The script applies to
  whatever raw data the consumer hands the `ObservationRecord` at
  load time. If the data changed shape (different point count, gaps
  appearing/disappearing) the script may not produce the same edited
  result — that's the consumer's concern, not the format's.
- **Persisting Plotly view state.** Zoom, pan, tooltips, legend
  toggles are display state, not QC operations.
- **Persisting qualifiers in this version.** Result-qualifier flags
  (the per-index "missing" / "estimated" / etc. codes the Qualifying
  Comments panel attaches) are tracked in a separate Pinia store
  outside `ObservationRecord.history`. They need their own
  serialization story; bundling them in here would conflate two
  conceptually distinct edit streams. **(Open question — see below.)**

---

## Why a script and not a snapshot

We could persist the edited `(dataX, dataY)` pair directly. We
already do that for the server submit path (`useQcSubmission`). But
that throws away the *reasoning*:

- A reviewer can't see *why* a value changed.
- A user can't tweak a threshold without redoing every downstream
  edit by hand.
- The server can't validate that the edits came from documented
  operations rather than ad-hoc writes.

A script-style record keeps the operation graph intact. The edited
data is always recomputable from `rawData + script.operations`.

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
    { "method": "VALUE_THRESHOLD", "args": [{ "Greater than": 100 }] },
    { "method": "DELETE_POINTS",   "args": [] },
    { "method": "FILL_GAPS",       "args": [[15, "m"], [5, "m"], true, -9999] },
    { "method": "ADD_POINTS",      "args": [[[1737000000000, 12.4], [1737003600000, 12.5]]] }
  ]
}
```

### Top-level fields

| Field        | Type     | Required | Notes                                                                 |
|--------------|----------|----------|-----------------------------------------------------------------------|
| `version`    | string   | yes      | `"1"` for the current schema. Loaders reject unknown versions.        |
| `createdAt`  | ISO-8601 | yes      | When the script was saved. Used for sorting and audit display.        |
| `window`     | object   | yes      | The date range the script was authored against. The loader fetches this exact window before replaying. |
| `window.startDate` | ISO-8601 | yes | Inclusive lower bound of the data window.                          |
| `window.endDate`   | ISO-8601 | yes | Inclusive upper bound of the data window.                          |
| `operations` | object[] | yes      | The replayable operation list (see below).                            |

**Why a `window` instead of "the full extent."** Real-world QC is
incremental: a technician QCs January data this month, more data
arrives, next month they QC February against the same datastream.
Each session produces its own script bound to its own window. When
the same script is loaded later (or layered on top of other
scripts), the loader knows exactly which slice of data the
operations were authored against — operations that reference
positional indices remain valid as long as the windowed dataset has
the same shape.

### Per-operation entry

| Field    | Type    | Required | Notes                                                              |
|----------|---------|----------|--------------------------------------------------------------------|
| `method` | string  | yes      | `EnumEditOperations` or `EnumFilterOperations` value (e.g. `"VALUE_THRESHOLD"`, `"FILL_GAPS"`). |
| `args`   | any[]   | yes      | Positional args forwarded to the operation handler. Per-method shape rules below. |
| `status` | string  | no       | `"failed"` if the operation threw at author-time, omitted otherwise. Round-tripped on save/load so failed steps stay visibly failed. |

The shape mirrors `ObservationRecord.dispatch`'s tuple form:
`[method, ...args]`. A loaded script is replayed via
`record.dispatch(operations.map(o => [o.method, ...o.args]))`.

---

## Per-method serialization rules

The runtime `HistoryItem` carries fields the script doesn't need:
`isLoading`, `duration`, `executionMode`, `selected`. These are all
either ephemeral (loading state, timing) or recomputable on replay
(`selected`). The script saves only `method`, `args`, and the
optional `status` field (used to round-trip author-time failures).

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

| Method                  | `args` shape                                                                                        | Reads `history[-2].selected` at runtime? |
|-------------------------|-----------------------------------------------------------------------------------------------------|------------------------------------------|
| `VALUE_THRESHOLD`       | `[{ "Greater than": number, ... }]`                                                                 | No                                       |
| `DATETIME_RANGE`        | `[fromTs?, toTs?]`                                                                                  | No                                       |
| `CHANGE`                | `[comparator, value]`                                                                               | No                                       |
| `RATE_OF_CHANGE`        | `[comparator, value]` — value is a fraction (0.5 = 50%)                                             | No                                       |
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
`history[length - 2].selected` and delegates to the underlying
worker-fan-out implementation (`_deleteDataPoints`, `_shift`, etc.).
The internal implementations keep their explicit-indices signatures
so that ops which call each other directly (`_assignDatetimesBulk`
chains `_deleteDataPoints` + `_addDataPoints`, `_shift` calls
`_deleteDataPoints` + `_addDataPoints`) can pass locally-computed
indices without going through history.

`DRIFT_CORRECTION`'s wrapper additionally partitions the selection
into consecutive groups via `_getConsecutiveGroups` and applies the
same `value` drift to each group. The internal `_driftCorrection`
retains its per-range `[start, end, value]` signature for any future
caller that needs distinct per-range values.

The `consumesPrecedingSelection` predicate in
[`observation-record.ts`](../src/utils/plotting/observation-record.ts)
is a separate, history-cleanup signal — it controls whether
`dispatchAction` drops a preceding SELECTION when a non-consuming
op (`ADD_POINTS`, `FILL_GAPS`) commits. That predicate is purely
about UI history hygiene; it doesn't influence the script format.

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
the method is in `EnumFilterOperations`. The `_isReplaying` flag is
**not** set during script load — these aren't undo/redo internals,
they're authoritative new dispatches. (The redo stack should be
cleared by a fresh load anyway.)

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
- Pure function — no Plotly, no Pinia. Trivially testable.
- The consumer wraps the return value in a `Blob` and triggers a
  download via `URL.createObjectURL` + a hidden `<a>` click. That
  glue lives in the Vue side (proposed: `useQcScript` composable).

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
  failures are caught, marked on the resulting `HistoryItem` with
  `status: "failed"`, and surfaced in the returned report — they
  never abort the remainder of the replay.

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

## Decisions

The questions raised in earlier drafts of this doc have been
resolved:

| Question                     | Decision                                                                                                                                                       |
|------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Datastream id matching       | **No enforcement, no field.** `datastreamId` is removed from the schema entirely — scripts are reusable across datastreams (template-able QC procedures). The consumer picks the target. |
| Qualifier state              | **Out of scope for v1.** The qualifier Pinia store has its own serialization story; bundling them here would conflate two distinct edit streams. Future schema can add a `qualifiers` field additively without bumping the major version. |
| Partial replay on failure    | **Continue.** `applyScript` catches per-op errors, marks the resulting `HistoryItem` with `status: "failed"`, and includes the failure in the returned `ApplyScriptReport`. The user sees both the failed step (badge in EditHistory UI) and the steps that did apply. |
| UI placement                 | **EditHistory header.** Save / Load buttons go alongside undo / redo / pop-out — co-located with the history they act on, no crowding the plot toolbar. |

## Failed-operation handling

Operations that throw during dispatch (whether at author time or
during a script replay) currently log to the console and otherwise
leave no trace — `HistoryItem.status` exists in the type but isn't
written. Shipping the save/load feature requires that change to land
first:

1. In `dispatchAction` and `dispatchFilter`'s `catch` blocks, set
   `stored.status = "failed"` on the `HistoryItem` (keeping the
   existing `console.log` for dev visibility).
2. Round-trip `status` through `serializeHistory` / `parseScript` so
   a script saved with failed steps loads back with those steps still
   marked failed (no silent re-success on reload).
3. Surface the badge in `EditHistory.vue` — a small red `mdi-alert`
   chip next to the entry's duration would be enough.

`ApplyScriptReport.failed` is the programmatic surface for the same
information; the UI consumes it for the post-load Snackbar but the
authoritative state lives on the entries themselves.

---

## Implementation plan

In dependency order. Each step is independently mergeable.

1. **`qc-utils/src/utils/plotting/observation-record.ts`** — set
   `stored.status = "failed"` in both dispatch `catch` blocks. Pure
   prerequisite for steps 2+ to round-trip failure state. No
   behavioral change to the success path.

2. **`hydroserver-qc-app/src/components/EditData/EditHistory.vue`** —
   render a small failure badge for entries with `status === "failed"`.
   Cosmetic; ships independently of save/load.

3. **`qc-utils/src/types/index.ts`** — add `QcScript`,
   `QcScriptOperation`, `QcScriptWindow`, `ApplyScriptReport` types.
   Pure type additions, no behavior.

4. **`qc-utils/src/utils/plotting/script.ts`** — new file containing:
   - `serializeHistory(record, window)`: walks `record.history`,
     strips runtime-only fields (`isLoading`, `duration`,
     `executionMode`, `selected`), returns a `QcScript`.
   - `parseScript(json)`: validation + parsing.
   - `applyScript(record, script)`: top-level load. Resets history /
     redo, calls `record.reload()`, then
     `record.dispatch(operations.map(o => [o.method, ...o.args]))`.
     Catches per-op failures, marks them with `status: "failed"`,
     returns `ApplyScriptReport`.
   - **No** per-method serialize/expand helpers — args round-trip
     verbatim.

5. **`qc-utils/src/utils/plotting/__tests__/script.spec.ts`** —
   round-trip tests: build a history with selection-coupled and
   independent ops (plus one deliberately-failing op), save, load,
   assert the dataset matches AND the failed entry comes back with
   `status: "failed"`. The selection-coupled ops are the
   highest-risk regression surface (they require a preceding
   SELECTION at replay) so each gets its own case.

6. **`hydroserver-qc-app/src/composables/useQcScript.ts`** — Vue
   wrapper: file picker via `<input type="file">`, blob download via
   `URL.createObjectURL`. Reads the active window from the data-vis
   store, calls `serializeHistory` / `applyScript` from qc-utils.
   Owns the window-fetch step on load (calls
   `observationStore.fetchObservationsInRange` before dispatch).

7. **`hydroserver-qc-app/src/components/EditData/EditHistory.vue`** —
   add Save / Load buttons to the header (icons:
   `mdi-tray-arrow-down` / `mdi-tray-arrow-up`). Hook to
   `useQcScript`. Show a Snackbar after load summarizing
   applied/failed counts.

8. **`hydroserver-qc-app/e2e/qc-script.spec.ts`** — full round-trip
   e2e: apply some operations (including one that will fail on
   replay), save, refresh page, load, assert history matches, plot
   data matches the successfully-applied subset, failed entry shows
   the badge.

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
