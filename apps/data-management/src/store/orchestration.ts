import { defineStore, storeToRefs } from 'pinia'
import hs, {
  Datastream,
  DatastreamExtended,
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
  const persistedLinkedDatastreamIds = ref<Set<string>>(new Set())
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
  let workspaceDatastreamRequestId = 0
  let linkedDatastreamRequestId = 0
  let workspaceMonitoringSitesRequestId = 0

  const resetWorkspaceDatastreams = () => {
    workspaceDatastreamRequestId += 1
    workspaceDatastreams.value = []
  }

  const resetWorkspaceMonitoringSites = () => {
    workspaceMonitoringSitesRequestId += 1
    workspaceMonitoringSites.value = []
  }

  const resetLinkedDatastreams = () => {
    linkedDatastreamRequestId += 1
    persistedLinkedDatastreamIds.value = new Set()
  }

  const resetDraftDatastreams = () => {
    draftDatastreams.value = []
  }
  
  const linkedDatastreamIds = computed(() => persistedLinkedDatastreamIds.value)

  const ensureWorkspaceLinkedDatastreams = async (
    requestedWorkspaceId = workspaceId.value
  ) => {
    if (!requestedWorkspaceId) {
      resetLinkedDatastreams()
      return linkedDatastreamIds.value
    }

    const requestId = ++linkedDatastreamRequestId
    const [mappings, transformations] = await Promise.all([
      hs.etlMappings.listAllItems({
        workspaceId: [requestedWorkspaceId],
      } as any),
      hs.dataProductTransformations.listAllItems({
        workspaceId: [requestedWorkspaceId],
      } as any),
    ])
    if (requestId !== linkedDatastreamRequestId) {
      return linkedDatastreamIds.value
    }

    const ids = new Set<string>()
    for (const mapping of mappings ?? []) {
      if (mapping.targetDatastreamId) ids.add(String(mapping.targetDatastreamId))
    }
    for (const transformation of transformations ?? []) {
      if (transformation.outputDatastreamId)
        ids.add(String(transformation.outputDatastreamId))
    }

    persistedLinkedDatastreamIds.value = ids
    return linkedDatastreamIds.value
  }

  const linkedDatastreams = computed(() =>
    workspaceDatastreams.value.filter((d) =>
      linkedDatastreamIds.value.has(String(d.id))
    )
  )

  const ensureWorkspaceDatastreams = async (
    requestedWorkspaceId = workspaceId.value
  ) => {
    if (!requestedWorkspaceId) {
      resetWorkspaceDatastreams()
      return []
    }

    const requestId = ++workspaceDatastreamRequestId
    const list = await hs.datastreams.listAllItems({
      workspaceId: [requestedWorkspaceId],
      expand_related: true,
    })
    if (requestId !== workspaceDatastreamRequestId) {
      return workspaceDatastreams.value
    }
    workspaceDatastreams.value = list ?? []
    return workspaceDatastreams.value
  }

  const ensureWorkspaceMonitoringSites = async (
    requestedWorkspaceId = workspaceId.value
  ) => {
    if (!requestedWorkspaceId) {
      resetWorkspaceMonitoringSites()
      return []
    }

    const requestId = ++workspaceMonitoringSitesRequestId
    const list = await hs.monitoringSites.listAllItems({
      workspaceId: [requestedWorkspaceId],
      sortby: ['name'],
    } as any)
    if (requestId !== workspaceMonitoringSitesRequestId) {
      return workspaceMonitoringSites.value
    }
    workspaceMonitoringSites.value = (list ?? []) as MonitoringSite[]
    return workspaceMonitoringSites.value
  }

  watch(workspaceId, () => {
    resetWorkspaceDatastreams()
    resetLinkedDatastreams()
    resetWorkspaceMonitoringSites()
    resetDraftDatastreams()
  })

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
    ensureWorkspaceLinkedDatastreams,
    ensureWorkspaceMonitoringSites,
    resetWorkspaceDatastreams,
    resetLinkedDatastreams,
    resetWorkspaceMonitoringSites,
    resetDraftDatastreams,
  }
})
