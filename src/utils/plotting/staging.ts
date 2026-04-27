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
 *
 * Gap bands used to live here as secondary red rectangles marking
 * detected gaps. They were removed because `edits.shapePosition:
 * true` (required for the stage band drag) forces every shape on
 * the plot to be hit-testable regardless of `editable: false`, so
 * the bands presented drag cursors and accepted edit gestures they
 * couldn't actually honour. The selection on the plot (gap
 * endpoints lit as red points) is now the sole visual indicator
 * for where the detected gaps are.
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
  // The stage shape is the only shape we own. Drop it outside pan
  // mode so zoom / select / lasso gestures aren't captured by the
  // shape-edit hit-tester.
  const shapes: PlotlyShape[] =
    stageShape && stagePanMode.value ? [stageShape] : []
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
 * Force the plot back into pan mode. Called by the staging-based
 * operation panels (Find Gaps / Fill Gaps) when they open so the
 * range overlay is immediately interactive — otherwise a user who
 * was last in zoom/select/lasso mode would open the panel to a
 * hidden band (we drop it outside pan mode to keep those tools
 * unobstructed) and have to switch tools themselves to resize it.
 */
export async function enterPanMode(): Promise<void> {
  const root = getRoot()
  if (!root) return
  if (currentDragmode() === 'pan') return
  await Plotly.relayout(root, { dragmode: 'pan' } as unknown as Partial<Layout>)
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
      // Bumped from 0.55/0.9 with a thin X-glyph: barely readable
      // over a dense data line. Fully opaque primary blue + bigger
      // dot-style glyph with a white outline so each preview point
      // pops against both the data and the staging band.
      color: 'rgb(25, 118, 210)',
      size: 10,
      symbol: 'circle',
      line: { width: 2, color: 'white' },
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

    // Stage shape is the only shape we flush, so its index is
    // always 0 in the layout shapes array.
    const stageIdx = 0
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
