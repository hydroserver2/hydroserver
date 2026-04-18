import { GraphSeries } from '@/types'
import { defineStore, storeToRefs } from 'pinia'
import { computed, Ref, ref } from 'vue'
import { HistoryItem } from "@uwrl/qc-utils"
import { useDataVisStore } from './dataVisualization'

import {
  applyTraceUpdate,
  createPlotlyOption,
  cropXaxisRange,
} from '@/utils/plotting/plotly'
import type {
  AppPlotlyHTMLElement,
  AppPlotlyTrace,
  PlotlyChartOptions,
} from '@/utils/plotting/plotly'
import { useObservationStore } from './observations'
import { Datastream } from '@hydroserver/client'

export const usePlotlyStore = defineStore('Plotly', () => {
  const showLegend = ref(true)
  const showTooltip = ref(false)
  const isUpdating = ref(false)
  const isSubmitting = ref(false)
  const tooltipsMaxDataPoints = ref(10 * 1000)
  const visiblePoints: Ref<number> = ref(0)
  const areTooltipsEnabled = ref(true)
  const showCoordinates = ref(false)
  const hover = ref({ x: 0, y: 0 })

  const graphSeriesArray = ref<GraphSeries[]>([])

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

  const clearChartState = () => {
    graphSeriesArray.value = []
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
   */
  async function redraw(recomputeXaxisRange?: boolean) {
    updateOptions()

    const opts = plotlyOptions.value
    if (!opts) return

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
    } as GraphSeries
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
    previewMode,
  }
})
