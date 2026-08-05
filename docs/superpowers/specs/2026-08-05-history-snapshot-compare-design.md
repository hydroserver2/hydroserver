# History snapshot compare

Plot the state of a QC session at any point in its operation history as a
separate line on the current plot, so a user editing a session can compare
against the same data at another point in history.

## Motivation

The editor can already *view* a past session, but viewing replaces the QC
series and flips the editor read-only. There is no way to see two points in
history side by side. This adds a second, read-only line rather than swapping
the working one.

## Definitions

A **snapshot** is a frozen `GraphSeries` holding the `ObservationRecord`
produced by replaying a session's operations up to a chosen point, computed
over that session's own window.

- `opIndex = -1` is the baseline: the state the session started from, before
  any of its own operations. This is the "Data loaded" row in `EditHistory`.
- `opIndex = k` is the state after operation `k`.

## Base and replay

Reuses the existing reconstruct services rather than a parallel
implementation.

| Session status | Base | Replayed |
| --- | --- | --- |
| Committed | `reconstructCommittedSession`: raw source over the union of the ancestor chain's windows | ancestors in `committedAt` order, then the target session's operations `0..k` |
| In progress | `loadLatestBase(managed, source)` | the live record's `history[0..k]` |

`reconstructCommittedSession` gains an optional `opLimit` parameter that
truncates the target session's own operations, so the committed path reuses it
rather than duplicating the ancestor-chain logic.

Reading the in-progress session's operations from the live record rather than
from the server means unsaved draft edits are included. That matches what a
user expects when comparing against work they are currently doing.

The window is the session chain's own window, never the plot's current time
range. `reconstructCommittedSession` already loads the union of the chain's
windows because operations replay against array indices, so a narrower base
misaligns a wider ancestor. Recomputing a snapshot over an arbitrary user
window would therefore corrupt the replay.

Consequence: a snapshot is **frozen at creation**. It is never refetched, and
changing the plot's time range does not recompute it. It spans only its
session's window; zooming outside that window shows no line there.

## Record isolation

`useObservationStore.fetchObservationsInRange` keeps one `ObservationRecord`
per datastream id and hands back the same instance. The reconstruct services
replay operations onto whatever their injected `fetchInRange` returns, so
building a snapshot through the store's fetcher would mutate the record the
plot is already using, and a second snapshot built from the same source would
clobber the first.

Snapshots therefore inject a **detached fetcher** with the same
`FetchObservationsInRange` signature:

```ts
async function fetchDetached(ds, start, end) {
  await fetchObservationsInRange(ds, start, end) // warm the raw cache
  const raw = observationsRaw.value[ds.id] ?? { datetimes: [], dataValues: [] }
  const record = new ObservationRecord(raw)
  await record.applyWindow(start.getTime(), end.getTime())
  return record
}
```

This is safe because `ObservationRecord`'s constructor copies into its own
`dataset.source` buffers and treats `rawData` as read-only; operations mutate
only `dataset.source`. The reconstruct services need no change to accept it.

A detached record does share the `rawData` *object* with the store, so a later
store fetch that widens the raw cache is visible to it. That only matters to a
record that calls `reload()`, which a frozen snapshot never does.

## Identity and store shape

Snapshots get the synthetic id `snap:<sessionId>:<opIndex>` and a synthetic
`Datastream`-shaped object pushed into `plottedDatastreams`. Legend rendering,
colour assignment, the eye toggle, drag reorder, and removal then work
unchanged instead of growing a parallel code path.

Four guards, each keyed off a single `isSnapshotId()` predicate:

1. `refreshGraphSeriesArray` skips the fetch for snapshot ids and keeps the
   existing series. This is what makes a snapshot frozen.
2. `releaseManagedDatastream` drops every snapshot when the editor closes.
   The QC target is chosen from the Select view, which lists real
   datastreams; a snapshot must never appear there.
3. Snapshots are excluded from the `ds` share key (see below).
4. A snapshot id is never sent to any server call.

`GraphSeries` gains:

```ts
snapshot?: {
  sessionId: string
  sessionLabel: string
  opIndex: number
  opCount: number
  opName: string
  performedBy?: string
  createdAt: string
}
```

## Y axis

Snapshots get their own axis, exactly like any other non-QC series. Being
able to shift a snapshot on its own axis is how the user lines it up against
the QC target, which is the point of plotting it. No axis is shared except
the x axis, which every series shares.

This means no change to `createPlotlyOption`'s axis assignment, and the
per-row axis-toggle button works on snapshot rows like any other.

## UI

### EditHistory

An add-to-plot icon button on each operation row and on the "Data loaded"
baseline row. It toggles: when that exact snapshot is already plotted, the
button removes it.

### PlottedDatastreams

Snapshot rows carry an `mdi-history` icon and a "snapshot" chip so they never
read as a live datastream:

```
[history icon] [snapshot] Session Mar 2024
                          step 3 of 7: Fill Gaps - by Alice - Mar 14 2026
```

Baseline rows read `session start - Mar 14 2026`.

Line colour comes from the existing per-series assigner. No dashed line and no
hover tooltip: the colour already distinguishes lines, and building tooltip
content per row is not worth the cost.

## Share URL

A new `snap` key rather than folding snapshots into `ds`:

```
snap=a1b2:3,a1b2:-1
```

Keeping it separate preserves both invariants the encoder relies on: the QC
target is the first id in `ds`, and the `h` / `ya` bitmasks are indexed by
position in `ds`.

On hydration, snapshots are replayed after `loadSessions` has run and are
appended after the real datastreams. A snapshot whose session no longer exists
is dropped silently rather than failing the whole hydration.

## Testing

Unit:

- snapshot builder: truncation at `k`, baseline at `-1`, committed versus
  in-progress base selection
- share encode/decode round trip for the `snap` key
- `refreshGraphSeriesArray` exemption: a snapshot series survives a refresh
  and is not fetched

Component:

- `EditHistory`: the add-to-plot button appears on operation rows and on the
  baseline row, and toggles a plotted snapshot off
- `PlottedDatastreams`: a snapshot row renders its provenance line, and the
  QC-target and axis-toggle buttons are suppressed

## Reload-from-step, fixed alongside

Stepping through a committed session's history restored the pre-replay
entries wholesale, which put the *old* timings back over the ones the replay
had just measured. Only the "Data loaded" row updated, because its time comes
from `record.loadingTime`.

The panel now keeps the replayed entries as the replay left them and appends
only the ones it dropped, recomputing the shown-step marker from the actual
replayed length (a replay can drop a preceding `SELECTION`). `isApplied()`
hides execution data for steps past the one on screen, since those did not run
in this view.

The "Data loaded" row is step `-1` and reloads to it, so a session's starting
state is reachable the same way any operation is. It carries the "Showing"
chip when it is the step on screen. Its reload-from-server button moved to a
cloud icon so the two reloads are not two identical glyphs doing different
things: one replays, the other refetches and drops the history.

`hasUnsavedChanges` / `unsavedEditCount` now return false / 0 while a
committed session is being viewed. They compare history entries by identity,
so a replay that swaps entries used to read as pending edits and prompted
"You have unsaved edits" on a read-only view. A committed session cannot be
edited, so the invariant belongs in the computed rather than being worked
around by preserving object identity.

## Out of scope

- No cap on the number of simultaneous snapshots. Each costs a base fetch plus
  a replay, so several at once over a wide window will be slow. Left visible
  rather than guessing where a limit belongs.
- Expanding a session still loads it (view mode). Decoupling expansion from
  viewing was considered and rejected as a separate concern; users already
  navigate back with "Return to current", and the snapshot survives that
  round trip.
