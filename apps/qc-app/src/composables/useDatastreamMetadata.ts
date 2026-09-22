/**
 * Reference data the create-datastream form offers: the workspace's sensors
 * (a datastream's "method" in HydroServer) and the datastream status
 * vocabulary. Loaded on demand rather than with the workspace catalog, since
 * only that one form needs them. A list that fails to load stays empty and
 * the form falls back to the source datastream's own value.
 */

import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import type { Sensor } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'

export function useDatastreamMetadata() {
  const { hs } = storeToRefs(useHydroServer())
  const { selectedWorkspaceId } = storeToRefs(useWorkspaceStore())

  const sensors = ref<Sensor[]>([])
  const statuses = ref<string[]>([])

  async function load(): Promise<void> {
    const workspaceId = selectedWorkspaceId.value
    if (!hs.value || !workspaceId) return

    const [sensorList, statusList] = await Promise.allSettled([
      // 'null' keeps the system-level sensors, which are selectable too.
      hs.value.sensors.listAllItems({
        workspace_id: [workspaceId, 'null'] as (string | 'null')[],
        order_by: ['name'] as const,
      }),
      hs.value.datastreams.getStatuses(),
    ])

    if (sensorList.status === 'rejected') {
      console.warn('Could not load the method list', sensorList.reason)
    }
    sensors.value =
      sensorList.status === 'fulfilled' ? (sensorList.value as Sensor[]) : []

    if (statusList.status === 'rejected') {
      console.warn('Could not load the status list', statusList.reason)
      statuses.value = []
    } else if (!statusList.value.ok) {
      console.warn('Could not load the status list', statusList.value)
      statuses.value = []
    } else {
      statuses.value = statusList.value.data
    }
  }

  return { sensors, statuses, load }
}
