/**
 * Commit a QC session: check it is still in progress and that its source
 * window hasn't changed since it started, push the observations, then lock
 * the session into the history.
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
  /** The source window's checksum now; compared to the one taken at session start. */
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
      'The source data changed since this session started, ' +
        'so these edits may no longer line up with it.'
    )
  }

  await pushObservations()
  return unwrap(await qcSessions.commit(historyId, sessionId))
}
