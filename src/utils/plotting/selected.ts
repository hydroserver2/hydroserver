import { usePlotlyStore } from '@/store/plotly'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import type {
  PlotData,
  PlotMouseEvent,
  PlotRelayoutEvent,
  PlotSelectionEvent,
} from 'plotly.js-dist'
import { EnumFilterOperations } from '@uwrl/qc-utils'
import type { AppPlotlyTrace } from './options'

/**
 * `handleSelected` is called from `handleClick` (with a `PlotMouseEvent`),
 * from `handleRelayout` (with a `PlotRelayoutEvent`-shaped object), and
 * occasionally with `null`/`undefined` to mean "re-sync the QC selection
 * without dispatching a filter".
 *
 * The SELECTION-dispatch branch is the source-of-truth for "user just
 * selected something on the plot". To distinguish a real user gesture
 * from the relayout echo of our own programmatic Plotly writes
 * (`setPlotSelection`, `clearSelected`), the writers arm
 * `suppressedEchoSelection` with the indices their write will land
 * on. When the next `plotly_relayout`-induced `handleSelected` call
 * fires (`fromRelayout: true`) we compare the trace's actual
 * `selectedpoints` against that expected payload — equal means the
 * echo (skip dispatch); different means a user gesture (box / lasso
 * select) raced through the same debounce window, so dispatch
 * normally. The click-induced path (`fromRelayout` falsy, default)
 * ignores the sentinel entirely — user clicks always dispatch.
 */
export const handleSelected = async (
  eventData?: PlotMouseEvent | PlotRelayoutEvent | PlotSelectionEvent | null,
  opts: { fromRelayout?: boolean } = {}
) => {
  const { plotlyRef, selectedSeries, isUpdating, suppressedEchoSelection } =
    storeToRefs(usePlotlyStore())
  const { selectedData } = storeToRefs(useDataVisStore())
  const { qcDatastream } = storeToRefs(useDataVisStore())

  const trace = plotlyRef.value?.data.find(
    (t: Partial<PlotData>) => (t as AppPlotlyTrace).id == qcDatastream.value?.id
  ) as (AppPlotlyTrace & { selectedpoints?: number[] }) | undefined

  // Plotly's `selectedpoints` are indices into the *windowed* x/y
  // arrays; offset by the window's start position before storing.
  const windowOffset = (trace as AppPlotlyTrace)?._windowStartIdx ?? 0
  const rawSelected = trace?.selectedpoints
  selectedData.value = rawSelected?.length
    ? rawSelected.map((i) => i + windowOffset)
    : null

  const relayout = eventData as Partial<PlotRelayoutEvent> | null | undefined
  if (
    relayout?.dragmode || // Changing selected tool
    relayout?.['xaxis.range[0]'] // Zooming
  ) {
    return
  }

  // Only dispatch the SELECTION filter on user gestures. Two
  // suppression signals layer here:
  //
  //  1. `isUpdating` — set by undo/redo and dispatch-helper composables
  //     so a programmatic re-render doesn't echo back as a SELECTION
  //     and clobber the redo stack.
  //  2. `suppressedEchoSelection` — payload-keyed sentinel armed by
  //     `setPlotSelection` / `clearSelected`. We always clear it (one-
  //     shot), but only suppress when the current selection MATCHES
  //     what the echo should carry. A mismatch means a real user
  //     gesture overlapped the programmatic write's debounce window,
  //     and dropping it would be the bug we're guarding against.
  //     Click and direct-call paths bypass — they're real gestures.
  if (opts.fromRelayout && suppressedEchoSelection.value != null) {
    const expected = suppressedEchoSelection.value
    suppressedEchoSelection.value = null
    const current = selectedData.value ?? []
    if (sameSelection(expected, current)) return
  }
  if (eventData && !isUpdating.value) {
    await selectedSeries.value?.data.dispatchFilter(
      EnumFilterOperations.SELECTION,
      selectedData.value ?? []
    )
  }
}

/** Order-preserving equality for selection payloads. Selection
 *  arrays are produced sorted by both Plotly and our setters, so a
 *  positional compare is enough — no need to allocate a Set. */
const sameSelection = (a: number[], b: number[]): boolean => {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false
  }
  return true
}
