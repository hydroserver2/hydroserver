/**
 * Synthetic ids for history snapshots. A snapshot is a frozen replay of a
 * session's operations, so it has no server-side datastream. The prefix lets
 * one predicate guard every path that would otherwise treat it as real.
 */

export const SNAPSHOT_PREFIX = 'snap:'

/** Baseline: the session's state before its first operation. */
export const SNAPSHOT_BASELINE_INDEX = -1

export interface SnapshotRef {
  sessionId: string
  opIndex: number
}

/** `sessionId:opIndex`, the id without its prefix. Share links carry this. */
export function snapshotKey({ sessionId, opIndex }: SnapshotRef): string {
  return `${sessionId}:${opIndex}`
}

export function parseSnapshotKey(key: string): SnapshotRef | null {
  const sep = key.lastIndexOf(':')
  if (sep <= 0) return null
  const sessionId = key.slice(0, sep)
  const opIndex = Number(key.slice(sep + 1))
  if (!Number.isInteger(opIndex)) return null
  if (opIndex < SNAPSHOT_BASELINE_INDEX) return null
  return { sessionId, opIndex }
}

export function makeSnapshotId(sessionId: string, opIndex: number): string {
  return SNAPSHOT_PREFIX + snapshotKey({ sessionId, opIndex })
}

export function isSnapshotId(id: string | null | undefined): boolean {
  return !!id && id.startsWith(SNAPSHOT_PREFIX)
}

export function parseSnapshotId(id: string): SnapshotRef | null {
  if (!isSnapshotId(id)) return null
  return parseSnapshotKey(id.slice(SNAPSHOT_PREFIX.length))
}
