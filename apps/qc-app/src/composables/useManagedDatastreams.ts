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
        // expand_related so each session carries `dependencyIds`, which the
        // deletion chain is derived from.
        const sessions = await hs.qualityControlSessions.listAllItems(
          historyId,
          { expand_related: true }
        )
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
   * Delete `chain` in order, deepest dependent first so each delete meets
   * the server's "no dependents" rule. Resolves with the ids removed. On
   * failure it throws, and the message names how many were already gone,
   * because the deletes that landed cannot be rolled back.
   *
   * Takes the chain rather than deriving one: it must be exactly what the
   * confirmation showed. If the server has since gained a dependent the
   * delete is refused there, which is the safe direction to be wrong in.
   */
  async function deleteSessionChain(
    historyId: string,
    chain: string[]
  ): Promise<string[]> {
    const { hs } = useHydroServer()
    if (!chain.length) {
      throw new Error('That session no longer exists.')
    }

    const deleted: string[] = []
    for (const id of chain) {
      const res = await hs.qualityControlSessions.delete(historyId, id)
      if (!res.ok) {
        const reason = res.message || 'Could not delete the session.'
        throw new Error(
          deleted.length
            ? `${reason} ${deleted.length} of ${chain.length} sessions were already deleted and cannot be restored.`
            : reason
        )
      }
      deleted.push(id)
    }
    return deleted
  }

  return { loadForSource, deleteManaged, deleteSessionChain }
}
