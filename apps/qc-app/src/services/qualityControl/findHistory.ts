import type {
  QualityControlHistoryService,
  QualityControlHistoryContract,
} from '@hydroserver/client'
import { unwrap } from './unwrap'

type QcHistoryDetail = QualityControlHistoryContract.DetailResponse

/**
 * Resolve the QC history for a managed datastream, or null if it has none
 * (i.e. the datastream is not set up for QC editing). Returns the expanded
 * detail so callers get the linked source datastream.
 */
export async function findHistoryForDatastream(
  qcHistories: QualityControlHistoryService,
  managedDatastreamId: string
): Promise<QcHistoryDetail | null> {
  const histories = unwrap(
    await qcHistories.list({
      managed_datastream_id: [managedDatastreamId],
      expand_related: true,
    })
  )
  return (histories[0] as QcHistoryDetail | undefined) ?? null
}
