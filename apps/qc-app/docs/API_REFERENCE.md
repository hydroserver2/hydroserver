# APIs &amp; Interoperability

This is a reference for the surfaces a developer integrates against —
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

The full method list lives in `qc-utils/src/services/api.ts` (the client
is carried in qc-utils for legacy reasons; the QC App uses
`@hydroserver/client` for the same endpoints).

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
posted window. The QC App always submits the full edited window —
incremental submission is not implemented today.

### Result qualifier codes

Listed via `fetchWorkspaceResultQualifiers`. The QC App tracks selected
qualifiers in `store/qualifiers.ts`, but **does not yet serialize them on
submit** (see [QUALITY.md](./QUALITY.md) tech-debt section and the TODO
in `useQcSubmission.ts:42`).

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

### `useQcSubmission()`

```ts
const { submitQcEdits } = useQcSubmission()
await submitQcEdits()    // POST observations with mode=replace, clear history
```

Single-shot: guards on (selectedSeries + qcDatastream + non-empty
history), serializes `[phenomenonTime, result]` rows, POSTs with
`mode: 'replace'`, surfaces a Snackbar, and clears the history in place
on success.

### `useResizable()`

Generic pointer-drag-resize hook. Used by `SelectDrawer`, `EditDrawer`,
and the plot's table-vs-chart splitter.

### `useBufferedNumber()`

Debounced numeric input wrapper for filter panels — avoids dispatching
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
`pinia-plugin-persistedstate` config — the storage key and the
specific slice picked. Stores with no Persistence line are session-only.

### `useDataVisStore()` — `src/store/dataVisualization.ts`

Catalog data (sites, datastreams, taxonomy), sidebar filters, plotted
set + QC target, time-range window. The orchestrator for everything in
the Select drawer and the rebuild pipeline that owns `rebuildPlot()`.

Persistence: `selectedDateBtnId` only (so the user's preset choice
survives reload); catalogs, filters, and in-flight maps refetch cleanly
on boot.

| Name                                | Kind     | Type / signature                                  | Notes |
|-------------------------------------|----------|---------------------------------------------------|-------|
| `things`                            | state    | `Thing[]`                                         | Sites in the active workspace; fetched once on workspace mount. |
| `datastreams`                       | state    | `(Datastream & DatastreamExtended)[]`             | All visible datastreams (with `expand_related` nested objects). |
| `observedProperties`                | state    | `ObservedProperty[]`                              | Taxonomy for the filter chips. |
| `processingLevels`                  | state    | `ProcessingLevel[]`                               | Taxonomy for the filter chips. |
| `selectedThings`                    | state    | `Thing[]`                                         | Site filter selection (sidebar). |
| `selectedObservedPropertyNames`     | state    | `string[]`                                        | Observed-property filter selection. |
| `selectedProcessingLevelNames`      | state    | `string[]`                                        | Processing-level filter selection. |
| `filteredDatastreams`               | computed | `(Datastream & DatastreamExtended)[]`             | `datastreams` narrowed by the three filter selections. |
| `plottedDatastreams`                | state    | `Datastream[]`                                    | Up to 5 streams currently on the chart. |
| `qcDatastreamId`                    | state    | `string \| null`                                  | Storage form of the QC target; survives plotted-list mutations. |
| `qcDatastream`                      | computed | `Datastream \| null`                              | Live lookup of `qcDatastreamId` in `plottedDatastreams`. |
| `qualifierSet`                      | state    | `Set<string>`                                     | Qualifier codes seen on the QC target's loaded points. |
| `selectedQualifier`                 | state    | `string`                                          | Active qualifier in the picker. |
| `selectedData`                      | state    | `number[] \| null`                                | Index list of the active selection (lasso, box, click). |
| `hasSelectionShape`                 | state    | `boolean`                                         | True while a box/lasso shape exists, even when it captured zero points. |
| `loadingStates`                     | state    | `Map<string, boolean>`                            | Per-datastream in-flight observation fetches. |
| `beginDate` / `endDate`             | state    | `Date`                                            | Active loaded time-range window (the date pickers' source of truth). |
| `dateOptions`                       | state    | `Array<{ id, icon, label, title, calculateBeginDate }>` | Preset definitions (1w, 1m, 6m, 1y, YTD, All). |
| `selectedDateBtnId`                 | state    | `number`                                          | Active preset id; `-1` when the user picked dates manually. |
| `matchesSelectedThing`              | action   | `(ds) => boolean`                                 | Filter predicate; exposed so the table can reuse it on row updates. |
| `matchesSelectedObservedProperty`   | action   | `(ds) => boolean`                                 | Same shape as above. |
| `matchesSelectedProcessingLevel`    | action   | `(ds) => boolean`                                 | Same shape as above. |
| `setDateRange`                      | action   | `({ begin?, end?, update?, custom? }) => Promise<void>` | No-ops when neither bound moves; clears zoom history when it does. |
| `onDateBtnClick`                    | action   | `(id: number) => void`                            | Anchors `endDate` to today, recomputes `beginDate`, applies the preset. |
| `syncRangeToPreset`                 | action   | `() => void`                                      | Re-derives `beginDate`/`endDate` from `selectedDateBtnId`. Run on `afterHydrate` so the restored preset's window applies to the first load. |
| `refreshGraphSeriesArray`           | action   | `() => Promise<unknown[]>`                        | Reconciles `graphSeriesArray` against `plottedDatastreams` (fetch deltas + reorder + recolor). |
| `resetState`                        | action   | `() => void`                                      | Clears filters + plotted set on a workspace swap; preserves the preset preference. |
| `toggleDatastream`                  | action   | `(ds: Datastream) => Promise<void>`               | Plot if absent, unplot if present. |
| `plotDatastream`                    | action   | `(ds: Datastream) => Promise<void>`               | Add to plot; promotes to QC when nothing's there yet. |
| `unplotDatastream`                  | action   | `(id: string) => Promise<void>`                   | Remove; promotes the previous plotted entry to QC if removing the QC target. |
| `clearPlottedDatastreams`           | action   | `() => Promise<void>`                             | Drop the entire plotted set. |
| `setPlottedDatastreams`             | action   | `(items: Datastream[], qcId?: string \| null) => Promise<void>` | Wholesale replace; used by URL hydration. |
| `setQcDatastream`                   | action   | `(id: string \| null) => Promise<void>`           | Change QC target; preserves the current zoom. |
| `rebuildPlot`                       | action   | `() => Promise<void>`                             | Serialized rebuild (drop zoom history, refresh series, regenerate options, render). Coalesces concurrent callers. |

### `usePlotlyStore()` — `src/store/plotly.ts`

Owns the Plotly DOM ref, the per-series array driving the chart,
viewport state (tooltips, crosshair, hover, zoom history), and the
redraw / restyle plumbing.

Persistence: `tooltipsMaxDataPoints`, `tooltipsMode`, and
`tooltipsManualEnabled` (key `qc.plot.tooltipsMaxDataPoints`) — the
user's data-points-mode preference. Everything else is ephemeral (DOM
handles, live chart caches).

| Name                       | Kind     | Type / signature                                  | Notes |
|----------------------------|----------|---------------------------------------------------|-------|
| `graphSeriesArray`         | state    | `GraphSeries[]`                                   | Per-series state driving traces, colors, and axis chips. |
| `plotlyOptions`            | state    | `PlotlyChartOptions`                              | Cached `createPlotlyOption` output; seeded empty so consumers can read without null-guards. |
| `plotlyRef`                | state    | `AppPlotlyHTMLElement \| null`                    | Live Plotly DOM element; populated by `handleNewPlot`. |
| `mainPlotEpoch`            | state    | `number`                                          | Monotonic counter — bumped per `handleNewPlot` so listeners can re-attach. |
| `selectedSeriesIndex`      | computed | `number`                                          | Index of the QC target in `graphSeriesArray` (`-1` when none). |
| `selectedSeries`           | computed | `GraphSeries`                                     | Convenience for `graphSeriesArray[selectedSeriesIndex]`. |
| `editHistory`              | state    | `HistoryItem[]`                                   | Mirrors `selectedSeries.data.history` (mutated in place — never reassign). |
| `suppressedEchoSelection`  | state    | `number[] \| null`                                | Sentinel armed by programmatic Plotly writes to suppress the echo SELECTION dispatch. |
| `isUpdating`               | state    | `boolean`                                         | Surfaced in the nav rail while a redraw runs. |
| `isSubmitting`             | state    | `boolean`                                         | True during a QC submit POST. |
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
| `tableScrollRequest`       | state    | `{ time: number; seq: number } \| null`           | Signal from the "zoom to range" presets; `DataTable` scrolls to the first row at/after `time`. `seq` re-triggers on repeats. |
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
| `redraw`                   | action   | `(recomputeXaxisRange?: boolean, preserveZoom?: boolean) => Promise<void>` | Push typed-array updates + restyle; preserves the user's zoom by default. |
| `clearChartState`          | action   | `() => void`                                      | Drop all series + zoom history (used on workspace swap). |
| `fetchGraphSeries`         | action   | `(ds, start: Date, end: Date) => Promise<GraphSeries>` | Build a fresh `GraphSeries` from observations; colour is filled later by `assignSeriesColors`. |
| `assignSeriesColors`       | action   | `(orderedIds: string[]) => void`                  | Stable per-id colour assignment over the legend order. |
| `colorForDatastream`       | action   | `(id?: string) => string`                         | Resolve the line colour for a datastream (QC is always black). |
| `labelColorForDatastream`  | action   | `(id?: string) => string`                         | Darker companion for legend text. |
| `clearZoomHistory`         | action   | `() => void`                                      | Empty both stacks. |
| `pushZoomState`            | action   | `(state: ZoomState) => void`                      | Called by the debounced recorder in `utils/plotting/zoom.ts`. |

### `useObservationStore()` — `src/store/observations.ts`

Fetches + caches observation windows and inflates them into
`ObservationRecord` instances.

| Name                       | Kind     | Type / signature                                  | Notes |
|----------------------------|----------|---------------------------------------------------|-------|
| `observations`             | state    | `Record<string, ObservationRecord>`               | Per-datastream record; reused across rebuilds. |
| `observationsRaw`          | state    | `Record<string, ObservationData>`                 | Typed-array cache (`Float64Array` datetimes + `Float32Array` values). |
| `fetchObservationsInRange` | action   | `(ds: Datastream, b: Date, e: Date) => Promise<ObservationRecord>` | Extends the cached range minimally; only fetches segments outside the existing window. |

### `useWorkspaceStore()` — `src/store/workspaces.ts`

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
| `applyWorkspaceById`       | action   | `(id: string) => Workspace \| null`               | Falls back to a placeholder `{ id }` when the list isn't loaded yet — used by URL hydration. |
| `clearSelection`           | action   | `() => void`                                      | Drop the selection. |

### `useUIStore()` — `src/store/userInterface.ts`

Drawer / view chrome state plus the per-operation form fields read
by every filter / edit panel. Mostly a flat bag — the panel
components own the validation; this store just keeps the values
reactive between mounts.

Persistence: `filterRangeActive` only (key `qc:userInterface:v1`) so
the user's "filter window" toggle survives reloads; per-operation
defaults are reseeded from the datastream on each mount.

| Name                              | Kind   | Type / signature                                  | Notes |
|-----------------------------------|--------|---------------------------------------------------|-------|
| `selectedDrawer`                  | state  | `DrawerType`                                      | `Edit`, `Select`, or `None` — which left drawer is active. |
| `isDrawerOpen`                    | state  | `boolean`                                         | Drawer open/collapsed. |
| `currentView`                     | state  | `'Edit' \| 'Select'`                              | Current main view (drives the nav rail's active state). |
| `selectedOperation`               | state  | `string \| null`                                  | Open operation panel id; `null` when nothing is open. |
| `cardHeight` / `tableHeight`      | state  | `number`                                          | Select-view top/bottom split. |
| `operators`                       | state  | `string[]`                                        | `Object.keys(Operator)` — Change-values operator choices. |
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

### `useQualifierStore()` — `src/store/qualifiers.ts`

Workspace-scoped qualifier dictionary plus the per-observation
applications added via the Qualifying Comments panel.

Persistence: `applied` only — the dictionary is reloaded on every
workspace change.

| Name                            | Kind     | Type / signature                                  | Notes |
|---------------------------------|----------|---------------------------------------------------|-------|
| `qualifiers`                    | state    | `Qualifier[]`                                     | Workspace dictionary. |
| `applied`                       | state    | `Record<datastreamId, Record<index, QualifierApplication[]>>` | Per-observation applications. |
| `isLoading`                     | state    | `boolean`                                         | True while `loadQualifiers` is in flight. |
| `qualifierById`                 | computed | `Record<string, Qualifier>`                       | Lookup map for the chips. |
| `loadQualifiers`                | action   | `() => Promise<void>`                             | Fetch dictionary for the active workspace; triggers a plot refresh so the qualifier band materialises. |
| `createQualifier`               | action   | `(code: string, description: string) => Promise<Qualifier>` | Server-side create with a local-only fallback when no workspace is active. |
| `applyQualifiers`               | action   | `(datastreamId, indices, qualifierIds, appliedBy) => void` | Idempotent merge — already-applied (qualifier, index) pairs are skipped. |
| `removeQualifier`               | action   | `(datastreamId, index, qualifierId) => void`      | Drops a single (qualifier, index) application. |
| `getApplicationsForDatastream`  | action   | `(datastreamId) => Array<{ index, qualifierId, appliedAt, appliedBy }>` | Flat list suitable for plotting. |
| `getApplicationsAtIndex`        | action   | `(datastreamId, index) => QualifierApplication[]` | Per-point lookup. |

### `useUiLayoutStore()` — `src/store/uiLayout.ts`

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

### `useOperationParamsStore()` — `src/store/operationParams.ts`

Per-datastream remembered slots for Find Gaps / Fill Gaps
parameters. `useUIStore` reads these to seed defaults; otherwise
each panel re-derives from the datastream's intended cadence.

Persistence: `byDatastream` (key `qc:opParams:v1`).

| Name           | Kind   | Type / signature                                          | Notes |
|----------------|--------|-----------------------------------------------------------|-------|
| `byDatastream` | state  | `Record<string, PersistedOpParams>`                       | Slots keyed by datastream id. |
| `load`         | action | `(id?: string \| null) => PersistedOpParams \| null`      | `null` when nothing's stored. |
| `save`         | action | `(id?: string \| null, patch: PersistedOpParams) => void` | Merges; partial patches don't clobber unrelated fields. |

### `useUserStore()` — `src/store/user.ts`

The signed-in user. Persisted in full.

| Name      | Kind   | Type / signature      | Notes |
|-----------|--------|-----------------------|-------|
| `user`    | state  | `User`                | Defaults to a fresh `new User()` until auth resolves. |
| `setUser` | action | `(u: User) => void`   | Replace wholesale (called by the session resolver in `main.ts`). |

### `useHydroServer()` — `src/store/hydroserver.ts`

Holds the `@hydroserver/client` instance. Initialized in `main.ts`
after settings load — every other store reaches `hs.value` through
`storeToRefs(useHydroServer())`. Not persisted (the client carries
ephemeral connection state).

| Name | Kind  | Type / signature   | Notes |
|------|-------|--------------------|-------|
| `hs` | state | `Ref<HydroServer>` | Non-null after `main.ts` finishes settings load; type-asserted as non-null for ergonomic consumer code. |

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

`fetchObservationsSync(datastream, startTime?, endTime?)` — paged
columnar fetch, returns `{ datetimes: number[]; dataValues: number[] }`.

### `src/utils/dateMath.ts`

`subtractDays`, `subtractMonths`, `subtractYears` for the time-range
preset buttons.

### `src/utils/rules.ts`

Vuetify validation rules used across forms (required, numeric, range).

## Test hooks

When `VITE_APP_E2E_HOOKS=1` (Playwright sets this), `src/testHooks.ts`
attaches `window.__vbwTestHooks` with the handles E2E specs need —
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

If you want to reuse the QC engine in a non-Vue context — a Jupyter
notebook driven by Pyodide, a Node CLI, another web app — depend on
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
