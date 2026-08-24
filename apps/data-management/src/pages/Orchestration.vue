<template>
  <div class="orchestration-page">
    <div v-if="!routeWorkspaceDenied" class="orchestration-page-body">
      <HsMasterDetailLayout :show-sidebar="!!selectedWorkspace">
        <template #rail>
          <OrchestrationNavRail :tabs="tabs" @select-tab="setActiveTab" />
        </template>

        <template v-if="selectedWorkspace" #sidebar>
          <OrchestrationContextSidebar
            :connections="filteredConnections"
            :sites="filteredSites"
            :can-create="canCreateDataConnections"
            :can-edit="canEditDataConnections"
            :can-delete="canDeleteDataConnections"
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
        </template>

        <HsEmptyState
          v-if="!selectedWorkspace"
          :icon="mdiBriefcaseOutline"
          eyebrow="No selected workspace"
          title="Select or create a workspace to manage jobs"
          data-testid="no-selected-workspace"
        >
          <p>
            Job orchestration is scoped to a workspace. Create a new workspace
            from the Workspaces view, or ask a workspace owner or administrator
            for edit permissions on the workspace whose jobs you need to manage.
          </p>
          <template #actions>
            <v-btn-primary @click="openWorkspaceManager">
              Open workspaces
            </v-btn-primary>
          </template>
        </HsEmptyState>

        <template v-else>
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
                @close="closeTaskDetailsAndSync"
                @deleted="onTaskDeleted"
                @updated="onTaskDetailsChanged"
              />
            </section>

            <TaskListPanel
              v-else
              :can-create="canCreateActiveTasks"
              :can-create-rating-curve="canCreateRatingCurves"
              :can-edit="canEditActiveTasks"
              :loading="listLoading"
              :has-selection="hasSelection"
              :detail-title="detailTitle"
              :detail-type-badge="detailTypeBadge"
              :selected-connection="selectedConnection"
              :visible-tasks="visibleTasks"
              :sorted-visible-tasks="sortedVisibleTasks"
              :empty-heading="emptyHeading"
              :empty-message="emptyMessage"
              :empty-tasks-message="emptyTasksMessage"
              @toggle-paused="onTogglePaused"
              @run-now="onRunNow"
              @open-task="goToTask"
              @add-task="openCreateTaskDialog(selectedConnection!)"
              @add-aggregation="openDataProductForm('aggregation')"
              @add-derivation="openDataProductForm('derivation')"
              @add-rating-curve="openRatingCurveTaskForm"
              @add-quality="openQualityTaskForm"
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
            :initial-monitoring-site-id="selectedMonitoringSiteId"
            :edit-task-id="editingAggregationTaskId"
            @close="closeAggregationForm"
            @created="onDataProductTaskCreated"
            @updated="onTaskDetailsChanged"
            @deleted="onTaskDetailsChanged"
          />
        </v-dialog>

        <v-dialog v-model="openDerivationForm" width="60rem">
          <DerivationForm
            :initial-monitoring-site-id="selectedMonitoringSiteId"
            :edit-task-id="editingDerivationTaskId"
            @close="closeDerivationForm"
            @created="onDataProductTaskCreated"
          />
        </v-dialog>

        <v-dialog v-model="openRatingCurveForm" width="60rem">
          <RatingCurveForm
            :initial-monitoring-site-id="selectedMonitoringSiteId"
            @close="openRatingCurveForm = false"
            @created="onDataProductTaskCreated"
          />
        </v-dialog>

        <v-dialog v-model="openQualityForm" width="64rem">
          <QualityManagementForm
            :initial-monitoring-site-id="selectedMonitoringSiteId"
            :edit-task-id="editingQualityTaskId"
            @close="closeQualityForm"
            @created="onQualityTaskCreated"
            @updated="onQualityTaskChanged"
            @deleted="onQualityTaskChanged"
          />
        </v-dialog>
      </HsMasterDetailLayout>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterView } from 'vue-router'
import { storeToRefs } from 'pinia'
import { sumBy } from 'lodash-es'
import { mdiBriefcaseOutline } from '@mdi/js'
import hs, {
  DataConnection,
  type DataProductTask,
  type MonitoringTask,
  PermissionAction,
  PermissionResource,
  type MonitoringSiteTaskSummary,
} from '@hydroserver/client'

import router from '@/router/router'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import type { Task } from '@/types/orchestrationTasks'
import { useWorkspaceStore } from '@/store/workspaces'
import { useOrchestrationStore } from '@/store/orchestration'
import { useOrchestrationData } from '@/composables/orchestration/useOrchestrationData'
import { useOrchestrationTaskRows } from '@/composables/orchestration/useOrchestrationTaskRows'
import { useTaskRunNowPolling } from '@/composables/orchestration/useTaskRunNowPolling'
import { useOrchestrationRouteState } from '@/composables/orchestration/useOrchestrationRouteState'

import OrchestrationNavRail from '@/components/Orchestration/workbench/OrchestrationNavRail.vue'
import OrchestrationContextSidebar from '@/components/Orchestration/workbench/OrchestrationContextSidebar.vue'
import TaskListPanel from '@/components/Orchestration/workbench/TaskListPanel.vue'
import HsEmptyState from '@/components/base/HsEmptyState.vue'
import HsMasterDetailLayout from '@/components/base/HsMasterDetailLayout.vue'
import DataConnectionForm from '@/components/Orchestration/connections/DataConnectionForm.vue'
import IngestionTaskForm from '@/components/Orchestration/ingestion/IngestionTaskForm.vue'
import DeleteDataConnectionCard from '@/components/Orchestration/connections/DeleteDataConnectionCard.vue'
import AggregationForm from '@/components/Orchestration/data-products/AggregationForm.vue'
import DerivationForm from '@/components/Orchestration/data-products/DerivationForm.vue'
import RatingCurveForm from '@/components/Orchestration/data-products/RatingCurveForm.vue'
import QualityManagementForm from '@/components/Orchestration/monitoring/QualityManagementForm.vue'

import {
  TAB_META,
  countTaskIssues,
  worstDotColor,
  DOT_PALETTE,
  DOT_EMPTY,
  DOT_DEFAULT_OK,
  type TabDefinition,
  type TabId,
  type TaskRow,
} from '@/components/Orchestration/workbench/orchestrationTabs'

const {
  view: routeView,
  taskKind: selectedTaskKind,
  taskId: selectedTaskId,
  runId: selectedRunId,
  workspaceId: routeWorkspaceId,
  dataConnectionId: routeDataConnectionId,
  siteId: routeSiteId,
  hasTaskDetails,
  replaceView,
  replaceSelectedGroup,
  closeTaskDetails,
  pushTaskDetails,
} = useOrchestrationRouteState()

const {
  loading,
  taskLoading,
  workspaceTasks,
  dataConnections,
  monitoringSites,
  datastreamMonitoringSiteByDatastreamId,
  dataProductTasks,
  monitoringTasks,
  loadedTaskGroup,
  fetchAll,
  refreshDataConnections,
  fetchTasksForGroup,
} = useOrchestrationData()

const orchestrationStore = useOrchestrationStore()
const workspaceStore = useWorkspaceStore()
const {
  orchestrationSearch,
  orchestrationStatusFilter,
  orchestrationTaskTypeFilter,
  activeTab,
  selectedConnectionId,
  selectedMonitoringSiteId,
  sidebarSearch,
  draftDatastreams,
} = storeToRefs(orchestrationStore)
const { selectedWorkspace, workspaces } = storeToRefs(workspaceStore)
const { hasPermission } = useWorkspacePermissions()
const selectedWorkspaceId = computed(() => selectedWorkspace.value?.id ?? null)

const applyRouteWorkspace = () => {
  const targetWorkspaceId = routeWorkspaceId.value
  if (!targetWorkspaceId || selectedWorkspace.value?.id === targetWorkspaceId) {
    return false
  }
  if (
    !workspaces.value.some((workspace) => workspace.id === targetWorkspaceId)
  ) {
    return false
  }
  workspaceStore.setSelectedWorkspaceById(targetWorkspaceId)
  return true
}

watch([routeWorkspaceId, workspaces], applyRouteWorkspace, { immediate: true })

// The workspaces list is the user's accessible (associated) workspaces, loaded
// before the app mounts. A workspace_id in the URL that isn't in that list is
// one the user has no permission to view, so surface an explicit error rather
// than silently falling back to a different workspace.
const routeWorkspaceDenied = computed(
  () =>
    !!routeWorkspaceId.value &&
    !workspaces.value.some((ws) => ws.id === routeWorkspaceId.value)
)

watch(
  routeWorkspaceDenied,
  (denied) => {
    if (denied) router.replace({ name: 'AccessDenied' })
  },
  { immediate: true }
)

watch(
  routeView,
  (view) => {
    activeTab.value = view
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
  startPollingForLatestRun,
  toggleSchedulePaused,
} = useTaskRunNowPolling({
  lists: {
    etl: workspaceTasks,
    dataProduct: dataProductTasks,
    monitoring: monitoringTasks,
  },
  currentWorkspaceId: () => selectedWorkspaceId.value!,
})

const { etlTaskRows, dataProductTaskRows, monitoringTaskRows, activeTaskRows } =
  useOrchestrationTaskRows({
    activeTab,
    workspaceTasks,
    dataProductTasks,
    monitoringTasks,
    datastreamMonitoringSiteByDatastreamId,
    runNowTriggeredByTaskId,
  })

const hasWorkspacePermission = (
  resource: PermissionResource,
  action: PermissionAction
) => {
  const ws = selectedWorkspace.value
  if (!ws) return false
  return hasPermission(resource, action, ws)
}

const activeTaskResource = computed(() =>
  activeTab.value === 'ingestion'
    ? PermissionResource.EtlTask
    : activeTab.value === 'aggregation'
      ? PermissionResource.DataProductTask
      : PermissionResource.MonitoringTask
)

const canCreateDataConnections = computed(() =>
  hasWorkspacePermission(
    PermissionResource.DataConnection,
    PermissionAction.Create
  )
)
const canEditDataConnections = computed(() =>
  hasWorkspacePermission(
    PermissionResource.DataConnection,
    PermissionAction.Edit
  )
)
const canDeleteDataConnections = computed(() =>
  hasWorkspacePermission(
    PermissionResource.DataConnection,
    PermissionAction.Delete
  )
)
const canCreateActiveTasks = computed(() =>
  hasWorkspacePermission(activeTaskResource.value, PermissionAction.Create)
)
const canEditActiveTasks = computed(() =>
  hasWorkspacePermission(activeTaskResource.value, PermissionAction.Edit)
)
const canCreateRatingCurves = computed(
  () =>
    canCreateActiveTasks.value &&
    hasWorkspacePermission(
      PermissionResource.RatingCurve,
      PermissionAction.Create
    )
)

const tabs = computed<TabDefinition[]>(() => [
  {
    ...TAB_META.ingestion,
    issues: sumBy(dataConnections.value, taskAttentionCount),
  },
  {
    ...TAB_META.aggregation,
    issues: sumBy(monitoringSites.value, productTaskAttentionCount),
  },
  {
    ...TAB_META.quality,
    issues: sumBy(monitoringSites.value, monitoringTaskAttentionCount),
  },
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
  filterByName(monitoringSites.value, sidebarSearch.value)
)

const connectionsById = computed(
  () => new Map(dataConnections.value.map((dc) => [dc.id, dc]))
)
const monitoringSitesById = computed(
  () => new Map(monitoringSites.value.map((th) => [th.id, th]))
)

const listLoading = computed(() => loading.value || taskLoading.value)

const taskAttentionCount = (connection: DataConnection) =>
  connection.taskAttentionCount

const productTaskAttentionCount = (monitoringSite: MonitoringSiteTaskSummary) =>
  monitoringSite.productTaskAttentionCount

const monitoringTaskAttentionCount = (
  monitoringSite: MonitoringSiteTaskSummary
) => monitoringSite.monitoringTaskAttentionCount

const summaryDotColor = (total: number, issues: number) => {
  if (total === 0) return DOT_EMPTY
  if (issues > 0) return DOT_PALETTE['Needs attention']
  return DOT_DEFAULT_OK
}

const taskCountForConnectionSummary = (dcId: string) =>
  connectionsById.value.get(dcId)?.taskCount ?? 0

const issueCountForConnectionSummary = (dcId: string) =>
  connectionsById.value.get(dcId)?.taskAttentionCount ?? 0

const loadedGroupMatches = (tab: TabId, groupId: string) =>
  loadedTaskGroup.value?.tab === tab &&
  loadedTaskGroup.value.groupId === groupId

const selectedConnectionRows = (dcId: string) =>
  etlTaskRows.value.filter((t) => t.dataConnectionId === dcId)

const selectedSiteRows = (monitoringSiteId: string) =>
  activeTaskRows.value.filter((t) => t.monitoringSiteId === monitoringSiteId)

const taskCountForConnection = (dcId: string) =>
  loadedGroupMatches('ingestion', dcId)
    ? selectedConnectionRows(dcId).length
    : taskCountForConnectionSummary(dcId)

const issueCountForConnection = (dcId: string) =>
  loadedGroupMatches('ingestion', dcId)
    ? countTaskIssues(selectedConnectionRows(dcId))
    : issueCountForConnectionSummary(dcId)

const taskCountForSiteSummary = (monitoringSiteId: string) => {
  const monitoringSite = monitoringSitesById.value.get(monitoringSiteId)
  if (!monitoringSite) return 0
  return activeTab.value === 'aggregation'
    ? monitoringSite.productTaskCount
    : monitoringSite.monitoringTaskCount
}

const issueCountForSiteSummary = (monitoringSiteId: string) => {
  const monitoringSite = monitoringSitesById.value.get(monitoringSiteId)
  if (!monitoringSite) return 0
  return activeTab.value === 'aggregation'
    ? monitoringSite.productTaskAttentionCount
    : monitoringSite.monitoringTaskAttentionCount
}

const taskCountForSite = (monitoringSiteId: string) =>
  loadedGroupMatches(activeTab.value, monitoringSiteId)
    ? selectedSiteRows(monitoringSiteId).length
    : taskCountForSiteSummary(monitoringSiteId)

const issueCountForSite = (monitoringSiteId: string) =>
  loadedGroupMatches(activeTab.value, monitoringSiteId)
    ? countTaskIssues(selectedSiteRows(monitoringSiteId))
    : issueCountForSiteSummary(monitoringSiteId)

const violationCountForSite = (monitoringSiteId: string) =>
  monitoringTaskRows.value
    .filter((t) => t.monitoringSiteId === monitoringSiteId)
    .reduce((sum, task) => sum + (task.monitoringRulesViolated ?? 0), 0)

const dotColorForConnection = (dcId: string) =>
  loadedGroupMatches('ingestion', dcId)
    ? worstDotColor(selectedConnectionRows(dcId))
    : summaryDotColor(
        taskCountForConnectionSummary(dcId),
        issueCountForConnectionSummary(dcId)
      )

const dotColorForSite = (monitoringSiteId: string) =>
  loadedGroupMatches(activeTab.value, monitoringSiteId)
    ? worstDotColor(selectedSiteRows(monitoringSiteId))
    : summaryDotColor(
        taskCountForSiteSummary(monitoringSiteId),
        issueCountForSiteSummary(monitoringSiteId)
      )

const selectedConnection = computed<DataConnection | null>(() =>
  selectedConnectionId.value
    ? (connectionsById.value.get(selectedConnectionId.value) ?? null)
    : null
)

const selectedSite = computed(() =>
  selectedMonitoringSiteId.value
    ? (monitoringSitesById.value.get(selectedMonitoringSiteId.value) ?? null)
    : null
)

const visibleTasks = computed<TaskRow[]>(() => {
  if (activeTab.value === 'ingestion') {
    if (!selectedConnectionId.value) return []
    return etlTaskRows.value.filter(
      (t) => t.dataConnectionId === selectedConnectionId.value
    )
  }
  if (!selectedMonitoringSiteId.value) return []
  return activeTaskRows.value.filter(
    (t) => t.monitoringSiteId === selectedMonitoringSiteId.value
  )
})

const TASK_QUALIFIER_PATTERN = /(status|name|type):(?:"([^"]*)"|(\S+))/gi

function parseTaskQuery(raw: string) {
  const statuses: string[] = []
  const names: string[] = []
  const types: string[] = []
  const textParts: string[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  TASK_QUALIFIER_PATTERN.lastIndex = 0
  while ((match = TASK_QUALIFIER_PATTERN.exec(raw))) {
    textParts.push(raw.slice(lastIndex, match.index))
    const key = match[1].toLowerCase()
    const value = (match[2] ?? match[3] ?? '').trim()
    if (value) {
      if (key === 'status') statuses.push(value)
      else if (key === 'type') types.push(value)
      else names.push(value)
    }
    lastIndex = TASK_QUALIFIER_PATTERN.lastIndex
  }
  textParts.push(raw.slice(lastIndex))

  return {
    statuses,
    names,
    types,
    text: textParts.join(' ').replace(/\s+/g, ' ').trim(),
  }
}

const searchedVisibleTasks = computed<TaskRow[]>(() => {
  const parsedQuery = parseTaskQuery(orchestrationSearch.value)
  const term = parsedQuery.text.toLowerCase()
  const filters = new Set(orchestrationStatusFilter.value)
  const taskTypeFilters = new Set(orchestrationTaskTypeFilter.value)
  const queryStatuses = new Set(
    parsedQuery.statuses.map((value) => value.toLowerCase())
  )
  const queryTaskTypes = new Set(
    parsedQuery.types.map((value) => value.toLowerCase())
  )
  return visibleTasks.value.filter((t) => {
    if (filters.size > 0) {
      const bucket = t.statusSort ?? 'Unknown'
      if (!filters.has(bucket)) return false
    }
    if (
      queryStatuses.size > 0 &&
      !queryStatuses.has((t.statusSort ?? 'Unknown').toLowerCase())
    ) {
      return false
    }
    if (activeTab.value === 'aggregation' && taskTypeFilters.size > 0) {
      if (!t.taskType || !taskTypeFilters.has(t.taskType)) return false
    }
    if (
      activeTab.value === 'aggregation' &&
      queryTaskTypes.size > 0 &&
      (!t.taskType || !queryTaskTypes.has(t.taskType.toLowerCase()))
    ) {
      return false
    }
    if (parsedQuery.names.length > 0) {
      const taskName = (t.name ?? '').toLowerCase()
      if (
        !parsedQuery.names.some((name) => taskName.includes(name.toLowerCase()))
      ) {
        return false
      }
    }
    if (!term) return true
    const haystack = [
      t.name,
      t.statusName,
      t.statusSort,
      t.lastRun,
      t.nextRun,
      t.taskType,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return haystack.includes(term)
  })
})

const sortedVisibleTasks = computed<TaskRow[]>(() => searchedVisibleTasks.value)

const hasSelection = computed(() =>
  activeTab.value === 'ingestion'
    ? !!selectedConnectionId.value
    : !!selectedMonitoringSiteId.value
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
  return selectedSite.value?.type ?? ''
})

const emptyHeading = computed(() =>
  activeTab.value === 'ingestion'
    ? dataConnections.value.length === 0
      ? 'No data connections have been registered yet.'
      : 'Select a data connection'
    : monitoringSites.value.length === 0
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
  if (monitoringSites.value.length === 0) {
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

const selectSidebarFromTaskDetails = () => {
  const task = selectedTask.value as any
  if (!hasTaskDetails.value || !task) return false
  if (selectedTaskKind.value === 'etl') {
    selectedConnectionId.value =
      task.dataConnection?.id ?? task.dataConnectionId ?? null
    return !!selectedConnectionId.value
  }
  selectedMonitoringSiteId.value =
    task.monitoringSite?.id ?? task.monitoringSiteId ?? null
  return !!selectedMonitoringSiteId.value
}

const selectSidebarFromRouteGroup = () => {
  if (activeTab.value === 'ingestion') {
    const id = routeDataConnectionId.value
    if (!id || !connectionsById.value.has(id)) return false
    selectedConnectionId.value = id
    return true
  }

  const id = routeSiteId.value
  if (!id || !monitoringSitesById.value.has(id)) return false
  selectedMonitoringSiteId.value = id
  return true
}

const autoSelectSidebar = () => {
  if (activeTab.value === 'ingestion') {
    const current = selectedConnectionId.value
    if (current && connectionsById.value.has(current)) return
    selectedConnectionId.value = dataConnections.value[0]?.id ?? null
  } else {
    const current = selectedMonitoringSiteId.value
    if (current && monitoringSitesById.value.has(current)) return
    selectedMonitoringSiteId.value = monitoringSites.value[0]?.id ?? null
  }
}

const selectedGroupIdForTab = (tab: TabId) =>
  tab === 'ingestion'
    ? selectedConnectionId.value
    : selectedMonitoringSiteId.value

const fetchVisibleTasks = async (force = false) => {
  if (!selectedWorkspaceId.value || hasTaskDetails.value) {
    return
  }

  await fetchTasksForGroup(
    activeTab.value,
    selectedGroupIdForTab(activeTab.value),
    selectedWorkspaceId.value,
    force
  )
}

const syncSelectedGroupToRoute = async (overrideWorkspaceId?: string) => {
  if (hasTaskDetails.value) return
  await replaceSelectedGroup(
    activeTab.value,
    selectedGroupIdForTab(activeTab.value),
    overrideWorkspaceId
  )
}

const autoSelectSidebarAndSync = async () => {
  autoSelectSidebar()
  await fetchVisibleTasks()
  await syncSelectedGroupToRoute()
}

const closeTaskDetailsAndSync = async () => {
  await closeTaskDetails()
  await fetchVisibleTasks()
  await syncSelectedGroupToRoute()
}

const setActiveTab = async (tab: TabId) => {
  sidebarSearch.value = ''
  await replaceView(tab, selectedGroupIdForTab(tab))
  autoSelectSidebar()
  await fetchVisibleTasks()
  await syncSelectedGroupToRoute()
}

const openWorkspaceManager = async () => {
  await router.push({ name: 'Workspaces' })
}

const selectConnection = async (id: string) => {
  selectedConnectionId.value = id
  await fetchVisibleTasks()
  await replaceView('ingestion', id)
}

const selectSite = async (id: string) => {
  selectedMonitoringSiteId.value = id
  await fetchVisibleTasks()
  await replaceView(activeTab.value, id)
}

const closeWorkspaceScopedUi = () => {
  openCreateDataConnection.value = false
  openCreateTask.value = false
  openEditDataConnection.value = false
  openDeleteDataConnection.value = false
  openAggregationForm.value = false
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
  orchestrationTaskTypeFilter.value = []
  draftDatastreams.value = []
}

watch(
  selectedWorkspaceId,
  async (newId, oldId) => {
    if (newId == null || routeWorkspaceDenied.value) return
    const workspaceChanged = oldId != null && oldId !== newId
    const routeSelectedThisWorkspace = routeWorkspaceId.value === newId
    // The URL workspace wins; only push the new selection into the URL when
    // the URL has none or the selected workspace actually changed.
    const overrideWorkspaceId =
      !routeWorkspaceId.value || workspaceChanged ? newId : undefined
    stopAll()
    closeWorkspaceScopedUi()
    selectedConnectionId.value = null
    selectedMonitoringSiteId.value = null
    if (workspaceChanged && !routeSelectedThisWorkspace)
      await closeTaskDetails()
    await fetchAll(newId)
    if (!selectSidebarFromTaskDetails() && !selectSidebarFromRouteGroup()) {
      autoSelectSidebar()
    }
    await fetchVisibleTasks(true)
    await syncSelectedGroupToRoute(overrideWorkspaceId)
  },
  { immediate: true }
)

watch([routeDataConnectionId, routeSiteId, routeView], async () => {
  if (loading.value || hasTaskDetails.value) {
    return
  }

  if (selectSidebarFromRouteGroup()) {
    await fetchVisibleTasks()
    return
  }

  const hasRouteSelection =
    activeTab.value === 'ingestion'
      ? !!routeDataConnectionId.value
      : !!routeSiteId.value
  if (!hasRouteSelection) return

  await autoSelectSidebarAndSync()
})

const openCreateDialog = () => {
  if (!canCreateDataConnections.value) return
  openCreateDataConnection.value = true
}

const openCreateTaskDialog = (dc: DataConnection) => {
  if (!canCreateActiveTasks.value) return
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
  if (!canEditDataConnections.value) return
  selectedDataConnection.value = dc
  openEditDataConnection.value = true
}

const openDeleteDialog = (dc: DataConnection) => {
  if (!canDeleteDataConnections.value) return
  selectedDataConnection.value = dc
  openDeleteDataConnection.value = true
}

const openDataProductForm = (form: 'aggregation' | 'derivation') => {
  if (!canCreateActiveTasks.value) return
  if (form === 'aggregation') openAggregationForm.value = true
  if (form === 'derivation') openDerivationForm.value = true
}

const openRatingCurveTaskForm = () => {
  if (!canCreateRatingCurves.value) return
  openRatingCurveForm.value = true
}

const openQualityTaskForm = () => {
  if (!canCreateActiveTasks.value) return
  openQualityForm.value = true
}

const onDataConnectionCreated = async () => {
  openCreateDataConnection.value = false
  await refreshDataConnections()
}

const onTaskCreated = async (_createdTask?: Task) => {
  closeCreateTaskDialog()
  await fetchAll()
  await autoSelectSidebarAndSync()
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
  closeDerivationForm()
  openRatingCurveForm.value = false
  await fetchAll()
  await autoSelectSidebarAndSync()
}

const onQualityTaskCreated = async (createdTask?: MonitoringTask) => {
  closeQualityForm()
  await fetchAll()
  await autoSelectSidebarAndSync()
}

const onQualityTaskChanged = async () => {
  closeQualityForm()
  await fetchAll()
  await autoSelectSidebarAndSync()
}

const onTaskDetailsChanged = async () => {
  resetDraftDatastreams()
  await fetchAll()
  await autoSelectSidebarAndSync()
}

const onTaskDeleted = async () => {
  resetDraftDatastreams()
  await fetchAll()
  await autoSelectSidebarAndSync()
}

const onDataConnectionUpdated = (updated: DataConnection) => {
  openEditDataConnection.value = false
  const idx = dataConnections.value.findIndex((dc) => dc.id === updated.id)
  if (idx !== -1) dataConnections.value[idx] = updated
}

const onDataConnectionDeleted = async () => {
  if (!selectedDataConnection.value || !canDeleteDataConnections.value) return
  const id = selectedDataConnection.value.id
  try {
    await hs.dataConnections.delete(id)
    resetDraftDatastreams()
    await fetchAll()
    if (selectedConnectionId.value === id) {
      selectedConnectionId.value = dataConnections.value[0]?.id ?? null
    }
    await autoSelectSidebarAndSync()
    openDeleteDataConnection.value = false
  } catch (error) {
    console.error('Error deleting data connection', error)
  }
}

const onRunNow = async (row: TaskRow) => {
  if (!canEditActiveTasks.value) return
  await runTaskNow(row.kind, row.id)
}

const onTogglePaused = async (row: TaskRow) => {
  if (!canEditActiveTasks.value) return
  if (!row.schedule) return
  await toggleSchedulePaused(row.kind, row.id, row.schedule)
}

const goToTask = async (row: TaskRow) => {
  await pushTaskDetails(row)
}
</script>

<style scoped>
.orchestration-page {
  background-color: var(--hs-background);
  display: flex;
  flex-direction: column;
  height: calc(100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px));
  min-height: 0;
  overflow: hidden;
}

.orchestration-page-body {
  flex: 1;
  display: flex;
  min-height: 0;
  overflow: hidden;
}

.detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--hs-background);
  min-width: 0;
}

.detail--task {
  padding: 0;
}

@media (max-width: 700px) {
  .orchestration-page {
    height: auto;
    min-height: calc(
      100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px)
    );
    overflow: visible;
  }

  .orchestration-page-body,
  .detail {
    width: 100%;
    max-width: 100%;
    min-width: 0;
    overflow: visible;
  }
}
</style>
