import { computed, ref, type Ref } from 'vue'
import hs, {
  DataConnection,
  MonitoringSiteTaskSummary,
} from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'
import type {
  TabId,
  TaskKind,
} from '@/components/Orchestration/workbench/orchestrationTabs'
import type {
  DataProductTask,
  Task,
  MonitoringTask,
} from '@/types/orchestrationTasks'

type LoadedTaskGroup = {
  workspaceId: string
  tab: TabId
  groupId: string
} | null

export function useOrchestrationData() {
  const { workspaceTasks } = storeToRefs(useOrchestrationStore())
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
  const selectedWorkspaceId = computed(
    () => selectedWorkspace.value?.id ?? null
  )

  const loading = ref(false)
  const taskLoading = ref(false)
  const dataConnections = ref<DataConnection[]>([])
  const monitoringSites = ref<MonitoringSiteTaskSummary[]>([])
  const dataProductTasks = ref<DataProductTask[]>([])
  const monitoringTasks = ref<MonitoringTask[]>([])
  const loadedTaskGroup = ref<LoadedTaskGroup>(null)

  let fetchRequestId = 0
  let taskRequestId = 0
  const summaryRequestIds = { etl: 0, site: 0 }

  const invalidateTaskRequests = () => {
    taskRequestId += 1
    taskLoading.value = false
  }

  const clearTaskLists = () => {
    invalidateTaskRequests()
    workspaceTasks.value = []
    dataProductTasks.value = []
    monitoringTasks.value = []
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
      monitoringSites.value = []
      return
    }

    loading.value = true
    try {
      const [dcItems, taskSummaryResponse] = await Promise.all([
        hs.dataConnections.listAllItems({
          workspaceId: requestedWorkspaceId,
          sortby: 'name',
        } as any),
        hs.monitoringSites.listTaskSummaries({
          workspaceId: [requestedWorkspaceId],
        }),
      ])

      if (requestId !== fetchRequestId) return

      dataConnections.value = dcItems
      monitoringSites.value = taskSummaryResponse.ok
        ? (taskSummaryResponse.data ?? [])
        : []
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
      workspaceId: requestedWorkspaceId,
      sortby: 'name',
    } as any)
  }

  // Status changes update badges without clearing the selected group's tasks.
  const refreshTaskSummaries = async (
    kind: TaskKind,
    requestedWorkspaceId = selectedWorkspaceId.value
  ) => {
    if (!requestedWorkspaceId) return
    const key = kind === 'etl' ? 'etl' : 'site'
    const requestId = ++summaryRequestIds[key]
    const fetchId = fetchRequestId
    const response =
      kind === 'etl'
        ? await hs.dataConnections.list({
            workspaceId: [requestedWorkspaceId],
            sortby: ['name'],
            fetch_all: true,
          })
        : await hs.monitoringSites.listTaskSummaries({
            workspaceId: [requestedWorkspaceId],
          })
    if (
      selectedWorkspaceId.value !== requestedWorkspaceId ||
      requestId !== summaryRequestIds[key] ||
      fetchId !== fetchRequestId
    )
      return
    if (!response.ok)
      throw new Error(response.message || 'Unable to refresh task summaries.')
    if (kind === 'etl')
      dataConnections.value = response.data as DataConnection[]
    else monitoringSites.value = response.data as MonitoringSiteTaskSummary[]
  }

  const fetchTasksForGroup = async (
    tab: TabId,
    groupId: string | null | undefined,
    requestedWorkspaceId = selectedWorkspaceId.value,
    force = false
  ) => {
    if (!requestedWorkspaceId || !groupId) {
      invalidateTaskRequests()
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
          workspaceId: [requestedWorkspaceId],
          dataConnectionId: [groupId],
          sortby: ['name'],
        })
        if (requestId !== taskRequestId) return
        workspaceTasks.value = items as any
      } else if (tab === 'aggregation') {
        const items = await hs.dataProductTasks.listAllItems({
          workspaceId: [requestedWorkspaceId],
          monitoringSiteId: [groupId],
          sortby: ['name'],
        } as any)
        if (requestId !== taskRequestId) return
        dataProductTasks.value = items as any
      } else {
        const items = await hs.monitoringTasks.listAllItems({
          workspaceId: [requestedWorkspaceId],
          monitoringSiteId: [groupId],
          sortby: ['name'],
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
    monitoringSites,
    dataProductTasks,
    monitoringTasks,
    loadedTaskGroup,
    fetchAll,
    refreshDataConnections,
    refreshTaskSummaries,
    fetchTasksForGroup,
  }
}

export type OrchestrationData = ReturnType<typeof useOrchestrationData>

export type TaskListRef =
  Ref<Task[]> | Ref<DataProductTask[]> | Ref<MonitoringTask[]>
