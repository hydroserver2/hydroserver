import type {
  QualityControlHistory,
  QualityControlHistoryService,
} from '@hydroserver/client'
import { unwrap } from './unwrap'

/**
 * Resolve the QC history for a managed datastream, or null if it has none
 * (i.e. the datastream is not set up for QC editing).
 */
export async function findHistoryForDatastream(
  qcHistories: QualityControlHistoryService,
  managedDatastreamId: string
): Promise<QualityControlHistory | null> {
  const histories = unwrap(
    await qcHistories.list({ managedDatastreamId: [managedDatastreamId] })
  )
  return histories[0] ?? null
}
