/**
 * Commit handshake for a QC session (spec section 9).
 *
 * Order of operations:
 *   1. ensure the session is in progress,
 *   2. checksum C: the source-window checksum fetched now (from the
 *      observations `X-Checksum` header) must equal the checksum captured
 *      when the session was created, otherwise the source data changed
 *      out-of-band and the commit is blocked,
 *   3. push the final observations to the managed datastream (replace mode),
 *   4. lock the session into the history.
 *
 * `pushObservations` is injected as a thunk so this unit-tests without the
 * HydroServer client. A/B integrity checks and chunked upload are deferred.
 */

import type {
  QualityControlSessionService,
  QualityControlSessionContract,
} from '@hydroserver/client'
import { unwrap } from './unwrap'

type QcSessionDetail = QualityControlSessionContract.DetailResponse

export interface CommitQcSessionInput {
  qcSessions: QualityControlSessionService
  historyId: string
  sessionId: string
  /** Source-window checksum fetched now; compared to the session's checksum C. */
  currentSourceChecksum: string
  /** Pushes the final observations to the managed datastream (replace mode). */
  pushObservations: () => Promise<void>
}

export async function commitQcSession(
  input: CommitQcSessionInput
): Promise<QcSessionDetail> {
  const { qcSessions, historyId, sessionId, currentSourceChecksum, pushObservations } =
    input

  const session = unwrap(
    await qcSessions.get(historyId, sessionId)
  ) as QcSessionDetail
  if (session.status !== 'in_progress') {
    throw new Error('Only an in-progress session can be committed.')
  }
  if (currentSourceChecksum !== session.sourceChecksum) {
    throw new Error(
      'Source data changed since this session started (checksum C mismatch). ' +
        'Re-fetch the source and verify your edits before committing again.'
    )
  }

  await pushObservations()
  return unwrap(await qcSessions.commit(historyId, sessionId))
}
