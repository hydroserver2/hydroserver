# Plotting Layer Design

The plotting layer (`src/utils/plotting/`) is the Vue / Pinia side's
adapter to Plotly. It owes its split into many short files to two
forces: the QC dispatch path needs to see clean seams to keep
testable, and Plotly's call surface (data writes vs. layout writes
vs. selection writes vs. event handlers) really is a set of distinct
concerns. This doc traces a single QC operation end-to-end so a new
contributor can read the modules in the order the code runs.

## The files at a glance

| File              | Concern                                                                                                                |
|-------------------|------------------------------------------------------------------------------------------------------------------------|
| `plotly.ts`       | Barrel re-export. `internal.ts` is intentionally *not* re-exported.                                                    |
| `internal.ts`     | Shared private helpers (`traceXAsNumbers`, `DENSITY_HIDE_MARKERS`, `Y_AXIS_KEY_RE`). Not exported through the barrel.  |
| `options.ts`      | `createPlotlyOption` builds the `{ traces, layout, config }` triple from `GraphSeries[]` + Pinia store state.          |
| `events.ts`       | `handleNewPlot` and the top-level event wiring (`plotly_click`, `plotly_relayout`, mouse / wheel).                     |
| `selected.ts`     | `handleSelected` translates Plotly selections into a `SELECTION` filter dispatch on `qc-utils`.                        |
| `zoom.ts`         | Zoom-history capture / apply. Lives on its own debounce, independent of `handleRelayout`.                              |
| `relayout.ts`     | `handleRelayout` handles viewport changes: tick recompute, visible-point count, density-based marker hiding.           |
| `interaction.ts`  | DOM-level handlers: throttled mousemove crosshair, wheel-zoom, axis-chip placement, y-axis drag-rect widening.         |
| `operations.ts`   | Imperative helpers callable from components: `zoomXaxisTo`, `toggleTraceVisibility`, `setSelectedPoints`, etc.         |
| `staging.ts`      | Visual-only overlays while a Find-Gaps / Fill-Gaps operation is staged. Ghost-fill trace + drag-resizable shape.       |

The split is not by file size, it's by the Plotly API each module
talks to. `options.ts` owns trace + layout construction. `events.ts`
owns event subscription. `selected.ts`, `zoom.ts`, `relayout.ts`,
`interaction.ts` each own one event family. `operations.ts` and
`staging.ts` are imperative call sites the rest of the app uses to
poke at the live plot. Keeping these as separate files lets each one
mock the seam it needs in tests without inheriting the entire Plotly
surface.

## End-to-end: one redraw

Take "user opens Find Gaps, picks a threshold, the plot updates". The
sequence is:

```
panel (FindGaps.vue)
   │
   │  validates inputs, sets store state
   ▼
useFilterDispatch / useQcScript
   │
   │  selectedSeries.data.dispatchFilter(FIND_GAPS, args)
   ▼
qc-utils (worker or inline)
   │
   │  mutates typed arrays + appends a HistoryItem
   ▼
plotly store (Pinia)
   │
   │  redraw() reads ObservationRecord, calls
   │  createPlotlyOption(graphSeriesArray) -> PlotlyChartOptions
   ▼
options.ts                 [building the triple]
   │
   │  trace builders, axis layout, gap overlay assembly,
   │  qualifier-band markers, density-based marker visibility
   ▼
events.ts                  [pushing the triple into Plotly]
   │
   │  handleNewPlot:
   │    Plotly.react(gd, traces, layout, config)
   │    installs plotly_click / plotly_relayout / select listeners
   │    installs zoom tracking, mousemove crosshair, axis chips
   ▼
Plotly runs                [GL render, then quiescent]
   │
   │  emits plotly_relayout for the initial layout pass
   ▼
relayout.ts                [post-render reconcile]
   │
   │  handleRelayout:
   │    recompute visible-point count
   │    drop scattergl marker opacity above DENSITY_HIDE_MARKERS
   │    realign ticks via computeIntendedTickvals when cadence is known
   ▼
selected.ts                [if the relayout carries selection echo]
   │
   │  handleSelected({ fromRelayout: true }):
   │    compare current trace.selectedpoints against
   │    suppressedEchoSelection sentinel; suppress when equal,
   │    dispatch SELECTION when different
```

The user-visible result is one frame painted by Plotly. The code path
to get there crosses four files in the plotting layer plus the qc-utils
dispatch boundary.

## End-to-end: one selection

User box-selects on the plot:

```
Plotly emits plotly_selected
   │
   ▼
events.ts wires it to selected.ts#handleSelected (no fromRelayout flag)
   │
   ▼
selected.ts
   │  read trace.selectedpoints
   │  offset by _windowStartIdx (the windowed-trace start)
   │  write to dataVis.selectedData (Pinia)
   │  dispatch SELECTION filter to qc-utils
   ▼
qc-utils HistoryItem is appended
   │
   ▼
Edit panels see a non-empty selectedData and enable their Apply
buttons; the SELECTION HistoryItem is what gets serialised in the QC
script.
```

The `_windowStartIdx` offset is the part most new readers miss. The
trace's `x` / `y` arrays carry only the visible window. When the user
zooms in on a 10M-point datastream, Plotly receives ~100k points, not
10M. Selection indices come back relative to that windowed slice. The
offset on `AppPlotlyTrace` records where the window started, so the
store gets indices into the full ObservationRecord.

## The suppressed-echo sentinel

When the app writes to `selectedpoints` programmatically (undo /
redo / clear-on-replay), Plotly echoes back a `plotly_relayout`
that looks like a fresh user selection. The naive handler would
dispatch a duplicate SELECTION on every undo and break the redo
stack.

The fix lives in two places:

1. **The writers** (`setSelectedPoints` in `operations.ts`,
   `clearSelected` in the dataVisualization store) arm
   `plotly.suppressedEchoSelection` with the payload they're about
   to write. One-shot, cleared on read.

2. **`handleSelected` in `selected.ts`** consults the sentinel only
   on the relayout-induced branch (`fromRelayout: true`). If the
   trace's current `selectedpoints` matches the sentinel, the call
   is an echo, so skip the dispatch. If it doesn't match, a real
   user gesture raced through the same debounce window, so dispatch
   normally.

Click-induced and direct-call paths bypass the sentinel entirely.
A user click always dispatches.

## The `isUpdating` flag

A coarser sibling of the echo sentinel. Set true by undo / redo /
dispatch-helper composables; while it's set, `handleSelected` skips
dispatch. Without it, a programmatic re-render after a HistoryItem
replay would look like a user selection and append another item to
the history. Cleared once the redraw is back in steady state.

## Why `internal.ts` isn't re-exported

`plotly.ts` is a barrel for everything the rest of the app needs.
`internal.ts` carries shared private helpers that should not leak
out: they're cross-module conveniences for the plotting layer
itself. Keeping the barrel narrow is what stops a Vue component
from reaching in and pulling `traceXAsNumbers` directly.

## Testing seams

Each file is unit-tested where it makes sense:

- `options.ts`, `selected.ts`, `zoom.ts`, `relayout.ts` are pure
  enough that fake Plotly objects suffice. Have dedicated specs.
- `events.ts`, `interaction.ts`, `operations.ts`, `staging.ts` are
  excluded from coverage (see `vite.config.ts:113-119`). Each one
  ultimately calls into Plotly's DOM-staging surface and mocking
  the full pixel-to-data conversion adds setup cost for marginal
  signal. Exercised via Playwright instead.
- `internal.ts` is covered transitively by the seams that import it.

The QC-app side stops at the dispatch boundary. Worker-pool tests,
calibration tests, and kernel correctness tests live in `qc-utils`.

## See also

- [ARCHITECTURE.md](./ARCHITECTURE.md) for system-level architecture
- [PERFORMANCE.md](./PERFORMANCE.md) for viewport windowing and
  scattergl density tradeoffs
- `src/store/plotly.ts` is the Pinia store this layer reads + writes
