/**
 * Snapshot ids are synthetic (no server-side datastream), so every guard
 * that keeps them out of fetches and share keys hangs off these helpers.
 */

import { describe, it, expect } from 'vitest'
import {
  SNAPSHOT_BASELINE_INDEX,
  isSnapshotId,
  makeSnapshotId,
  parseSnapshotId,
} from '@/utils/snapshotId'

describe('snapshot ids', () => {
  it('round-trips a session id and operation index', () => {
    const id = makeSnapshotId('sess-1', 3)
    expect(parseSnapshotId(id)).toEqual({ sessionId: 'sess-1', opIndex: 3 })
  })

  it('round-trips the baseline index', () => {
    const id = makeSnapshotId('sess-1', SNAPSHOT_BASELINE_INDEX)
    expect(parseSnapshotId(id)).toEqual({
      sessionId: 'sess-1',
      opIndex: SNAPSHOT_BASELINE_INDEX,
    })
  })

  it('recognises snapshot ids and rejects real datastream ids', () => {
    expect(isSnapshotId(makeSnapshotId('sess-1', 0))).toBe(true)
    expect(isSnapshotId('7c9e6679-7425-40de-944b-e07fc1f90ae7')).toBe(false)
    expect(isSnapshotId(undefined)).toBe(false)
    expect(isSnapshotId(null)).toBe(false)
  })

  it('returns null for ids that are not snapshots or are malformed', () => {
    expect(parseSnapshotId('ds-a')).toBeNull()
    expect(parseSnapshotId('snap:')).toBeNull()
    expect(parseSnapshotId('snap:sess-1')).toBeNull()
    expect(parseSnapshotId('snap:sess-1:abc')).toBeNull()
    expect(parseSnapshotId('snap:sess-1:-2')).toBeNull()
  })
})
