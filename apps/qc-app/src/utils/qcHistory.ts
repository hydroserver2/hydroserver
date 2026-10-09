import type {
  QualityControlHistory,
  QualityControlOperation,
  QualityControlSession,
} from '@hydroserver/client'

/** A session with its operations, which load from their own endpoint. */
export type QcSession = QualityControlSession & {
  operations: QualityControlOperation[]
}

export const historyManagedId = (h: QualityControlHistory): string =>
  h.managedDatastreamId

export const historySourceId = (h: QualityControlHistory): string =>
  h.sourceDatastreamId

/** A session's operations, or none for a session read without them. */
export const sessionOperations = (s: QcSession | QualityControlSession) =>
  'operations' in s ? s.operations : []
