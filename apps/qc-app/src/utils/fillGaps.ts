/** A gap's two endpoints, as GapFinder reports them. */
export interface FillSpan {
  leftTs: number
  rightTs: number
  leftY: number
  rightY: number
}

export interface FillFanout {
  xs: number[]
  ys: number[]
  count: number
}

const MIN_FILL_LIMIT = 10_000

/**
 * Most points one Fill gaps edit may add: twice the points loaded, and at
 * least 10,000. A finer cadence than that freezes the tab building them.
 */
export function fillLimit(loadedPoints: number): number {
  return Math.max(2 * loadedPoints, MIN_FILL_LIMIT)
}

/** How many points `fillFanout` would build, without building them. */
export function estimateFillCount(plans: FillSpan[], deltaMs: number): number {
  let count = 0
  for (const p of plans) {
    count += Math.max(0, Math.ceil((p.rightTs - p.leftTs) / deltaMs) - 1)
  }
  return count
}

/**
 * The points a FILL_GAPS edit inserts, interpolated between each gap's
 * endpoints. Mirrors the loop in qc-utils' `_fillGaps` so the preview
 * matches what the edit writes.
 */
export function fillFanout(plans: FillSpan[], deltaMs: number): FillFanout {
  const xs: number[] = []
  const ys: number[] = []
  for (const p of plans) {
    const span = p.rightTs - p.leftTs
    const valueSpan = p.rightY - p.leftY
    for (let t = p.leftTs + deltaMs; t < p.rightTs; t += deltaMs) {
      xs.push(t)
      ys.push(p.leftY + ((t - p.leftTs) * valueSpan) / span)
    }
  }
  return { xs, ys, count: xs.length }
}
