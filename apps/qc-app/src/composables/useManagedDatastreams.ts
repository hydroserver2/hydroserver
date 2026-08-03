/**
 * Resolve the managed (QC) datastreams for a source datastream and their
 * sessions, for the "Start editing" chooser. The source -> managed mapping
 * comes from the QC histories loaded into the data-vis store; sessions are
 * fetched per history on demand.
 */

import type {
  Datastream,
  DatastreamExtended,
  QualityControlSession,
} from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
import { useDataVisStore } from '@/store/dataVisualization'

export interface ManagedDatastreamOption {
  historyId: string
  // Resolved from the expand_related catalog, so the nested objects
  // (processingLevel, ...) are available for display.
  managed: Datastream & Partial<DatastreamExtended>
  sessions: QualityControlSession[]
}

export function useManagedDatastreams() {
  async function loadForSource(
    sourceId: string
  ): Promise<ManagedDatastreamOption[]> {
    const { hs } = useHydroServer()
    const { datastreams, historiesBySource } = useDataVisStore()
    const histories = historiesBySource.get(sourceId) ?? []
    return Promise.all(
      histories.map(async (h: any) => {
        const historyId = h.id as string
        const managedId = h.managedDatastreamId ?? h.managedDatastream?.id
        // Managed datastreams are in the full catalog (just hidden from the
        // table); fall back to a name-only stub if it isn't loaded.
        const managed =
          datastreams.find((d) => d.id === managedId) ??
          ({
            id: managedId,
            name: h.managedDatastream?.name ?? managedId,
          } as Datastream)
        const sessions =
          await hs.qualityControlSessions.listAllItems(historyId)
        return { historyId, managed, sessions }
      })
    )
  }

  /**
   * Delete a managed datastream: remove its QC history (cascading its
   * sessions/operations) first, then the now-unmanaged datastream so it
   * doesn't reappear in the catalog as a raw row. Throws on failure.
   */
  async function deleteManaged(
    historyId: string,
    managedId: string
  ): Promise<void> {
    const { hs } = useHydroServer()
    const historyRes = await hs.qualityControlHistories.delete(historyId)
    if (!historyRes.ok) {
      throw new Error(historyRes.message || 'Could not delete the QC history.')
    }
    const datastreamRes = await hs.datastreams.delete(managedId)
    if (!datastreamRes.ok) {
      throw new Error(
        datastreamRes.message || 'Could not delete the managed datastream.'
      )
    }
  }

  /**
   * Discard an in-progress session, dropping its draft operations. Committed
   * sessions are immutable server-side, so only the draft can be deleted.
   * Throws on failure.
   */
  async function deleteSession(
    historyId: string,
    sessionId: string
  ): Promise<void> {
    const { hs } = useHydroServer()
    const res = await hs.qualityControlSessions.delete(historyId, sessionId)
    if (!res.ok) {
      throw new Error(res.message || 'Could not discard the session.')
    }
  }

  return { loadForSource, deleteManaged, deleteSession }
}
