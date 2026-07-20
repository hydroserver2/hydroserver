import { ObservationRecord } from '@uwrl/qc-utils'

export type EnumDictionary<T extends string | symbol | number, U> = {
  [K in T]: U
}

export interface GraphSeries {
  id: string
  name: string
  data: ObservationRecord
  yAxisLabel: string
  /**
   * Non-QC line colour. Assigned by `assignSeriesColors` after every
   * refresh of the graph-series array, walking `plottedDatastreams`
   * in legend order and claiming the first `COLORS[1..]` slot not
   * already taken by an earlier series in the walk. Persisted on the
   * series so reordering the legend doesn't reshuffle colours, and so
   * a series whose fetch is still in flight gets a colour as soon as
   * its place in the legend is known. Empty string until the first
   * assignment runs. The QC series always renders as `COLORS[0]`
   * regardless of its stored value.
   */
  color: string
  /**
   * Datastream's intended observation cadence, in milliseconds. When set,
   * the plot breaks the line wherever consecutive observations sit
   * farther apart than this value, so true data gaps render as
   * disconnected segments. Null/undefined when the datastream has no
   * declared cadence — those series draw lines through every gap as
   * before.
   */
  intendedSpacingMs?: number | null
}
