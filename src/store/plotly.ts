import { GraphSeries } from '@/types'
import { defineStore, storeToRefs } from 'pinia'
import { computed, Ref, ref } from 'vue'
import { HistoryItem } from "@uwrl/qc-utils"
import type { LayoutAxis, PlotData } from 'plotly.js-dist'
import { useDataVisStore } from './dataVisualization'

import {
  applyTraceUpdate,
  COLORS,
  createPlotlyOption,
  cropXaxisRange,
  labelColorFor,
  LABEL_COLORS,
} from '@/utils/plotting/plotly'
import type {
  AppPlotlyHTMLElement,
  AppPlotlyTrace,
  AxisChip,
  PlotlyChartOptions,
} from '@/utils/plotting/plotly'
import { useObservationStore } from './observations'
import { Datastream } from '@hydroserver/client'

export interface ZoomState {
  xRange: [number, number] | null
  yRanges: Record<string, [number, number]>
  /** Where the state came from; drives tooltip wording on the undo/redo buttons. */
  source: 'init' | 'user' | 'preset' | 'fitX' | 'fitY'
}

export const usePlotlyStore = defineStore('Plotly', () => {
  const showLegend = ref(true)
  const showTooltip = ref(false)
  const isUpdating = ref(false)
  const isSubmitting = ref(false)
  // Persisted as a user preference — large plots are cheap on fast machines
  // and expensive on slow ones, so let the user pick. Bounded in the UI
  // but not hard-clamped here so power users can override via storage.
  // Persistence is wired through pinia-plugin-persistedstate at the
  // bottom of this store.
  const tooltipsMaxDataPoints = ref<number>(10 * 1000)
  const visiblePoints: Ref<number> = ref(0)
  // Two-mode toggle for individual data-point rendering / hover.
  //   - 'manual' — user controls on/off via `tooltipsManualEnabled`.
  //                Threshold ignored.
  //   - 'auto'   — threshold-driven: on while visiblePoints <=
  //                threshold, off otherwise. Default keeps backward
  //                behavior for existing users.
  const tooltipsMode = ref<'manual' | 'auto'>('auto')
  // Persisted on/off state for `manual` mode. Ignored when mode is
  // `auto`. Defaults to `true` so the first manual click feels like
  // an explicit toggle off.
  const tooltipsManualEnabled = ref(true)
  // Derived "is hover currently rendering?" — read by the relayout
  // pipeline and the toolbar UI. Auto mode reads the live threshold;
  // manual mode reads the user's explicit on/off.
  const areTooltipsEnabled = computed(() => {
    if (tooltipsMode.value === 'manual') return tooltipsManualEnabled.value
    return visiblePoints.value <= tooltipsMaxDataPoints.value
  })
  const showCoordinates = ref(false)
  // `x` is the numeric epoch under the cursor. `y` is rendered as a
  // pre-rounded string (toFixed(4)) by interaction.ts so the readout
  // chip can use it directly without further formatting.
  const hover = ref<{ x: number; y: number | string }>({ x: 0, y: 0 })

  /**
   * Crosshair droplines (horizontal to the QC y-axis, vertical to the
   * x-axis) rendered as CSS lines in `Plot.vue`. Positions are pixels
   * relative to the plot root element and are written by
   * `processMouseMove` on every frame. Lives outside Plotly's
   * `showspikes` because the built-in spikes are gated on
   * `hoverinfo !== 'skip'` and so disappear when tooltips auto-
   * disable at high point counts — users want the crosshair to stay
   * regardless of tooltip state. The CSS driver also avoids the
   * noticeable lag behind the cursor that Plotly's spike layer has
   * on scattergl.
   */
  const crosshair = ref({
    visible: false,
    cursorX: 0,
    cursorY: 0,
    plotLeft: 0,
    plotBottom: 0,
  })

  const graphSeriesArray = ref<GraphSeries[]>([])

  /**
   * Datastream IDs whose non-QC right-side y-axis is currently hidden.
   * `createPlotlyOption` reads this while building overlay axes and
   * sets `visible: false` on matches — the trace itself keeps
   * rendering, only the axis chrome (line, ticks, labels, title) goes
   * away, and autoshift reclaims the column's horizontal space. Keyed
   * by datastream id so trace reorders and QC promotions don't
   * invalidate the preference.
   */
  const hiddenAxisIds = ref<Set<string>>(new Set())

  /**
   * Eye-toggle state. Datastream ids whose main + gap-overlay traces
   * are hidden on the plot via the per-row toggle in
   * `PlottedDatastreams`. Lifted to the store (it lived as local
   * component state) so the share URL can reflect it; the toggle
   * itself still drives `Plotly.restyle` calls inside
   * `PlottedDatastreams`. Datastreams not present in the set are
   * visible.
   */
  const hiddenTraceIds = ref<Set<string>>(new Set())

  /**
   * Active center-column tab. `'plot'` shows the Plotly chart,
   * `'table'` shows the editable observation table. Lifted out of
   * `Plot.vue`'s local state so the share URL can capture which tab
   * the sender was looking at.
   */
  const activeTab = ref<'plot' | 'table'>('plot')

  /**
   * Horizontal title chips rendered above each non-QC right-side axis
   * (see `.plot-axis-chip` in Plot.vue). Replaces Plotly's rotated
   * vertical axis titles — horizontal text is much easier to scan
   * when several right-side axes stack up. Populated by
   * `updateAxisChips` after each plot/relayout; each entry carries
   * the datastream id, the axis line's pixel position (for
   * alignment), the label text, and the series' label colour.
   */
  const axisChips = ref<AxisChip[]>([])

  /**
   * Toggles a lightweight preview layout in `createPlotlyOption`: the
   * qualifier flag band, the plot title, select/lasso modebar buttons,
   * and the custom Y-autoscale button are all suppressed. Plot.vue
   * flips this based on its `preview` prop so the Select-view chart
   * stays uncluttered.
   */
  const previewMode = ref(false)
  /** The index of the series that represents the datastream selected for quality control */
  const selectedSeriesIndex = computed(() => {
    const { qcDatastream } = storeToRefs(useDataVisStore())
    if (qcDatastream?.value?.id) {
      return graphSeriesArray.value.findIndex(
        (s) => s.id === qcDatastream.value?.id
      )
    }
    return -1
  })

  /** The edit history for the currently selected series */
  const editHistory: Ref<HistoryItem[]> = ref([])

  /**
   * Sentinel armed by programmatic Plotly writes (`setPlotSelection`,
   * `clearSelected`). When the next `plotly_relayout`-induced
   * `handleSelected` call fires, we compare the current selection
   * against this expected payload — if they match it's the echo of
   * our own write (skip the SELECTION dispatch); if they differ a
   * user gesture (box/lasso select) raced through the same debounce
   * window, so we let the dispatch proceed. `handleClick` (the
   * direct-call user-gesture path) ignores the sentinel entirely.
   *
   * `null` = nothing armed. An array (possibly empty) = "expect this
   * exact selection on the next relayout echo".
   */
  const suppressedEchoSelection: Ref<number[] | null> = ref(null)

  const selectedSeries = computed(() => {
    return graphSeriesArray.value[selectedSeriesIndex.value]
  })

  // Initialize to an empty-trace PlotlyChartOptions so consumers can read
  // `plotlyOptions.value.traces` etc. without null-guards. 
  const plotlyOptions: Ref<PlotlyChartOptions> = ref(createPlotlyOption([]))
  const plotlyRef: Ref<AppPlotlyHTMLElement | null> = ref(null)
  // ^ Populated during DataVisualization onMounted hook (handleNewPlot).
  /**
   * Monotonic counter bumped once per `handleNewPlot` run. `Plotly.newPlot`
   * reuses the same DOM element (so `plotlyRef.value`'s identity does not
   * change) but purges every externally-attached event listener — code
   * outside `handleNewPlot` that subscribes to `plotly_relayout` /
   * `plotly_restyle` (e.g. `ContextPlot.vue`) needs a positive signal to
   * re-attach. Watch this ref instead of trying to detect element
   * re-creation.
   */
  const mainPlotEpoch = ref(0)

  /**
   * This function searches through the Pinia store's GraphSeries[] to determine which colors,
   * are currently in use. It then selects and returns
   * the first color that is not already being used in any of the graph series.
   *
   * @returns {string} - Hex code of the first available color that is not in use. Returns black as a default if all are in use.
   */
  // function assignColor(): string {
  //   const usedColors = new Set(
  //     graphSeriesArray.value.map((s) => s.seriesOption.itemStyle?.color)
  //   )

  //   for (const color of LineColors) {
  //     if (!usedColors.has(color)) {
  //       return color
  //     }
  //   }

  //   return '#000000'
  // }

  /**
   * Zoom history — separate from `editHistory` (which tracks QC data
   * edits). Each entry captures the plot's visible ranges at a point in
   * time so the user can step back/forward through viewport changes.
   *
   * The stacks are mutated by the debounced recorder in
   * `utils/plotting/plotly.ts` and restored via `undoZoom` / `redoZoom`.
   * `suppressZoomHistory` is flipped on during programmatic restores to
   * keep the recorder from re-capturing what we just set.
   */
  const zoomUndoStack = ref<ZoomState[]>([])
  const zoomRedoStack = ref<ZoomState[]>([])
  const suppressZoomHistory = ref(false)
  const ZOOM_HISTORY_CAP = 50

  const canUndoZoom = computed(() => zoomUndoStack.value.length > 1)
  const canRedoZoom = computed(() => zoomRedoStack.value.length > 0)

  /**
   * Live ranges currently shown on the plot. Top of the undo stack
   * after every relayout (zoom, pan, axis drag) — `null` when nothing
   * has been recorded yet (initial mount before the first layout
   * settles). The share URL watcher subscribes to this so the link
   * reflects the latest viewport without poking into the stack
   * internals.
   */
  const currentZoom = computed<ZoomState | null>(() => {
    const stack = zoomUndoStack.value
    return stack.length ? (stack[stack.length - 1] as ZoomState) : null
  })

  /**
   * Zoom state seeded from a share URL. Set by the URL hydrator before
   * the plot is drawn for the first time. `Plot.vue`'s mount hook
   * checks this after the initial `handleNewPlot` and, when present,
   * applies the ranges via `Plotly.relayout` then clears the ref. Null
   * means "no URL-supplied zoom, render at the default fit."
   */
  const pendingShareZoom = ref<ZoomState | null>(null)

  function clearZoomHistory() {
    zoomUndoStack.value = []
    zoomRedoStack.value = []
  }

  /** Push `state` onto the undo stack. Called by the debounced recorder. */
  function pushZoomState(state: ZoomState) {
    zoomUndoStack.value.push(state)
    if (zoomUndoStack.value.length > ZOOM_HISTORY_CAP) {
      zoomUndoStack.value.shift()
    }
    // Any new user-initiated zoom invalidates the redo history.
    zoomRedoStack.value = []
  }

  const clearChartState = () => {
    graphSeriesArray.value = []
    clearZoomHistory()
  }

  /**
   * Set the initial chart options.
   */
  function updateOptions() {
    // The cast pins the array shape so vue-tsc's structural check
    // against qc-utils' deep ObservationRecord type doesn't blow up
    // on the public PlotlyChartOptions param. `graphSeriesArray` is
    // already typed as `GraphSeries[]`.
    plotlyOptions.value = createPlotlyOption(graphSeriesArray.value as GraphSeries[])
  }

  /**
   * Use this function to update the chart after the data has mutated.
   * @param recomputeXaxisRange Useful for when an operation can add or delete elements in the array and the axis range needs to be updated.
   * @param preserveZoom When true (default), the current live x/y ranges
   *   are copied onto the fresh layout so QC edits don't reset the user's
   *   zoom. Pass `false` when the caller *wants* the new layout's default
   *   range to apply — notably when the user changed the date filter
   *   (`useDataVisStore#setDateRange`), where preserving the old range
   *   would defeat the action.
   */
  async function redraw(
    recomputeXaxisRange?: boolean,
    preserveZoom: boolean = true
  ) {
    updateOptions()

    const opts = plotlyOptions.value
    if (!opts) return

    // `createPlotlyOption` rebuilds the layout with default axis ranges
    // every call. Passing that straight to `Plotly.update` would clobber
    // the user's current zoom/pan on every edit. Copy the live axis
    // ranges from the current plot into the fresh layout so the viewport
    // survives the update. `recomputeXaxisRange` below re-clips the
    // x-axis when an operation can change the data extent.
    const liveLayout = preserveZoom
      ? (plotlyRef.value?.layout as
        | Record<string, Partial<LayoutAxis> | unknown>
        | undefined)
      : undefined
    if (liveLayout) {
      const layoutRecord = opts.layout as Record<string, unknown>
      for (const key of Object.keys(layoutRecord)) {
        if (key !== 'xaxis' && !key.startsWith('yaxis')) continue
        const nextAxis = layoutRecord[key] as Partial<LayoutAxis> | undefined
        const liveAxis = liveLayout[key] as Partial<LayoutAxis> | undefined
        const liveRange = liveAxis?.range as
          | Array<string | number>
          | undefined
        if (nextAxis && liveRange) {
          nextAxis.range = [...liveRange]
          nextAxis.autorange = false
        }
      }
    }

    // Update all traces. `opts.traces` is `Data[]`; each entry carries the
    // QC-app trace shape (`AppPlotlyTrace`) including numeric `x`/`y`.
    // `Plotly.update` accepts an array-of-arrays for multi-trace updates
    // but the published `Partial<PlotData>` types `x`/`y` as a single
    // Datum[]; cast through `unknown` to bypass that narrow shape.
    await applyTraceUpdate(
      plotlyRef.value,
      {
        x: opts.traces.map((t) => (t as AppPlotlyTrace).x),
        y: opts.traces.map((t) => (t as AppPlotlyTrace).y),
      } as unknown as Partial<PlotData>,
      opts.layout
    )

    if (recomputeXaxisRange) {
      await cropXaxisRange()
    }
  }

  const fetchGraphSeries = async (
    datastream: Datastream,
    start: Date,
    end: Date
  ): Promise<GraphSeries> => {
    const { fetchObservationsInRange } = useObservationStore()

    const data = await fetchObservationsInRange(datastream, start, end)

    if (!data.dataset.source.x) {
      await data.reload()
    }

    // HydroServer returns full `observedProperty` / `unit` objects on
    // the wire even though the published `Datastream` type only carries
    // their ids. The catalog endpoint enriches the response, so we
    // narrow with an inline shape rather than swapping the public type
    // (callers throughout the app still pass plain `Datastream`).
    const enriched = datastream as Datastream & {
      observedProperty?: { name?: string }
      unit?: { symbol?: string }
    }
    const propName = enriched.observedProperty?.name
    const unitSymbol = enriched.unit?.symbol
    const yAxisLabel =
      propName && unitSymbol
        ? `${propName} (${unitSymbol})`
        : propName || unitSymbol || 'Unknown'

    return {
      id: datastream.id,
      name: datastream.name,
      data,
      yAxisLabel,
      // Colour assignment is deferred to `assignSeriesColors`, which
      // runs once after every refresh against the full ordered list
      // of plotted datastreams. Doing it here used to read a stale
      // `graphSeriesArray` when several series cold-loaded in
      // parallel (each `Promise.all` branch saw the array before the
      // other branches' pushes had landed), so two new series could
      // both claim `COLORS[1]` and the same reload would re-roll
      // different colour pairs depending on fetch-completion order.
      // Leave a sentinel here; the post-refresh assigner fills it in.
      color: '',
      intendedSpacingMs: spacingMsFromDatastream(datastream),
    } as GraphSeries
  }

  /**
   * Convert a datastream's declared `intendedTimeSpacing` (+ unit) into
   * milliseconds. Returns null when either field is missing or unusable
   * so the plotter falls back to drawing lines through every gap.
   */
  function spacingMsFromDatastream(
    ds: Datastream | (Datastream & { intendedTimeSpacing?: number; intendedTimeSpacingUnit?: string | null })
  ): number | null {
    const raw = (ds as { intendedTimeSpacing?: number }).intendedTimeSpacing
    const n = Number(raw)
    if (!Number.isFinite(n) || n <= 0) return null
    const unit = (ds as { intendedTimeSpacingUnit?: string | null })
      .intendedTimeSpacingUnit
    switch (unit) {
      case 'seconds':
        return n * 1000
      case 'minutes':
        return n * 60 * 1000
      case 'hours':
        return n * 60 * 60 * 1000
      case 'days':
        return n * 24 * 60 * 60 * 1000
      default:
        return null
    }
  }

  /**
   * Deterministically (re)assign non-QC line colours across the
   * currently plotted series. Walks `orderedIds` (the legend order
   * from `plottedDatastreams`) once. Series that already carry a
   * non-empty `color` keep it; series with the empty-string sentinel
   * claim the first `COLORS[1..]` slot not held by an earlier series
   * in the walk.
   *
   * Race-safe because the walk is synchronous and reads the array
   * exactly once. Stable across reloads because the walk order is
   * the user-facing legend order, not fetch-completion order — so
   * the same `plottedDatastreams` configuration yields the same
   * colour assignment every time.
   *
   * If every slot is already in use, the assigner wraps back to
   * `COLORS[1]` rather than touching `COLORS[0]`, which is reserved
   * for the QC datastream.
   */
  function assignSeriesColors(orderedIds: string[]): void {
    const byId = new Map(graphSeriesArray.value.map((s) => [s.id, s]))
    const used = new Set<string>()
    // First pass: collect colours already locked in.
    for (const id of orderedIds) {
      const series = byId.get(id)
      if (series && series.color) used.add(series.color)
    }
    // Second pass: fill the gaps, claiming the first free slot.
    let nextHint = 1
    for (const id of orderedIds) {
      const series = byId.get(id)
      if (!series || series.color) continue
      let pick = ''
      // Start from where we last paused so the worst case is linear
      // in `COLORS.length`, not quadratic in `orderedIds.length`.
      for (let i = nextHint; i < COLORS.length; i++) {
        if (!used.has(COLORS[i] as string)) {
          pick = COLORS[i] as string
          nextHint = i + 1
          break
        }
      }
      if (!pick) pick = COLORS[1]!
      series.color = pick
      used.add(pick)
    }
  }

  /**
   * Resolve the render colour for a plotted datastream. The QC
   * datastream is always black; every other datastream uses the colour
   * persisted on its `GraphSeries` when it was added to the plot.
   */
  function colorForDatastream(id: string | undefined): string {
    if (!id) return COLORS[1]!
    const { qcDatastream } = storeToRefs(useDataVisStore())
    if (qcDatastream.value?.id === id) return COLORS[0]!
    const series = graphSeriesArray.value.find((s) => s.id === id)
    // `||` (not `??`) so the empty-string sentinel emitted by
    // `fetchGraphSeries` before `assignSeriesColors` runs also falls
    // back gracefully. Downstream Plotly options need a real colour
    // string; rendering a swatch as "" silently breaks the chip.
    return series?.color || COLORS[1]!
  }

  /**
   * Darker companion of `colorForDatastream` for legend text. Keeps the
   * hue of the series so the row visually ties to its line colour, but
   * shifts to the darker `LABEL_COLORS` shade so the text stays legible
   * against the row background (the pastel line colours don't).
   */
  function labelColorForDatastream(id: string | undefined): string {
    if (!id) return LABEL_COLORS[1]!
    const { qcDatastream } = storeToRefs(useDataVisStore())
    if (qcDatastream.value?.id === id) return LABEL_COLORS[0]!
    const series = graphSeriesArray.value.find((s) => s.id === id)
    if (!series || !series.color) return LABEL_COLORS[1]!
    return labelColorFor(series.color)
  }

  return {
    graphSeriesArray,
    showLegend,
    showTooltip,
    selectedSeriesIndex,
    selectedSeries,
    editHistory,
    suppressedEchoSelection,
    updateOptions,
    redraw,
    clearChartState,
    colorForDatastream,
    labelColorForDatastream,
    assignSeriesColors,
    fetchGraphSeries,
    plotlyOptions,
    plotlyRef,
    mainPlotEpoch,
    isUpdating,
    isSubmitting,
    tooltipsMaxDataPoints,
    visiblePoints,
    tooltipsMode,
    tooltipsManualEnabled,
    areTooltipsEnabled,
    showCoordinates,
    hover,
    crosshair,
    hiddenAxisIds,
    hiddenTraceIds,
    activeTab,
    axisChips,
    previewMode,
    // Zoom history
    zoomUndoStack,
    zoomRedoStack,
    suppressZoomHistory,
    canUndoZoom,
    canRedoZoom,
    currentZoom,
    pendingShareZoom,
    clearZoomHistory,
    pushZoomState,
  }
}, {
  // `plotlyRef` / `graphSeriesArray` / Plotly shape caches are all
  // ephemeral (DOM handles, live chart data). Only persist the small
  // user preference so reloads keep the chosen tooltip threshold.
  persist: {
    key: 'qc.plot.tooltipsMaxDataPoints',
    pick: ['tooltipsMaxDataPoints', 'tooltipsMode', 'tooltipsManualEnabled'],
  },
})
