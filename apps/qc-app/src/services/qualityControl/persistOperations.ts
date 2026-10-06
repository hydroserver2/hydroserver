/**
 * Persist an edit session's operations to the QC API.
 *
 * qc-utils' `serializeHistory` emits operations as `{ method, args }`; the
 * QC API speaks `{ operationType, arguments, order }`. The enum values are
 * identical, so the only app-side glue is a field rename plus assigning
 * `order` by position.
 */

import { isEqual } from 'lodash-es'
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

// Args are compared in their wire form (Dates as ISO strings), and `isEqual`
// ignores key order, which JSONB does not preserve.
function sameOperation(
  persisted: QualityControlOperation,
  local: QcHistoryOperation
): boolean {
  return (
    persisted.operationType === local.method &&
    isEqual(persisted.arguments, JSON.parse(JSON.stringify(local.args)))
  )
}

/**
 * Reconcile a session's persisted operations with the current ordered set
 * (used when saving an in-progress session).
 *
 * The persisted prefix that still matches is left untouched so it keeps its
 * original creator (drafts are shared, and the server stamps each create
 * request with the requesting user). From the first operation that differs,
 * persisted operations are deleted and the local ones appended.
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

  let kept = 0
  while (
    kept < existing.length &&
    kept < operations.length &&
    sameOperation(existing[kept]!, operations[kept]!)
  ) {
    kept++
  }

  for (let i = existing.length - 1; i >= kept; i--) {
    unwrap(await qcOperations.delete(historyId, sessionId, existing[i]!.id))
  }

  // Comments are patched in place on the kept prefix.
  for (let i = 0; i < kept; i++) {
    const persisted = existing[i]!
    const comment = commentOf(operations[i]!.comment)
    if (commentOf(persisted.comment) === comment) continue
    unwrap(
      await qcOperations.update(historyId, sessionId, persisted.id, { comment })
    )
  }

  const appended = operations.slice(kept)
  if (appended.length) {
    unwrap(
      await qcOperations.create(
        historyId,
        sessionId,
        appended.map((op, index) => operationBody(op, kept + index))
      )
    )
  }

  return unwrap(
    await qcOperations.list(historyId, sessionId, { fetch_all: true })
  )
}
