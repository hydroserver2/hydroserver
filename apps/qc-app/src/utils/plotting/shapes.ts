/**
 * `layout.shapes` belongs to the staging helpers (the stage band).
 * `createPlotlyOption` builds layouts without shapes, so a full re-plot
 * carries the live ones over.
 */

import type { Layout } from 'plotly.js-dist'

export type PlotlyShape = Partial<NonNullable<Layout['shapes']>[number]> & {
  editable?: boolean
  name?: string
}

export const STAGE_SHAPE_NAME = 'stage'

/** A copy of a fresh `createPlotlyOption` layout carrying the live plot's
 *  shapes. */
export function withLiveShapes(
  layout: Partial<Layout>,
  liveLayout: Partial<Layout> | undefined
): Partial<Layout> {
  return { ...layout, shapes: [...(liveLayout?.shapes ?? [])] }
}
