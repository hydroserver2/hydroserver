import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import {
  formatDate,
  findFirstGreaterOrEqual,
  findLastLessOrEqual,
} from '@uwrl/qc-utils'
import {
  clearSelection,
  handleSelected,
  setSelectedPoints,
} from '@/utils/plotting/plotly'
import type {
  AppPlotlyTrace,
  AppPlotRelayoutEvent,
} from '@/utils/plotting/plotly'
import { storeToRefs } from 'pinia'

import { computed } from 'vue'

export function useDataSelection() {
  const { plotlyRef } = storeToRefs(usePlotlyStore())
  const { selectedSeries } = storeToRefs(usePlotlyStore())
  const { selectedData } = storeToRefs(useDataVisStore())

  /**
   * Locate the plotly trace index for the QC series we're editing.
   * Traces are rendered in the order: non-QC → QC → qualifier band, so
   * the old `data.length - 1` shortcut targeted the last qualifier-band
   * trace whenever a qualifier band was present — selected points were
   * written to an invisible trace, which matched the reported bug: the
   * "N points selected" label still tracked `selectedData`, but the QC
   * trace had no `selectedpoints` and nothing was highlighted. Match by
   * the series id (the QC trace is tagged with `selectedSeries.id` in
   * `createPlotlyOption`) and fall back to the trailing trace only when
   * a match can't be found.
   */
  const qcTraceIndex = (): number => {
    const data = plotlyRef.value?.data
    if (!data?.length) return -1
    const id = selectedSeries.value?.id
    if (id) {
      const idx = data.findIndex((t) => (t as AppPlotlyTrace).id == id)
      if (idx !== -1) return idx
    }
    return data.length - 1
  }

  /** Dispatch selection  */
  const dispatchSelection = async (selection: number[]) => {
    const traceIndex = qcTraceIndex()
    if (traceIndex < 0) return
    await setSelectedPoints(plotlyRef.value, traceIndex, selection)

    // Authoritative assignment: we already hold the indices returned by
    // dispatchFilter, so write them straight into the store rather than
    // round-tripping through Plotly trace introspection.
    selectedData.value = [...selection]
  }

  /**
   * Call this method after operations that change the order of elements or
   * remove elements in the data.
   *
   * `dispatchFilter` controls whether the Plotly-event-driven
   * `handleSelected` flow runs, which issues an extra empty-SELECTION
   * filter dispatch through `ObservationRecord.dispatchFilter`. That path
   * can be surprisingly expensive (a reactive history push + Vue flush +
   * devtools serialization of the whole series). Callers that have just
   * logged their own SELECTION entry (e.g. table bulk save) should pass
   * `false` to skip the redundant round-trip.
   */
  const clearSelected = async ({
    dispatchFilter = true,
  }: { dispatchFilter?: boolean } = {}) => {
    const { selectedData } = storeToRefs(useDataVisStore())

    const traceIndex = qcTraceIndex()
    if (traceIndex >= 0) {
      await clearSelection(plotlyRef.value, traceIndex)
    }

    selectedData.value = []

    if (dispatchFilter) {
      // Pass an empty event so `handleSelected` dispatches an empty
      // selection filter to ObservationRecord.
      handleSelected({} as AppPlotRelayoutEvent)
    }
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
