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
| `shapes.ts`       | `withLiveShapes`: carries the live stage band onto a fresh layout when the plot is re-created.                         |

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
useFilterDispatch / useQcHistory
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
   │    drop scattergl marker opacity above DENSITY_HIDE_MARKERS,
   │      except for scatter-only series (no gap-overlay line) which
   │      keep markers opaque regardless of the data-points toggle
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
   │  offset by _windowStartIdx (0; the record is already windowed)
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

The time-range window is applied in the **data layer**: `ObservationRecord`
keeps the full series in `rawData` but materializes only the selected
`[begin, end]` slice into `dataset.source` (`dataX` / `dataY`) via
`applyWindow(begin, end)` (qc-utils). The observations store calls it as the
window changes; a window change clears history (the new window is a fresh QC
baseline). So the record, the plot trace, the observation table and the
"pts loaded" count all reflect the same window. `createPlotlyOption` draws
the record's data directly (no slicing of its own), and selection indices
come back already aligned with the record, so `_windowStartIdx` is `0`. The
offset on `AppPlotlyTrace` is kept as a generic hook (`selected.ts` reads it,
defaulting to `0`) should a trace ever carry a sub-slice again.

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

## History snapshot series

A `GraphSeries` carrying a `snapshot` field is a frozen replay of a QC
session at one operation, not a live datastream. To `createPlotlyOption` it
is an ordinary non-QC series: it gets its own overlaying right-side axis and
its own colour from the shared assigner. That is deliberate. Being able to
shift a snapshot on its own axis is how the user lines it up against the
edit target, which is the point of plotting it.

What differs is upstream, not here: the data never refetches (see
`refreshGraphSeriesArray`'s `isSnapshotId` guard), and `PlottedDatastreams`
renders the row's provenance instead of a point count.

## Source groups and batched selection

A source datastream and every managed (QC) datastream derived from it form a
**source group**. Managed datastreams are filtered out of
`filteredDatastreams`, so the group has exactly one row in the datastreams
table, and its check box opens `PlotSourceDialog` rather than toggling.

`useDataVisStore.sourceGroupIds(sourceId)` resolves the group from
`historiesBySource`. `plotSourceSelection(sourceId, ids)` then applies the
dialog's answer as a whole: `ids` is the complete set wanted from that group,
so members absent from it are unplotted in the same pass.

Doing it in one pass matters even with nothing to promote: looping
`plotDatastream` / `unplotDatastream` would trigger a `rebuildPlot` per
change, where the batched action means exactly one, against the final set.
The plot load queue never has to absorb a burst.

Additions are appended in `ids` order, which the dialog builds in display
order (raw first, then managed). Plotting never singles one out as an edit
target, so this order only matters for the legend and axis stacking.

## Series roles

`createPlotlyOption` reads roles off the stores, not a field on `GraphSeries`:

- **Edit target** (`useDataVisStore().qcDatastream`): primary axis `y`,
  black, selectable.
- **Source context** (`sourceContextDatastream`): shares `y` with the edit
  target, grey, drawn underneath it, read-only (no selection styling, no
  own axis).
- **Everything else** (context traces, and history snapshots): overlaying
  right-side axes (`y2`, `y3`, …), same as today.
- **No edit target** (Select view): the first entry in `seriesDatastreams`
  (the first plotted datastream) takes the primary axis `y`, styled like any
  other context trace but without an axis chip.

The edit target's data reaches the plot through one store action,
`setEditRecord(record)`, which upserts its graph series. `useEditSession`
calls it instead of assigning `selectedSeries.value.data` directly.

## Context range

The plot toolbar's `TimeRangeMenu` is the one range control. With no edit
target it is the Select view's **Time range** (every preset); with one it is
the **Context** menu, which adds the source context switch and passes
`DataVisTimeFilters` the `EDITOR_PRESETS` (YTD left out, All highlighted for
a persisted YTD through `shownPresetId`). Both bind the same `beginDate` /
`endDate` store range. When the plot is not mounted (nothing plotted, or no
observations in the range), `DataVisualization` shows the menu in a toolbar
row of its own, so a window can be set before any data is pulled. Each mode remembers its own preset: `activePresetId` is `contextPresetId` while editing
and `selectedDateBtnId` otherwise, and every range action goes through it.
Picking a preset or a custom date calls `setDateRange`, which, while an
edit target is set, reloads only the context series
(`refreshGraphSeriesArray`, which never fetches the edit target) and
redraws with `redraw(false, true)` to keep the user's current zoom. The edit
target's working copy is never re-windowed by this control.

`resolvePresetWindow` is the one place that picks how a preset resolves.
While an edit target has a session window (`viewedSession`, else
`inProgressSession`), it uses `presetAroundWindow`: 1w / 1m / 6m / 1y add
their span before the window's start and after its end, and All (and a
persisted YTD) is the context data extent widened to cover the window.
Otherwise, in the Select view or before the session loads, `presetWindow`
counts back from the context data's end. The extent comes from the context
series only (`seriesDatastreams` minus the edit target and snapshots).

The context loads on `setEditTarget`'s rebuild, before the session is known.
The store watches the session window, and when it appears or changes it
re-applies the active preset through `setDateRange`: one context reload,
no edit-target fetch, zoom kept, and a no-op when the range is unchanged or
the range is Custom. It is a watch rather than a call from each session
action because the window follows every session store write (sessions
applied, a session viewed, returning to the current one, a failed view
reverted), and a missed call would silently leave the context on the wrong
range.

Plot loads run one at a time. A rebuild (`rebuildPlot`) and a range reload
(`setDateRange`) are both plot loads: a request made while one runs waits
in a single queued follow-up, which becomes a rebuild if any request it
absorbed was one, since a rebuild resolves the preset itself. So a re-anchor
that lands while a rebuild is queued joins it instead of loading on its own,
and a rebuild requested during a range reload waits for it. `setDateRange`
still moves `beginDate` / `endDate` at once, so a load already running can
find its range moved: `updateOrFetchGraphSeries` drops every response whose
range no longer matches, and the load loads the new range before drawing.
A range reload queued behind it then finds the range already loaded and
skips.

The session window is not drawn as a shape: a shape would sit over the plot,
and with `edits.shapePosition` on (needed to drag the stage band) Plotly
makes every shape grab the mouse, which blocks box select. The data shows it
instead. The edit target is one trace in QC grey (`COLORS[0]`), and its
working copy spans only the session window. The source is the context around
it, drawn light grey (`SOURCE_CONTEXT_COLOR`) and only outside
`editSessionWindow` (the viewed session's window, else the in-progress one).
`sourceContextDatastream` is that drawn source: null when the Context menu's
switch is off (`showSourceContext`), or when the user plotted the source
themselves, which then draws whole as an ordinary series and counts toward
the 4. `editSourceDatastream` is the edit target's source either way.
`setEditTarget` resets the session store when the target changes, so the
previous target's window is never applied to the new one.

- **Pieces**: `splitAroundWindow` cuts the source record into the points
  before and after the window, as `subarray` views of the same buffers, so
  nothing is copied. The main trace (which keeps the series `id`) draws the
  before points; the after points ride on a companion trace tagged
  `_partOf`, as do the gap overlays, one per piece so no line crosses the
  window. `_partOf` routes visibility toggles and replot carries to every
  trace of the series.
- **Bridge**: `bridgeAcrossWindow` adds one more `_partOf` line joining the
  source's last point before the window to the edit target's first, and the
  target's last to the source's first after it. A step wider than the
  cadence stays open, as it would inside a line. Every source trace always
  exists (pieces are empty without a window), so the trace count never
  changes between `redraw`s. `ContextPlot` draws the source with the same
  gap.
- **Loading**: the source waits for the window, and its context load passes
  the window as `exclude` to `fetchObservationsInRange`, so the window's
  observations are never requested for it. Working copies and snapshots build
  on `fetchDetachedRecord`, so they never re-window the shared record the
  plot draws; building a base over the window used to cut the plotted
  source down to the window, leaving no context.
- **Axes**: a re-plot (`handleNewPlot`) or `redraw` keeps the live y range
  only for an axis that had points drawn; an empty axis sits on Plotly's
  default range, and carrying it would put the new data off the plot. Series
  sharing an axis (the edit target and its source) share one axis chip. The window watch runs a rebuild,
  since the source's traces first appear then and only a rebuild adds
  traces. The window is part of the `loadKey` a range reload checks.

`layout.shapes` belongs to `staging.ts` alone (the `stage` band, always
`shapes[0]`). `createPlotlyOption` builds layouts without shapes, so
`Plotly.update` from `redraw` and `cropXaxisRange` leaves the band alone.
`handleNewPlot` (`events.ts`) re-creates the plot, so on a re-plot of the
live element it carries the live shapes over with `withLiveShapes`, and an
operation's staged band survives a rebuild; a first mount has no live
layout to carry anything from.

Plot rebuilds (`rebuildPlot`, run when plotted datastreams change) keep
the user's zoom while an edit target is set and drop it in the Select
view. `setEditTarget` clears the zoom history when the target changes, so
**Undo zoom** never steps back to the Select view's or a previous target's
viewports.

One `Plot` serves both views. `VisualizeData.vue` teleports a single
`DataVisualization` into whichever layout is showing, so a Select / Edit round
trip moves the Plotly graph div instead of rebuilding it: the zoom, the live
`layout.shapes` and the WebGL traces all stay. `userInterface.isPlotPreview`
(Select view, nothing being edited) drives the preview chrome; with an edit
target the full plot shows in both views, and the flag only flips alongside a
rebuild (`setEditTarget` / `clearEditTarget`). The overview strip
(`ContextPlot`) is the exception: it mounts only in the Edit view, and
draws from the current series when it does.

A share link's zoom (`pendingShareZoom`) is an explicit viewport, so it beats
the editor's default "open on the session window" for the session that link
itself opens. `plotly.shareZoomEditTarget` holds the link's `ed` target for
exactly that, and `Plot.vue` drops it at the first session window it sees: a
link without an edit target, or an editor opened later in the page's life,
zooms to its session window as usual.

While observations load, `DataVisualization.vue` keeps `Plot` mounted and
passes its loading overlay through Plot's `body-overlay` slot. The overlay
covers the plot and table body only; the toolbar stays usable and shows its
own spinner.

`Plot` draws its first frame when its plot element renders, not on mount.
The Plot tab's window item renders lazily, so a view that opens on the
Table tab (a share link with the table tab) has no element until the Plot
tab first opens; the draw waits for it. Until then `plotlyRef` is null, and
every caller that redraws an existing plot (`handleNewPlot(undefined)`)
skips, since that first draw renders the latest options anyway.

## Editor readiness

`useDataVisStore().isEditorReady` says the editor is settled: the session
window is known, the edit record is on the plot, no session is opening, and
no plot work is pending. Plot work is counted by `trackPlotWork`: every plot
load (queued or running), `setEditRecord`'s draw, and `Plot`'s first draw
from the moment its element appears through the mount delay. The edit view
binds it to `data-editor-ready` on `edit-plot-column`, which the e2e helper
`waitForEditorReady` waits on.

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
