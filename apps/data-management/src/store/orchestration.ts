import { defineStore, storeToRefs } from 'pinia'
import hs, {
  Datastream,
  DatastreamExtended,
  TaskExpanded,
  Thing,
} from '@hydroserver/client'
import { computed, ref, watch } from 'vue'
import { useWorkspaceStore } from '@/store/workspaces'
import type {
  ActiveView,
  DataProductTaskType,
  TabId,
} from '@/components/Orchestration/workbench/orchestrationTabs'
import type { Task } from '@/types/orchestrationTasks'

export const useOrchestrationStore = defineStore('orchestration', () => {
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())

  const workspaceId = computed(() => selectedWorkspace.value?.id ?? null)
  const workspaceDatastreams = ref<Datastream[]>([])
  const draftDatastreams = ref<DatastreamExtended[]>([])
  const workspaceTasks = ref<Task[]>([])
  const workspaceThings = ref<Thing[]>([])
  const orchestrationSearch = ref('')
  const orchestrationStatusFilter = ref<string[]>([])
  const orchestrationTaskTypeFilter = ref<NonNullable<DataProductTaskType>[]>(
    []
  )

  const activeTab = ref<TabId>('ingestion')
  const activeView = ref<ActiveView>('tasks')
  const selectedConnectionId = ref<string | null>(null)
  const selectedThingId = ref<string | null>(null)
  const sidebarSearch = ref('')
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

  const resetDraftDatastreams = () => {
    draftDatastreams.value = []
  }

  const linkedDatastreamIds = computed(() => {
    const ids = new Set<string>()

    for (const task of workspaceTasks.value) {
      for (const mapping of task.mappings ?? []) {
        const id =
          'targetDatastream' in mapping ? mapping.targetDatastream?.id : null
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
        resetDraftDatastreams()
        return
      }
      if (loadedWorkspaceDatastreamId.value !== wsId) {
        resetWorkspaceDatastreams()
        resetDraftDatastreams()
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
    orchestrationTaskTypeFilter,
    activeTab,
    activeView,
    selectedConnectionId,
    selectedThingId,
    sidebarSearch,
    ensureWorkspaceDatastreams,
    ensureWorkspaceThings,
    resetWorkspaceDatastreams,
    resetWorkspaceThings,
    resetDraftDatastreams,
  }
})
