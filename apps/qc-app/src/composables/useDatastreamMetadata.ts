/**
 * Reference data the create-datastream form offers: the workspace's methods
 * and the datastream status vocabulary. Loaded on demand rather than with the
 * workspace catalog, since only that one form needs them. A list that fails
 * to load stays empty and the form falls back to the source datastream's own
 * value.
 */

import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import type { Method } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
import { useWorkspaceStore } from '@/store/workspaces'

export function useDatastreamMetadata() {
  const { hs } = storeToRefs(useHydroServer())
  const { selectedWorkspaceId } = storeToRefs(useWorkspaceStore())

  const methods = ref<Method[]>([])
  const statuses = ref<string[]>([])

  async function load(): Promise<void> {
    const workspaceId = selectedWorkspaceId.value
    if (!hs.value || !workspaceId) return

    const [methodList, statusList] = await Promise.allSettled([
      // 'null' keeps the system-level methods, which are selectable too.
      hs.value.methods.list({
        workspaceId: [workspaceId, 'null'],
        sortby: ['name'],
        fetch_all: true,
      }),
      hs.value.datastreamStatuses.list({ fetch_all: true }),
    ])

    if (methodList.status === 'rejected') {
      console.warn('Could not load the method list', methodList.reason)
      methods.value = []
    } else if (!methodList.value.ok) {
      console.warn('Could not load the method list', methodList.value)
      methods.value = []
    } else {
      methods.value = methodList.value.data
    }

    if (statusList.status === 'rejected') {
      console.warn('Could not load the status list', statusList.reason)
      statuses.value = []
    } else if (!statusList.value.ok) {
      console.warn('Could not load the status list', statusList.value)
      statuses.value = []
    } else {
      statuses.value = statusList.value.data.map((status) => status.name)
    }
  }

  return { methods, statuses, load }
}
