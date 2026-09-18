/**
 * `layout.shapes` has several writers, and each owns only the shapes it
 * names: `createPlotlyOption` owns the session window band, the staging
 * helpers own the stage band. A write replaces its own shapes and carries
 * everything else on the live plot through unchanged.
 */

import type { Layout } from 'plotly.js-dist'

export type PlotlyShape = Partial<NonNullable<Layout['shapes']>[number]> & {
  editable?: boolean
  name?: string
}

export const EDIT_WINDOW_SHAPE_NAME = 'edit-window'
export const STAGE_SHAPE_NAME = 'stage'

/** `live` with the shapes named `name` replaced by `own`. `first` puts
 *  `own` ahead of the other writers' shapes instead of after them. */
export function composeShapes(
  live: readonly PlotlyShape[] | undefined,
  name: string,
  own: readonly PlotlyShape[],
  { first = false }: { first?: boolean } = {}
): PlotlyShape[] {
  const others = (live ?? []).filter((shape) => shape?.name !== name)
  return first ? [...own, ...others] : [...others, ...own]
}

/** A copy of a fresh `createPlotlyOption` layout whose shapes keep what
 *  other writers have on the live plot. */
export function withLiveShapes(
  layout: Partial<Layout>,
  liveLayout: Partial<Layout> | undefined
): Partial<Layout> {
  const own = ((layout.shapes ?? []) as PlotlyShape[]).filter(
    (shape) => shape.name === EDIT_WINDOW_SHAPE_NAME
  )
  const live = liveLayout?.shapes as PlotlyShape[] | undefined
  return { ...layout, shapes: composeShapes(live, EDIT_WINDOW_SHAPE_NAME, own) }
}
