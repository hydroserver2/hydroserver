<template>
  <div class="orchestration-shell">
    <OrchestrationNavRail
      :tabs="tabs"
      :active-tab="activeTab"
      :active-view="activeView"
      @select-tab="setActiveTab"
      @open-workspaces="openWorkspaceManager"
      @open-hydro-loader="goToHydroLoader"
    />

    <section v-if="activeView === 'workspaces'" class="workspace-detail">
      <OrchestrationWorkspaceManager table-height="calc(100vh - 230px)" />
    </section>

    <template v-else>
      <OrchestrationContextSidebar
        :active-tab="activeTab"
        :connections="filteredConnections"
        :sites="filteredSites"
        :selected-connection-id="selectedConnectionId"
        :selected-thing-id="selectedThingId"
        :search="sidebarSearch"
        :title="sidebarTitle"
        :add-label="addLabel"
        :accent="activeAccent"
        :can-edit="canEditOrchestration"
        :task-count-for-connection="taskCountForConnection"
        :task-count-for-site="taskCountForSite"
        :issue-count-for-site="issueCountForSite"
        :violation-count-for-site="violationCountForSite"
        :dot-color-for-connection="dotColorForConnection"
        :dot-color-for-site="dotColorForSite"
        @update:search="sidebarSearch = $event"
        @select-connection="selectConnection"
        @select-site="selectSite"
        @edit-connection="openEditDialog"
        @delete-connection="openDeleteDialog"
        @create="openCreateDialog"
      />

      <section v-if="selectedTaskId" class="detail detail--task">
        <TaskDetails
          :task-id="selectedTaskId"
          :task-kind="selectedTaskKind"
          :run-id="selectedRunId"
          embedded
          @close="closeTaskDetails"
          @deleted="onTaskDetailsChanged"
          @updated="onTaskDetailsChanged"
        />
      </section>

      <TaskListPanel
        v-else
        :active-tab="activeTab"
        :accent="activeAccent"
        :accent-light="activeAccentLight"
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
        :task-search="taskSearch"
        :status-filter="statusFilter"
        :sort-key="sortKey"
        :sort-dir="sortDir"
        @update:task-search="taskSearch = $event"
        @update:status-filter="statusFilter = $event"
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
      <TaskForm
        :initial-data-connection="selectedTaskDataConnection"
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
        :workspace-id="workspaceId"
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
        :workspace-id="workspaceId"
        :initial-thing-id="selectedThingId"
        @close="openExpressionForm = false"
        @created="onDataProductTaskCreated"
      />
    </v-dialog>

    <v-dialog v-model="openDerivationForm" width="60rem">
      <DerivationForm
        :workspace-id="workspaceId"
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
        :workspace-id="workspaceId"
        :initial-thing-id="selectedThingId"
        @close="openRatingCurveForm = false"
        @created="onDataProductTaskCreated"
      />
    </v-dialog>

    <v-dialog v-model="openQualityForm" width="64rem">
      <QualityManagementForm
        :workspace-id="workspaceId"
        :initial-thing-id="selectedThingId"
        :edit-task-id="editingQualityTaskId"
        @close="closeQualityForm"
        @created="onQualityTaskChanged"
        @updated="onQualityTaskChanged"
        @deleted="onQualityTaskChanged"
      />
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import hs, {
  DataConnection,
  PermissionAction,
  PermissionResource,
} from '@hydroserver/client'

import router from '@/router/router'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useWorkspaceStore } from '@/store/workspaces'
import { useOrchestrationStore } from '@/store/orchestration'

import { useOrchestrationData } from '@/composables/orchestration/useOrchestrationData'
import { useOrchestrationTaskRows } from '@/composables/orchestration/useOrchestrationTaskRows'
import { useTaskRunNowPolling } from '@/composables/orchestration/useTaskRunNowPolling'

import OrchestrationNavRail from './workbench/OrchestrationNavRail.vue'
import OrchestrationContextSidebar from './workbench/OrchestrationContextSidebar.vue'
import TaskListPanel from './workbench/TaskListPanel.vue'
import {
  TAB_META,
  TAB_TO_KIND,
  worstDotColor,
  type ActiveView,
  type TabDefinition,
  type TabId,
  type TaskKind,
  type TaskRow,
} from './workbench/orchestrationTabs'

const DataConnectionForm = defineAsyncComponent(
  () => import('@/components/Orchestration/DataConnectionForm.vue')
)
const OrchestrationWorkspaceManager = defineAsyncComponent(
  () => import('@/components/Workspace/OrchestrationWorkspaceManager.vue')
)
const TaskForm = defineAsyncComponent(
  () => import('@/components/Orchestration/TaskForm.vue')
)
const DeleteDataConnectionCard = defineAsyncComponent(
  () => import('@/components/Orchestration/DeleteDataConnectionCard.vue')
)
const TaskDetails = defineAsyncComponent(
  () => import('@/pages/TaskDetails.vue')
)
const AggregationForm = defineAsyncComponent(
  () => import('@/components/Orchestration/AggregationForm.vue')
)
const ExpressionForm = defineAsyncComponent(
  () => import('@/components/Orchestration/ExpressionForm.vue')
)
const DerivationForm = defineAsyncComponent(
  () => import('@/components/Orchestration/DerivationForm.vue')
)
const RatingCurveForm = defineAsyncComponent(
  () => import('@/components/Orchestration/RatingCurveForm.vue')
)
const QualityManagementForm = defineAsyncComponent(
  () => import('@/components/Orchestration/QualityManagementForm.vue')
)

const props = defineProps<{ workspaceId: string }>()

const route = useRoute()

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

const { orchestrationSearch, orchestrationStatusFilter } = storeToRefs(
  useOrchestrationStore()
)
const { workspaces } = storeToRefs(useWorkspaceStore())
const { hasPermission, isAdmin, isOwner } = useWorkspacePermissions()

const activeTab = ref<TabId>('ingestion')
const activeView = ref<ActiveView>('tasks')
const sidebarSearch = ref('')
const taskSearch = ref('')
const statusFilter = ref<string[]>([])
const selectedConnectionId = ref<string | null>(null)
const selectedThingId = ref<string | null>(null)

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
  toggleSchedulePaused,
  startMonitoringRun,
} = useTaskRunNowPolling({
  lists: {
    etl: workspaceTasks,
    dataProduct: dataProductTasks,
    monitoring: monitoringTasks,
  },
  currentWorkspaceId: () => props.workspaceId,
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

const workspaceForPage = computed(() =>
  workspaces.value.find((w) => w.id === props.workspaceId)
)

const canEditOrchestration = computed(() => {
  const workspace = workspaceForPage.value
  if (!workspace) return false
  const roleName = `${workspace.collaboratorRole?.name ?? ''}`.toLowerCase()
  if (isAdmin() || isOwner(workspace) || roleName === 'editor') return true
  return hasPermission(
    PermissionResource.Workspace,
    PermissionAction.Edit,
    workspace
  )
})

const countIssues = (rows: TaskRow[]) =>
  rows.filter(
    (r) =>
      r.statusSort === 'Needs attention' || r.statusSort === 'Behind schedule'
  ).length

const tabs = computed<TabDefinition[]>(() => [
  { ...TAB_META.ingestion, issues: countIssues(etlTaskRows.value) },
  { ...TAB_META.aggregation, issues: countIssues(dataProductTaskRows.value) },
  { ...TAB_META.quality, issues: countIssues(monitoringTaskRows.value) },
])

const activeTabDef = computed(
  () => tabs.value.find((t) => t.id === activeTab.value) ?? tabs.value[0]
)
const activeAccent = computed(() => activeTabDef.value.accent)
const activeAccentLight = computed(() => activeTabDef.value.accentLight)

const sidebarTitle = computed(() =>
  activeTab.value === 'ingestion' ? 'Connections' : 'Sites'
)
const addLabel = computed(() =>
  activeTab.value === 'ingestion' ? 'Add data connection' : 'Add site'
)

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

const taskCountForSite = (thingId: string) =>
  activeTaskRows.value.filter((t) => t.thingId === thingId).length

const issueCountForSite = (thingId: string) =>
  activeTaskRows.value.filter(
    (t) =>
      t.thingId === thingId &&
      (t.statusSort === 'Needs attention' || t.statusSort === 'Behind schedule')
  ).length

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
  const term = taskSearch.value.trim().toLowerCase()
  const filters = new Set(statusFilter.value)
  return visibleTasks.value.filter((t) => {
    if (filters.size > 0) {
      const bucket = t.statusSort ?? 'Unknown'
      if (!filters.has(bucket)) return false
    }
    if (!term) return true
    const haystack = [t.name, t.statusName, t.lastRun, t.nextRun]
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

const selectedTaskId = computed(() => {
  const value = route.query.taskId
  return typeof value === 'string' && value.trim() ? value : null
})

const selectedRunId = computed(() => {
  const value = route.query.runId
  return typeof value === 'string' && value.trim() ? value : null
})

const selectedTaskKind = computed<TaskKind>(() => {
  const value = route.query.taskKind
  if (value === 'etl' || value === 'dataProduct' || value === 'monitoring') {
    return value
  }

  const taskId = selectedTaskId.value
  const row = taskId
    ? [
        ...etlTaskRows.value,
        ...dataProductTaskRows.value,
        ...monitoringTaskRows.value,
      ].find((candidate) => candidate.id === taskId)
    : null
  return row?.kind ?? TAB_TO_KIND[activeTab.value]
})

const hasTaskDetailsQuery = computed(
  () => selectedTaskId.value !== null || selectedRunId.value !== null
)

const closeTaskDetails = async () => {
  if (!hasTaskDetailsQuery.value) return
  const nextQuery = { ...route.query }
  delete nextQuery.taskId
  delete nextQuery.taskKind
  delete nextQuery.runId
  await router.replace({ name: 'Orchestration', query: nextQuery })
}

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
  activeView.value = 'tasks'
  activeTab.value = tab
  sidebarSearch.value = ''
  autoSelectSidebar()
  await closeTaskDetails()
}

const openWorkspaceManager = async () => {
  activeView.value = 'workspaces'
  await closeTaskDetails()
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

watch(
  () => props.workspaceId,
  async (newId) => {
    if (newId == null) return
    stopAll()
    selectedConnectionId.value = null
    selectedThingId.value = null
    await fetchAll(newId)
    autoSelectSidebar()
    const NON_TERMINAL = ['PENDING', 'STARTED']
    for (const task of workspaceTasks.value) {
      if (
        task.latestRun?.id &&
        NON_TERMINAL.includes(task.latestRun.status ?? '')
      )
        startMonitoringRun('etl', task.id, task.latestRun.id)
    }
    for (const task of dataProductTasks.value) {
      if (
        task.latestRun?.id &&
        NON_TERMINAL.includes(task.latestRun.status ?? '')
      )
        startMonitoringRun('dataProduct', task.id, task.latestRun.id)
    }
    for (const task of monitoringTasks.value) {
      if (
        task.latestRun?.id &&
        NON_TERMINAL.includes(task.latestRun.status ?? '')
      )
        startMonitoringRun('monitoring', task.id, task.latestRun.id)
    }
  },
  { immediate: true }
)

// Persist task search + status filter across navigations via the store.
watch(
  orchestrationSearch,
  (value) => {
    if (value) taskSearch.value = value
  },
  { immediate: true }
)
watch(taskSearch, (value) => {
  orchestrationSearch.value = value ?? ''
})

watch(
  orchestrationStatusFilter,
  (value) => {
    if (Array.isArray(value) && value.length) statusFilter.value = [...value]
  },
  { immediate: true }
)
watch(statusFilter, (value) => {
  if (!Array.isArray(value)) {
    statusFilter.value = []
    return
  }
  orchestrationStatusFilter.value = [...value]
})

const openCreateDialog = () => {
  if (!canEditOrchestration.value) return
  openCreateDataConnection.value = true
}

const openCreateTaskDialog = (dc: DataConnection) => {
  if (!canEditOrchestration.value) return
  selectedTaskDataConnection.value = dc
  openCreateTask.value = true
}

const closeCreateTaskDialog = () => {
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
  await refreshDataConnections(props.workspaceId)
}

const onTaskCreated = async () => {
  closeCreateTaskDialog()
  await fetchAll(props.workspaceId)
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

const onDataProductTaskCreated = async () => {
  openAggregationForm.value = false
  openDerivationForm.value = false
  openExpressionForm.value = false
  openRatingCurveForm.value = false
  await fetchAll(props.workspaceId)
  autoSelectSidebar()
}

const onQualityTaskChanged = async () => {
  closeQualityForm()
  await fetchAll(props.workspaceId)
  autoSelectSidebar()
}

const onTaskDetailsChanged = async () => {
  await fetchAll(props.workspaceId)
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
    dataConnections.value = dataConnections.value.filter((dc) => dc.id !== id)
    if (selectedConnectionId.value === id) {
      selectedConnectionId.value = dataConnections.value[0]?.id ?? null
    }
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
  const currentQuery = { ...(router.currentRoute.value.query ?? {}) }
  delete currentQuery.runId
  await router.push({
    name: 'Orchestration',
    query: {
      ...currentQuery,
      workspaceId: props.workspaceId,
      taskId: row.id,
      taskKind: row.kind,
    },
  })
}
</script>

<style scoped>
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
