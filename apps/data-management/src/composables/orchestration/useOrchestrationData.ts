import { computed, ref, type Ref } from 'vue'
import hs, {
  DataConnection,
  DataProductTaskExpanded,
  MonitoringTaskExpanded,
  TaskExpanded,
  ThingTaskSummary,
} from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'
import type { TabId } from '@/components/Orchestration/workbench/orchestrationTabs'

type LoadedTaskGroup = {
  workspaceId: string
  tab: TabId
  groupId: string
} | null

export function useOrchestrationData() {
  const { workspaceTasks } = storeToRefs(useOrchestrationStore())
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
  const selectedWorkspaceId = computed(() => selectedWorkspace.value?.id ?? null)

  const loading = ref(false)
  const taskLoading = ref(false)
  const dataConnections = ref<DataConnection[]>([])
  const things = ref<ThingTaskSummary[]>([])
  const datastreamThingByDatastreamId = ref<Record<string, string>>({})
  const dataProductTasks = ref<DataProductTaskExpanded[]>([])
  const monitoringTasks = ref<MonitoringTaskExpanded[]>([])
  const loadedTaskGroup = ref<LoadedTaskGroup>(null)

  let fetchRequestId = 0
  let taskRequestId = 0

  const clearTaskLists = () => {
    workspaceTasks.value = []
    dataProductTasks.value = []
    monitoringTasks.value = []
    datastreamThingByDatastreamId.value = {}
    loadedTaskGroup.value = null
  }

  const clearTaskListForTab = (tab: TabId) => {
    if (tab === 'ingestion') workspaceTasks.value = []
    else if (tab === 'aggregation') dataProductTasks.value = []
    else monitoringTasks.value = []
  }

  const fetchAll = async (requestedWorkspaceId = selectedWorkspaceId.value) => {
    const requestId = ++fetchRequestId
    if (!requestedWorkspaceId) {
      loading.value = false
      dataConnections.value = []
      clearTaskLists()
      things.value = []
      return
    }

    loading.value = true
    try {
      const [dcItems, taskSummaryResponse] = await Promise.all([
        hs.dataConnections.listAllItems({
          workspace_id: requestedWorkspaceId,
          order_by: 'name',
        } as any),
        hs.things.listTaskSummaries({
          workspace_id: [requestedWorkspaceId],
        }),
      ])

      if (requestId !== fetchRequestId) return

      dataConnections.value = dcItems
      things.value = taskSummaryResponse.ok ? taskSummaryResponse.data ?? [] : []
      clearTaskLists()
    } catch (error) {
      if (requestId !== fetchRequestId) return
      console.error('Error fetching orchestration data', error)
    } finally {
      if (requestId === fetchRequestId) loading.value = false
    }
  }

  const refreshDataConnections = async (
    requestedWorkspaceId = selectedWorkspaceId.value
  ) => {
    if (!requestedWorkspaceId) {
      dataConnections.value = []
      return
    }
    dataConnections.value = await hs.dataConnections.listAllItems({
      workspace_id: requestedWorkspaceId,
      order_by: 'name',
    } as any)
  }

  const fetchTasksForGroup = async (
    tab: TabId,
    groupId: string | null | undefined,
    requestedWorkspaceId = selectedWorkspaceId.value,
    force = false
  ) => {
    if (!requestedWorkspaceId || !groupId) {
      clearTaskListForTab(tab)
      loadedTaskGroup.value = null
      return
    }

    const current = loadedTaskGroup.value
    if (
      !force &&
      current?.workspaceId === requestedWorkspaceId &&
      current.tab === tab &&
      current.groupId === groupId
    ) {
      return
    }

    const requestId = ++taskRequestId
    taskLoading.value = true
    clearTaskListForTab(tab)

    try {
      if (tab === 'ingestion') {
        const items = await hs.tasks.listAllItems({
          workspace_id: [requestedWorkspaceId],
          data_connection_id: [groupId],
          order_by: ['name'],
        } as any)
        if (requestId !== taskRequestId) return
        workspaceTasks.value = items as any
      } else if (tab === 'aggregation') {
        const items = await hs.dataProductTasks.listAllItems({
          workspace_id: [requestedWorkspaceId],
          thing_id: [groupId],
          order_by: ['name'],
        } as any)
        if (requestId !== taskRequestId) return
        dataProductTasks.value = items as any
      } else {
        const items = await hs.monitoringTasks.listAllItems({
          workspace_id: [requestedWorkspaceId],
          thing_id: [groupId],
          order_by: ['name'],
        } as any)
        if (requestId !== taskRequestId) return
        monitoringTasks.value = items as any
      }

      loadedTaskGroup.value = {
        workspaceId: requestedWorkspaceId,
        tab,
        groupId,
      }
    } catch (error) {
      if (requestId !== taskRequestId) return
      console.error('Error fetching orchestration tasks', error)
    } finally {
      if (requestId === taskRequestId) taskLoading.value = false
    }
  }

  return {
    loading,
    taskLoading,
    workspaceTasks,
    dataConnections,
    things,
    datastreamThingByDatastreamId,
    dataProductTasks,
    monitoringTasks,
    loadedTaskGroup,
    fetchAll,
    refreshDataConnections,
    fetchTasksForGroup,
  }
}

export type OrchestrationData = ReturnType<typeof useOrchestrationData>

export type TaskListRef =
  | Ref<TaskExpanded[]>
  | Ref<DataProductTaskExpanded[]>
  | Ref<MonitoringTaskExpanded[]>
