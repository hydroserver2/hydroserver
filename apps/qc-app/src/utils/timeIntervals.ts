/** Closed `[start, end]` epoch-ms intervals. Timestamps are whole
 *  milliseconds, so neighbouring intervals meet at `end + 1`. */
export type Interval = [number, number]

/** Sorted, non-overlapping union of `intervals`. Touching ones join. */
export function mergeIntervals(intervals: readonly Interval[]): Interval[] {
  const sorted = [...intervals].sort((a, b) => a[0] - b[0])
  const out: Interval[] = []
  for (const [start, end] of sorted) {
    const last = out[out.length - 1]
    if (last && start <= last[1] + 1) last[1] = Math.max(last[1], end)
    else out.push([start, end])
  }
  return out
}

/** The parts of `from` that no interval in `remove` covers. */
export function subtractIntervals(
  from: readonly Interval[],
  remove: readonly Interval[]
): Interval[] {
  const cuts = mergeIntervals(remove)
  const out: Interval[] = []
  for (const [start, end] of from) {
    let cursor = start
    for (const [cutStart, cutEnd] of cuts) {
      if (cutEnd < cursor) continue
      if (cutStart > end) break
      if (cutStart > cursor) out.push([cursor, cutStart - 1])
      cursor = cutEnd + 1
      if (cursor > end) break
    }
    if (cursor <= end) out.push([cursor, end])
  }
  return out
}
