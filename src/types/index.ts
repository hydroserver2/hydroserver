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
   * Non-QC line colour, assigned at fetch time from the free slots of
   * `COLORS[1..]` and persisted on the series so reordering the legend
   * doesn't reshuffle colours. The QC series always renders as
   * `COLORS[0]` regardless of its stored `color`.
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
