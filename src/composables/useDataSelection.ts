import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import {
  formatDate,
  findFirstGreaterOrEqual,
  findLastLessOrEqual,
} from '@uwrl/qc-utils'
import { handleSelected } from '@/utils/plotting/plotly'
import { storeToRefs } from 'pinia'

// @ts-ignore no type definitions
import Plotly from 'plotly.js-dist'
import { computed } from 'vue'

export function useDataSelection() {
  const { plotlyRef } = storeToRefs(usePlotlyStore())
  const { selectedSeries } = storeToRefs(usePlotlyStore())
  const { selectedData } = storeToRefs(useDataVisStore())

  /** Dispatch selection  */
  const dispatchSelection = async (selection: number[]) => {
    await Plotly.update(
      plotlyRef.value,
      {
        selections: [], // Removes the selected areas
        selectedpoints: [selection], // Plotly expects one array per trace (even if updating a single trace).
      },
      {},
      [plotlyRef.value?.data.length - 1]
    )

    await handleSelected(false)
  }

  /** Call this method after operations that change the order of elements or remove elements in the data */
  const clearSelected = async () => {
    const { selectedData } = storeToRefs(useDataVisStore())

    // Removes selected areas
    await Plotly.update(
      plotlyRef.value,
      {},
      { selections: [], selectedpoints: [[]] },
      [plotlyRef.value?.data.length - 1]
    )

    // Updates the color
    await Plotly.restyle(plotlyRef.value, {
      selectedpoints: [[]],
    })

    selectedData.value = []

    handleSelected(true)
  }

  const startDate = computed(() => {
    let datetime = selectedSeries.value?.data.beginTime
    if (selectedData.value?.length) {
      const startIndex = selectedData.value[0] as number
      datetime =
        new Date(plotlyRef.value?.data[0].x[startIndex]) ||
        selectedSeries.value?.data.beginTime
    }
    return datetime ?? new Date()
  })

  const endDate = computed(() => {
    let datetime = selectedSeries.value?.data.endTime
    if (selectedData.value?.length) {
      const endIndex = selectedData.value[
        selectedData.value.length - 1
      ] as number
      datetime =
        new Date(plotlyRef.value?.data[0].x[endIndex]) ||
        selectedSeries.value?.data.endTime
    }
    return datetime ?? new Date()
  })

  const startDateString = computed(() =>
    startDate.value ? formatDate(startDate.value) : ''
  )

  const endDateString = computed(() =>
    endDate.value ? formatDate(endDate.value) : ''
  )

  /** Select all data points within the given date range */
  const selectDateRange = async (from: Date, to: Date) => {
    const dataX = selectedSeries.value?.data.dataX
    if (!dataX?.length) return

    const fromTs = from.getTime()
    const toTs = to.getTime()

    const startIdx = findFirstGreaterOrEqual(dataX, fromTs)
    const endIdx = findLastLessOrEqual(dataX, toTs)

    if (startIdx > endIdx) return

    const selection: number[] = []
    for (let i = startIdx; i <= endIdx; i++) {
      selection.push(i)
    }

    await dispatchSelection(selection)
  }

  return {
    dispatchSelection,
    clearSelected,
    startDate,
    endDate,
    startDateString,
    endDateString,
    selectDateRange,
  }
}
