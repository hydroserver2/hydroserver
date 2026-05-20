import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import {
  EnumFilterOperations,
  formatDate,
  findFirstGreaterOrEqual,
  findLastLessOrEqual,
} from '@uwrl/qc-utils'
import {
  clearSelection,
  setSelectedPoints,
} from '@/utils/plotting/plotly'
import type { AppPlotlyTrace } from '@/utils/plotting/plotly'
import type { PlotData } from 'plotly.js-dist'
import { storeToRefs } from 'pinia'

import { computed } from 'vue'

export function useDataSelection() {
  const { plotlyRef, suppressedEchoSelection } = storeToRefs(
    usePlotlyStore()
  )
  const { selectedSeries } = storeToRefs(usePlotlyStore())
  const { selectedData } = storeToRefs(useDataVisStore())

  /**
   * Tell the next `plotly_relayout`-induced `handleSelected` call
   * what selection to expect from this programmatic write. The
   * relayout handler compares the expected payload against the
   * trace's actual `selectedpoints` — a match is the echo (skip
   * dispatch); a mismatch means a user gesture (box / lasso select)
   * raced through the same debounce window, so dispatch normally.
   *
   * The boolean variant we used to ship swallowed those user
   * gestures: a fast box-select right after `clearSelected` got
   * collapsed into the same debounce as the clear, and the single
   * post-debounce `handleSelected` consumed the sentinel without
   * ever logging the user's selection.
   */
  const armEchoSuppression = (expected: number[]) => {
    suppressedEchoSelection.value = [...expected]
  }

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

  /**
   * Push `selection` into Plotly as the QC trace's `selectedpoints`
   * and mirror it into `selectedData`. Visual-only — does NOT push
   * a SELECTION entry into the ObservationRecord history. The
   * Plotly write triggers a `plotly_relayout` that would otherwise
   * round-trip through `handleSelected` and dispatch a SELECTION
   * filter carrying these same indices (a "selection echo"); arming
   * `suppressSelectionEchoUntil` here makes `handleSelected` skip
   * that dispatch for the next `SUPPRESS_ECHO_MS`.
   */
  const setPlotSelection = async (selection: number[]) => {
    const traceIndex = qcTraceIndex()
    if (traceIndex < 0) return
    armEchoSuppression(selection)
    await setSelectedPoints(plotlyRef.value, traceIndex, selection)
    // Authoritative assignment: we already hold the indices the
    // caller intends to highlight, so write them straight into the
    // store rather than round-tripping through Plotly trace
    // introspection.
    selectedData.value = [...selection]
  }

  /**
   * Wipe the QC trace's `selectedpoints` plus any active
   * box-/lasso-selection rectangles, and clear `selectedData`. The
   * Plotly write's relayout echo is suppressed so no phantom
   * SELECTION lands from that round-trip.
   *
   * `recordHistory` (default `true`) controls whether the clear is
   * recorded in qc-utils history — when true, an empty SELECTION is
   * dispatched, which `_selection` may use to drop the underlying
   * filter entry (the user actively cleared a filter-driven
   * selection). Programmatic callers that have already logged what
   * they want, or that are running inside a replay/undo and must not
   * mutate history (`applyReplayedSelection`, panel mount cleanup,
   * `DataTable` bulk save) should pass `recordHistory: false`.
   */
  const clearSelected = async ({
    recordHistory = true,
  }: { recordHistory?: boolean } = {}) => {
    const { selectedData, hasSelectionShape } = storeToRefs(useDataVisStore())

    const traceIndex = qcTraceIndex()
    if (traceIndex >= 0) {
      armEchoSuppression([])
      await clearSelection(plotlyRef.value, traceIndex)
    }

    selectedData.value = []
    hasSelectionShape.value = false

    if (recordHistory) {
      // Explicitly log the cleared state so qc-utils' `_selection`
      // empty-case logic (pop self, optionally pop the underlying
      // filter that drove the now-cleared selection) runs even though
      // the relayout echo is suppressed.
      await selectedSeries.value?.data.dispatchFilter(
        EnumFilterOperations.SELECTION,
        []
      )
    }
  }

  // `startDate` / `endDate` bracket the current selection, or the full
  // series when nothing is selected. The `|| fallback` arm that used to
  // sit on `new Date(...)` was dead code — `new Date()` is truthy even
  // when given `undefined` (it just produces an Invalid Date) — so the
  // fallback was unreachable. The computeds now always return a Date,
  // and the downstream string helpers stop guarding against a value
  // that can't appear.
  const traceX = (): number[] | undefined => {
    const trace = plotlyRef.value?.data[0] as Partial<PlotData> | undefined
    return trace?.x as number[] | undefined
  }

  const startDate = computed(() => {
    if (selectedData.value?.length) {
      const startIndex = selectedData.value[0] as number
      const xs = traceX()
      const ts = xs?.[startIndex]
      if (ts !== undefined) return new Date(ts)
    }
    return selectedSeries.value?.data.beginTime ?? new Date()
  })

  const endDate = computed(() => {
    if (selectedData.value?.length) {
      const endIndex = selectedData.value[
        selectedData.value.length - 1
      ] as number
      const xs = traceX()
      const ts = xs?.[endIndex]
      if (ts !== undefined) return new Date(ts)
    }
    return selectedSeries.value?.data.endTime ?? new Date()
  })

  const startDateString = computed(() => formatDate(startDate.value))
  const endDateString = computed(() => formatDate(endDate.value))

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

    await setPlotSelection(selection)
  }

  return {
    setPlotSelection,
    clearSelected,
    startDate,
    endDate,
    startDateString,
    endDateString,
    selectDateRange,
  }
}
