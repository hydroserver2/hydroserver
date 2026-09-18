# APIs &amp; Interoperability

This is a reference for the surfaces a developer integrates against:
both the in-app TypeScript surfaces (Pinia stores, composables, plotting
utils) and the external HydroServer REST endpoints the app consumes.

## Design principles

- **No app-specific API.** The QC App is a client of HydroServer; it
  does not expose its own REST surface. Interop happens at three layers:
  the `@hydroserver/client` REST client, the `@uwrl/qc-utils` QC engine,
  and the QC History JSON file format.
- **JSON over the wire, typed arrays in memory.** The app fetches
  observations in HydroServer's columnar JSON format and inflates them
  to `Float64Array` + `Float32Array` inside `ObservationRecord`.
- **History is the contract.** The QC History file format is the
  durable record of edits. It is not pinned to a datastream id, so the
  same script can be replayed against many datastreams.
- **Auth lives on the backend.** Cookies + Django AllAuth. The app
  holds no secrets and emits no service-to-service tokens.

## External: HydroServer REST API

The app talks to a HydroServer instance via the `@hydroserver/client`
package. QC uses the current origin's `/api` route so it shares the
Data Management app's authenticated session. Endpoint groups used:

| Group              | Base path                              | Purpose                                             |
|--------------------|----------------------------------------|-----------------------------------------------------|
| Session / auth     | `/auth/browser/session`                | Current session and logout. Login is handled by Data Management. |
| Account            | `/auth/browser/account`                | Current user profile.                               |
| Workspaces         | `/data/workspaces`                     | List, pick, create workspaces.                      |
| Things (sites)     | `/data/things`                         | Sites the operator can browse.                      |
| Datastreams        | `/data/datastreams`                    | List + fetch metadata + observations + bulk replace.|
| Observations       | `/data/datastreams/{id}/observations`  | Paged columnar read, bulk POST with `mode=replace`. |
| Result qualifiers  | `/data/result-qualifiers`              | Qualifier code lookups per workspace.               |
| Observed props / processing levels / units / sensors | `/data/observed-properties`, `/data/processing-levels`, `/data/units`, `/data/sensors` | Filter taxonomy. |

The QC App uses `@hydroserver/client` for these endpoints; the legacy
qc-utils service layer lives under `packages/qc-utils/src/services/`.

### Standards support

- **REST + JSON over HTTPS.** Authentication is session cookies issued by
  the HydroServer backend; CSRF tokens are read from the same domain.
- **HydroServer columnar response format** is the preferred shape for
  observation fetches (`format=column`). It returns parallel
  `phenomenonTime[]` + `result[]` arrays and is dramatically faster than
  the row-oriented response. The QC App can decode both, but uses column
  format end-to-end today (see `src/utils/observations.ts:33`).
- **No OData, no GraphQL, no OGC SensorThings.** Bridging to those
  standards is a HydroServer-backend concern; the QC App will inherit
  whatever HydroServer exposes.
- **Login / OAuth.** Delegated to the HydroServer Data Management app.

### Observation read

Paged GET against `/data/datastreams/{id}/observations` with
`format=column`, `order_by=phenomenonTime`, `page_size=50000`, and
`phenomenon_time_min` / `phenomenon_time_max` ISO-8601 bounds. The app
paginates client-side and caches the merged window in
`useObservationStore`.

### Observation write (QC submission)

```ts
hs.datastreams.createObservations(
  datastream.id,
  {
    fields: ['phenomenonTime', 'result'],
    data: dataX.map((ts, i) => [new Date(ts).toISOString(), dataY[i]]),
  },
  { mode: 'replace' }
)
```

Replace mode tells HydroServer to overwrite any observation inside the
posted window. The QC App always submits the full edited window;
incremental submission is not implemented today.

### Result qualifier codes

Listed via `fetchWorkspaceResultQualifiers`. The QC App tracks selected
qualifiers in `store/qualifiers.ts`, but **does not yet serialize them on
commit** (see [QUALITY.md](./QUALITY.md) tech-debt section and the note
in `services/qualityControl/observationsBody.ts`).

## Internal: composables

Composables are the public hook surface for components. They wrap stores
+ qc-utils with the orchestration each flow needs.

### `useFilterDispatch()`

```ts
const { runFilter } = useFilterDispatch()
await runFilter(EnumFilterOperations.VALUE_THRESHOLD, [{ 'Greater than': 100 }])
```

- Calls `selectedSeries.data.dispatchFilter(...)` on the QC datastream.
- Appends a `HistoryItem` to the edit history.
- Highlights the resulting selection on the plot.
- Surfaces Snackbar errors on failure.

### `useDataSelection()`

Bridges Plotly's `plotly_selected` events to the qc-utils dispatch.

```ts
const { setSelected, clearSelected } = useDataSelection()
await setSelected([0, 1, 2, 5])      // dispatches SELECTION
await clearSelected({ recordHistory: false })  // skip history append on cleanup
```

### `useEditEntry()`

```ts
const { enterEdit, startSessionOver, leaveEdit } = useEditEntry()

const result = await enterEdit(managedId, window)
// result: 'editing' | 'needs-window' | 'not-managed' | 'superseded'
```

Sets the edit target and switches to the Edit view. Shared by the row Edit
flow (`StartEditingFlow.vue`), reload resume (`useResumeEditSession()`
below), and share-link hydration (the `ed` query param).

- `enterEdit(managedId, window?)`: sets the edit target
  (`setEditTarget`), resolves its QC history via `beginEditing()`, and
  resumes an in-progress session. With no session and no `window`, returns
  `'needs-window'` so the caller opens `SessionWindowDialog.vue` (the
  session-window step) and calls back in with the chosen window, or calls
  `startSessionOver` instead; with a `window`, starts the session
  immediately.
- `startSessionOver(window)`: starts a new session on the current edit
  target over `window` (a `utils/timeRangePresets.ts` `TimeWindow`); backs
  **Start new session** and the editor footer's **New session**.
- `leaveEdit()`: returns to the Select view, clears the resume pointer and
  the edit target (`clearEditTarget`). Every exit uses it, including the nav
  rail's Home and Workspaces buttons, so a reload never reopens an editor the
  user left.

Entries can overlap (a reload resume and a click land close together);
whichever call sets the edit target last owns the view: a call that finds
the target changed after an `await` stands down without touching view
state, the target, or the resume pointer.

### `useResumeEditSession()`

```ts
const { resume } = useResumeEditSession(async (id) => {
  await startEditing.value?.resume(id) // StartEditingFlow
})
```

Reopens the editor after a page reload, using the persisted
`qcSession.resumeDatastreamId`: waits for the workspace catalog to arrive
(it's empty at mount), then calls the supplied callback with the managed
datastream id (normally wired to `StartEditingFlow`'s exposed `resume`, which
enters through `useEditEntry()` and opens the session-window step when there
is no session to continue). Resumes at
most once. A pointer to a datastream missing from the catalog (deleted, or
another workspace) is dropped rather than retried.

Note the watcher must not use Vue's `once` together with `immediate`: the
immediate call fires on the initial empty catalog and stops the watcher, so
the resume would never run on the cold reload it exists for.

### `useUnsavedChangesWarning()`

```ts
useUnsavedChangesWarning(hasUnsavedChanges) // Ref<boolean>
```

Asks the browser for its native "leave site?" confirmation while the ref is
true, so a reload mid-session can't silently drop edits that never reached
the server. Registers on mount and removes the listener on unmount. Browsers
ignore any custom message and only honour the prompt once the user has
interacted with the page.

### `useQcHistory()`

```ts
const { exportHistory, importHistory } = useQcHistory()

await exportHistory()             // downloads qc-history-<datastream>-<isoTimestamp>.json
const report = await importHistory(file)
// report = { applied: 12, failed: [{ index, method, error }, ...] }
```

`exportHistory` reads the current wall-clock window from
`useDataVisStore`. `importHistory` fetches the script's authored window
into the active datastream **before** replay (selection-coupled ops
reference indices against this windowed dataset).

### `useEditSession()`

Orchestrates the server-backed QC session workflow against the
`services/qualityControl/` glue:

```ts
const {
  beginEditing, startSession, saveDraft, discardUnsavedEdits, commit,
  needsSession, needsHistory, hasUnsavedChanges, unsavedEditCount,
} = useEditSession()
```

- `beginEditing()`: resolves the QC history for the QC datastream, loads
  its sessions, resumes the in-progress one (or sets `needsSession`); sets
  `needsHistory` when the datastream isn't QC-managed yet. Resuming rebuilds
  the shared working copy; if that rebuild is superseded it throws
  `ResumeSupersededError`, leaves `needsSession` false, and `enterEdit`
  returns to the Select view. Entries can overlap, so it also throws
  `ResumeSupersededError` when the edit target changes during any of its
  fetches, and it never writes the session store (source, sessions) for a
  target it no longer owns: sessions are fetched with `fetchSessions` and
  applied only while still the owner.
- `startSession(spec)`: creates a session and copies the source window in.
  When the history already has an in-progress session it resumes that one
  through the same replay instead (throwing `ResumeSupersededError` the same
  way), so saved draft operations are never dropped. The same ownership rule
  guards its session reload.
- `saveDraft()`: persists the record's edit operations to the session
  (append-only reconcile).
- `discardUnsavedEdits()`: drops edits made since the last save and restores
  edited comments.
- `commit()`: saves, verifies checksum C, pushes observations
  (`mode: 'replace'`), then locks the session and reloads the sessions. If
  another target took over the editor while they reloaded, it leaves the
  session store and the saved-edits baseline alone and still resolves, since
  the commit itself went through.
- `hasUnsavedChanges` / `unsavedEditCount`: the working copy compared with
  the saved-edits baseline (`qcSession.savedEdits` / `savedComments`). The
  baseline lives in the store, so every caller agrees: the editor footer and
  the nav rail's exit guard both read it.

### `useCreateManagedDatastream()`

```ts
const { create } = useCreateManagedDatastream()
const { managedDatastream, history } = await create({ source, processingLevelId, name })
```

Delegates to the tested `createManagedDatastream` orchestration with the
live client (`hs.datastreams` + `hs.qualityControlHistories`). The datastream
is created with `expand_related: true`, so `managedDatastream` comes back in
the same `Datastream & DatastreamExtended` shape as the `datastreams` catalog
and can be appended to it directly. Without the flag the 201 body is the flat
model (FK ids only) and catalog consumers reading `ds.processingLevel.id`
would break.

### `useManagedDatastreams()`

```ts
const { loadForSource } = useManagedDatastreams()
const options = await loadForSource(sourceDatastreamId)
// options: [{ historyId, managed, sessions }]
```

Resolves a source datastream's managed (QC) datastreams from the loaded QC
histories and fetches each one's sessions. Feeds the row Edit button's
chooser (`StartEditingFlow.vue`), which lists managed datastreams with their
in-progress/committed sessions.

### `useWorkspacePermissions()`

Synchronous, reactive role/permission checks for gating UI. The role
travels with the `Workspace` object (`collaboratorRole.permissions`; owners
have a null role; `accountType === 'admin'` overrides), so no separate
endpoint is needed.

```ts
const { canEdit, canCreateDatastream, roleName, isOwner, can } =
  useWorkspacePermissions()
canEdit()                 // selected workspace: can run the QC edit flow?
canCreateDatastream(ws)   // can create the managed datastream here?
roleName(ws)              // 'Owner' | <collaborator role> | 'Admin' | 'Read-only'
```

Used to disable the row Edit button, the editor's Save / Commit controls,
and the create-datastream form, and to mark each workspace's role on the
picker.

### `useResizable()`

Generic pointer-drag-resize hook. Used by `SelectDrawer`, `EditDrawer`,
and the plot's table-vs-chart splitter.

### `useBufferedNumber()`

Debounced numeric input wrapper for filter panels. Avoids dispatching
on every keystroke when a user is typing a threshold.

## Internal: Pinia stores

Each store is a `defineStore('id', () => ...)` factory. Import via the
matching `useXxxStore()` and destructure with `storeToRefs` to keep refs
reactive.

Columns in the per-store tables:

- **Kind**: `state` (a `ref`), `computed` (a `ComputedRef`), or
  `action` (a method).
- **Type / signature**: the runtime shape consumers see. Refs list the
  `T` inside `Ref<T>`; actions list the call signature.

The "Persistence" line at the top of each store cites the
`pinia-plugin-persistedstate` config: the storage key and the
specific slice picked. Stores with no Persistence line are session-only.

### `useDataVisStore()` (`src/store/dataVisualization.ts`)

Catalog data (sites, datastreams, taxonomy), sidebar filters, plotted
set + edit target, time-range window. The orchestrator for everything in
the Select drawer and the rebuild pipeline that owns `rebuildPlot()`.

Persistence: `selectedDateBtnId` only (so the user's preset choice
survives reload); catalogs, filters, and in-flight maps refetch cleanly
on boot.

| Name                                | Kind     | Type / signature                                  | Notes |
|-------------------------------------|----------|---------------------------------------------------|-------|
| `things`                            | state    | `Thing[]`                                         | Sites in the active workspace; fetched once on workspace mount. |
| `datastreams`                       | state    | `(Datastream & DatastreamExtended)[]`             | All visible datastreams (with `expand_related` nested objects). |
| `qcHistories`                       | state    | `QualityControlHistory[]`                         | Workspace QC histories (each links a managed datastream to its source); loaded with the catalog. |
| `managedDatastreamIds`              | computed | `Set<string>`                                     | Ids of every managed (QC) datastream; hidden from the catalog (reached via the row Edit chooser). |
| `historiesBySource`                 | computed | `Map<string, QualityControlHistory[]>`            | `sourceDatastreamId` -> its QC histories; drives the row Edit chooser. |
| `addQcHistory`                      | action   | `(history: QualityControlHistory) => void`        | Register a newly-created history so its managed datastream hides from the catalog and shows in the chooser without a reload. |
| `removeManagedDatastream`           | action   | `(historyId: string, managedId: string) => void`  | Drop a deleted managed datastream + its history from local state (chooser/catalog) after deleting it server-side. |
| `replaceDatastream`                 | action   | `(ds: Datastream & DatastreamExtended) => void`   | Swap a fresh copy into the catalog and plotted set (used after a commit moves a managed datastream's phenomenon times). |
| `observedProperties`                | state    | `ObservedProperty[]`                              | Taxonomy for the filter chips. |
| `processingLevels`                  | state    | `ProcessingLevel[]`                               | Taxonomy for the filter chips. |
| `selectedThings`                    | state    | `Thing[]`                                         | Site filter selection (sidebar). |
| `selectedObservedPropertyNames`     | state    | `string[]`                                        | Observed-property filter selection. |
| `selectedProcessingLevelNames`      | state    | `string[]`                                        | Processing-level filter selection. |
| `filteredDatastreams`               | computed | `(Datastream & DatastreamExtended)[]`             | `datastreams` narrowed by the three filter selections, with managed (QC) datastreams excluded. |
| `plottedDatastreams`                | state    | `Datastream[]`                                    | Up to 5 streams the user chose to plot. Editing never adds to or removes from it (snapshots are the exception, dropped on leave); the 5-stream cap doesn't count the edit target or its source. |
| `qcDatastreamId`                    | state    | `string \| null`                                  | The edit target's id. Set only by the edit flow (`setEditTarget` / `clearEditTarget`); null in the Select view. |
| `qcDatastream`                      | computed | `Datastream \| null`                              | Live catalog lookup of `qcDatastreamId` in `datastreams`, not `plottedDatastreams`, since the edit target isn't a plotted entry. |
| `sourceContextDatastream`           | computed | `Datastream \| null`                              | The edit target's catalog source, resolved through `qcHistories`; null without an edit target. Drawn behind the edit target as context. |
| `seriesDatastreams`                 | computed | `Datastream[]`                                    | What the plot actually draws, in order: `[edit target, its source, ...plotted minus those]` while editing, otherwise `plottedDatastreams` unchanged. Refresh, colour assignment, series ordering, working-copy invalidation, `PlottedDatastreams`, the share watcher, and snapshots all iterate this instead of `plottedDatastreams`. |
| `qualifierSet`                      | state    | `Set<string>`                                     | Qualifier codes seen on the edit target's loaded points. |
| `selectedQualifier`                 | state    | `string`                                          | Active qualifier in the picker. |
| `selectedData`                      | state    | `number[] \| null`                                | Index list of the active selection (lasso, box, click). |
| `hasSelectionShape`                 | state    | `boolean`                                         | True while a box/lasso shape exists, even when it captured zero points. |
| `loadingStates`                     | state    | `Map<string, boolean>`                            | Per-datastream in-flight observation fetches. Only the latest request for a datastream clears its flag. |
| `isEditorReady`                     | computed | `boolean`                                         | True while editing once the session window is known, the edit record is on the plot, no session is opening (`isSwitchingSession`), and no plot work is pending: no queued or running plot load (including the context re-anchor around the session window) and no tracked draw. Bound to `data-editor-ready` on the edit view's `edit-plot-column`; e2e `waitForEditorReady` waits on it. |
| `trackPlotWork`                     | action   | `(work: () => Promise<void>) => Promise<void>`    | Run `work` counted as pending plot work for `isEditorReady`. Plot loads and `setEditRecord` use it, and `Plot.vue` counts its first draw from the moment the plot element appears. |
| `beginDate` / `endDate`             | state    | `Date`                                            | Active loaded window. A preset re-resolves it on every plot rebuild: around the edit session's window while one is set (`presetAroundWindow`), otherwise back from the context data's (`seriesDatastreams` minus the edit target) end (`presetWindow`). It also re-resolves when the edit session's window loads or changes. A custom range stays fixed. |
| `selectedDateBtnId`                 | state    | `number`                                          | Active preset id (default `1`, 1m); `-1` (`CUSTOM_PRESET_ID`) for a manual range. Presets are defined in `utils/timeRangePresets.ts`. |
| `matchesSelectedThing`              | action   | `(ds) => boolean`                                 | Filter predicate; exposed so the table can reuse it on row updates. |
| `matchesSelectedObservedProperty`   | action   | `(ds) => boolean`                                 | Same shape as above. |
| `matchesSelectedProcessingLevel`    | action   | `(ds) => boolean`                                 | Same shape as above. |
| `setDateRange`                      | action   | `({ begin?, end?, update?, custom? }) => Promise<void>` | No-ops when neither bound moves. Otherwise sets the bounds at once and queues a range reload as a plot load (see `rebuildPlot`), which joins a queued rebuild instead of loading on its own and is skipped when an earlier load already caught up with the range. While editing it reloads context only and preserves the zoom (`redraw(false, true)`), since the edit target's data isn't fetched here. Otherwise it clears zoom history and applies the new window. |
| `onDateBtnClick`                    | action   | `(id: number) => Promise<void>`                   | Selects the preset and applies the window the internal `resolvePresetWindow` gives it: around the edit session's window while editing one, otherwise back from the context data's end. With nothing to anchor to, only the selection changes. |
| `refreshGraphSeriesArray`           | action   | `() => Promise<unknown[]>`                        | Reconciles `graphSeriesArray` against `seriesDatastreams` (fetch deltas + reorder + recolor), skipping the edit target (its data is owned by the edit session, not this refresh). A managed datastream with a loaded working copy (`useWorkingCopiesStore`) uses it instead of fetching. Invalidates the working copy of any managed datastream no longer in `seriesDatastreams`, except the edit target. |
| `resetState`                        | action   | `() => void`                                      | Clears filters, the plotted set, and the edit target, and drops every working copy, on a workspace swap; preserves the preset preference. |
| `toggleDatastream`                  | action   | `(ds: Datastream) => Promise<void>`               | Plot if absent, unplot if present. |
| `plotDatastream`                    | action   | `(ds: Datastream) => Promise<void>`               | Add to plot. Plotting never picks or changes the edit target. |
| `unplotDatastream`                  | action   | `(id: string) => Promise<void>`                   | Remove from the plotted set. Never touches the edit target. |
| `clearPlottedDatastreams`           | action   | `() => Promise<void>`                             | Drop the entire plotted set. |
| `sourceGroupIds`                    | action   | `(sourceId: string) => string[]`                  | The source datastream plus every managed (QC) datastream derived from it. |
| `plotSourceSelection`               | action   | `(sourceId: string, ids: string[]) => Promise<void>` | Apply a whole "what to plot for this source" choice at once: `ids` is the complete set wanted from that source's group. Group members absent from `ids` are unplotted, additions are appended in `ids` order. One rebuild for the whole selection; never touches the edit target. |
| `addSnapshotSeries`                 | action   | `(id: string, record: ObservationRecord, meta: SnapshotMeta) => Promise<void>` | Add a frozen history snapshot as an extra comparison line under the synthetic id `snap:<sessionId>:<opIndex>`. Never touches the edit target; `refreshGraphSeriesArray` skips its fetch. |
| `removeSnapshotSeries`              | action   | `(id: string) => Promise<void>`                   | Drop one snapshot line. Leaves the edit target alone. |
| `setPlottedDatastreams`             | action   | `(items: Datastream[]) => Promise<void>`          | Replace the plotted set wholesale (used by URL hydration). Doesn't touch the edit target. Hydrate that separately with `setEditTarget`. |
| `setEditTarget`                     | action   | `(managedId: string) => Promise<void>`            | Begin editing `managedId`: drops snapshots, resets the `qcSession` store (not `resumeDatastreamId`) and clears zoom history when the target changes, sets `qcDatastreamId`, rebuilds the plot. Its data arrives later via `setEditRecord`. This action doesn't fetch it. |
| `setEditRecord`                     | action   | `(record: ObservationRecord) => Promise<void>`    | Put the edit target's record on the plot: updates its graph series in place if one exists, otherwise adds it (`buildGraphSeries`) and redraws. The only path by which the edit target's data reaches the plot. Counted as plot work until drawn. |
| `clearEditTarget`                   | action   | `() => Promise<void>`                             | Stop editing: drops snapshots, invalidates the edit target's working copy, clears `qcDatastreamId`, removes its graph series, and rebuilds. Plotted datastreams are left exactly as they were. |
| `rebuildPlot`                       | action   | `() => Promise<void>`                             | Rebuild (refresh series, regenerate options, render) as a plot load. Plot loads (rebuilds and `setDateRange` range reloads) run one at a time; requests made while one runs share one queued follow-up, which is a rebuild if any of them was, and every caller resolves only after a load that started after its change. A load whose range moves while it loads drops those responses and loads again before drawing. Drops zoom history in the Select view; keeps the zoom while an edit target is set. |

### `useWorkingCopiesStore()` (`src/store/workingCopies.ts`)

One working copy per managed datastream, keyed by its in-progress
session: the Select-view plot and the editor share it so the preview
shows exactly what editing opens. Not persisted, not reactive (records
hold large typed arrays that must not be proxied).

Concurrency: a per-managed-id generation counter, bumped by `invalidate`,
`set`, `clear`, and every new build, guards each build's cache write: a
build whose generation is no longer current is discarded rather than
resurrecting a stale copy. Concurrent `load()` calls for the same managed
id share one in-flight build and resolve to the same record, and a `load()`
that meets an in-flight `rebuild()` joins it instead of starting its own
build. A superseded `rebuild()` or `load()` never returns the record it
discarded: it resolves to the newer in-flight `rebuild()`'s result
(whichever fetch finishes first), otherwise to whatever is now cached
(`null` after `invalidate` or `clear`). `invalidate`, `set`, and `clear`
also drop the in-flight load they supersede, so the next `load()` starts
fresh.

| Name         | Kind   | Type / signature                                                                                     | Notes |
|--------------|--------|-------------------------------------------------------------------------------------------------------|-------|
| `get`        | action | `(managedId: string) => WorkingCopy \| undefined`                                                     | Current cached copy for a managed datastream, if any. |
| `load`       | action | `(managed: Datastream, source: Datastream, historyId: string) => Promise<WorkingCopy \| null>`        | Returns the cached copy when it matches the history's in-progress session; rebuilds and caches otherwise; `null` (and evicts any stale cache entry) when the history has no in-progress session. Concurrent calls for the same managed id dedupe onto one build, and a call made while a `rebuild()` is in flight joins it. If superseded mid-build, resolves to the superseding `rebuild()`'s result or the now-current cache entry (or `null`) instead of the discarded build. |
| `rebuild`    | action | `(managed: Datastream, source: Datastream, historyId: string, session: SessionWindow) => Promise<WorkingCopy \| null>` | Always reconstructs from the session window and replays its operations, even when a cached copy already matches; supersedes any in-flight `load()` build or earlier `rebuild()` for this managed id and overwrites the cache. If superseded itself while awaiting, never returns the discarded build: resolves to a later in-flight `rebuild()`'s result, or reads the cache after a synchronous `invalidate`/`set`/`clear`, which is `null` when nothing ended up cached. |
| `set`        | action | `(managedId: string, sessionId: string, record: ObservationRecord, begin: Date, end: Date) => void`   | Insert or replace a cache entry directly (used by `startSession` to store a new session's fresh base); supersedes any in-flight build or load for this managed id. |
| `invalidate` | action | `(managedId: string) => void`                                                                          | Drop a managed datastream's cached copy; supersedes any in-flight build or load for this managed id. |
| `clear`      | action | `() => void`                                                                                           | Drop every cached copy and supersede every in-flight build and load; called by `useDataVisStore().resetState()` on a workspace reset. |
| `extents`    | action | `(managedIds: string[]) => { phenomenonBeginTime: string; phenomenonEndTime: string }[]`               | The cached copies' windows for the given managed ids, in ISO form; ids with no cached copy are omitted. |

### `usePlotlyStore()` (`src/store/plotly.ts`)

Owns the Plotly DOM ref, the per-series array driving the chart,
viewport state (tooltips, crosshair, hover, zoom history), and the
redraw / restyle plumbing.

Persistence: `tooltipsMaxDataPoints`, `tooltipsMode`, and
`tooltipsManualEnabled` (key `qc.plot.tooltipsMaxDataPoints`): the
user's data-points-mode preference. Everything else is ephemeral (DOM
handles, live chart caches).

| Name                       | Kind     | Type / signature                                  | Notes |
|----------------------------|----------|---------------------------------------------------|-------|
| `graphSeriesArray`         | state    | `GraphSeries[]`                                   | Per-series state driving traces, colors, and axis chips. |
| `plotlyOptions`            | state    | `PlotlyChartOptions`                              | Cached `createPlotlyOption` output; seeded empty so consumers can read without null-guards. |
| `plotlyRef`                | state    | `AppPlotlyHTMLElement \| null`                    | Live Plotly DOM element; populated by `handleNewPlot`. |
| `mainPlotEpoch`            | state    | `number`                                          | Monotonic counter, bumped per `handleNewPlot` so listeners can re-attach. |
| `selectedSeriesIndex`      | computed | `number`                                          | Index of the edit target in `graphSeriesArray` (`-1` when none). |
| `selectedSeries`           | computed | `GraphSeries`                                     | Convenience for `graphSeriesArray[selectedSeriesIndex]`. |
| `editHistory`              | state    | `HistoryItem[]`                                   | Mirrors `selectedSeries.data.history` (mutated in place; never reassign). |
| `suppressedEchoSelection`  | state    | `number[] \| null`                                | Sentinel armed by programmatic Plotly writes to suppress the echo SELECTION dispatch. |
| `isUpdating`               | state    | `boolean`                                         | Surfaced in the nav rail while a redraw runs. |
| `showLegend`               | state    | `boolean`                                         | Drives Plotly's legend visibility. |
| `showTooltip`              | state    | `boolean`                                         | Legacy flag; tooltip control routes through the auto/manual mode below. |
| `tooltipsMaxDataPoints`    | state    | `number`                                          | Auto-mode cutoff (default 10 000); user-tunable from the data-points menu. |
| `visiblePoints`            | state    | `number`                                          | Live count of points inside the current X range. |
| `tooltipsMode`             | state    | `'manual' \| 'auto'`                              | Mode toggle: manual = user controls on/off; auto = threshold-driven. |
| `tooltipsManualEnabled`    | state    | `boolean`                                         | Manual-mode on/off state. |
| `areTooltipsEnabled`       | computed | `boolean`                                         | Resolved on/off accounting for mode + threshold. |
| `showCoordinates`          | state    | `boolean`                                         | Hover-coordinates chip visibility. |
| `hover`                    | state    | `{ x: number; y: number \| string }`              | Latest cursor-under-plot epoch + value. |
| `crosshair`                | state    | `{ visible, cursorX, cursorY, plotLeft, plotBottom }` | CSS-driven crosshair position. |
| `hiddenAxisIds`            | state    | `Set<string>`                                     | Datastream ids whose right-side y-axis chrome is hidden. |
| `hiddenTraceIds`           | state    | `Set<string>`                                     | Datastream ids whose trace is fully hidden (eye toggle). |
| `activeTab`                | state    | `'plot' \| 'table'`                               | Center-column tab; captured by the share URL. |
| `tableScrollRequest`       | state    | `{ time: number; seq: number } \| null`           | Set when the plot zooms to the session window; `DataTable` scrolls to the first row at/after `time`. `seq` re-triggers on repeats. |
| `requestTableScroll`       | action   | `(time: number) => void`                          | Publish a `tableScrollRequest` for the given epoch-ms range start (bumps `seq`). |
| `axisChips`                | state    | `AxisChip[]`                                      | Horizontal axis title chips (replaces Plotly's rotated titles). |
| `previewMode`              | state    | `boolean`                                         | Strips select/lasso/etc when the chart is rendered in the Select view's preview slot. |
| `zoomUndoStack`            | state    | `ZoomState[]`                                     | Captured viewports for the modebar's Undo zoom button. |
| `zoomRedoStack`            | state    | `ZoomState[]`                                     | Cleared on every new user-initiated zoom. |
| `suppressZoomHistory`      | state    | `boolean`                                         | Flipped on during programmatic restores so the recorder doesn't double-capture. |
| `pendingShareZoom`         | state    | `ZoomState \| null`                               | URL-hydrated zoom; applied once on mount then cleared. |
| `canUndoZoom`              | computed | `boolean`                                         | `zoomUndoStack.length > 1`. |
| `canRedoZoom`              | computed | `boolean`                                         | `zoomRedoStack.length > 0`. |
| `currentZoom`              | computed | `ZoomState \| null`                               | Top of the undo stack; what the share URL writer subscribes to. |
| `updateOptions`            | action   | `() => void`                                      | Rebuild `plotlyOptions` from `graphSeriesArray`. |
| `redraw`                   | action   | `(recomputeXaxisRange?: boolean, preserveZoom?: boolean) => Promise<void>` | Push typed-array updates + restyle; preserves the user's zoom by default. Keeps shapes other writers own (the staging band) and replaces `edit-window`. |
| `clearChartState`          | action   | `() => void`                                      | Drop all series + zoom history (used on workspace swap). |
| `fetchGraphSeries`         | action   | `(ds, start: Date, end: Date) => Promise<GraphSeries>` | Fetch observations for `ds` over `[start, end]` and build a `GraphSeries` via `buildGraphSeries`. |
| `buildGraphSeries`         | action   | `(ds: Datastream, data: ObservationRecord) => GraphSeries` | Build a `GraphSeries` from an already-loaded record, no fetch. Used directly for a managed datastream's working copy. |
| `assignSeriesColors`       | action   | `(orderedIds: string[]) => void`                  | Stable per-id colour assignment over the legend order. |
| `colorForDatastream`       | action   | `(id?: string) => string`                         | Resolve the line colour for a datastream (QC is always black). |
| `labelColorForDatastream`  | action   | `(id?: string) => string`                         | Darker companion for legend text. |
| `clearZoomHistory`         | action   | `() => void`                                      | Empty both stacks. |
| `pushZoomState`            | action   | `(state: ZoomState) => void`                      | Called by the debounced recorder in `utils/plotting/zoom.ts`. |

### `useObservationStore()` (`src/store/observations.ts`)

Fetches + caches observation windows and inflates them into
`ObservationRecord` instances.

| Name                       | Kind     | Type / signature                                  | Notes |
|----------------------------|----------|---------------------------------------------------|-------|
| `observations`             | state    | `Record<string, ObservationRecord>`               | Per-datastream record; reused across rebuilds. |
| `observationsRaw`          | state    | `Record<string, ObservationData>`                 | Typed-array cache (`Float64Array` datetimes + `Float32Array` values). |
| `fetchObservationsInRange` | action   | `(ds: Datastream, b: Date, e: Date) => Promise<ObservationRecord>` | Extends the cached range minimally; only fetches segments outside the existing window. Requests for one datastream run in order, so the record ends on the latest requested window and the cache never merges the same segment twice; a request matching the last queued range shares its promise. |

### `useWorkspaceStore()` (`src/store/workspaces.ts`)

Workspace selection + role-derived edit permission.

Persistence: `selectedWorkspace` only (key
`qc:selectedWorkspace:v1`) so the router's `hasWorkspaceGuard` sees a
restored selection on the first navigation.

| Name                       | Kind     | Type / signature                                  | Notes |
|----------------------------|----------|---------------------------------------------------|-------|
| `availableWorkspaces`      | state    | `Workspace[]`                                     | Filled by `loadWorkspaces`. |
| `selectedWorkspace`        | state    | `Workspace \| null`                               | The currently active workspace (persisted). |
| `isLoading`                | state    | `boolean`                                         | True while `loadWorkspaces` is in flight. |
| `selectedWorkspaceId`      | computed | `string \| null`                                  | Shortcut for `selectedWorkspace?.id`. |
| `hasSelection`             | computed | `boolean`                                         | True iff `selectedWorkspace` is non-null. |
| `canEditSelected`          | computed | `boolean`                                         | True for workspace owners; for collaborators, true when their role includes an Observation create/edit permission. |
| `loadWorkspaces`           | action   | `() => Promise<Workspace[]>`                      | Refetch + reconcile against the stored selection (drops the selection if the user lost access). |
| `selectWorkspace`          | action   | `(id: string \| null) => Workspace \| null`       | Pick by id from `availableWorkspaces`. |
| `applyWorkspaceById`       | action   | `(id: string) => Workspace \| null`               | Falls back to a placeholder `{ id }` when the list isn't loaded yet. Used by URL hydration. |
| `clearSelection`           | action   | `() => void`                                      | Drop the selection. |

### `useUIStore()` (`src/store/userInterface.ts`)

Drawer / view chrome state plus the per-operation form fields read
by every filter / edit panel. Mostly a flat bag: the panel
components own the validation; this store just keeps the values
reactive between mounts.

Persistence: `filterRangeActive` only (key `qc:userInterface:v1`) so
the user's "filter window" toggle survives reloads; per-operation
defaults are reseeded from the datastream on each mount.

| Name                              | Kind   | Type / signature                                  | Notes |
|-----------------------------------|--------|---------------------------------------------------|-------|
| `selectedDrawer`                  | state  | `DrawerType`                                      | `Edit`, `Select`, or `None`: which left drawer is active. |
| `isDrawerOpen`                    | state  | `boolean`                                         | Drawer open/collapsed. |
| `currentView`                     | state  | `'Edit' \| 'Select'`                              | Current main view (drives the nav rail's active state). |
| `selectedOperation`               | state  | `string \| null`                                  | Open operation panel id; `null` when nothing is open. |
| `cardHeight` / `tableHeight`      | state  | `number`                                          | Select-view top/bottom split. |
| `operators`                       | state  | `string[]`                                        | `Object.keys(Operator)`: Change-values operator choices. |
| `selectedOperator`                | state  | `number`                                          | Index into `operators`. |
| `operationValue`                  | state  | `number`                                          | Change-values numeric operand. |
| `interpolateValues`               | state  | `boolean`                                         | Fill-gaps: interpolate vs constant. |
| `selectedInterpolationMethod`     | state  | `InterpolationMethods`                            | Interpolation algorithm (`LINEAR` only today). |
| `gapUnits` / `selectedGapUnit` / `gapAmount` | state | `string[]` / `string` / `number`          | Find-gaps threshold (unit + amount). |
| `fillUnits` / `selectedFillUnit` / `fillAmount` | state | `string[]` / `string` / `number`       | Fill-gaps cadence (unit + amount). |
| `noDataValue`                     | state  | `number`                                          | Sentinel written into "no-data" filled points; seeds from the QC datastream. |
| `selectedDriftCorrectionMethod`   | state  | `DriftCorrectionMethods`                          | Drift correction algorithm (`LINEAR` only today). |
| `driftGapWidth`                   | state  | `number`                                          | Drift correction gap-width input. |
| `shiftUnits` / `selectedShiftUnit` / `shiftAmount` | state | `string[]` / `string` / `number`     | Shift-datetimes amount + unit. |
| `logicalComparators`              | state  | `{ value, title }[]`                              | Reusable comparator dropdown items. |
| `selectedRateOfChangeComparator` / `rateOfChangeValue` | state | shape above / `number`          | Rate-of-change filter inputs. |
| `selectedChangeComparator` / `changeValue` | state | shape above / `number`                    | Change-threshold filter inputs. |
| `filterRangeActive`               | state  | `boolean`                                         | Toggles the shared filter-window UX; the only persisted field. |
| `filterRangeFromTs` / `filterRangeToTs` | state | `number \| null`                            | Filter-window epoch bounds; reseed on each panel mount. |
| `onRailItemClicked`               | action | `(title: DrawerType) => void`                     | Nav-rail click handler: toggles open/closed on repeat, switches view on first click. |

### `useQualifierStore()` (`src/store/qualifiers.ts`)

Workspace-scoped qualifier dictionary plus the per-observation
applications added via the Qualifying Comments panel.

Persistence: `applied` only; the dictionary is reloaded on every
workspace change.

| Name                            | Kind     | Type / signature                                  | Notes |
|---------------------------------|----------|---------------------------------------------------|-------|
| `qualifiers`                    | state    | `Qualifier[]`                                     | Workspace dictionary. |
| `applied`                       | state    | `Record<datastreamId, Record<index, QualifierApplication[]>>` | Per-observation applications. |
| `isLoading`                     | state    | `boolean`                                         | True while `loadQualifiers` is in flight. |
| `qualifierById`                 | computed | `Record<string, Qualifier>`                       | Lookup map for the chips. |
| `loadQualifiers`                | action   | `() => Promise<void>`                             | Fetch dictionary for the active workspace; triggers a plot refresh so the qualifier band materialises. |
| `createQualifier`               | action   | `(code: string, description: string) => Promise<Qualifier>` | Server-side create with a local-only fallback when no workspace is active. |
| `applyQualifiers`               | action   | `(datastreamId, indices, qualifierIds, appliedBy) => void` | Idempotent merge: already-applied (qualifier, index) pairs are skipped. |
| `removeQualifier`               | action   | `(datastreamId, index, qualifierId) => void`      | Drops a single (qualifier, index) application. |
| `getApplicationsForDatastream`  | action   | `(datastreamId) => Array<{ index, qualifierId, appliedAt, appliedBy }>` | Flat list suitable for plotting. |
| `getApplicationsAtIndex`        | action   | `(datastreamId, index) => QualifierApplication[]` | Per-point lookup. |

### `useUiLayoutStore()` (`src/store/uiLayout.ts`)

Persisted drawer / splitter geometry. A bag of values keyed by
strings the calling composable supplies, so new resizable components
plug in without touching this store.

Persistence: both `sizes` and `flags` (key `qc:uiLayout:v1`).

| Name      | Kind   | Type / signature                                  | Notes |
|-----------|--------|---------------------------------------------------|-------|
| `sizes`   | state  | `Record<string, number>`                          | Pixel widths / percentages, written by `useResizable`. |
| `flags`   | state  | `Record<string, boolean>`                         | Toggle state, written by `usePersistedFlag`. |
| `getSize` | action | `(key: string) => number \| null`                 | `null` when unset or non-finite. |
| `setSize` | action | `(key: string, value: number) => void`            | Reassigns the whole object so reactive watchers fire. |
| `getFlag` | action | `(key: string) => boolean \| null`                | `null` lets callers distinguish "unset" from "explicit false". |
| `setFlag` | action | `(key: string, value: boolean) => void`           | Same fresh-object pattern. |

### `useOperationParamsStore()` (`src/store/operationParams.ts`)

Per-datastream remembered slots for Find Gaps / Fill Gaps
parameters. `useUIStore` reads these to seed defaults; otherwise
each panel re-derives from the datastream's intended cadence.

Persistence: `byDatastream` (key `qc:opParams:v1`).

| Name           | Kind   | Type / signature                                          | Notes |
|----------------|--------|-----------------------------------------------------------|-------|
| `byDatastream` | state  | `Record<string, PersistedOpParams>`                       | Slots keyed by datastream id. |
| `load`         | action | `(id?: string \| null) => PersistedOpParams \| null`      | `null` when nothing's stored. |
| `save`         | action | `(id?: string \| null, patch: PersistedOpParams) => void` | Merges; partial patches don't clobber unrelated fields. |

### `useUserStore()` (`src/store/user.ts`)

The signed-in user. Persisted in full.

| Name      | Kind   | Type / signature      | Notes |
|-----------|--------|-----------------------|-------|
| `user`    | state  | `User`                | Defaults to a fresh `new User()` until auth resolves. |
| `setUser` | action | `(u: User) => void`   | Replace wholesale (called by the session resolver in `main.ts`). |

### `useHydroServer()` (`src/store/hydroserver.ts`)

Holds the `@hydroserver/client` instance. Initialized in `main.ts`
after settings load; every other store reaches `hs.value` through
`storeToRefs(useHydroServer())`. Not persisted (the client carries
ephemeral connection state).

| Name | Kind  | Type / signature   | Notes |
|------|-------|--------------------|-------|
| `hs` | state | `Ref<HydroServer>` | Non-null after `main.ts` finishes settings load; type-asserted as non-null for ergonomic consumer code. |

### `useQcSessionStore()` (`src/store/qcSession.ts`)

View-mode state for QC sessions: which session is editable (the single
in-progress one) and which is being viewed. Viewing a committed session
puts the editor in read-only mode.

| Name                | Kind     | Type / signature                        | Notes |
|---------------------|----------|-----------------------------------------|-------|
| `historyId`         | state    | `string \| null`                        | The managed datastream's QC history being navigated. |
| `resumeDatastreamId`| state    | `string \| null`                        | Managed datastream the editor was last open on. The only persisted field: a page reload replots it and resumes its session from the last save. Set on entering the editor, cleared on exit. |
| `sessions`          | state    | `QualityControlSession[]`               | Committed + in-progress sessions for the history. |
| `currentSessionId`  | state    | `string \| null`                        | The single in-progress (editable) session. |
| `viewedSessionId`   | state    | `string \| null`                        | The session currently being viewed. |
| `isSwitchingSession`| state    | `boolean`                               | True while another session's data and operations load. The operations panel renders a loading state instead of the outgoing session's entries, which would otherwise linger and read as the incoming session's. |
| `savedEdits`        | state    | `HistoryItem[]`                         | Edit history entries (by reference) at the last load or save. `useEditSession` compares the working copy against it for `hasUnsavedChanges`; kept in the store so the editor footer and the nav rail's exit guard agree. |
| `savedComments`     | state    | `string[]`                              | Comment text of `savedEdits`, since comments are edited in place. |
| `isReadOnly`        | computed | `boolean`                               | True when sessions exist and the viewed one isn't the in-progress session. Guarded on `sessions.length` so plain editing outside the session workflow isn't treated as read-only. |
| `inProgressSession` | computed | `QualityControlSession \| null`         | The editable session, if any. |
| `committedSessions` | computed | `QualityControlSession[]`               | Sessions with status `committed`. |
| `viewedSession`     | computed | `QualityControlSession \| null`         | The session for `viewedSessionId`. |
| `fetchSessions`     | action   | `(historyId: string) => Promise<QualityControlSession[]>` | Fetch a history's sessions with their operations without writing any state, so a caller can drop a result that went stale (see `useEditSession`). |
| `applySessions`     | action   | `(historyId: string, sessions: QualityControlSession[]) => void` | Adopt fetched sessions; default the view to the in-progress one, else the latest committed. |
| `viewSession`       | action   | `(sessionId: string) => void`           | View a session read-only (no-op for an unknown id). |
| `returnToCurrent`   | action   | `() => void`                            | Return to the editable in-progress session. |
| `reset`             | action   | `() => void`                            | Clear all state. |

### `useQcPreferencesStore()` (`src/store/qcPreferences.ts`)

Persisted QC editing preferences. Persistence: key `qc:preferences:v1`,
`pick: ['processingLevelId']`.

| Name                | Kind  | Type / signature | Notes |
|---------------------|-------|------------------|-------|
| `processingLevelId` | state | `string \| null` | Last-used processing level for the Create-Datastream-for-Editing form; null on first use (no assumed default). |

## Internal: utilities

### `src/utils/plotting/plotly.ts` (barrel)

Re-exports:

| Function                 | Purpose                                                          |
|--------------------------|------------------------------------------------------------------|
| `handleNewPlot(...)`     | First-mount: build traces, wire events, set initial range.       |
| `setSelectedPoints(...)` | Programmatic selection update via `Plotly.restyle`.              |
| `clearSelection(...)`    | Drop the selection shape + restyle.                              |
| `redrawTraces(...)`      | Push new typed-array x/y into all plotted traces.                |
| `updateOptions(...)`     | Apply axis label / range / tick-formatting changes.              |

### `src/utils/observations.ts`

`fetchObservationsSync(datastream, startTime?, endTime?)`: paged
columnar fetch, returns `{ datetimes: number[]; dataValues: number[] }`.

### `src/utils/dateMath.ts`

`subtractDays`, `subtractMonths`, `subtractYears` for the time-range
preset buttons.

### `src/utils/timeRangePresets.ts`

Preset definitions (`TIME_RANGE_PRESETS`, ids stable for the share URL)
and their pure resolution:

- `dataExtent(datastreams)`: earliest begin to latest end over the given
  phenomenon times; `null` when none has observations.
- `presetWindow(id, extent)`: the preset counted back from `extent.end`
  (All is the whole extent, YTD starts Jan 1 of the end year). Used in the
  Select view and while editing without a session window.
- `presetAroundWindow(id, window, extent)`: the editor's rule while a
  session window is known. 1w / 1m / 6m / 1y return
  `[window.begin - span, window.end + span]`, not clipped to the data.
  All returns `extent` widened to cover `window` (or `window` when `extent`
  is `null`); YTD resolves the same as All. `null` for an unknown id.
- `EDITOR_PRESETS`: the presets the editor's Context menu offers, without
  YTD and titled for the session window.
- `shownPresetId(selectedId, presets)`: the chip that shows the selection
  among `presets`. YTD shows as All where it is not offered; `null` for
  Custom or an unknown id. Display only: `DataVisTimeFilters` highlights it
  and `selectedDateBtnId` is unchanged.

### `src/utils/sessionWindow.ts`

Pure validation for the session-window step (`SessionWindowDialog.vue`,
opened from the row Edit chooser or the editor footer's **New session**):

- `defaultSessionWindow(source)`. The step's default window: the source's
  full extent, begin to end. `null` when the source has no observations.
  The rules below accept it whenever the committed history lies inside that
  extent; the dialog reports the rare case where it does not.
- `validateSessionWindow(window, source, sessions)`: `null` when `window`
  is valid, otherwise an error string. The window must lie inside the
  source's extent, and it can't leave a gap before or after the committed
  history (history spec 7.2.3 / 7.2.4). Touching an edge or overlapping is
  fine.
- `committedExtent(sessions)`: the earliest committed start to the latest
  committed end, or `null` with nothing committed.

### `src/utils/rules.ts`

Vuetify validation rules used across forms (required, numeric, range).

## Test hooks

When `VITE_APP_E2E_HOOKS=1` (Playwright sets this), `src/testHooks.ts`
attaches `window.__vbwTestHooks` with the handles E2E specs need:
selecting a datastream programmatically, reading the current edit
history, asserting the plot is ready. These are e2e plumbing, not a
public surface; treat the names as unstable.

## QC History file format

The save / load JSON format is the only durable export the app produces.
Wire shape:

```jsonc
{
  "version": "1",
  "createdAt": "2026-04-19T12:34:56.000Z",
  "window": {
    "startDate": "2024-01-01T00:00:00.000Z",
    "endDate":   "2024-06-30T23:59:59.999Z"
  },
  "operations": [
    { "method": "VALUE_THRESHOLD", "args": [{ "Greater than": 100 }] },
    { "method": "CHANGE_VALUES",   "args": ["ASSIGN", 11.5] }
  ]
}
```

## Integrating from outside

If you want to reuse the QC engine in a non-Vue context (a Jupyter
notebook driven by Pyodide, a Node CLI, another web app), depend on
`@uwrl/qc-utils` directly and skip the QC App entirely. The QC App is a
UI shell; the engine is independent.

If you want to *automate* the QC App (e.g. drive a regression suite),
the supported surface is the E2E test hooks (`window.__vbwTestHooks`)
plus the QC History file as input. Treat anything else as private.

## See also

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [PERFORMANCE.md](./PERFORMANCE.md)
- HydroServer documentation: <https://hydroserver2.github.io/hydroserver/>
