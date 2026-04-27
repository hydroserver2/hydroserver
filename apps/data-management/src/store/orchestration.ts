import { defineStore, storeToRefs } from 'pinia'
import hs, {
  Datastream,
  DatastreamExtended,
  TaskExpanded,
  Thing,
} from '@hydroserver/client'
import { computed, ref, watch } from 'vue'
import { useWorkspaceStore } from '@/store/workspaces'

export const useOrchestrationStore = defineStore('orchestration', () => {
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())

  const workspaceId = computed(() => selectedWorkspace.value?.id ?? null)
  const workspaceDatastreams = ref<Datastream[]>([])
  const draftDatastreams = ref<DatastreamExtended[]>([])
  const workspaceTasks = ref<TaskExpanded[]>([])
  const workspaceThings = ref<Thing[]>([])
  const orchestrationSearch = ref('')
  const orchestrationStatusFilter = ref<string[]>([])
  const loadedWorkspaceDatastreamId = ref<string | null>(null)
  const loadedWorkspaceThingsId = ref<string | null>(null)
  let workspaceDatastreamRequestId = 0
  let workspaceThingsRequestId = 0

  const resetWorkspaceDatastreams = () => {
    workspaceDatastreamRequestId += 1
    workspaceDatastreams.value = []
    loadedWorkspaceDatastreamId.value = null
  }

  const resetWorkspaceThings = () => {
    workspaceThingsRequestId += 1
    workspaceThings.value = []
    loadedWorkspaceThingsId.value = null
  }

  const linkedDatastreamIds = computed(() => {
    const ids = new Set<string>()

    for (const task of workspaceTasks.value) {
      for (const id of (task as any).targetIdentifiers ?? []) {
        if (id) ids.add(String(id))
      }
      for (const mapping of task.mappings ?? []) {
        const id = mapping.targetDatastream?.id
        if (id) ids.add(String(id))
        for (const path of (mapping as any).paths ?? []) {
          if (path?.targetIdentifier) ids.add(String(path.targetIdentifier))
        }
      }
    }

    return ids
  })

  const linkedDatastreams = computed(() =>
    workspaceDatastreams.value.filter((d) =>
      linkedDatastreamIds.value.has(String(d.id))
    )
  )

  const ensureWorkspaceDatastreams = async (
    requestedWorkspaceId = workspaceId.value,
    force = false
  ) => {
    if (!requestedWorkspaceId) {
      resetWorkspaceDatastreams()
      return []
    }

    if (!force && loadedWorkspaceDatastreamId.value === requestedWorkspaceId) {
      return workspaceDatastreams.value
    }

    const requestId = ++workspaceDatastreamRequestId
    const list = await hs.datastreams.listAllItems({
      workspace_id: [requestedWorkspaceId],
    })
    if (requestId !== workspaceDatastreamRequestId) {
      return workspaceDatastreams.value
    }
    workspaceDatastreams.value = list ?? []
    loadedWorkspaceDatastreamId.value = requestedWorkspaceId
    return workspaceDatastreams.value
  }

  const ensureWorkspaceThings = async (
    requestedWorkspaceId = workspaceId.value,
    force = false
  ) => {
    if (!requestedWorkspaceId) {
      resetWorkspaceThings()
      return []
    }

    if (!force && loadedWorkspaceThingsId.value === requestedWorkspaceId) {
      return workspaceThings.value
    }

    const requestId = ++workspaceThingsRequestId
    const list = await hs.things.listAllItems({
      workspace_id: [requestedWorkspaceId],
      order_by: ['name'],
    } as any)
    if (requestId !== workspaceThingsRequestId) {
      return workspaceThings.value
    }
    workspaceThings.value = (list ?? []) as Thing[]
    loadedWorkspaceThingsId.value = requestedWorkspaceId
    return workspaceThings.value
  }

  watch(
    workspaceId,
    (wsId) => {
      if (!wsId) {
        resetWorkspaceDatastreams()
        resetWorkspaceThings()
        return
      }
      if (loadedWorkspaceDatastreamId.value !== wsId) {
        resetWorkspaceDatastreams()
      }
      if (loadedWorkspaceThingsId.value !== wsId) {
        resetWorkspaceThings()
      }
    },
    { immediate: true }
  )

  return {
    workspaceTasks,
    linkedDatastreamIds,
    linkedDatastreams,
    draftDatastreams,
    workspaceDatastreams,
    workspaceThings,
    orchestrationSearch,
    orchestrationStatusFilter,
    ensureWorkspaceDatastreams,
    ensureWorkspaceThings,
    resetWorkspaceDatastreams,
    resetWorkspaceThings,
  }
})
