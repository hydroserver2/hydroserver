import { GraphSeries } from '@/types'
import { defineStore, storeToRefs } from 'pinia'
import { computed, Ref, ref } from 'vue'
import { HistoryItem } from "@uwrl/qc-utils"
import { useDataVisStore } from './dataVisualization'
// @ts-ignore no type definitions
import Plotly from 'plotly.js-dist'

import { createPlotlyOption, cropXaxisRange } from '@/utils/plotting/plotly'
import { useObservationStore } from './observations'
import { useHydroServer } from './hydroserver'
import { Datastream } from '@hydroserver/client'

export const usePlotlyStore = defineStore('Plotly', () => {
  const showLegend = ref(true)
  const showTooltip = ref(false)
  const isUpdating = ref(false)
  const tooltipsMaxDataPoints = ref(10 * 1000)
  const visiblePoints: Ref<number> = ref(0)
  const areTooltipsEnabled = ref(true)
  const showCoordinates = ref(false)
  const hover = ref({ x: 0, y: 0 })

  const graphSeriesArray = ref<GraphSeries[]>([])
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

  const plotlyOptions: Ref<any> = ref({})
  const plotlyRef: Ref<(HTMLDivElement & { [key: string]: any }) | null> =
    ref(null) // Populated during DataVisualization onMounted hook

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
    // @ts-ignore
    plotlyOptions.value = createPlotlyOption(graphSeriesArray.value)
  }

  /**
   * Use this function to update the chart after the data has mutated.
   * @param recomputeXaxisRange Useful for when an operation can add or delete elements in the array and the axis range needs to be updated.
   */
  async function redraw(recomputeXaxisRange?: boolean) {
    updateOptions()

    // Update all traces
    await Plotly.update(
      plotlyRef.value,
      {
        x: plotlyOptions.value.traces.map((t: any) => t.x),
        y: plotlyOptions.value.traces.map((t: any) => t.y),
      },
      plotlyOptions.value.layout
    )

    if (recomputeXaxisRange) {
      await cropXaxisRange()
    }
  }

  const fetchGraphSeries = async (
    datastream: Datastream,
    start: Date,
    end: Date
  ) => {
    const { fetchObservationsInRange } = useObservationStore()
    const { hs } = storeToRefs(useHydroServer())

    const observationsPromise = fetchObservationsInRange(datastream, start, end)

    const fetchUnitPromise = hs.value.units
      .get(datastream.unitId)
      .catch((error) => {
        console.error('Failed to fetch Unit:', error)
        return null
      })
    const fetchObservedPropertyPromise = hs.value.observedProperties
      .get(datastream.observedPropertyId)
      .catch((error) => {
        console.error('Failed to fetch ObservedProperty:', error)
        return null
      })

    const [data, unit, observedProperty] = await Promise.all([
      observationsPromise,
      fetchUnitPromise,
      fetchObservedPropertyPromise,
    ])

    if (!data.dataset.source.x) {
      await data.reload()
    }

    const yAxisLabel =
      observedProperty && unit
        ? `${observedProperty.data.name} (${unit.data.symbol})`
        : 'Unknown'

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
    tooltipsMaxDataPoints,
    visiblePoints,
    areTooltipsEnabled,
    showCoordinates,
    hover,
  }
})
