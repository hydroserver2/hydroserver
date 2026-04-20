/**
 * Plot overlays used while an operation is being staged (Find Gaps /
 * Fill Gaps). Everything in here is visual-only: shapes get pushed
 * into `layout.shapes`, the ghost insertion preview rides on a
 * throwaway scattergl trace, and nothing touches the real data. Each
 * helper tolerates being called when the plot isn't mounted yet so
 * callers can fire-and-forget from setup/unmount hooks.
 *
 * We own the shape state in module-local refs rather than
 * round-tripping through `gd.layout.shapes` between writes: Plotly
 * canonicalises layout reads (e.g. date `x0` values come back as ISO
 * strings, unknown fields like `name` get stripped) which made the
 * older "read, filter by name, write" pattern lose track of its own
 * shapes on the second call.
 */

import Plotly from 'plotly.js-dist'
import type { Layout } from 'plotly.js-dist'
import { ref } from 'vue'
import { usePlotlyStore } from '@/store/plotly'
import { storeToRefs } from 'pinia'

const GHOST_TRACE_NAME = 'qc-ghost-fills'

type PlotlyShape = Partial<NonNullable<Layout['shapes']>[number]> & {
  editable?: boolean
}

let stageShape: PlotlyShape | null = null
let gapBandShapes: PlotlyShape[] = []
/** True when the plot is in pan mode, meaning the editable stage
 *  shape should be rendered. In zoom / select / lasso modes we drop
 *  the shape from the flushed array entirely so it can't swallow
 *  the mouse-down gesture or keep its grab cursor over the band —
 *  setting `editable: false` alone doesn't fully back out Plotly's
 *  shape-edit hit-testing when `edits.shapePosition` is on.
 *
 *  Reactive so RangeStager can show a hint ("Range hidden in zoom
 *  mode — switch back to pan to resize") when the band goes away.
 */
export const stagePanMode = ref(true)


function getRoot(): HTMLElement | null {
  const { plotlyRef } = storeToRefs(usePlotlyStore())
  return (plotlyRef.value as unknown as HTMLElement | null) ?? null
}

async function flushShapes() {
  const root = getRoot()
  if (!root) return
  // Drop the stage shape entirely outside pan mode. We can't swap
  // in an `editable: false` visual clone — `edits.shapePosition:
  // true` makes Plotly hit-test every shape regardless, so the
  // clone would still swallow zoom / select / lasso mousedowns.
  // Red gap bands are fine to keep: they're editable: false AND
  // the user's intent-to-draw-a-box is communicated before they
  // hit a band, so the band's hit-capture doesn't matter much
  // in practice. (If it does we'd have to drop those too.)
  const shapes: PlotlyShape[] = [
    ...gapBandShapes,
    ...(stageShape && stagePanMode.value ? [stageShape] : []),
  ]
  await Plotly.relayout(root, { shapes } as unknown as Partial<Layout>)
}

/**
 * Read the plot's current dragmode off the live layout. Used at
 * setup time to seed `stagePanMode` before the first drag event
 * delivers a `dragmode` relayout key.
 */
function currentDragmode(): string {
  const root = getRoot() as unknown as { layout?: Partial<Layout> } | null
  return (
    (root?.layout as { dragmode?: string } | undefined)?.dragmode ?? 'pan'
  )
}

/**
 * Add (or replace) the single editable range shape that represents
 * the operation's staged date window. The shape spans the full
 * y-axis so the user can grab it anywhere vertically. It only
 * actually renders in pan mode (see `flushShapes`) — zoom /
 * select / lasso modes drop it entirely to keep their box-drag
 * gestures unobstructed.
 */
export async function setStageShape(fromTs: number, toTs: number) {
  stagePanMode.value = currentDragmode() === 'pan'
  stageShape = {
    type: 'rect',
    xref: 'x',
    yref: 'paper',
    x0: fromTs,
    x1: toTs,
    y0: 0,
    y1: 1,
    fillcolor: 'rgba(25, 118, 210, 0.14)',
    line: { color: 'rgba(25, 118, 210, 0.9)', width: 2 },
    editable: true,
    layer: 'above',
  } as PlotlyShape
  await flushShapes()
}

export async function clearStageShape() {
  stageShape = null
  await flushShapes()
}

/**
 * The last x-range we pushed into the stage shape. Used by the drag
 * listener to distinguish our own shape updates from unrelated
 * relayouts.
 */
export function readStageShape(): [number, number] | null {
  if (!stageShape) return null
  const x0 = Number(stageShape.x0)
  const x1 = Number(stageShape.x1)
  if (!Number.isFinite(x0) || !Number.isFinite(x1)) return null
  return x0 <= x1 ? [x0, x1] : [x1, x0]
}

/**
 * Replace the set of read-only "found gap" bands on the x-axis. Each
 * band renders as a translucent red rectangle so the gap positions
 * stand out against the normal data line. Called with an empty list
 * to clear all bands in one relayout.
 */
export async function setGapBands(bands: Array<[number, number]>) {
  gapBandShapes = bands.map(
    ([x0, x1]) =>
      ({
        type: 'rect',
        xref: 'x',
        yref: 'paper',
        x0,
        x1,
        y0: 0,
        y1: 1,
        fillcolor: 'rgba(229, 57, 53, 0.18)',
        line: { width: 0 },
        layer: 'below',
        // The plot has `edits.shapePosition: true` enabled for the
        // stage shape; opt these out so bands stay inert.
        editable: false,
      }) as PlotlyShape
  )
  await flushShapes()
}

export async function clearGapBands() {
  gapBandShapes = []
  await flushShapes()
}

/**
 * Render a scatter trace of ghost markers at the supplied parallel
 * (x, y) coordinates to preview the points Fill Gaps would insert.
 * Callers typically compute y by linear interpolation between the
 * two sides of each gap so the markers trace the would-be fill line.
 * Called with an empty list to tear the trace down.
 */
export async function setGhostFills(xs: number[], ys: number[]) {
  const root = getRoot()
  if (!root) return
  const data = (root as unknown as { data?: { name?: string }[] }).data ?? []
  const existingIdx = data.findIndex((t) => t?.name === GHOST_TRACE_NAME)

  if (xs.length === 0) {
    if (existingIdx >= 0) {
      await Plotly.deleteTraces(root, existingIdx)
    }
    return
  }

  const trace = {
    name: GHOST_TRACE_NAME,
    type: 'scattergl',
    mode: 'markers',
    x: xs,
    y: ys,
    marker: {
      color: 'rgba(25, 118, 210, 0.55)',
      size: 7,
      symbol: 'x-thin',
      line: { width: 1.5, color: 'rgba(25, 118, 210, 0.9)' },
    },
    hoverinfo: 'skip',
    showlegend: false,
  } as unknown as Plotly.Data

  if (existingIdx >= 0) {
    await Plotly.deleteTraces(root, existingIdx)
  }
  await Plotly.addTraces(root, [trace])
}

export async function clearGhostFills() {
  await setGhostFills([], [])
}

/**
 * Watch for drag gestures on the staging shape. Plotly fires
 * `plotly_relayout` with event keys like `shapes[i].x0` /
 * `shapes[i].x1` while the user drags. We translate the changed
 * shape's new x-range back into a [from, to] callback and mirror it
 * into our module-local state so the next full flush doesn't
 * overwrite the user's drag with stale values.
 *
 * Returns a teardown function that removes the listener.
 */
export function onStageDrag(
  cb: (from: number, to: number) => void
): () => void {
  const root = getRoot() as unknown as {
    on?: (ev: string, fn: (e: unknown) => void) => void
    removeListener?: (ev: string, fn: (e: unknown) => void) => void
  } | null
  if (!root?.on) return () => { }

  const parseTs = (v: unknown): number | null => {
    if (typeof v === 'number' && Number.isFinite(v)) return v
    if (typeof v === 'string') {
      const t = Date.parse(v)
      return Number.isFinite(t) ? t : null
    }
    if (v instanceof Date) return v.getTime()
    return null
  }

  const handler = (event: unknown) => {
    const evt = event as Record<string, unknown> | null
    if (!evt || !stageShape) return

    // Dragmode change: the user picked zoom / select / lasso from
    // the modebar. Drop the stage shape from the flushed array so
    // those tools can draw their own box over the band without the
    // shape-edit hit-tester swallowing the gesture or keeping the
    // grab cursor visible. Pan mode is the only time the band
    // actually renders.
    if (typeof evt.dragmode === 'string') {
      const nextPan = evt.dragmode === 'pan'
      if (stagePanMode.value !== nextPan) {
        stagePanMode.value = nextPan
        void flushShapes()
      }
      return
    }

    // Stage shape is always last in our flushed order, so its index
    // equals `gapBandShapes.length`.
    const stageIdx = gapBandShapes.length
    const x0Key = `shapes[${stageIdx}].x0`
    const x1Key = `shapes[${stageIdx}].x1`
    const y0Key = `shapes[${stageIdx}].y0`
    const y1Key = `shapes[${stageIdx}].y1`
    const touchedX0 = Object.prototype.hasOwnProperty.call(evt, x0Key)
    const touchedX1 = Object.prototype.hasOwnProperty.call(evt, x1Key)
    const touchedY0 = Object.prototype.hasOwnProperty.call(evt, y0Key)
    const touchedY1 = Object.prototype.hasOwnProperty.call(evt, y1Key)
    if (!touchedX0 && !touchedX1 && !touchedY0 && !touchedY1) return

    // Horizontal edit: pick the new x from whichever side(s) the
    // event carried, falling back to the stashed value for the
    // untouched side.
    const nextX0 = touchedX0 ? parseTs(evt[x0Key]) : Number(stageShape.x0)
    const nextX1 = touchedX1 ? parseTs(evt[x1Key]) : Number(stageShape.x1)
    if (!Number.isFinite(nextX0) || !Number.isFinite(nextX1)) return
    const from = Math.min(nextX0 as number, nextX1 as number)
    const to = Math.max(nextX0 as number, nextX1 as number)

    // Rebuild the shape with the horizontal update applied and y
    // pinned to the full paper span. Pushing the whole shape (not
    // a dotted-path y0/y1 relayout) overrides Plotly's in-progress
    // drag state in a single write — the earlier split approach
    // (x via the parent's watcher, y via a separate relayout) was
    // racing, leaving vertical edits visible and horizontal edits
    // dropped.
    stageShape = { ...stageShape, x0: from, x1: to, y0: 0, y1: 1 }
    void flushShapes()

    // Only notify the parent when the horizontal range actually
    // moved; pure y drags are absorbed locally so we don't churn
    // downstream computeds or re-dispatch selections.
    if (touchedX0 || touchedX1) cb(from, to)
  }

  root.on('plotly_relayout', handler)
  return () => {
    root.removeListener?.('plotly_relayout', handler)
  }
}
