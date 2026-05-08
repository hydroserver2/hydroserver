<template>
  <div class="orchestration-page">
    <div class="orchestration-page-toolbar">
      <WorkspaceToolbar
        layout="orchestration"
        title="Job orchestration"
        hide-workspace-management
      />
    </div>

    <div v-if="!!selectedWorkspace" class="orchestration-page-body">
      <div class="orchestration-shell">
        <OrchestrationNavRail
          :tabs="tabs"
          @select-tab="setActiveTab"
          @open-workspaces="openWorkspaceManager"
          @open-hydro-loader="goToHydroLoader"
        />

        <section v-if="activeView === 'workspaces'" class="workspace-detail">
          <OrchestrationWorkspaceManager table-height="calc(100vh - 230px)" />
        </section>

        <template v-else>
          <OrchestrationContextSidebar
            :connections="filteredConnections"
            :sites="filteredSites"
            :can-edit="canEditOrchestration"
            :task-count-for-connection="taskCountForConnection"
            :issue-count-for-connection="issueCountForConnection"
            :task-count-for-site="taskCountForSite"
            :issue-count-for-site="issueCountForSite"
            :violation-count-for-site="violationCountForSite"
            :dot-color-for-connection="dotColorForConnection"
            :dot-color-for-site="dotColorForSite"
            @select-connection="selectConnection"
            @select-site="selectSite"
            @edit-connection="openEditDialog"
            @delete-connection="openDeleteDialog"
            @create="openCreateDialog"
          />

          <RouterView v-slot="{ Component }">
            <section
              v-if="hasTaskDetails && Component"
              class="detail detail--task"
            >
              <component
                :is="Component"
                :task-id="selectedTaskId"
                :run-id="selectedRunId"
                :initial-task="selectedTask"
                embedded
                @close="closeTaskDetails"
                @deleted="onTaskDeleted"
                @updated="onTaskDetailsChanged"
              />
            </section>

            <TaskListPanel
              v-else
              :can-edit="canEditOrchestration"
              :loading="loading"
              :has-selection="hasSelection"
              :detail-title="detailTitle"
              :detail-type-badge="detailTypeBadge"
              :selected-connection="selectedConnection"
              :visible-tasks="visibleTasks"
              :sorted-visible-tasks="sortedVisibleTasks"
              :empty-heading="emptyHeading"
              :empty-message="emptyMessage"
              :empty-tasks-message="emptyTasksMessage"
              :sort-key="sortKey"
              :sort-dir="sortDir"
              @toggle-sort="toggleSort"
              @toggle-paused="onTogglePaused"
              @run-now="onRunNow"
              @open-task="goToTask"
              @add-task="openCreateTaskDialog(selectedConnection!)"
              @add-aggregation="openAggregationForm = true"
              @add-expression="openExpressionForm = true"
              @add-derivation="openDerivationForm = true"
              @add-rating-curve="openRatingCurveForm = true"
              @add-quality="openQualityForm = true"
            />
          </RouterView>
        </template>

        <v-dialog v-model="openCreateDataConnection" width="60rem">
          <DataConnectionForm
            @close="openCreateDataConnection = false"
            @created="onDataConnectionCreated"
          />
        </v-dialog>

        <v-dialog
          v-if="selectedTaskDataConnection"
          v-model="openCreateTask"
          width="80rem"
        >
          <IngestionTaskForm
            :data-connection="selectedTaskDataConnection"
            @close="closeCreateTaskDialog"
            @created="onTaskCreated"
          />
        </v-dialog>

        <v-dialog
          v-if="selectedDataConnection"
          v-model="openEditDataConnection"
          width="80rem"
        >
          <DataConnectionForm
            :dataConnection="selectedDataConnection"
            @close="openEditDataConnection = false"
            @updated="onDataConnectionUpdated"
          />
        </v-dialog>

        <v-dialog
          v-if="selectedDataConnection"
          v-model="openDeleteDataConnection"
          width="40rem"
        >
          <DeleteDataConnectionCard
            :itemName="selectedDataConnection.name"
            @close="openDeleteDataConnection = false"
            @delete="onDataConnectionDeleted"
          />
        </v-dialog>

        <v-dialog v-model="openAggregationForm" width="60rem">
          <AggregationForm
            :initial-thing-id="selectedThingId"
            :edit-task-id="editingAggregationTaskId"
            @close="closeAggregationForm"
            @created="onDataProductTaskCreated"
            @updated="onTaskDetailsChanged"
            @deleted="onTaskDetailsChanged"
          />
        </v-dialog>

        <v-dialog v-model="openExpressionForm" width="60rem">
          <ExpressionForm
            :initial-thing-id="selectedThingId"
            @close="openExpressionForm = false"
            @created="onDataProductTaskCreated"
          />
        </v-dialog>

        <v-dialog v-model="openDerivationForm" width="60rem">
          <DerivationForm
            :initial-thing-id="selectedThingId"
            :edit-task-id="editingDerivationTaskId"
            @close="closeDerivationForm"
            @created="onDataProductTaskCreated"
            @updated="onTaskDetailsChanged"
            @deleted="onTaskDetailsChanged"
          />
        </v-dialog>

        <v-dialog v-model="openRatingCurveForm" width="60rem">
          <RatingCurveForm
            :initial-thing-id="selectedThingId"
            @close="openRatingCurveForm = false"
            @created="onDataProductTaskCreated"
          />
        </v-dialog>

        <v-dialog v-model="openQualityForm" width="64rem">
          <QualityManagementForm
            :initial-thing-id="selectedThingId"
            :edit-task-id="editingQualityTaskId"
            @close="closeQualityForm"
            @created="onQualityTaskChanged"
            @updated="onQualityTaskChanged"
            @deleted="onQualityTaskChanged"
          />
        </v-dialog>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterView } from 'vue-router'
import { storeToRefs } from 'pinia'
import hs, {
  DataConnection,
  type DataProductTask,
  PermissionAction,
  PermissionResource,
  type TaskExpanded,
} from '@hydroserver/client'

import router from '@/router/router'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useWorkspaceStore } from '@/store/workspaces'
import { useOrchestrationStore } from '@/store/orchestration'
import { useOrchestrationData } from '@/composables/orchestration/useOrchestrationData'
import { useOrchestrationTaskRows } from '@/composables/orchestration/useOrchestrationTaskRows'
import { useTaskRunNowPolling } from '@/composables/orchestration/useTaskRunNowPolling'
import { useOrchestrationRouteState } from '@/composables/orchestration/useOrchestrationRouteState'

import WorkspaceToolbar from '@/components/Workspace/WorkspaceToolbar.vue'
import OrchestrationNavRail from '@/components/Orchestration/workbench/OrchestrationNavRail.vue'
import OrchestrationContextSidebar from '@/components/Orchestration/workbench/OrchestrationContextSidebar.vue'
import TaskListPanel from '@/components/Orchestration/workbench/TaskListPanel.vue'
import DataConnectionForm from '@/components/Orchestration/connections/DataConnectionForm.vue'
import OrchestrationWorkspaceManager from '@/components/Workspace/OrchestrationWorkspaceManager.vue'
import IngestionTaskForm from '@/components/Orchestration/ingestion/IngestionTaskForm.vue'
import DeleteDataConnectionCard from '@/components/Orchestration/connections/DeleteDataConnectionCard.vue'
import AggregationForm from '@/components/Orchestration/data-products/AggregationForm.vue'
import ExpressionForm from '@/components/Orchestration/data-products/ExpressionForm.vue'
import DerivationForm from '@/components/Orchestration/data-products/DerivationForm.vue'
import RatingCurveForm from '@/components/Orchestration/data-products/RatingCurveForm.vue'
import QualityManagementForm from '@/components/Orchestration/monitoring/QualityManagementForm.vue'

import {
  TAB_META,
  countTaskIssues,
  taskHasIssue,
  worstDotColor,
  type TabDefinition,
  type TabId,
  type TaskRow,
} from '@/components/Orchestration/workbench/orchestrationTabs'

const {
  view: routeView,
  taskKind: selectedTaskKind,
  taskId: selectedTaskId,
  runId: selectedRunId,
  hasTaskDetails,
  replaceView,
  closeTaskDetails,
  pushTaskDetails,
} = useOrchestrationRouteState()

const {
  loading,
  workspaceTasks,
  dataConnections,
  things,
  datastreamThingByDatastreamId,
  dataProductTasks,
  monitoringTasks,
  fetchAll,
  refreshDataConnections,
} = useOrchestrationData()

const orchestrationStore = useOrchestrationStore()
const {
  orchestrationSearch,
  orchestrationStatusFilter,
  activeTab,
  activeView,
  selectedConnectionId,
  selectedThingId,
  sidebarSearch,
  draftDatastreams,
} = storeToRefs(orchestrationStore)
const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
const { hasPermission, isAdmin, isOwner } = useWorkspacePermissions()
const selectedWorkspaceId = computed(() => selectedWorkspace.value?.id ?? null)

watch(
  routeView,
  (view) => {
    if (view === 'workspaces') {
      activeView.value = 'workspaces'
    } else {
      activeView.value = 'tasks'
      activeTab.value = view
    }
  },
  { immediate: true }
)
const activeRunStatuses = new Set(['PENDING', 'STARTED'])

const selectedDataConnection = ref<DataConnection | null>(null)
const selectedTaskDataConnection = ref<DataConnection | null>(null)
const openCreateDataConnection = ref(false)
const openCreateTask = ref(false)
const openEditDataConnection = ref(false)
const openDeleteDataConnection = ref(false)
const openAggregationForm = ref(false)
const editingAggregationTaskId = ref<string | null>(null)
const openExpressionForm = ref(false)
const openDerivationForm = ref(false)
const editingDerivationTaskId = ref<string | null>(null)
const openRatingCurveForm = ref(false)
const openQualityForm = ref(false)
const editingQualityTaskId = ref<string | null>(null)

const {
  runNowTriggeredByTaskId,
  stopAll,
  runTaskNow,
  startPollingTaskRun,
  toggleSchedulePaused,
} = useTaskRunNowPolling({
  lists: {
    etl: workspaceTasks,
    dataProduct: dataProductTasks,
    monitoring: monitoringTasks,
  },
  currentWorkspaceId: () => selectedWorkspaceId.value!,
})

const {
  etlTaskRows,
  dataProductTaskRows,
  monitoringTaskRows,
  activeTaskRows,
  sortKey,
  sortDir,
  toggleSort,
  sortRows,
} = useOrchestrationTaskRows({
  activeTab,
  workspaceTasks,
  dataProductTasks,
  monitoringTasks,
  datastreamThingByDatastreamId,
  runNowTriggeredByTaskId,
})

const canEditOrchestration = computed(() => {
  const ws = selectedWorkspace.value
  if (!ws) return false
  const roleName = `${ws.collaboratorRole?.name ?? ''}`.toLowerCase()
  if (isAdmin() || isOwner(ws) || roleName === 'editor') return true
  return hasPermission(PermissionResource.Workspace, PermissionAction.Edit, ws)
})

const tabs = computed<TabDefinition[]>(() => [
  { ...TAB_META.ingestion, issues: countTaskIssues(etlTaskRows.value) },
  {
    ...TAB_META.aggregation,
    issues: countTaskIssues(dataProductTaskRows.value),
  },
  { ...TAB_META.quality, issues: countTaskIssues(monitoringTaskRows.value) },
])

const filterByName = <T extends { name: string }>(items: T[], term: string) => {
  const q = term.trim().toLowerCase()
  if (!q) return items
  return items.filter((x) => x.name.toLowerCase().includes(q))
}

const filteredConnections = computed(() =>
  filterByName(dataConnections.value, sidebarSearch.value)
)
const filteredSites = computed(() =>
  filterByName(things.value, sidebarSearch.value)
)

const connectionsById = computed(
  () => new Map(dataConnections.value.map((dc) => [dc.id, dc]))
)
const thingsById = computed(
  () => new Map(things.value.map((th) => [th.id, th]))
)

const taskCountForConnection = (dcId: string) =>
  etlTaskRows.value.filter((t) => t.dataConnectionId === dcId).length

const issueCountForConnection = (dcId: string) =>
  etlTaskRows.value.filter(
    (t) => t.dataConnectionId === dcId && taskHasIssue(t)
  ).length

const taskCountForSite = (thingId: string) =>
  activeTaskRows.value.filter((t) => t.thingId === thingId).length

const issueCountForSite = (thingId: string) =>
  activeTaskRows.value.filter((t) => t.thingId === thingId && taskHasIssue(t))
    .length

const violationCountForSite = (thingId: string) =>
  monitoringTaskRows.value
    .filter((t) => t.thingId === thingId)
    .reduce((sum, task) => sum + (task.monitoringRulesViolated ?? 0), 0)

const dotColorForConnection = (dcId: string) =>
  worstDotColor(etlTaskRows.value.filter((t) => t.dataConnectionId === dcId))

const dotColorForSite = (thingId: string) =>
  worstDotColor(activeTaskRows.value.filter((t) => t.thingId === thingId))

const selectedConnection = computed<DataConnection | null>(() =>
  selectedConnectionId.value
    ? connectionsById.value.get(selectedConnectionId.value) ?? null
    : null
)

const selectedSite = computed(() =>
  selectedThingId.value
    ? thingsById.value.get(selectedThingId.value) ?? null
    : null
)

const visibleTasks = computed<TaskRow[]>(() => {
  if (activeTab.value === 'ingestion') {
    if (!selectedConnectionId.value) return []
    return etlTaskRows.value.filter(
      (t) => t.dataConnectionId === selectedConnectionId.value
    )
  }
  if (!selectedThingId.value) return []
  return activeTaskRows.value.filter((t) => t.thingId === selectedThingId.value)
})

const searchedVisibleTasks = computed<TaskRow[]>(() => {
  const term = orchestrationSearch.value.trim().toLowerCase()
  const filters = new Set(orchestrationStatusFilter.value)
  return visibleTasks.value.filter((t) => {
    if (filters.size > 0) {
      const bucket = t.statusSort ?? 'Unknown'
      if (!filters.has(bucket)) return false
    }
    if (!term) return true
    const haystack = [t.name, t.statusName, t.statusSort, t.lastRun, t.nextRun]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return haystack.includes(term)
  })
})

const sortedVisibleTasks = computed<TaskRow[]>(() =>
  sortRows(searchedVisibleTasks.value)
)

const hasSelection = computed(() =>
  activeTab.value === 'ingestion'
    ? !!selectedConnectionId.value
    : !!selectedThingId.value
)

const detailTitle = computed(() => {
  if (activeTab.value === 'ingestion') {
    return selectedConnection.value?.name ?? 'Select a data connection'
  }
  return selectedSite.value?.name ?? 'Select a site'
})

const detailTypeBadge = computed(() => {
  if (activeTab.value === 'ingestion') {
    return selectedConnection.value?.payload?.type ?? ''
  }
  return selectedSite.value?.siteType ?? ''
})

const emptyHeading = computed(() =>
  activeTab.value === 'ingestion'
    ? dataConnections.value.length === 0
      ? 'No data connections have been registered yet.'
      : 'Select a data connection'
    : things.value.length === 0
    ? 'No sites registered in this workspace.'
    : 'Select a site'
)

const emptyMessage = computed(() => {
  if (activeTab.value === 'ingestion') {
    if (dataConnections.value.length === 0) {
      return "Click 'Add data connection' to get started."
    }
    return 'Pick a connection from the list to view its tasks.'
  }
  if (things.value.length === 0) {
    return 'Create a site in your workspace to assign tasks to it.'
  }
  return 'Pick a site to view the tasks writing data to it.'
})

const emptyTasksMessage = computed(() =>
  activeTab.value === 'ingestion'
    ? 'No tasks registered for this data connection.'
    : 'No tasks are writing data to this site yet.'
)

const selectedTask = computed(() => {
  const taskId = selectedTaskId.value
  const kind = selectedTaskKind.value
  if (!taskId || !kind) return null
  if (kind === 'etl')
    return workspaceTasks.value.find((t) => t.id === taskId) ?? null
  if (kind === 'dataProduct')
    return dataProductTasks.value.find((t) => t.id === taskId) ?? null
  return monitoringTasks.value.find((t) => t.id === taskId) ?? null
})

const autoSelectSidebar = () => {
  if (activeTab.value === 'ingestion') {
    const current = selectedConnectionId.value
    if (current && connectionsById.value.has(current)) return
    selectedConnectionId.value = dataConnections.value[0]?.id ?? null
  } else {
    const current = selectedThingId.value
    if (current && thingsById.value.has(current)) return
    selectedThingId.value = things.value[0]?.id ?? null
  }
}

const setActiveTab = async (tab: TabId) => {
  sidebarSearch.value = ''
  await replaceView(tab)
  autoSelectSidebar()
}

const openWorkspaceManager = async () => {
  await replaceView('workspaces')
}

const goToHydroLoader = async () => {
  await router.push({ name: 'HydroLoader' })
}

const selectConnection = async (id: string) => {
  selectedConnectionId.value = id
  await closeTaskDetails()
}

const selectSite = async (id: string) => {
  selectedThingId.value = id
  await closeTaskDetails()
}

const closeWorkspaceScopedUi = () => {
  openCreateDataConnection.value = false
  openCreateTask.value = false
  openEditDataConnection.value = false
  openDeleteDataConnection.value = false
  openAggregationForm.value = false
  openExpressionForm.value = false
  openDerivationForm.value = false
  openRatingCurveForm.value = false
  openQualityForm.value = false
  selectedDataConnection.value = null
  selectedTaskDataConnection.value = null
  editingAggregationTaskId.value = null
  editingDerivationTaskId.value = null
  editingQualityTaskId.value = null
  sidebarSearch.value = ''
  orchestrationSearch.value = ''
  orchestrationStatusFilter.value = []
  draftDatastreams.value = []
}

watch(
  selectedWorkspaceId,
  async (newId) => {
    if (newId == null) return
    stopAll()
    closeWorkspaceScopedUi()
    selectedConnectionId.value = null
    selectedThingId.value = null
    await closeTaskDetails()
    await fetchAll(newId)
    autoSelectSidebar()
  },
  { immediate: true }
)

const openCreateDialog = () => {
  if (!canEditOrchestration.value) return
  openCreateDataConnection.value = true
}

const openCreateTaskDialog = (dc: DataConnection) => {
  if (!canEditOrchestration.value) return
  selectedTaskDataConnection.value = dc
  openCreateTask.value = true
}

const resetDraftDatastreams = () => {
  draftDatastreams.value = []
}

const closeCreateTaskDialog = () => {
  resetDraftDatastreams()
  openCreateTask.value = false
  selectedTaskDataConnection.value = null
}

const openEditDialog = (dc: DataConnection) => {
  if (!canEditOrchestration.value) return
  selectedDataConnection.value = dc
  openEditDataConnection.value = true
}

const openDeleteDialog = (dc: DataConnection) => {
  if (!canEditOrchestration.value) return
  selectedDataConnection.value = dc
  openDeleteDataConnection.value = true
}

const onDataConnectionCreated = async () => {
  openCreateDataConnection.value = false
  await refreshDataConnections()
}

const onTaskCreated = async (createdTask?: TaskExpanded) => {
  closeCreateTaskDialog()
  await fetchAll()
  const taskToPoll =
    (createdTask?.latestRun?.id ? createdTask : null) ??
    workspaceTasks.value.find((task) => task.id === createdTask?.id)

  if (!taskToPoll?.id) {
    autoSelectSidebar()
    return
  }

  if (
    taskToPoll?.latestRun?.id &&
    activeRunStatuses.has(taskToPoll.latestRun.status)
  ) {
    startPollingTaskRun('etl', taskToPoll.id, taskToPoll.latestRun.id)
  } else if (!taskToPoll?.latestRun) {
    await runTaskNow('etl', taskToPoll.id)
  }
  autoSelectSidebar()
}

const closeAggregationForm = () => {
  openAggregationForm.value = false
  editingAggregationTaskId.value = null
}

const closeDerivationForm = () => {
  openDerivationForm.value = false
  editingDerivationTaskId.value = null
}

const closeQualityForm = () => {
  openQualityForm.value = false
  editingQualityTaskId.value = null
}

const onDataProductTaskCreated = async (createdTask?: DataProductTask) => {
  openAggregationForm.value = false
  openDerivationForm.value = false
  openExpressionForm.value = false
  openRatingCurveForm.value = false
  await fetchAll()

  const taskToPoll = dataProductTasks.value.find(
    (task) => task.id === createdTask?.id
  )

  if (taskToPoll?.id) {
    if (
      taskToPoll.latestRun?.id &&
      activeRunStatuses.has(taskToPoll.latestRun.status)
    ) {
      startPollingTaskRun('dataProduct', taskToPoll.id, taskToPoll.latestRun.id)
    } else if (!taskToPoll.latestRun) {
      await runTaskNow('dataProduct', taskToPoll.id)
    }
  }

  autoSelectSidebar()
}

const onQualityTaskChanged = async () => {
  closeQualityForm()
  await fetchAll()
  autoSelectSidebar()
}

const onTaskDetailsChanged = async () => {
  resetDraftDatastreams()
  await fetchAll()
  autoSelectSidebar()
}

const onTaskDeleted = async () => {
  resetDraftDatastreams()
  await fetchAll()
  autoSelectSidebar()
}

const onDataConnectionUpdated = (updated: DataConnection) => {
  openEditDataConnection.value = false
  const idx = dataConnections.value.findIndex((dc) => dc.id === updated.id)
  if (idx !== -1) dataConnections.value[idx] = updated
}

const onDataConnectionDeleted = async () => {
  if (!selectedDataConnection.value) return
  const id = selectedDataConnection.value.id
  try {
    await hs.dataConnections.delete(id)
    resetDraftDatastreams()
    await fetchAll()
    if (selectedConnectionId.value === id) {
      selectedConnectionId.value = dataConnections.value[0]?.id ?? null
    }
    autoSelectSidebar()
    openDeleteDataConnection.value = false
  } catch (error) {
    console.error('Error deleting data connection', error)
  }
}

const onRunNow = async (row: TaskRow) => {
  if (!canEditOrchestration.value) return
  await runTaskNow(row.kind, row.id)
}

const onTogglePaused = async (row: TaskRow) => {
  if (!canEditOrchestration.value) return
  if (!row.schedule) return
  await toggleSchedulePaused(row.kind, row.id, row.schedule)
}

const goToTask = async (row: TaskRow) => {
  await pushTaskDetails(row)
}
</script>

<style scoped>
.orchestration-page {
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  height: calc(100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px));
  min-height: 0;
  overflow: hidden;
}

.orchestration-page-toolbar {
  flex-shrink: 0;
}

.orchestration-page-body {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

.orchestration-shell {
  display: flex;
  flex: 1;
  min-height: 0;
  background: #ffffff;
  overflow: hidden;
}

.workspace-detail {
  flex: 1;
  min-width: 0;
  overflow: auto;
  background: white;
  padding: 16px 22px;
}

.detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: white;
  min-width: 0;
}

.detail--task {
  padding: 0;
}
</style>
