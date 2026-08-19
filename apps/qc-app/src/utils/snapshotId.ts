/**
 * Synthetic ids for history snapshots. A snapshot is a frozen replay of a
 * session's operations, so it has no server-side datastream. The prefix lets
 * one predicate guard every path that would otherwise treat it as real.
 */

export const SNAPSHOT_PREFIX = 'snap:'

/** Baseline: the session's state before its first operation. */
export const SNAPSHOT_BASELINE_INDEX = -1

export function makeSnapshotId(sessionId: string, opIndex: number): string {
  return `${SNAPSHOT_PREFIX}${sessionId}:${opIndex}`
}

export function isSnapshotId(id: string | null | undefined): boolean {
  return !!id && id.startsWith(SNAPSHOT_PREFIX)
}

export function parseSnapshotId(
  id: string
): { sessionId: string; opIndex: number } | null {
  if (!isSnapshotId(id)) return null
  const rest = id.slice(SNAPSHOT_PREFIX.length)
  const sep = rest.lastIndexOf(':')
  if (sep <= 0) return null
  const sessionId = rest.slice(0, sep)
  const opIndex = Number(rest.slice(sep + 1))
  if (!Number.isInteger(opIndex)) return null
  if (opIndex < SNAPSHOT_BASELINE_INDEX) return null
  return { sessionId, opIndex }
}
