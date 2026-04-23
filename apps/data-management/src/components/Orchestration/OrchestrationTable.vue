<template>
  <div class="orchestration-shell">
    <!-- Left nav rail -->
    <nav class="nav-rail">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="rail-btn"
        :class="{ active: activeTab === tab.id }"
        :style="activeTab === tab.id ? { '--accent': tab.accent, '--accent-light': tab.accentLight } : {}"
        @click="setActiveTab(tab.id)"
      >
        <span
          class="rail-pill"
          :style="activeTab === tab.id ? { background: tab.accentLight } : {}"
        >
          <v-icon
            :icon="tab.icon"
            size="22"
            :color="activeTab === tab.id ? tab.accent : undefined"
          />
          <span v-if="tab.issues > 0" class="rail-badge">{{ tab.issues }}</span>
        </span>
        <span
          class="rail-label"
          :style="activeTab === tab.id ? { color: tab.accent, fontWeight: 600 } : {}"
        >
          {{ tab.short }}
        </span>
      </button>
    </nav>

    <!-- Contextual sidebar: Connections (Ingestion) or Sites (Aggregation / Quality) -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="flex items-center">
          <span class="sidebar-title">{{ sidebarTitle }}</span>
          <v-tooltip v-if="activeTab === 'ingestion'" location="top" :disabled="canEditOrchestration">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="ml-auto inline-flex">
                <button
                  type="button"
                  class="sidebar-add"
                  :style="{ background: activeAccent, opacity: canEditOrchestration ? 1 : 0.5 }"
                  :disabled="!canEditOrchestration"
                  @click="openCreateDialog"
                  :aria-label="addLabel"
                >
                  <v-icon :icon="mdiPlus" size="16" color="white" />
                </button>
              </span>
            </template>
            <span>{{ readOnlyTooltip }}</span>
          </v-tooltip>
        </div>
        <div class="sidebar-search">
          <v-icon :icon="mdiMagnify" size="16" class="sidebar-search-icon" />
          <input
            v-model="sidebarSearch"
            :placeholder="`Search ${sidebarTitle.toLowerCase()}…`"
            class="sidebar-search-input"
          />
        </div>
      </div>

      <div class="sidebar-list">
        <template v-if="activeTab === 'ingestion'">
          <div
            v-for="dc in filteredConnections"
            :key="dc.id"
            class="sidebar-item"
            :class="{ selected: selectedConnectionId === dc.id }"
            :style="
              selectedConnectionId === dc.id
                ? { background: activeAccent, color: 'white' }
                : {}
            "
            @click="selectConnection(dc.id)"
          >
            <span
              class="sidebar-dot"
              :style="{
                background:
                  selectedConnectionId === dc.id
                    ? 'rgba(255,255,255,0.7)'
                    : dotColorForConnection(dc.id),
              }"
            />
            <div class="sidebar-item-body">
              <div class="sidebar-item-title">{{ dc.name }}</div>
              <div class="sidebar-item-meta">
                {{ taskCountForConnection(dc.id) }} task{{
                  taskCountForConnection(dc.id) === 1 ? '' : 's'
                }}
                <span v-if="dc.payload?.type">· {{ dc.payload.type }}</span>
              </div>
            </div>
          </div>
          <div v-if="filteredConnections.length === 0" class="sidebar-empty">
            No data connections yet.
          </div>
        </template>

        <template v-else>
          <div
            v-for="thing in filteredSites"
            :key="thing.id"
            class="sidebar-item"
            :class="{ selected: selectedThingId === thing.id }"
            :style="
              selectedThingId === thing.id
                ? { background: activeAccent, color: 'white' }
                : {}
            "
            @click="selectSite(thing.id)"
          >
            <span
              class="sidebar-dot"
              :style="{
                background:
                  selectedThingId === thing.id
                    ? 'rgba(255,255,255,0.7)'
                    : dotColorForSite(thing.id),
              }"
            />
            <div class="sidebar-item-body">
              <div class="sidebar-item-title">{{ thing.name }}</div>
              <div class="sidebar-item-meta">
                {{ taskCountForSite(thing.id) }} task{{
                  taskCountForSite(thing.id) === 1 ? '' : 's'
                }}
              </div>
            </div>
            <span
              v-if="
                selectedThingId !== thing.id &&
                issueCountForSite(thing.id) > 0
              "
              class="sidebar-item-badge"
            >
              {{ issueCountForSite(thing.id) }}
            </span>
          </div>
          <div v-if="filteredSites.length === 0" class="sidebar-empty">
            No sites yet.
          </div>
        </template>
      </div>

      <div v-if="activeTab === 'ingestion'" class="sidebar-footer">
        <v-tooltip location="top" :disabled="canEditOrchestration">
          <template #activator="{ props: tooltipProps }">
            <span v-bind="tooltipProps" class="inline-flex w-full">
              <button
                type="button"
                class="sidebar-footer-btn"
                :style="{ color: activeAccent, borderColor: activeAccent + '66' }"
                :disabled="!canEditOrchestration"
                @click="openCreateDialog"
              >
                <v-icon :icon="mdiPlus" size="16" class="mr-1" />
                {{ addLabel }}
              </button>
            </span>
          </template>
          <span>{{ readOnlyTooltip }}</span>
        </v-tooltip>
      </div>
    </aside>

    <!-- Detail pane -->
    <section class="detail">
      <header class="detail-header">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="detail-title">{{ detailTitle }}</h2>
            <span
              v-if="detailTypeBadge"
              class="detail-badge"
              :style="{ color: activeAccent, background: activeAccentLight }"
            >
              {{ detailTypeBadge }}
            </span>
          </div>
          <div class="detail-subtitle">
            <HealthPills :tasks="visibleTasks" />
          </div>
        </div>
        <div class="detail-actions">
          <template v-if="activeTab === 'ingestion' && selectedConnection">
            <v-tooltip location="top" :disabled="canEditOrchestration">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn
                    variant="text"
                    :prepend-icon="mdiPencil"
                    :disabled="!canEditOrchestration"
                    class="detail-action-btn text-none"
                    color="blue-grey-darken-2"
                    @click="openEditDialog(selectedConnection)"
                  >
                    Edit
                  </v-btn>
                </span>
              </template>
              <span>{{ readOnlyTooltip }}</span>
            </v-tooltip>
            <v-tooltip location="top" :disabled="canEditOrchestration">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn
                    variant="text"
                    :prepend-icon="mdiTrashCanOutline"
                    color="red-darken-2"
                    class="detail-action-btn text-none"
                    :disabled="!canEditOrchestration"
                    @click="openDeleteDialog(selectedConnection)"
                  >
                    Delete
                  </v-btn>
                </span>
              </template>
              <span>{{ readOnlyTooltip }}</span>
            </v-tooltip>
            <v-tooltip location="top" :disabled="canEditOrchestration">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn
                    variant="flat"
                    :prepend-icon="mdiPlus"
                    :style="{ background: activeAccent, color: 'white' }"
                    :disabled="!canEditOrchestration"
                    class="detail-action-btn detail-action-btn--primary text-none"
                    rounded="lg"
                    @click="openCreateTaskDialog(selectedConnection)"
                  >
                    Add task
                  </v-btn>
                </span>
              </template>
              <span>{{ readOnlyTooltip }}</span>
            </v-tooltip>
          </template>
        </div>
      </header>

      <div
        v-if="hasSelection && visibleTasks.length > 0"
        class="detail-filterbar"
      >
        <v-text-field
          v-model="taskSearch"
          :prepend-inner-icon="mdiMagnify"
          placeholder="Search tasks"
          hide-details
          clearable
          density="compact"
          variant="outlined"
          class="detail-search"
        />
        <v-autocomplete
          v-model="statusFilter"
          :items="STATUS_OPTIONS"
          item-title="title"
          item-value="value"
          label="Status filters"
          multiple
          clearable
          hide-details
          density="compact"
          variant="outlined"
          :prepend-inner-icon="mdiFilterVariant"
          autocomplete="off"
          name="orchestration-status-filter"
          spellcheck="false"
          class="detail-status-filter"
        >
          <template #selection="{ item, index }">
            <v-chip
              color="primary-lighten-2"
              rounded
              density="comfortable"
              closable
              class="mr-1"
              @click:close="statusFilter.splice(index, 1)"
            >
              <span>{{ item.title }}</span>
            </v-chip>
          </template>
        </v-autocomplete>
      </div>

      <div class="detail-body">
        <div v-if="loading" class="detail-loading">
          <v-progress-circular
            indeterminate
            size="22"
            width="2"
            color="blue-grey-darken-1"
          />
          <span>Loading…</span>
        </div>

        <div v-else-if="!hasSelection" class="detail-empty">
          <h4>{{ emptyHeading }}</h4>
          <p>{{ emptyMessage }}</p>
        </div>

        <div v-else-if="visibleTasks.length === 0" class="detail-empty">
          <h4>No tasks</h4>
          <p>{{ emptyTasksMessage }}</p>
        </div>

        <div
          v-else-if="sortedVisibleTasks.length === 0"
          class="detail-empty"
        >
          <h4>No tasks match your filter</h4>
          <p>Clear search or status filters to see all tasks.</p>
        </div>

        <table v-else class="tasks-table">
          <thead>
            <tr>
              <th>
                <button type="button" class="th-sort" @click="toggleSort('name')">
                  Task name
                  <v-icon :icon="sortIcon('name')" size="14" />
                </button>
              </th>
              <th>
                <button type="button" class="th-sort" @click="toggleSort('status')">
                  Status
                  <v-icon :icon="sortIcon('status')" size="14" />
                </button>
              </th>
              <th>
                <button type="button" class="th-sort" @click="toggleSort('lastRunAt')">
                  Last run
                  <v-icon :icon="sortIcon('lastRunAt')" size="14" />
                </button>
              </th>
              <th>
                <button type="button" class="th-sort" @click="toggleSort('nextRunAt')">
                  Next run
                  <v-icon :icon="sortIcon('nextRunAt')" size="14" />
                </button>
              </th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedVisibleTasks" :key="row.id">
              <td class="task-name">{{ row.name || '—' }}</td>
              <td>
                <v-tooltip
                  location="bottom"
                  :open-delay="0"
                  :close-delay="80"
                  content-class="pa-0 ma-0 bg-transparent"
                  max-width="520"
                >
                  <template #activator="{ props: tooltipProps }">
                    <span v-bind="tooltipProps" class="inline-flex">
                      <TaskStatus
                        :status="row.statusName"
                        :paused="row.schedule ? !row.schedule.enabled : false"
                      />
                    </span>
                  </template>
                  <v-card
                    elevation="6"
                    rounded="lg"
                    class="ma-0 pa-0 border border-slate-200"
                    style="max-width: 520px"
                  >
                    <v-card-text class="px-4 py-3">
                      <div class="mb-1 flex items-center justify-between gap-3">
                        <div class="text-[0.7rem] font-extrabold uppercase tracking-[0.12em] text-slate-600">
                          Last run summary
                        </div>
                        <div
                          v-if="row.lastRun && row.lastRun !== '-'"
                          class="text-xs font-medium text-slate-500"
                        >
                          {{ row.lastRun }}
                        </div>
                      </div>
                      <div class="text-sm leading-snug text-slate-800">
                        {{
                          row.lastRunMessage ||
                          'No run history available yet.'
                        }}
                      </div>
                    </v-card-text>
                  </v-card>
                </v-tooltip>
              </td>
              <td class="task-time">{{ row.lastRun }}</td>
              <td class="task-time">{{ row.nextRun }}</td>
              <td class="task-actions">
                <div class="task-actions-inner">
                  <v-tooltip location="top" :open-delay="0" :close-delay="0">
                    <template #activator="{ props: tooltipProps }">
                      <span v-bind="tooltipProps" class="inline-flex">
                        <v-btn
                          variant="text"
                          size="small"
                          color="black"
                          :icon="row.schedule?.enabled ? mdiPause : mdiPlay"
                          :disabled="!canEditOrchestration"
                          class="task-pause-btn"
                          @click.stop="togglePaused(row)"
                          aria-label="Pause or resume task"
                        />
                      </span>
                    </template>
                    <span>{{
                      !canEditOrchestration
                        ? readOnlyTooltip
                        : row.schedule?.enabled
                          ? 'Pause task'
                          : 'Resume task'
                    }}</span>
                  </v-tooltip>
                  <v-btn
                    v-if="canEditOrchestration && !row.userClickedRunNow"
                    variant="outlined"
                    color="green-darken-3"
                    :prepend-icon="mdiPlay"
                    class="detail-action-btn detail-action-btn--compact text-none"
                    rounded="lg"
                    @click.stop="runTaskNow(row)"
                  >
                    Run now
                  </v-btn>
                  <span
                    v-else-if="canEditOrchestration && row.userClickedRunNow"
                    class="text-xs font-semibold text-slate-500"
                  >
                    Run requested
                  </span>
                  <v-btn
                    variant="text"
                    size="small"
                    :style="{ color: activeAccent }"
                    :append-icon="mdiChevronRight"
                    class="text-none"
                    @click.stop="goToTask(row)"
                  >
                    Details
                  </v-btn>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <v-dialog v-model="openCreateDataConnection" width="60rem">
      <DataConnectionForm
        @close="openCreateDataConnection = false"
        @created="onDataConnectionCreated"
      />
    </v-dialog>

    <v-dialog v-if="selectedTaskDataConnection" v-model="openCreateTask" width="80rem">
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
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  onBeforeUnmount,
  reactive,
  ref,
  watch,
} from 'vue'
import TaskStatus from '@/components/Orchestration/TaskStatus.vue'
import HealthPills from '@/components/Orchestration/HealthPills.vue'
import router from '@/router/router'
import {
  getDisplayedTaskStatus,
  getTaskRunMessage,
  getTaskStatusText,
} from '@/utils/orchestration/taskRunDetails'
import { formatTime } from '@/utils/time'
import hs, {
  DataConnection,
  DataProductTaskExpanded,
  MonitoringTaskExpanded,
  PermissionAction,
  PermissionResource,
  TaskExpanded,
  TaskRun,
  TaskSchedule,
  Thing,
} from '@hydroserver/client'
import {
  mdiArrowDown,
  mdiArrowUp,
  mdiArrowUpDown,
  mdiChevronRight,
  mdiClose,
  mdiDatabaseArrowDownOutline,
  mdiFileTree,
  mdiFilterVariant,
  mdiMagnify,
  mdiPause,
  mdiPencil,
  mdiPlay,
  mdiPlus,
  mdiShieldCheckOutline,
  mdiTrashCanOutline,
} from '@mdi/js'
import { storeToRefs } from 'pinia'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'

const DataConnectionForm = defineAsyncComponent(
  () => import('@/components/Orchestration/DataConnectionForm.vue')
)
const TaskForm = defineAsyncComponent(
  () => import('@/components/Orchestration/TaskForm.vue')
)
const DeleteDataConnectionCard = defineAsyncComponent(
  () => import('@/components/Orchestration/DeleteDataConnectionCard.vue')
)

const props = defineProps<{
  workspaceId: string
}>()

const INGESTION_ACCENT = '#1565C0'
const INGESTION_ACCENT_LIGHT = '#E3F2FD'
const AGGREGATION_ACCENT = '#6A1B9A'
const AGGREGATION_ACCENT_LIGHT = '#F3E5F5'
const QUALITY_ACCENT = '#00695C'
const QUALITY_ACCENT_LIGHT = '#E0F2F1'

type TabId = 'ingestion' | 'aggregation' | 'quality'
type TaskKind = 'etl' | 'dataProduct' | 'monitoring'

const TAB_TO_KIND: Record<TabId, TaskKind> = {
  ingestion: 'etl',
  aggregation: 'dataProduct',
  quality: 'monitoring',
}

const { workspaceTasks, orchestrationSearch, orchestrationStatusFilter } =
  storeToRefs(useOrchestrationStore())
const { workspaces } = storeToRefs(useWorkspaceStore())
const { hasPermission, isAdmin, isOwner } = useWorkspacePermissions()

const loading = ref(false)
const runNowTriggeredByTaskId = reactive<Record<string, boolean>>({})

const dataConnections = ref<DataConnection[]>([])
const things = ref<Thing[]>([])
const datastreamThingByDatastreamId = ref<Record<string, string>>({})
const dataProductTasks = ref<DataProductTaskExpanded[]>([])
const monitoringTasks = ref<MonitoringTaskExpanded[]>([])
const selectedDataConnection = ref<DataConnection | null>(null)
const selectedTaskDataConnection = ref<DataConnection | null>(null)
const openCreateDataConnection = ref(false)
const openCreateTask = ref(false)
const openEditDataConnection = ref(false)
const openDeleteDataConnection = ref(false)

const activeTab = ref<TabId>('ingestion')
const sidebarSearch = ref('')
const taskSearch = ref('')
const statusFilter = ref<string[]>([])
const selectedConnectionId = ref<string | null>(null)
const selectedThingId = ref<string | null>(null)

const STATUS_OPTIONS = [
  { title: 'OK', value: 'OK' },
  { title: 'Needs attention', value: 'Needs attention' },
  { title: 'Behind schedule', value: 'Behind schedule' },
  { title: 'Loading paused', value: 'Loading paused' },
  { title: 'Pending', value: 'Pending' },
  { title: 'Unknown', value: 'Unknown' },
] as const

const serviceForKind = (kind: TaskKind) => {
  if (kind === 'etl') return hs.tasks
  if (kind === 'dataProduct') return hs.dataProductTasks
  return hs.monitoringTasks
}

let orchestrationFetchRequestId = 0
const taskPollTimeouts = new Map<string, number>()
const POLL_INTERVAL_MS = 4000
const POLL_MAX_ATTEMPTS = 150

const workspaceForPage = computed(() =>
  workspaces.value.find((workspace) => workspace.id === props.workspaceId)
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
const readOnlyTooltip =
  'You have read-only access to this workspace. Ask an editor or owner to make changes.'

type SortKey = 'name' | 'status' | 'lastRunAt' | 'nextRunAt'
type SortDir = 'asc' | 'desc'
const sortKey = ref<SortKey>('name')
const sortDir = ref<SortDir>('asc')

const toggleSort = (key: SortKey) => {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

const sortIcon = (key: SortKey) => {
  if (sortKey.value !== key) return mdiArrowUpDown
  return sortDir.value === 'asc' ? mdiArrowUp : mdiArrowDown
}

type TaskRow = {
  id: string
  kind: TaskKind
  name: string
  schedule: TaskSchedule | null
  latestRun: TaskRun | null | undefined
  statusName: ReturnType<typeof getTaskStatusText>
  statusSort: ReturnType<typeof getDisplayedTaskStatus>
  lastRun: string
  nextRun: string
  lastRunAt: string | null
  nextRunAt: string | null
  lastRunMessage: string
  dataConnectionId: string | null
  thingId: string | null
  userClickedRunNow: boolean
  raw: TaskExpanded | DataProductTaskExpanded | MonitoringTaskExpanded
}

const toRowBase = (
  t: TaskExpanded | DataProductTaskExpanded | MonitoringTaskExpanded,
  kind: TaskKind
) => {
  const schedule = t.schedule ?? null
  const latestRun = (t as any).latestRun as TaskRun | null | undefined
  return {
    id: t.id,
    kind,
    name: t.name,
    schedule,
    latestRun,
    statusName: getTaskStatusText(t as any),
    statusSort: getDisplayedTaskStatus(t as any),
    lastRun: latestRun?.startedAt ? formatTime(latestRun.startedAt) : '-',
    nextRun: schedule?.nextRunAt ? formatTime(schedule.nextRunAt) : '-',
    lastRunAt: latestRun?.startedAt ?? null,
    nextRunAt: schedule?.nextRunAt ?? null,
    lastRunMessage: getTaskRunMessage(latestRun as any),
    userClickedRunNow: !!runNowTriggeredByTaskId[t.id],
    raw: t,
  }
}

const etlTaskRows = computed<TaskRow[]>(() =>
  workspaceTasks.value.map((t) => ({
    ...toRowBase(t, 'etl'),
    dataConnectionId: (t as any).dataConnection?.id ?? null,
    thingId: resolveEtlTaskThingId(t),
  }))
)

const dataProductTaskRows = computed<TaskRow[]>(() =>
  dataProductTasks.value.map((t) => ({
    ...toRowBase(t, 'dataProduct'),
    dataConnectionId: null,
    thingId: t.thing?.id ?? null,
  }))
)

const monitoringTaskRows = computed<TaskRow[]>(() =>
  monitoringTasks.value.map((t) => ({
    ...toRowBase(t, 'monitoring'),
    dataConnectionId: null,
    thingId: t.thing?.id ?? null,
  }))
)

const activeTaskRows = computed<TaskRow[]>(() => {
  if (activeTab.value === 'ingestion') return etlTaskRows.value
  if (activeTab.value === 'aggregation') return dataProductTaskRows.value
  return monitoringTaskRows.value
})

// ETL tasks don't carry their site on the task itself; infer it from the first mapping's
// target datastream, cross-referencing the workspace datastream list for thingId.
function resolveEtlTaskThingId(task: TaskExpanded): string | null {
  for (const mapping of task.mappings ?? []) {
    const ds = mapping.targetDatastream as any
    const dsThingId = ds?.thingId ?? ds?.thing_id
    if (dsThingId) return dsThingId
    const fromMap = datastreamThingByDatastreamId.value[ds?.id]
    if (fromMap) return fromMap
  }
  return null
}

const connectionsById = computed(() => {
  const map = new Map<string, DataConnection>()
  for (const dc of dataConnections.value) map.set(dc.id, dc)
  return map
})

const thingsById = computed(() => {
  const map = new Map<string, Thing>()
  for (const th of things.value) map.set(th.id, th)
  return map
})

const countIssues = (rows: TaskRow[]) =>
  rows.filter((r) => {
    const s = r.statusSort
    return s === 'Needs attention' || s === 'Behind schedule'
  }).length

const tabs = computed(() => [
  {
    id: 'ingestion' as TabId,
    short: 'Ingestion',
    icon: mdiDatabaseArrowDownOutline,
    accent: INGESTION_ACCENT,
    accentLight: INGESTION_ACCENT_LIGHT,
    issues: countIssues(etlTaskRows.value),
  },
  {
    id: 'aggregation' as TabId,
    short: 'Aggregations',
    icon: mdiFileTree,
    accent: AGGREGATION_ACCENT,
    accentLight: AGGREGATION_ACCENT_LIGHT,
    issues: countIssues(dataProductTaskRows.value),
  },
  {
    id: 'quality' as TabId,
    short: 'Quality',
    icon: mdiShieldCheckOutline,
    accent: QUALITY_ACCENT,
    accentLight: QUALITY_ACCENT_LIGHT,
    issues: countIssues(monitoringTaskRows.value),
  },
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

const filteredConnections = computed(() => {
  const term = sidebarSearch.value.trim().toLowerCase()
  if (!term) return dataConnections.value
  return dataConnections.value.filter((dc) =>
    dc.name.toLowerCase().includes(term)
  )
})

const filteredSites = computed(() => {
  const term = sidebarSearch.value.trim().toLowerCase()
  if (!term) return things.value
  return things.value.filter((th) => th.name.toLowerCase().includes(term))
})

const taskCountForConnection = (dcId: string) =>
  etlTaskRows.value.filter((t) => t.dataConnectionId === dcId).length

const taskCountForSite = (thingId: string) =>
  activeTaskRows.value.filter((t) => t.thingId === thingId).length

const issueCountForSite = (thingId: string) =>
  activeTaskRows.value.filter(
    (t) =>
      t.thingId === thingId &&
      (t.statusSort === 'Needs attention' ||
        t.statusSort === 'Behind schedule')
  ).length

const dotColorForConnection = (dcId: string) => {
  const rows = etlTaskRows.value.filter((t) => t.dataConnectionId === dcId)
  return worstDotColor(rows)
}

const dotColorForSite = (thingId: string) => {
  const rows = activeTaskRows.value.filter((t) => t.thingId === thingId)
  return worstDotColor(rows)
}

function worstDotColor(rows: TaskRow[]) {
  if (rows.length === 0) return '#CAC4D0'
  const order = ['Needs attention', 'Behind schedule', 'Loading paused', 'Pending', 'OK']
  const palette: Record<string, string> = {
    'Needs attention': '#B71C1C',
    'Behind schedule': '#BF360C',
    'Loading paused': '#546E7A',
    Pending: '#1565C0',
    OK: '#2E7D32',
  }
  for (const s of order) {
    if (rows.some((r) => r.statusSort === s)) return palette[s] ?? '#2E7D32'
  }
  return '#2E7D32'
}

const selectedConnection = computed<DataConnection | null>(() =>
  selectedConnectionId.value
    ? connectionsById.value.get(selectedConnectionId.value) ?? null
    : null
)

const selectedSite = computed<Thing | null>(() =>
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

const compareText = (a: unknown, b: unknown) =>
  `${a ?? ''}`.localeCompare(`${b ?? ''}`, undefined, {
    numeric: true,
    sensitivity: 'base',
  })

const compareNullableDate = (a: unknown, b: unknown) => {
  const aVal = a ? new Date(a as any).getTime() : null
  const bVal = b ? new Date(b as any).getTime() : null
  if (aVal == null && bVal == null) return 0
  if (aVal == null) return 1
  if (bVal == null) return -1
  return aVal - bVal
}

const sortedVisibleTasks = computed<TaskRow[]>(() => {
  const rows = [...searchedVisibleTasks.value]
  const dir = sortDir.value === 'asc' ? 1 : -1
  rows.sort((a, b) => {
    let cmp = 0
    if (sortKey.value === 'name') cmp = compareText(a.name, b.name)
    else if (sortKey.value === 'status')
      cmp = compareText(a.statusSort, b.statusSort)
    else if (sortKey.value === 'lastRunAt')
      cmp = compareNullableDate(a.lastRunAt, b.lastRunAt)
    else if (sortKey.value === 'nextRunAt')
      cmp = compareNullableDate(a.nextRunAt, b.nextRunAt)
    return cmp * dir
  })
  return rows
})

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

const emptyTasksMessage = computed(() => {
  if (activeTab.value === 'ingestion') {
    return 'No tasks registered for this data connection.'
  }
  return 'No tasks are writing data to this site yet.'
})

const setActiveTab = (tab: TabId) => {
  activeTab.value = tab
  sidebarSearch.value = ''
  autoSelectSidebar()
}

const selectConnection = (id: string) => {
  selectedConnectionId.value = id
}

const selectSite = (id: string) => {
  selectedThingId.value = id
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

const fetchOrchestrationData = async (newId: string) => {
  const requestId = ++orchestrationFetchRequestId
  loading.value = true
  try {
    const [dcItems, etlItems, dpItems, monItems, thingItems, dsItems] =
      await Promise.all([
        hs.dataConnections.listAllItems({
          workspace_id: newId,
          order_by: 'name',
        } as any),
        hs.tasks.listAllItems({ workspace_id: newId } as any),
        hs.dataProductTasks.listAllItems({ workspace_id: [newId] } as any),
        hs.monitoringTasks.listAllItems({ workspace_id: [newId] } as any),
        hs.things.listAllItems({
          workspace_id: [newId],
          order_by: ['name'],
        } as any),
        hs.datastreams.listAllItems({ workspace_id: [newId] } as any),
      ])

    if (requestId !== orchestrationFetchRequestId) return

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

    autoSelectSidebar()
  } catch (error) {
    if (requestId !== orchestrationFetchRequestId) return
    console.error('Error fetching orchestration data', error)
  } finally {
    if (requestId === orchestrationFetchRequestId) {
      loading.value = false
    }
  }
}

watch(
  () => props.workspaceId,
  async (newId) => {
    if (newId == null) return
    stopAllTaskPolling()
    selectedConnectionId.value = null
    selectedThingId.value = null
    await fetchOrchestrationData(newId)
  },
  { immediate: true }
)

// Persist task search and status filter across navigations via the store.
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
  const items = await hs.dataConnections.listAllItems({
    workspace_id: props.workspaceId,
    order_by: 'name',
  } as any)
  dataConnections.value = items
}

const onTaskCreated = async () => {
  closeCreateTaskDialog()
  await fetchOrchestrationData(props.workspaceId)
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

const upsertTask = (
  kind: TaskKind,
  t: TaskExpanded | DataProductTaskExpanded | MonitoringTaskExpanded | null
) => {
  if (!t) return
  const target =
    kind === 'etl'
      ? workspaceTasks
      : kind === 'dataProduct'
        ? dataProductTasks
        : monitoringTasks
  const next = [...target.value]
  const index = next.findIndex((p) => p.id === t.id)
  if (index !== -1) next[index] = t as any
  else next.push(t as any)
  target.value = next as any
}

const findTaskByKind = (
  kind: TaskKind,
  taskId: string
): TaskExpanded | DataProductTaskExpanded | MonitoringTaskExpanded | null => {
  const list =
    kind === 'etl'
      ? workspaceTasks.value
      : kind === 'dataProduct'
        ? dataProductTasks.value
        : monitoringTasks.value
  return (list as any[]).find((t) => t.id === taskId) ?? null
}

function stopAllTaskPolling() {
  taskPollTimeouts.forEach((timeoutId) => window.clearTimeout(timeoutId))
  taskPollTimeouts.clear()
  for (const taskId of Object.keys(runNowTriggeredByTaskId)) {
    delete runNowTriggeredByTaskId[taskId]
  }
}

const syncTaskLatestRun = (kind: TaskKind, taskId: string, run: TaskRun) => {
  const existingTask = findTaskByKind(kind, taskId)
  if (!existingTask) return
  upsertTask(kind, {
    ...(existingTask as any),
    latestRun: run,
  })
}

const refreshTaskAfterRunCompletion = async (kind: TaskKind, taskId: string) => {
  try {
    const svc = serviceForKind(kind)
    const updated = (await svc.getItem(taskId, { expand_related: true })) as any
    if (updated) upsertTask(kind, updated)
  } catch (error) {
    console.error('Error refreshing task after run completion', error)
  }
}

const stopTaskPolling = (taskId: string) => {
  const timeoutId = taskPollTimeouts.get(taskId)
  if (timeoutId) window.clearTimeout(timeoutId)
  taskPollTimeouts.delete(taskId)
}

const scheduleTaskPoll = (
  kind: TaskKind,
  taskId: string,
  requestedRunId: string | null,
  previousRunId: string | null,
  attempt = 0,
  workspaceId = props.workspaceId
) => {
  stopTaskPolling(taskId)
  if (attempt > POLL_MAX_ATTEMPTS) {
    runNowTriggeredByTaskId[taskId] = false
    return
  }

  const svc = serviceForKind(kind)

  const timeoutId = window.setTimeout(async () => {
    if (workspaceId !== props.workspaceId) {
      runNowTriggeredByTaskId[taskId] = false
      stopTaskPolling(taskId)
      return
    }

    try {
      if (requestedRunId) {
        const runResponse = await svc.getTaskRun(taskId, requestedRunId)
        const updatedRun = runResponse.ok
          ? ((runResponse.data as TaskRun) ?? null)
          : null

        if (workspaceId !== props.workspaceId) {
          runNowTriggeredByTaskId[taskId] = false
          stopTaskPolling(taskId)
          return
        }

        if (updatedRun?.id) {
          syncTaskLatestRun(kind, taskId, updatedRun)
          if (updatedRun.status && updatedRun.status !== 'RUNNING') {
            runNowTriggeredByTaskId[taskId] = false
            stopTaskPolling(taskId)
            await refreshTaskAfterRunCompletion(kind, taskId)
            return
          }
        }
      } else {
        const updated = (await svc.getItem(taskId, {
          expand_related: true,
        })) as any

        if (workspaceId !== props.workspaceId) {
          runNowTriggeredByTaskId[taskId] = false
          stopTaskPolling(taskId)
          return
        }

        if (updated) {
          upsertTask(kind, updated)
          const latestRunId = updated.latestRun?.id ?? null
          const status = updated.latestRun?.status
          const sawRequestedRun = previousRunId
            ? !!latestRunId && latestRunId !== previousRunId
            : !!latestRunId
          if (sawRequestedRun && status) {
            if (updated.latestRun)
              syncTaskLatestRun(kind, taskId, updated.latestRun)
            if (status !== 'RUNNING') {
              runNowTriggeredByTaskId[taskId] = false
              stopTaskPolling(taskId)
              await refreshTaskAfterRunCompletion(kind, taskId)
              return
            }
          }
        }
      }
    } catch (error) {
      console.error('Error polling task status', error)
    }
    scheduleTaskPoll(
      kind,
      taskId,
      requestedRunId,
      previousRunId,
      attempt + 1,
      workspaceId
    )
  }, POLL_INTERVAL_MS)

  taskPollTimeouts.set(taskId, timeoutId)
}

async function runTaskNow(row: TaskRow) {
  if (!canEditOrchestration.value) return
  const previousRunId =
    (findTaskByKind(row.kind, row.id) as any)?.latestRun?.id ?? null
  runNowTriggeredByTaskId[row.id] = true
  try {
    const svc = serviceForKind(row.kind)
    const response = await svc.runTask(row.id)
    if (!response.ok) {
      throw new Error(response.message || 'Unable to run task now.')
    }
    const requestedRun = response.ok
      ? ((response.data as TaskRun) ?? null)
      : null
    if (requestedRun?.id) syncTaskLatestRun(row.kind, row.id, requestedRun)
    scheduleTaskPoll(
      row.kind,
      row.id,
      requestedRun?.id ?? null,
      previousRunId,
      0,
      props.workspaceId
    )
  } catch (error) {
    runNowTriggeredByTaskId[row.id] = false
    console.error('Error running task now', error)
  }
}

async function togglePaused(row: TaskRow) {
  if (!canEditOrchestration.value) return
  if (!row.schedule) return
  const schedule = row.schedule
  const previousEnabled = !!schedule.enabled
  schedule.enabled = !previousEnabled
  try {
    const svc = serviceForKind(row.kind)
    await svc.update({
      id: row.id,
      schedule,
    } as any)
    const updated = (await svc.getItem(row.id)) as any
    if (updated) upsertTask(row.kind, updated)
  } catch (error) {
    schedule.enabled = previousEnabled
    console.error('Error toggling task paused state', error)
  }
}

const goToTask = async (item: any) => {
  const currentQuery = router.currentRoute.value.query ?? {}
  await router.push({
    name: 'Orchestration',
    query: {
      ...currentQuery,
      workspaceId: props.workspaceId,
      taskId: item.id,
      runId: undefined,
    },
  })
}

onBeforeUnmount(() => {
  stopAllTaskPolling()
})
</script>

<style scoped>
.orchestration-shell {
  display: flex;
  flex: 1;
  min-height: 0;
  background: #ffffff;
  overflow: hidden;
}

.nav-rail {
  width: 88px;
  border-right: 1px solid #e8e8e8;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  gap: 2px;
  flex-shrink: 0;
}
.rail-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 4px;
  width: 100%;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
}
.rail-btn:hover .rail-pill {
  background: rgba(0, 0, 0, 0.05);
}
.rail-pill {
  width: 58px;
  height: 32px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: background 0.15s;
}
.rail-badge {
  position: absolute;
  top: 1px;
  right: 4px;
  background: #b71c1c;
  color: white;
  border-radius: 8px;
  min-width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  padding: 0 3px;
  line-height: 1;
}
.rail-label {
  font-size: 10.5px;
  color: #49454f;
  line-height: 1.2;
  text-align: center;
}

.sidebar {
  width: 260px;
  border-right: 1px solid #e8e8e8;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  min-height: 0;
}
.sidebar-header {
  padding: 11px 14px 10px;
  border-bottom: 1px solid #ebebeb;
}
.sidebar-title {
  font-size: 11px;
  font-weight: 700;
  color: #49454f;
  text-transform: uppercase;
  letter-spacing: 0.7px;
}
.sidebar-add {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.sidebar-search {
  position: relative;
  margin-top: 8px;
}
.sidebar-search-icon {
  position: absolute;
  left: 8px;
  top: 50%;
  transform: translateY(-50%);
  color: #cac4d0;
  pointer-events: none;
}
.sidebar-search-input {
  width: 100%;
  border: 1px solid #cac4d0;
  border-radius: 20px;
  height: 30px;
  padding-left: 30px;
  padding-right: 10px;
  font-size: 12px;
  outline: none;
  background: white;
}
.sidebar-list {
  flex: 1;
  overflow-y: auto;
}
.sidebar-item {
  padding: 10px 14px;
  cursor: pointer;
  border-bottom: 1px solid #ebebeb;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  transition: background 0.1s;
}
.sidebar-item:not(.selected):hover {
  background: rgba(0, 0, 0, 0.035);
}
.sidebar-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}
.sidebar-item-body {
  flex: 1;
  min-width: 0;
}
.sidebar-item-title {
  font-size: 13px;
  color: inherit;
}
.sidebar-item.selected .sidebar-item-title {
  font-weight: 600;
}
.sidebar-item-meta {
  font-size: 11px;
  color: #49454f;
  margin-top: 2px;
}
.sidebar-item.selected .sidebar-item-meta {
  color: rgba(255, 255, 255, 0.7);
}
.sidebar-item-badge {
  background: #ffebee;
  color: #b3261e;
  border-radius: 10px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 700;
}
.sidebar-empty {
  padding: 16px 14px;
  font-size: 12px;
  color: #9ca3af;
}
.sidebar-footer {
  padding: 10px 14px;
  border-top: 1px solid #ebebeb;
}
.sidebar-footer-btn {
  background: none;
  border: 1px dashed;
  border-radius: 8px;
  padding: 6px 0;
  width: 100%;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.sidebar-footer-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: white;
  min-width: 0;
}
.detail-header {
  padding: 12px 22px;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  gap: 12px;
  background: white;
  flex-shrink: 0;
}
.detail-title {
  font-size: 17px;
  font-weight: 400;
  color: #1c1b1f;
}
.detail-badge {
  font-size: 10px;
  border-radius: 4px;
  padding: 2px 7px;
  font-weight: 700;
}
.detail-subtitle {
  margin-top: 4px;
}
.detail-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}
.detail-action-btn {
  min-height: 40px;
}
.detail-action-btn--primary {
  padding-inline: 20px;
}
.detail-action-btn--compact {
  min-height: 32px;
  padding-inline: 12px;
}
.detail-filterbar {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 10px 22px;
  border-bottom: 1px solid #eef1f5;
  background: white;
}
.detail-search {
  max-width: 260px;
}
.detail-status-filter {
  max-width: 320px;
}

.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px;
}
.detail-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 0;
  color: #475569;
  font-size: 13px;
}
.detail-empty {
  padding: 40px 20px;
  text-align: center;
  color: #475569;
}
.detail-empty h4 {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 6px;
}

.tasks-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.tasks-table thead tr {
  border-bottom: 2px solid #ebebeb;
}
.tasks-table th {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 10.5px;
  color: #49454f;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.tasks-table th.text-right {
  text-align: right;
}
.tasks-table tbody tr {
  border-bottom: 1px solid #f0f0f0;
}
.tasks-table tbody tr:hover {
  background: #f5f7fa;
}
.th-sort {
  background: none;
  border: none;
  cursor: pointer;
  font: inherit;
  color: inherit;
  text-transform: inherit;
  letter-spacing: inherit;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 4px;
  border-radius: 4px;
}
.th-sort:hover {
  background: rgba(0, 0, 0, 0.05);
}
.task-name {
  padding: 13px 12px;
  font-weight: 500;
  color: #1c1b1f;
}
.task-time {
  padding: 13px 12px;
  color: #49454f;
  font-size: 12px;
  font-family: 'Roboto Mono', monospace;
  white-space: nowrap;
}
.tasks-table td {
  padding: 13px 12px;
}
.task-actions {
  text-align: right;
  white-space: nowrap;
}
.task-actions-inner {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}
.task-pause-btn {
  align-self: center;
}
</style>
