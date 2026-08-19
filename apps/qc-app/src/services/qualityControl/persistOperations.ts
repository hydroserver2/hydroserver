/**
 * Persist an edit session's operations to the QC API (spec section 5-6).
 *
 * qc-utils' `serializeHistory` emits operations as `{ method, args }`; the
 * QC API speaks `{ operationType, arguments, order }`. The enum values are
 * identical, so the only app-side glue is a field rename plus assigning
 * `order` by position.
 */

import type { QcHistoryOperation } from '@uwrl/qc-utils'
import type {
  QualityControlOperationService,
  QualityControlOperation,
  QualityControlOperationContract,
} from '@hydroserver/client'
import { unwrap } from './unwrap'

type QcOperationPostBody = QualityControlOperationContract.PostBody[number]

function operationBody(op: QcHistoryOperation, order: number): QcOperationPostBody {
  const body: QcOperationPostBody = {
    operationType: op.method as unknown as QcOperationPostBody['operationType'],
    arguments: op.args,
    order,
  }
  if (op.comment) body.comment = op.comment
  return body
}

/** Normalized comment for comparison: blank and absent are both "no comment". */
const commentOf = (value?: string | null): string | null => value?.trim() || null

/**
 * Map qc-utils serialized operations to QC API operation bodies: rename
 * method/args to operationType/arguments and assign order by index.
 */
export function sessionOperationsFromSerialized(
  operations: QcHistoryOperation[]
): QcOperationPostBody[] {
  return operations.map((op, index) => operationBody(op, index))
}

/**
 * Reconcile a session's persisted operations with the current ordered set
 * (used when saving an in-progress session).
 *
 * Append-only: existing operations are left untouched so they keep their
 * original creator (drafts are shared, and the server stamps each create
 * request with the requesting user). Only operations added since the last
 * save are created; operations removed by undo are deleted from the tail.
 *
 * Limitation: reconciles by position, so a mid-history rewrite that keeps
 * the operation count but changes earlier operations is not re-persisted;
 * the common append / trailing-undo flow is.
 */
export async function persistSessionOperations(
  qcOperations: QualityControlOperationService,
  historyId: string,
  sessionId: string,
  operations: QcHistoryOperation[]
): Promise<QualityControlOperation[]> {
  // fetch_all: the reconcile is position-based, so it needs every persisted
  // operation, not just the first page.
  const existing = unwrap(
    await qcOperations.list(historyId, sessionId, { fetch_all: true })
  )

  // Undo: drop persisted operations past the current length (newest first).
  for (let i = existing.length - 1; i >= operations.length; i--) {
    const op = existing[i]
    if (op) unwrap(await qcOperations.delete(historyId, sessionId, op.id))
  }

  // Comments are patched in place; the rest of an operation is append-only.
  const retained = Math.min(existing.length, operations.length)
  for (let i = 0; i < retained; i++) {
    const persisted = existing[i]
    const local = operations[i]
    if (!persisted || !local) continue
    const comment = commentOf(local.comment)
    if (commentOf(persisted.comment) === comment) continue
    unwrap(
      await qcOperations.update(historyId, sessionId, persisted.id, { comment })
    )
  }

  // Append the operations added since the last save (server stamps creator).
  const appended = operations.slice(existing.length)
  if (appended.length) {
    unwrap(
      await qcOperations.create(
        historyId,
        sessionId,
        appended.map((op, index) => operationBody(op, existing.length + index))
      )
    )
  }

  return unwrap(
    await qcOperations.list(historyId, sessionId, { fetch_all: true })
  )
}
