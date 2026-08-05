import { ObservationRecord } from '@uwrl/qc-utils'

export type EnumDictionary<T extends string | symbol | number, U> = {
  [K in T]: U
}

/**
 * Provenance for a history snapshot series: which session it came from and
 * how far through that session's operations it was replayed. Present only on
 * snapshot series; absent on real datastream series.
 */
export interface SnapshotMeta {
  sessionId: string
  /** Session description, or its formatted window when it has none. */
  sessionLabel: string
  /** -1 for the session baseline, else the index of the last replayed op. */
  opIndex: number
  /** Total operations in the session, for the "step 3 of 7" label. */
  opCount: number
  /** Formatted operation name, empty string for the baseline. */
  opName: string
  performedBy?: string
  /** ISO timestamp shown in the provenance line. */
  createdAt: string
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
  /**
   * Set when this series is a frozen replay of a session's history rather
   * than a live datastream. Drives the legend provenance row and the guards
   * that keep snapshots out of fetches and the QC-target selector.
   */
  snapshot?: SnapshotMeta
}
