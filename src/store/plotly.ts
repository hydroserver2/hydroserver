import { GraphSeries } from '@/types'
import { defineStore, storeToRefs } from 'pinia'
import { computed, Ref, ref } from 'vue'
import { HistoryItem } from "@uwrl/qc-utils"
import type { LayoutAxis } from 'plotly.js-dist'
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
  const areTooltipsEnabled = ref(true)
  const showCoordinates = ref(false)
  const hover = ref({ x: 0, y: 0 })

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

  const selectedSeries = computed(() => {
    return graphSeriesArray.value[selectedSeriesIndex.value]
  })

  // Initialize to an empty-trace PlotlyChartOptions so consumers can read
  // `plotlyOptions.value.traces` etc. without null-guards. 
  const plotlyOptions: Ref<PlotlyChartOptions> = ref(createPlotlyOption([]))
  const plotlyRef: Ref<AppPlotlyHTMLElement | null> = ref(null)
  // ^ Populated during DataVisualization onMounted hook (handleNewPlot).

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
    plotlyOptions.value = createPlotlyOption(graphSeriesArray.value)
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
    await applyTraceUpdate(
      plotlyRef.value,
      {
        x: opts.traces.map((t) => (t as AppPlotlyTrace).x),
        y: opts.traces.map((t) => (t as AppPlotlyTrace).y),
      },
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

    // `Datastream` already carries its `observedProperty` and `unit`
    // inline (see @hydroserver/client types), so use those directly.
    // The previous implementation re-fetched them via `hs.*.get()` and
    // indexed `.data.name` / `.data.symbol` on the `ApiResponse`
    // wrapper, which produced "undefined (undefined)" when the fetch
    // failed or the response shape shifted. Reading the embedded values
    // avoids both pitfalls and skips two superfluous network round trips.
    const propName = datastream.observedProperty?.name
    const unitSymbol = datastream.unit?.symbol
    const yAxisLabel =
      propName && unitSymbol
        ? `${propName} (${unitSymbol})`
        : propName || unitSymbol || 'Unknown'

    return {
      id: datastream.id,
      name: datastream.name,
      data,
      yAxisLabel,
      // Persist the non-QC colour on the series itself so reorders in
      // PlottedDatastreams don't reshuffle line colours. QC always renders
      // as COLORS[0] (black); we still assign a slot here so the series
      // retains its colour if it's ever demoted from QC.
      color: assignFreeColor(),
    } as GraphSeries
  }

  /**
   * Pick the first colour in `COLORS[1..]` that no currently-plotted
   * series is using. If every slot is taken, wrap back to the second
   * colour rather than reusing black (`COLORS[0]`), which is reserved
   * for the QC datastream.
   */
  function assignFreeColor(): string {
    const used = new Set(graphSeriesArray.value.map((s) => s.color))
    for (let i = 1; i < COLORS.length; i++) {
      if (!used.has(COLORS[i])) return COLORS[i]
    }
    return COLORS[1]
  }

  /**
   * Resolve the render colour for a plotted datastream. The QC
   * datastream is always black; every other datastream uses the colour
   * persisted on its `GraphSeries` when it was added to the plot.
   */
  function colorForDatastream(id: string | undefined): string {
    if (!id) return COLORS[1]
    const { qcDatastream } = storeToRefs(useDataVisStore())
    if (qcDatastream.value?.id === id) return COLORS[0]
    const series = graphSeriesArray.value.find((s) => s.id === id)
    return series?.color ?? COLORS[1]
  }

  /**
   * Darker companion of `colorForDatastream` for legend text. Keeps the
   * hue of the series so the row visually ties to its line colour, but
   * shifts to the darker `LABEL_COLORS` shade so the text stays legible
   * against the row background (the pastel line colours don't).
   */
  function labelColorForDatastream(id: string | undefined): string {
    if (!id) return LABEL_COLORS[1]
    const { qcDatastream } = storeToRefs(useDataVisStore())
    if (qcDatastream.value?.id === id) return LABEL_COLORS[0]
    const series = graphSeriesArray.value.find((s) => s.id === id)
    return series ? labelColorFor(series.color) : LABEL_COLORS[1]
  }

  return {
    graphSeriesArray,
    showLegend,
    showTooltip,
    selectedSeriesIndex,
    selectedSeries,
    editHistory,
    updateOptions,
    redraw,
    clearChartState,
    colorForDatastream,
    labelColorForDatastream,
    fetchGraphSeries,
    plotlyOptions,
    plotlyRef,
    isUpdating,
    isSubmitting,
    tooltipsMaxDataPoints,
    visiblePoints,
    areTooltipsEnabled,
    showCoordinates,
    hover,
    crosshair,
    hiddenAxisIds,
    axisChips,
    previewMode,
    // Zoom history
    zoomUndoStack,
    zoomRedoStack,
    suppressZoomHistory,
    canUndoZoom,
    canRedoZoom,
    clearZoomHistory,
    pushZoomState,
  }
}, {
  // `plotlyRef` / `graphSeriesArray` / Plotly shape caches are all
  // ephemeral (DOM handles, live chart data). Only persist the small
  // user preference so reloads keep the chosen tooltip threshold.
  persist: {
    key: 'qc.plot.tooltipsMaxDataPoints',
    pick: ['tooltipsMaxDataPoints'],
  },
})
