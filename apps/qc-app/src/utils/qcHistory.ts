import type {
  QualityControlHistory,
  QualityControlSession,
} from '@hydroserver/client'

/** A history lists its datastreams as ids (summary) or nested (detail). */
export const historyManagedId = (h: QualityControlHistory): string =>
  'managedDatastream' in h ? h.managedDatastream.id : h.managedDatastreamId

export const historySourceId = (h: QualityControlHistory): string =>
  'sourceDatastream' in h ? h.sourceDatastream.id : h.sourceDatastreamId

/** A session's operations, which only the detail shape embeds. */
export const sessionOperations = (s: QualityControlSession) =>
  'operations' in s ? s.operations : []
