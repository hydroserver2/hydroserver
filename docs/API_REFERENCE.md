# APIs &amp; Interoperability

This is a reference for the surfaces a developer integrates against —
both the in-app TypeScript surfaces (Pinia stores, composables, plotting
utils) and the external HydroServer REST endpoints the app consumes.

For the QC engine itself (operation enums, dispatch, history scripts),
see [`qc-utils/docs/API_REFERENCE.md`](../../qc-utils/docs/API_REFERENCE.md)
and [`qc-utils/docs/HISTORY_SCRIPT.md`](../../qc-utils/docs/HISTORY_SCRIPT.md).

## Design principles

- **No app-specific API.** The QC App is a client of HydroServer; it
  does not expose its own REST surface. Interop happens at three layers:
  the `@hydroserver/client` REST client, the `@uwrl/qc-utils` QC engine,
  and the QC script JSON file format.
- **JSON over the wire, typed arrays in memory.** The app fetches
  observations in HydroServer's columnar JSON format and inflates them
  to `Float64Array` + `Float32Array` inside `ObservationRecord`.
- **History is the contract.** The QC script file format is the
  durable record of edits. It is not pinned to a datastream id, so the
  same script can be replayed against many datastreams.
- **Auth lives on the backend.** Cookies + Django AllAuth. The app
  holds no secrets and emits no service-to-service tokens.

## External: HydroServer REST API

The app talks to a HydroServer instance via the `@hydroserver/client`
package. The base URL is `${VITE_APP_API_URL}/api`. Endpoint groups used:

| Group              | Base path                              | Purpose                                             |
|--------------------|----------------------------------------|-----------------------------------------------------|
| Session / auth     | `/auth/browser/session`                | Login, logout, current session.                     |
| Account            | `/auth/browser/account`                | User profile, signup, email verification.           |
| OAuth providers    | `/auth/browser/provider`               | Google sign-in handshake (Django AllAuth).          |
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
- **OAuth2 (Google).** Delegated to HydroServer's Django AllAuth setup.

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

### `useQcScript()`

```ts
const { exportScript, importScript } = useQcScript()

await exportScript()             // downloads qc-script-<datastream>-<isoTimestamp>.json
const report = await importScript(file)
// report = { applied: 12, failed: [{ index, method, error }, ...] }
```

`exportScript` reads the current wall-clock window from
`useDataVisStore`. `importScript` fetches the script's authored window
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

### `useDataVisStore()`

Selected datastream, plotted streams, QC datastream, plot time range,
selected data indices.

Key exports:

| Export                | Type                          | Notes                                              |
|-----------------------|-------------------------------|----------------------------------------------------|
| `things`              | `Ref<Thing[]>`                | Sites, fetched once per page load.                 |
| `datastreams`         | `Ref<Datastream[]>`           | All visible datastreams in the workspace.          |
| `plottedDatastreams`  | `Ref<Datastream[]>`           | Up to 5 streams currently on the chart.            |
| `qcDatastream`        | `ComputedRef<Datastream\|null>` | First plotted stream; the QC target.             |
| `selectedData`        | `Ref<number[]\|null>`         | Index list of the active selection.                |
| `beginDate` / `endDate` | `Ref<Date>`                 | Active time-range window.                          |
| `resetState()`        | method                        | Clears filters + plot state for a workspace swap.  |

### `usePlotlyStore()`

Owns the Plotly DOM ref, the per-series `ObservationRecord` history,
and the redraw / restyle plumbing.

| Export             | Notes                                                                  |
|--------------------|------------------------------------------------------------------------|
| `selectedSeries`   | The `GraphSeries` whose `data` is the QC target.                       |
| `editHistory`      | Ref to `selectedSeries.data.history` (in-place — never reassign).      |
| `isUpdating` / `isSubmitting` | Loading flags surfaced in nav rail + drawers.               |
| `redraw()`         | Pushes typed-array updates to Plotly + restyles selections / staging. |

### `useObservationStore()`

Fetches + caches observation windows. `fetchObservationsInRange(ds, b, e)`
extends the cached range minimally — only fetches the segments outside
the existing window.

### `useWorkspaceStore()`

`workspaces`, `selectedWorkspace`, `selectWorkspace(id)`. Persisted in
`localStorage` under the `workspaces` key.

### `useUIStore()`

Drawer state, current view (`Select` | `Edit`), nav-rail click handler.
The `editCount` / unsaved-edits guard logic lives in `NavigationRail.vue`
because it spans drawer state + edit history.

### `useHydroServer()`

Holds the `hs` ref — the `@hydroserver/client` instance. Initialized in
`main.ts` after settings load.

### `useUserStore()`, `useQualifierStore()`, `useUiLayoutStore()`, `useOperationParamsStore()`

Auxiliary stores; see their files for the surface.

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

## QC script file format

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

See [`qc-utils/docs/HISTORY_SCRIPT.md`](../../qc-utils/docs/HISTORY_SCRIPT.md)
for per-op arg shapes, versioning rules, and the round-trip contract.

## Integrating from outside

If you want to reuse the QC engine in a non-Vue context — a Jupyter
notebook driven by Pyodide, a Node CLI, another web app — depend on
`@uwrl/qc-utils` directly and skip the QC App entirely. The QC App is a
UI shell; the engine is independent.

If you want to *automate* the QC App (e.g. drive a regression suite),
the supported surface is the E2E test hooks (`window.__vbwTestHooks`)
plus the QC script file as input. Treat anything else as private.

## See also

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [PERFORMANCE.md](./PERFORMANCE.md)
- [`qc-utils/docs/HISTORY_SCRIPT.md`](../../qc-utils/docs/HISTORY_SCRIPT.md)
- [`qc-utils/docs/CALIBRATION.md`](../../qc-utils/docs/CALIBRATION.md)
- HydroServer documentation: <https://hydroserver2.github.io/hydroserver/>
