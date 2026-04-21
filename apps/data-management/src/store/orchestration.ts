import { defineStore, storeToRefs } from 'pinia'
import hs, {
  Datastream,
  DatastreamExtended,
  TaskExpanded,
} from '@hydroserver/client'
import { computed, ref, watch } from 'vue'
import { useWorkspaceStore } from '@/store/workspaces'

export const useOrchestrationStore = defineStore('orchestration', () => {
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())

  const workspaceId = computed(() => selectedWorkspace.value?.id ?? null)
  const workspaceDatastreams = ref<Datastream[]>([])
  const draftDatastreams = ref<DatastreamExtended[]>([])
  const workspaceTasks = ref<TaskExpanded[]>([])
  const orchestrationSearch = ref('')
  const orchestrationStatusFilter = ref<string[]>([])
  const loadedWorkspaceDatastreamId = ref<string | null>(null)
  let workspaceDatastreamRequestId = 0

  const resetWorkspaceDatastreams = () => {
    workspaceDatastreamRequestId += 1
    workspaceDatastreams.value = []
    loadedWorkspaceDatastreamId.value = null
  }

  const linkedDatastreamIds = computed(() => {
    const ids = new Set<string>()

    for (const task of workspaceTasks.value) {
      for (const mapping of task.mappings ?? []) {
        const id = mapping.targetDatastream?.id
        if (id) ids.add(String(id))
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

  watch(
    workspaceId,
    (wsId) => {
      if (!wsId) {
        resetWorkspaceDatastreams()
        return
      }
      if (loadedWorkspaceDatastreamId.value === wsId) return
      resetWorkspaceDatastreams()
    },
    { immediate: true }
  )

  return {
    workspaceTasks,
    linkedDatastreamIds,
    linkedDatastreams,
    draftDatastreams,
    workspaceDatastreams,
    orchestrationSearch,
    orchestrationStatusFilter,
    ensureWorkspaceDatastreams,
    resetWorkspaceDatastreams,
  }
})
