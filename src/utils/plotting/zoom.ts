import { usePlotlyStore, type ZoomState } from '@/store/plotly'
import Plotly from 'plotly.js-dist'
import type {
  Layout,
  LayoutAxis,
  PlotlyHTMLElement,
  PrivatePlotlyHTMLElement,
} from 'plotly.js-dist'
import { storeToRefs } from 'pinia'
import { debounce } from 'lodash-es'
import { Y_AXIS_KEY_RE } from './internal'

// --- Zoom history -----------------------------------------------------------
//
// State lives on the plotly store (stacks + suppressZoomHistory flag). This
// seam owns the Plotly-specific pieces: reading the live layout into a
// ZoomState snapshot, applying a snapshot back onto the plot, and the
// debounced recorder that listens to `plotly_relayout` on its own timer so
// it's independent of the existing relayout handler (tooltip/visible-point
// work) in `handleRelayout`.

/**
 * Read the current xaxis + yaxisN ranges from the live plot into a
 * serialisable snapshot. Returns `null` if the plot hasn't mounted yet.
 */
export const captureCurrentZoomState = (
  source: ZoomState['source'] = 'user'
): ZoomState | null => {
  const { plotlyRef } = storeToRefs(usePlotlyStore())
  const gd = plotlyRef.value as
    | (PrivatePlotlyHTMLElement & { layout?: Partial<Layout> })
    | null
  if (!gd?.layout) return null

  const layout = gd.layout as Partial<Layout> & Record<string, unknown>

  const xAxis = layout.xaxis as Partial<LayoutAxis> | undefined
  const xR = xAxis?.range as Array<number | string> | undefined
  const xStart = xR ? Number(typeof xR[0] === 'string' ? Date.parse(xR[0]) : xR[0]) : NaN
  const xEnd = xR ? Number(typeof xR[1] === 'string' ? Date.parse(xR[1]) : xR[1]) : NaN
  const xRange: [number, number] | null =
    Number.isFinite(xStart) && Number.isFinite(xEnd) ? [xStart, xEnd] : null

  const yRanges: Record<string, [number, number]> = {}
  for (const key of Object.keys(layout)) {
    if (!Y_AXIS_KEY_RE.test(key)) continue
    const axis = layout[key] as Partial<LayoutAxis> | undefined
    const r = axis?.range as Array<number> | undefined
    if (!r || !Number.isFinite(r[0]) || !Number.isFinite(r[1])) continue
    yRanges[key] = [Number(r[0]), Number(r[1])]
  }

  return { xRange, yRanges, source }
}

/**
 * Push a snapshot of the live plot onto the undo stack. No-ops when the
 * snapshot would be identical to (or an imperceptible move from) the
 * current top of the stack, which keeps drag-gesture churn from flooding
 * the history.
 */
const THRESHOLD = 0.005 // 0.5% of span
const sameRange = (
  a: [number, number] | null,
  b: [number, number] | null
): boolean => {
  if (!a || !b) return a === b
  const span = Math.max(Math.abs(a[1] - a[0]), Math.abs(b[1] - b[0]), 1)
  return (
    Math.abs(a[0] - b[0]) / span < THRESHOLD &&
    Math.abs(a[1] - b[1]) / span < THRESHOLD
  )
}
const sameZoomState = (a: ZoomState, b: ZoomState): boolean => {
  if (!sameRange(a.xRange, b.xRange)) return false
  const keys = new Set([...Object.keys(a.yRanges), ...Object.keys(b.yRanges)])
  for (const k of keys) {
    if (!sameRange(a.yRanges[k] ?? null, b.yRanges[k] ?? null)) return false
  }
  return true
}

export const recordZoomIfSettled = (
  source: ZoomState['source'] = 'user'
) => {
  const store = usePlotlyStore()
  if (store.suppressZoomHistory) return
  if (!store.graphSeriesArray.length) return
  const snap = captureCurrentZoomState(source)
  if (!snap) return
  const top = store.zoomUndoStack[store.zoomUndoStack.length - 1]
  if (top && sameZoomState(top, snap)) return
  store.pushZoomState(snap)
}

/** 350 ms debounce — slightly longer than the relayout handler so a single
 * drag gesture collapses to one entry even when the user pauses briefly
 * mid-gesture. Module-private: wire via `installZoomTracking` instead. */
const recordZoomDebounced = debounce(
  () => recordZoomIfSettled('user'),
  350
)

/**
 * Wire the module-private zoom-history recorder to `plotly_relayout` on
 * the given plot. Kept independent of the main relayout handler so this
 * module can own its own state (debouncer + stacks via the store).
 */
export const installZoomTracking = (
  plotlyRef: PlotlyHTMLElement | null | undefined
): void => {
  plotlyRef?.on('plotly_relayout', () => recordZoomDebounced())
}

/**
 * Apply a ZoomState snapshot to the live plot. Gates with
 * `suppressZoomHistory` so the recorder doesn't re-capture what we just
 * set. Does nothing when the plot hasn't mounted.
 */
export const applyZoomState = async (state: ZoomState): Promise<void> => {
  const store = usePlotlyStore()
  const gd = store.plotlyRef as
    | (PrivatePlotlyHTMLElement & { layout?: Partial<Layout> })
    | null
  if (!gd) return

  const update: Record<string, unknown> = {}
  if (state.xRange) {
    update['xaxis.range'] = [state.xRange[0], state.xRange[1]]
    update['xaxis.autorange'] = false
  } else {
    update['xaxis.autorange'] = true
  }
  for (const [key, range] of Object.entries(state.yRanges)) {
    update[`${key}.range`] = [range[0], range[1]]
    update[`${key}.autorange`] = false
  }

  store.suppressZoomHistory = true
  try {
    await Plotly.relayout(gd as unknown as HTMLElement, update)
  } finally {
    // Let the debounced recorder tick past (350 ms + slack) before
    // re-arming.
    setTimeout(() => {
      store.suppressZoomHistory = false
    }, 450)
  }
}

/** Step one entry back in the zoom history. */
export const undoZoom = async (): Promise<void> => {
  const store = usePlotlyStore()
  if (!store.canUndoZoom) return
  const current = store.zoomUndoStack.pop()
  if (current) store.zoomRedoStack.push(current)
  const target = store.zoomUndoStack[store.zoomUndoStack.length - 1]
  if (target) await applyZoomState(target)
}

/** Step one entry forward in the zoom history. */
export const redoZoom = async (): Promise<void> => {
  const store = usePlotlyStore()
  if (!store.canRedoZoom) return
  const target = store.zoomRedoStack.pop()
  if (!target) return
  store.zoomUndoStack.push(target)
  await applyZoomState(target)
}
