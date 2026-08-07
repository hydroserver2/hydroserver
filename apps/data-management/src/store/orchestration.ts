import { defineStore, storeToRefs } from 'pinia'
import hs, {
  Datastream,
  DatastreamExtended,
  TaskMapping,
  MonitoringSite,
} from '@hydroserver/client'
import { computed, ref, watch } from 'vue'
import { useWorkspaceStore } from '@/store/workspaces'
import type {
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
  const workspaceMonitoringSites = ref<MonitoringSite[]>([])
  const orchestrationSearch = ref('')
  const orchestrationStatusFilter = ref<string[]>([])
  const orchestrationTaskTypeFilter = ref<NonNullable<DataProductTaskType>[]>(
    []
  )

  const activeTab = ref<TabId>('ingestion')
  const selectedConnectionId = ref<string | null>(null)
  const selectedMonitoringSiteId = ref<string | null>(null)
  const sidebarSearch = ref('')
  const loadedWorkspaceDatastreamId = ref<string | null>(null)
  const loadedWorkspaceMonitoringSitesId = ref<string | null>(null)
  let workspaceDatastreamRequestId = 0
  let workspaceMonitoringSitesRequestId = 0

  const resetWorkspaceDatastreams = () => {
    workspaceDatastreamRequestId += 1
    workspaceDatastreams.value = []
    loadedWorkspaceDatastreamId.value = null
  }

  const resetWorkspaceMonitoringSites = () => {
    workspaceMonitoringSitesRequestId += 1
    workspaceMonitoringSites.value = []
    loadedWorkspaceMonitoringSitesId.value = null
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

  const ensureWorkspaceMonitoringSites = async (
    requestedWorkspaceId = workspaceId.value,
    force = false
  ) => {
    if (!requestedWorkspaceId) {
      resetWorkspaceMonitoringSites()
      return []
    }

    if (!force && loadedWorkspaceMonitoringSitesId.value === requestedWorkspaceId) {
      return workspaceMonitoringSites.value
    }

    const requestId = ++workspaceMonitoringSitesRequestId
    const list = await hs.monitoringSites.listAllItems({
      workspace_id: [requestedWorkspaceId],
      order_by: ['name'],
    } as any)
    if (requestId !== workspaceMonitoringSitesRequestId) {
      return workspaceMonitoringSites.value
    }
    workspaceMonitoringSites.value = (list ?? []) as MonitoringSite[]
    loadedWorkspaceMonitoringSitesId.value = requestedWorkspaceId
    return workspaceMonitoringSites.value
  }

  watch(
    workspaceId,
    (wsId) => {
      if (!wsId) {
        resetWorkspaceDatastreams()
        resetWorkspaceMonitoringSites()
        resetDraftDatastreams()
        return
      }
      if (loadedWorkspaceDatastreamId.value !== wsId) {
        resetWorkspaceDatastreams()
        resetDraftDatastreams()
      }
      if (loadedWorkspaceMonitoringSitesId.value !== wsId) {
        resetWorkspaceMonitoringSites()
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
    workspaceMonitoringSites,
    orchestrationSearch,
    orchestrationStatusFilter,
    orchestrationTaskTypeFilter,
    activeTab,
    selectedConnectionId,
    selectedMonitoringSiteId,
    sidebarSearch,
    ensureWorkspaceDatastreams,
    ensureWorkspaceMonitoringSites,
    resetWorkspaceDatastreams,
    resetWorkspaceMonitoringSites,
    resetDraftDatastreams,
  }
})
