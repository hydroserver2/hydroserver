import { storeToRefs } from 'pinia'
import { EnumFilterOperations } from '@uwrl/qc-utils'
import { useDataSelection } from '@/composables/useDataSelection'
import { usePlotlyStore } from '@/store/plotly'

/**
 * Filter-panel dispatch helper.
 *
 * Every "Filter Data" panel (Value Threshold, Find Gaps, Change,
 * Rate of Change, Persistence, Datetime Range) shares the same
 * commit shape:
 *
 *   1. Mark the app `isUpdating` so debounced relayout handlers and
 *      undo/redo guards skip their reactive work.
 *   2. Run the qc-utils filter through the active series, getting
 *      back the indices it selected.
 *   3. Mirror the result into Plotly's `selectedpoints` for visual
 *      feedback.
 *   4. Drop `isUpdating`.
 *
 * Doing this inline in each panel produced a swamp of `setTimeout(0)`
 * + try/finally + `clearSelected`/`setPlotSelection` boilerplate that
 * drifted between panels (some called `clearSelected` first, some
 * didn't; some forgot `isUpdating`). Centralizing here keeps the
 * sequence — including the echo-suppression hand-off in
 * `setPlotSelection` — consistent.
 *
 * Returns the indices the filter produced so callers can run extra
 * UI side-effects (e.g. updating local state) without re-fetching.
 */
export function useFilterDispatch() {
  const { selectedSeries, isUpdating } = storeToRefs(usePlotlyStore())
  const { setPlotSelection, clearSelected } = useDataSelection()

  /**
   * Dispatch a filter and apply its resulting selection to the plot.
   *
   * @param method Filter enum value (e.g. `VALUE_THRESHOLD`).
   * @param args Filter-specific arguments forwarded verbatim to
   *   `ObservationRecord.dispatchFilter`. See qc-utils for the
   *   per-method signatures.
   * @returns The indices the filter produced (or `[]` if no series).
   */
  const dispatchFilter = async (
    method: EnumFilterOperations,
    ...args: any[]
  ): Promise<number[]> => {
    const series = selectedSeries.value?.data
    if (!series) return []

    isUpdating.value = true
    try {
      const indices = (await series.dispatchFilter(method, ...args)) ?? []
      await setPlotSelection(indices)
      return indices
    } finally {
      isUpdating.value = false
    }
  }

  return {
    dispatchFilter,
    /** Re-exported so panels don't need to wire `useDataSelection` separately. */
    clearSelected,
    /** Re-exported for panels that need to push a manual selection
     *  (e.g. "Re-select gaps" buttons that don't re-run the filter). */
    setPlotSelection,
  }
}
