import { computed, ref, type Ref } from 'vue'
import hs, {
  DataConnection,
  DataProductTaskExpanded,
  MonitoringTaskExpanded,
  TaskExpanded,
  Thing,
} from '@hydroserver/client'
import { storeToRefs } from 'pinia'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'

export function useOrchestrationData() {
  const { workspaceTasks } = storeToRefs(useOrchestrationStore())
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
  const selectedWorkspaceId = computed(() => selectedWorkspace.value?.id ?? null)

  const loading = ref(false)
  const dataConnections = ref<DataConnection[]>([])
  const things = ref<Thing[]>([])
  const datastreamThingByDatastreamId = ref<Record<string, string>>({})
  const dataProductTasks = ref<DataProductTaskExpanded[]>([])
  const monitoringTasks = ref<MonitoringTaskExpanded[]>([])

  let fetchRequestId = 0

  const fetchAll = async (requestedWorkspaceId = selectedWorkspaceId.value) => {
    const requestId = ++fetchRequestId
    if (!requestedWorkspaceId) {
      loading.value = false
      dataConnections.value = []
      workspaceTasks.value = []
      dataProductTasks.value = []
      monitoringTasks.value = []
      things.value = []
      datastreamThingByDatastreamId.value = {}
      return
    }

    loading.value = true
    try {
      const [dcItems, etlItems, dpItems, monItems, thingItems, dsItems] =
        await Promise.all([
          hs.dataConnections.listAllItems({
            workspace_id: requestedWorkspaceId,
            order_by: 'name',
          } as any),
          hs.tasks.listAllItems({ workspace_id: requestedWorkspaceId } as any),
          hs.dataProductTasks.listAllItems({
            workspace_id: [requestedWorkspaceId],
          } as any),
          hs.monitoringTasks.listAllItems({
            workspace_id: [requestedWorkspaceId],
          } as any),
          hs.things.listAllItems({
            workspace_id: [requestedWorkspaceId],
            order_by: ['name'],
          } as any),
          hs.datastreams.listAllItems({
            workspace_id: [requestedWorkspaceId],
          } as any),
        ])

      if (requestId !== fetchRequestId) return

      dataConnections.value = dcItems
      workspaceTasks.value = etlItems as any
      dataProductTasks.value = dpItems as any
      monitoringTasks.value = monItems as any
      things.value = thingItems as any

      const map: Record<string, string> = {}
      for (const ds of dsItems ?? []) {
        if (ds?.id && ds?.thingId) map[ds.id] = ds.thingId
      }
      datastreamThingByDatastreamId.value = map
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

  return {
    loading,
    workspaceTasks,
    dataConnections,
    things,
    datastreamThingByDatastreamId,
    dataProductTasks,
    monitoringTasks,
    fetchAll,
    refreshDataConnections,
  }
}

export type OrchestrationData = ReturnType<typeof useOrchestrationData>

export type TaskListRef =
  | Ref<TaskExpanded[]>
  | Ref<DataProductTaskExpanded[]>
  | Ref<MonitoringTaskExpanded[]>
