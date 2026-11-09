import { storeToRefs } from 'pinia'
import { Snackbar } from '@uwrl/qc-utils'
import type { ApiResponse, Datastream, DatastreamExtended } from '@hydroserver/client'
import { useDataVisStore } from '@/store/dataVisualization'
import { useHydroServer } from '@/store/hydroserver'

/** Loads every page of the Select view's lists; failed loads are reported. */
export function useWorkspaceCatalog() {
  const {
    monitoringSites,
    processingLevels,
    observedProperties,
    datastreams,
    qcHistories,
  } = storeToRefs(useDataVisStore())
  const { hs } = storeToRefs(useHydroServer())

  async function load(workspaceId: string) {
    const failed: string[] = []
    async function read<T>(
      name: string,
      request: () => Promise<ApiResponse<T[]>>
    ): Promise<T[]> {
      try {
        const res = await request()
        if (res.ok) return res.data
      } catch {}
      failed.push(name)
      return []
    }

    const [sites, streams, levels, properties, histories] = await Promise.all([
      read('sites', () =>
        hs.value.monitoringSites.list({ workspaceId, fetch_all: true } as any)
      ),
      read('datastreams', () =>
        hs.value.datastreams.list({
          workspaceId,
          expand_related: true,
          fetch_all: true,
        } as any)
      ),
      read('processing levels', () =>
        hs.value.processingLevels.list({ workspaceId, fetch_all: true } as any)
      ),
      read('observed properties', () =>
        hs.value.observedProperties.list({ workspaceId, fetch_all: true } as any)
      ),
      // QC histories aren't workspace-filterable server-side; entries for
      // other workspaces simply never match this catalog's datastream ids.
      read('QC histories', () =>
        hs.value.qualityControlHistories.list({ fetch_all: true })
      ),
    ])

    monitoringSites.value = sites
    datastreams.value = streams as (Datastream & DatastreamExtended)[]
    processingLevels.value = levels
    observedProperties.value = properties
    qcHistories.value = histories

    if (failed.length) {
      Snackbar.error(
        `Couldn't load ${joinNames(failed)}. Reload the page to try again.`
      )
    }
  }

  function clear() {
    monitoringSites.value = []
    datastreams.value = []
    processingLevels.value = []
    observedProperties.value = []
  }

  return { load, clear }
}

function joinNames(names: string[]) {
  if (names.length < 2) return names.join('')
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}
