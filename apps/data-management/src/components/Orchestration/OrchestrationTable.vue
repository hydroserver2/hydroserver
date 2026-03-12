<template>
  <v-card>
    <v-toolbar flat color="cyan-darken-3" class="gap-3">
      <v-toolbar-title class="flex-shrink-0">
        Orchestration systems
      </v-toolbar-title>
      <div class="ml-auto flex min-w-0 items-center gap-3">
        <v-text-field
          class="w-[250px] max-w-[250px]"
          clearable
          v-model="search"
          :prepend-inner-icon="mdiMagnify"
          label="Search"
          hide-details
          density="compact"
          variant="underlined"
          rounded="xl"
        />

        <v-autocomplete
          v-model="statusFilter"
          :items="statusOptions"
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
          class="w-[280px] max-w-[280px] mx-1"
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
        <v-btn
          class="mr-4"
          @click="
            openDataConnectionTableDialog = !openDataConnectionTableDialog
          "
          rounded="xl"
          color="white"
          variant="outlined"
          density="comfortable"
          :append-icon="openDataConnectionTableDialog ? mdiMenuUp : mdiMenuDown"
        >
          Manage data connections
        </v-btn>
      </div>
    </v-toolbar>

    <div class="orchestration-table">
      <div
        v-if="loading"
        class="rounded-lg border border-slate-200 bg-white p-6"
      >
        <div class="mb-4 rounded-md bg-slate-50 px-4 py-3">
          <div class="flex items-center gap-3 text-sm text-slate-600">
            <v-progress-circular
              indeterminate
              size="20"
              width="2"
              color="blue-grey-darken-1"
            />
            <span class="font-medium">Loading orchestration tasks...</span>
          </div>
        </div>
        <v-skeleton-loader type="table" class="rounded-md" />
      </div>

      <div
        v-else-if="groupList.length === 0"
        class="rounded-lg border border-slate-200 bg-white p-6 text-center text-sm text-slate-500"
      >
        <h4
          class="mt-2 text-base font-semibold text-slate-700"
          v-if="statusFilter.length === 0 && !`${search || ''}`.trim()"
        >
          You have not registered any orchestration systems.
        </h4>
        <h4 class="mt-2 text-base font-semibold text-slate-700" v-else>
          No tasks match your search/filter.
        </h4>
        <p
          class="mt-2"
          v-if="statusFilter.length === 0 && !`${search || ''}`.trim()"
        >
          Click the 'download Streaming Data Loader' button to get started or
          <a
            href="https://hydroserver.org"
            target="_blank"
            class="text-blue-600 underline"
            >read the documentation</a
          >
          to learn more.
        </p>
      </div>

      <div
        v-else
        class="overflow-hidden rounded-b-lg border border-slate-200 bg-white shadow-sm"
      >
        <section
          v-for="(group, index) in groupList"
          :key="group.name"
          class="overflow-hidden bg-white"
          :class="index > 0 ? 'border-t border-slate-200' : ''"
        >
          <div
            role="button"
            tabindex="0"
            class="flex w-full items-center gap-3 bg-[#eceff1] px-4 py-3 text-left cursor-pointer select-none"
            :class="isGroupOpen(group.name) ? 'border-b border-slate-200' : ''"
            @click="toggleGroup(group.name)"
            @keydown.enter.prevent="toggleGroup(group.name)"
            @keydown.space.prevent="toggleGroup(group.name)"
          >
            <v-btn
              variant="outlined"
              density="comfortable"
              size="small"
              :icon="isGroupOpen(group.name) ? mdiChevronDown : mdiChevronRight"
              class="flex-shrink-0"
            />
            <div class="flex min-w-0 flex-1 items-center gap-4">
              <span class="truncate text-sm font-semibold text-slate-800">
                {{ group.name }}
              </span>
              <div class="hidden flex-wrap items-center gap-2 md:flex">
                <v-chip size="small" variant="tonal" color="blue-grey-darken-2">
                  Total tasks: {{ group.summary.total }}
                </v-chip>
                <v-chip
                  v-if="group.summary.ok > 0"
                  size="small"
                  variant="tonal"
                  color="green-darken-2"
                >
                  OK: {{ group.summary.ok }}
                </v-chip>
                <v-chip
                  v-if="group.summary.needsAttention > 0"
                  size="small"
                  variant="tonal"
                  color="error"
                >
                  Needs attention: {{ group.summary.needsAttention }}
                </v-chip>
                <v-chip
                  v-if="group.summary.loadingPaused > 0"
                  size="small"
                  variant="tonal"
                  color="blue-grey"
                >
                  Loading paused: {{ group.summary.loadingPaused }}
                </v-chip>
                <v-chip
                  v-if="group.summary.behindSchedule > 0"
                  size="small"
                  variant="tonal"
                  color="orange-darken-3"
                >
                  Behind schedule: {{ group.summary.behindSchedule }}
                </v-chip>
                <v-chip
                  v-if="group.summary.pending > 0"
                  size="small"
                  variant="tonal"
                  color="blue"
                >
                  Pending: {{ group.summary.pending }}
                </v-chip>
                <v-chip
                  v-if="group.summary.unknown > 0"
                  size="small"
                  variant="tonal"
                  color="grey-darken-1"
                >
                  Unknown: {{ group.summary.unknown }}
                </v-chip>
              </div>
            </div>
            <div class="ml-auto flex items-center gap-3">
              <v-tooltip
                location="top"
                :disabled="!groupActionDisabledReason(group)"
              >
                <template #activator="{ props: tooltipProps }">
                  <span v-bind="tooltipProps" class="inline-flex">
                    <v-btn-add
                      class="hidden md:inline-flex"
                      color="white"
                      @click.stop="openCreateDialog(group.orchestrationSystem)"
                      :disabled="
                        !canEditOrchestration || !group.orchestrationSystem
                      "
                    >
                      Add task
                    </v-btn-add>
                  </span>
                </template>
                <span>{{ groupActionDisabledReason(group) }}</span>
              </v-tooltip>
              <v-tooltip
                location="top"
                :disabled="!groupActionDisabledReason(group)"
              >
                <template #activator="{ props: tooltipProps }">
                  <span v-bind="tooltipProps" class="inline-flex">
                    <v-btn
                      variant="text"
                      color="red-darken-2"
                      :icon="mdiTrashCanOutline"
                      @click.stop="openDeleteDialog(group.orchestrationSystem)"
                      :disabled="
                        !canEditOrchestration || !group.orchestrationSystem
                      "
                    />
                  </span>
                </template>
                <span>{{ groupActionDisabledReason(group) }}</span>
              </v-tooltip>
            </div>
          </div>

          <div v-if="isGroupOpen(group.name)">
            <div
              class="max-h-[62vh] overflow-auto"
              ref="bodyScrollRef"
              @scroll.passive="onBodyScroll"
            >
              <table class="w-full table-fixed text-sm whitespace-nowrap">
                <thead
                  class="sticky top-0 z-10 bg-slate-50 text-sm font-semibold text-slate-700"
                >
                  <tr>
                    <th class="px-3 py-3 text-left w-[23%]">
                      <button
                        type="button"
                        class="flex items-center gap-1 cursor-pointer bg-transparent p-0 text-left hover:text-slate-900"
                        @click="toggleSort('name')"
                        title="Click to sort, click again to reverse, click again to clear"
                      >
                        <span>Task name</span>
                        <v-icon :icon="sortIcon('name')" size="16" />
                        <span
                          v-if="sortBadge('name')"
                          class="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-slate-200 px-1 text-[10px] font-semibold text-slate-700"
                        >
                          {{ sortBadge('name') }}
                        </span>
                      </button>
                    </th>
                    <th class="px-3 py-3 text-left w-[17%]">
                      <button
                        type="button"
                        class="flex items-center gap-1 cursor-pointer bg-transparent p-0 text-left hover:text-slate-900"
                        @click="toggleSort('dataConnection')"
                        title="Click to sort, click again to reverse, click again to clear"
                      >
                        <span>Data connection</span>
                        <v-icon :icon="sortIcon('dataConnection')" size="16" />
                        <span
                          v-if="sortBadge('dataConnection')"
                          class="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-slate-200 px-1 text-[10px] font-semibold text-slate-700"
                        >
                          {{ sortBadge('dataConnection') }}
                        </span>
                      </button>
                    </th>
                    <th class="px-3 py-3 text-left w-[10%]">
                      <button
                        type="button"
                        class="flex items-center gap-1 cursor-pointer bg-transparent p-0 text-left hover:text-slate-900"
                        @click="toggleSort('status')"
                        title="Click to sort, click again to reverse, click again to clear"
                      >
                        <span>Status</span>
                        <v-icon :icon="sortIcon('status')" size="16" />
                        <span
                          v-if="sortBadge('status')"
                          class="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-slate-200 px-1 text-[10px] font-semibold text-slate-700"
                        >
                          {{ sortBadge('status') }}
                        </span>
                      </button>
                    </th>
                    <th class="px-3 py-3 text-left w-[15%]">
                      <button
                        type="button"
                        class="flex items-center gap-1 cursor-pointer bg-transparent p-0 text-left hover:text-slate-900"
                        @click="toggleSort('lastRunAt')"
                        title="Click to sort, click again to reverse, click again to clear"
                      >
                        <span>Last run</span>
                        <v-icon :icon="sortIcon('lastRunAt')" size="16" />
                        <span
                          v-if="sortBadge('lastRunAt')"
                          class="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-slate-200 px-1 text-[10px] font-semibold text-slate-700"
                        >
                          {{ sortBadge('lastRunAt') }}
                        </span>
                      </button>
                    </th>
                    <th class="px-3 py-3 text-left w-[15%]">
                      <button
                        type="button"
                        class="flex items-center gap-1 cursor-pointer bg-transparent p-0 text-left hover:text-slate-900"
                        @click="toggleSort('nextRunAt')"
                        title="Click to sort, click again to reverse, click again to clear"
                      >
                        <span>Next run</span>
                        <v-icon :icon="sortIcon('nextRunAt')" size="16" />
                        <span
                          v-if="sortBadge('nextRunAt')"
                          class="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-slate-200 px-1 text-[10px] font-semibold text-slate-700"
                        >
                          {{ sortBadge('nextRunAt') }}
                        </span>
                      </button>
                    </th>
                    <th class="px-3 py-3 text-right w-[20%]">Actions</th>
                  </tr>
                </thead>
                <tbody v-if="openGroupRows.length === 0">
                  <tr>
                    <td
                      colspan="6"
                      class="px-3 py-6 text-center text-sm text-slate-500"
                    >
                      No tasks registered for this orchestration system.
                    </td>
                  </tr>
                </tbody>
                <tbody v-else>
                  <tr
                    class="border-0"
                    :style="{ height: `${virtualPaddingTop}px` }"
                  >
                    <td colspan="6"></td>
                  </tr>
                  <tr
                    v-for="row in virtualRows"
                    :key="row.id"
                    class="h-20 border-b border-slate-100"
                    :class="row.isPlaceholder ? 'text-slate-400' : ''"
                  >
                    <td
                      class="px-3 py-2 font-medium text-slate-800 whitespace-normal break-words"
                    >
                      {{ row.name || '—' }}
                    </td>
                    <td
                      class="px-3 py-2 text-slate-600 whitespace-normal break-words"
                    >
                      {{ row.dataConnection?.name || '—' }}
                    </td>
                    <td class="px-3 py-2">
                      <v-tooltip
                        v-if="!row.isPlaceholder"
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
                              :paused="row.schedule?.paused"
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
                            <div
                              class="mb-1 flex items-center justify-between gap-3"
                            >
                              <div
                                class="text-[0.7rem] font-extrabold uppercase tracking-[0.12em] text-slate-600"
                              >
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
                      <span v-else class="text-slate-400">—</span>
                    </td>
                    <td class="px-3 py-2 text-slate-700">{{ row.lastRun }}</td>
                    <td class="px-3 py-2 text-slate-700">{{ row.nextRun }}</td>
                    <td class="px-3 py-2 text-right">
                      <div
                        v-if="!row.isPlaceholder"
                        class="flex flex-col gap-3"
                      >
                        <div
                          class="flex flex-wrap items-center justify-end gap-3"
                        >
                          <v-tooltip
                            location="top"
                            :open-delay="0"
                            :close-delay="0"
                          >
                            <template #activator="{ props: tooltipProps }">
                              <span v-bind="tooltipProps" class="inline-flex">
                                <v-btn
                                  variant="text"
                                  color="black"
                                  :icon="
                                    row.schedule?.paused ? mdiPlay : mdiPause
                                  "
                                  :disabled="!canEditOrchestration"
                                  @click.stop="togglePaused(row)"
                                  aria-label="Pause or run task"
                                />
                              </span>
                            </template>
                            <span>{{
                              !canEditOrchestration
                                ? readOnlyTooltip
                                : row.schedule?.paused
                                ? 'Resume task'
                                : 'Pause task'
                            }}</span>
                          </v-tooltip>
                          <v-btn
                            v-if="
                              canEditOrchestration &&
                              isInternalSystem(row) &&
                              !row.userClickedRunNow
                            "
                            variant="outlined"
                            color="green-darken-3"
                            :append-icon="mdiPlay"
                            @click.stop="runTaskNow(row)"
                          >
                            Run now
                          </v-btn>
                          <span
                            v-else-if="
                              canEditOrchestration &&
                              isInternalSystem(row) &&
                              row.userClickedRunNow
                            "
                            class="text-sm font-semibold text-slate-500"
                          >
                            Run requested
                          </span>
                        </div>
                        <div class="flex items-center justify-end gap-3">
                          <v-btn
                            variant="outlined"
                            color="blue-grey-darken-3"
                            @click.stop="goToTask(row)"
                            aria-label="View details"
                            title="View task details"
                            class="text-none"
                            :append-icon="mdiChevronRight"
                          >
                            View details
                          </v-btn>
                        </div>
                      </div>
                    </td>
                  </tr>
                  <tr
                    class="border-0"
                    :style="{ height: `${virtualPaddingBottom}px` }"
                  >
                    <td colspan="6"></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </div>
  </v-card>

  <v-dialog v-model="openCreate" v-if="selectedOrchestrationSystem">
    <TaskForm
      :orchestration-system="selectedOrchestrationSystem"
      @close="openCreate = false"
      @created="refreshTable"
    />
  </v-dialog>

  <v-dialog
    v-if="selectedOrchestrationSystem"
    v-model="openDelete"
    width="40rem"
  >
    <DeleteOrchestrationSystemCard
      :orchestration-system="selectedOrchestrationSystem"
      :tasks="workspaceTasks"
      @close="openDelete = false"
      @delete="refreshTable"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import {
  computed,
  reactive,
  ref,
  watch,
  nextTick,
  onMounted,
  onBeforeUnmount,
} from 'vue'
import TaskForm from '@/components/Orchestration/TaskForm.vue'
import TaskStatus from '@/components/Orchestration/TaskStatus.vue'
import DeleteOrchestrationSystemCard from '@/components/Orchestration/DeleteOrchestrationSystemCard.vue'
import router from '@/router/router'
import { formatTime } from '@/utils/time'
import hs, {
  OrchestrationSystem,
  PermissionAction,
  PermissionResource,
  StatusType,
  Task,
  TaskExpanded,
} from '@hydroserver/client'
import {
  mdiFilterVariant,
  mdiMagnify,
  mdiPause,
  mdiPlay,
  mdiTrashCanOutline,
  mdiChevronRight,
  mdiChevronDown,
  mdiArrowUp,
  mdiArrowDown,
  mdiArrowUpDown,
} from '@mdi/js'
import { mdiMenuDown, mdiMenuUp } from '@mdi/js'
import { storeToRefs } from 'pinia'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { useDataConnectionStore } from '@/store/dataConnection'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'

const props = defineProps<{
  workspaceId: string
}>()

const { openDataConnectionTableDialog } = storeToRefs(useDataConnectionStore())
const { workspaceTasks, orchestrationSearch, orchestrationStatusFilter } =
  storeToRefs(useOrchestrationStore())
const { workspaces } = storeToRefs(useWorkspaceStore())
const { hasPermission, isAdmin, isOwner } = useWorkspacePermissions()

const openCreate = ref(false)
const openDelete = ref(false)
const search = orchestrationSearch
const orchestrationSystems = ref<OrchestrationSystem[]>([])
const selectedOrchestrationSystem = ref<OrchestrationSystem>()
const loading = ref(false)
const runNowTriggeredByTaskId = reactive<Record<string, boolean>>({})
const statusFilter = orchestrationStatusFilter

const openGroupName = ref<string | null>(null)
const hasAutoOpened = ref(false)

const bodyScrollRef = ref<HTMLElement | HTMLElement[] | null>(null)
const bodyScrollTop = ref(0)
const bodyHeight = ref(0)
let resizeObserver: ResizeObserver | null = null

const ROW_HEIGHT = 80
const OVERSCAN = 6
const POLL_INTERVAL_MS = 4000
const POLL_MAX_ATTEMPTS = 20

const taskPollTimeouts = new Map<string, number>()

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

const groupActionDisabledReason = (group: {
  orchestrationSystem?: OrchestrationSystem
}) => {
  if (!canEditOrchestration.value) return readOnlyTooltip
  if (!group?.orchestrationSystem)
    return 'No orchestration system is available for this action.'
  return ''
}

type SortKey = 'name' | 'dataConnection' | 'status' | 'lastRunAt' | 'nextRunAt'
type SortSpec = { key: SortKey; dir: 'asc' | 'desc' }

// Multi-sort: first clicked column is primary, subsequent clicks add secondary sorts.
const sortSpecs = ref<SortSpec[]>([{ key: 'name', dir: 'asc' }])

watch(
  statusFilter,
  (value) => {
    if (!Array.isArray(value)) {
      statusFilter.value = []
      return
    }
    if (value.includes('all')) {
      statusFilter.value = value.filter((entry) => entry !== 'all')
    }
  },
  { immediate: true }
)

type TaskHealthFilter =
  | 'OK'
  | 'Needs attention'
  | 'Loading paused'
  | 'Behind schedule'
  | 'Pending'
  | 'Unknown'

const statusOptions = [
  { title: 'OK', value: 'OK' },
  { title: 'Needs attention', value: 'Needs attention' },
  { title: 'Loading paused', value: 'Loading paused' },
  { title: 'Behind schedule', value: 'Behind schedule' },
  { title: 'Pending', value: 'Pending' },
  { title: 'Unknown', value: 'Unknown' },
] as const

const classifyTask = (task: {
  statusName: StatusType
  schedule?: { paused?: boolean } | null
}) => {
  const displayedStatus = getDisplayedStatus(task)
  if (
    displayedStatus === 'OK' ||
    displayedStatus === 'Needs attention' ||
    displayedStatus === 'Loading paused' ||
    displayedStatus === 'Behind schedule' ||
    displayedStatus === 'Pending'
  ) {
    return displayedStatus
  }
  return 'Unknown'
}

const getDisplayedStatus = (task: {
  statusName: StatusType
  schedule?: { paused?: boolean } | null
}) => {
  if (task.schedule?.paused && task.statusName !== 'Needs attention') {
    return 'Loading paused' as StatusType
  }
  return task.statusName
}

const groupHealthSummary = (rows: readonly any[]) => {
  return rows.reduce(
    (summary, row) => {
      const task = row?.raw ?? row
      if (!task || task.isPlaceholder) return summary

      const displayedStatus = getDisplayedStatus({
        statusName: task.statusName ?? hs.tasks.getStatusText(task),
        schedule: task.schedule,
      })

      if (displayedStatus === 'OK') summary.ok += 1
      else if (displayedStatus === 'Needs attention')
        summary.needsAttention += 1
      else if (displayedStatus === 'Loading paused') summary.loadingPaused += 1
      else if (displayedStatus === 'Behind schedule')
        summary.behindSchedule += 1
      else if (displayedStatus === 'Pending') summary.pending += 1
      else summary.unknown += 1

      summary.total += 1
      return summary
    },
    {
      ok: 0,
      needsAttention: 0,
      loadingPaused: 0,
      behindSchedule: 0,
      pending: 0,
      unknown: 0,
      total: 0,
    }
  )
}

const fetchOrchestrationData = async (newId: string) => {
  loading.value = true
  try {
    const [orchestrationSystemResponse, taskItems] = await Promise.all([
      hs.orchestrationSystems.listAllItems(),
      hs.tasks.listAllItems({ expand_related: true, workspace_id: [newId] }),
    ])

    // TODO: Allow HydroShare as an option once we have archival functionality in the orchestration system
    orchestrationSystems.value = orchestrationSystemResponse.filter(
      (os) =>
        (os.workspaceId === newId || !os.workspaceId) &&
        os.type !== 'HydroShare'
    )
    workspaceTasks.value = taskItems as any
  } catch (error) {
    console.error('Error fetching orchestration data', error)
  } finally {
    loading.value = false
  }
}

const refreshTable = async () => {
  await fetchOrchestrationData(props.workspaceId)
}

watch(
  () => props.workspaceId,
  async (newId) => {
    if (newId == null) return
    await fetchOrchestrationData(newId)
  },
  { immediate: true }
)

const searchText = computed(() => `${search.value || ''}`.trim().toLowerCase())

const resolveGroupName = (task: any) => {
  const directName = task?.orchestrationSystem?.name
  if (directName) return directName
  const matched = orchestrationSystems.value.find(
    (os) => os.id === task?.orchestrationSystemId
  )
  return matched?.name ?? 'Unknown'
}

const resolveOrchestrationSystem = (task: any) => {
  if (task?.orchestrationSystem) return task.orchestrationSystem
  const matchedById = orchestrationSystems.value.find(
    (os) => os.id === task?.orchestrationSystemId
  )
  if (matchedById) return matchedById
  return orchestrationSystems.value.find(
    (os) => os.name === resolveGroupName(task)
  )
}

const getRunMessage = (run?: any) => {
  const result =
    run?.result && typeof run.result === 'object' ? run.result : {}
  return (
    run?.failureReason ||
    result.summary ||
    result.status_message ||
    result.statusMessage ||
    result.failure_reason ||
    result.failureReason ||
    result.error ||
    result.message ||
    ''
  )
}

const taskRows = computed(() =>
  workspaceTasks.value.map((t) => ({
    ...t,
    schedule: t.schedule ?? null,
    statusName: hs.tasks.getStatusText(t),
    statusSort: getDisplayedStatus({
      statusName: hs.tasks.getStatusText(t),
      schedule: t.schedule ?? null,
    }),
    lastRun: !!t.latestRun?.startedAt ? formatTime(t.latestRun.startedAt) : '-',
    nextRun: t.schedule?.nextRunAt ? formatTime(t.schedule?.nextRunAt) : '-',
    lastRunAt: t.latestRun?.startedAt ?? null,
    nextRunAt: t.schedule?.nextRunAt ?? null,
    lastRunMessage: getRunMessage(t.latestRun as any),
    orchestrationSystemName: resolveGroupName(t),
    isPlaceholder: false,
    userClickedRunNow: !!runNowTriggeredByTaskId[t.id],
  }))
)

const matchesSearch = (task: any, term: string) => {
  if (!term) return true
  const haystack = [
    task.name,
    task.dataConnection?.name,
    task.statusName,
    task.lastRun,
    task.nextRun,
    task.orchestrationSystemName,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return haystack.includes(term)
}

const filteredTaskRows = computed(() => {
  const activeFilters = new Set(statusFilter.value as TaskHealthFilter[])
  return taskRows.value.filter((task) => {
    const statusMatch =
      activeFilters.size === 0 || activeFilters.has(classifyTask(task))
    const searchMatch = matchesSearch(task, searchText.value)
    return statusMatch && searchMatch
  })
})

const compareText = (a: unknown, b: unknown) =>
  `${a ?? ''}`.localeCompare(`${b ?? ''}`, undefined, {
    numeric: true,
    sensitivity: 'base',
  })

const compareNullableDate = (a: unknown, b: unknown) => {
  // Treat missing dates as "last" when sorting ascending.
  const aVal = a ? new Date(a as any).getTime() : null
  const bVal = b ? new Date(b as any).getTime() : null
  if (aVal == null && bVal == null) return 0
  if (aVal == null) return 1
  if (bVal == null) return -1
  return aVal - bVal
}

const buildComparatorForKey = (key: SortKey) => {
  if (key === 'name') return (a: any, b: any) => compareText(a?.name, b?.name)
  if (key === 'dataConnection')
    return (a: any, b: any) =>
      compareText(a?.dataConnection?.name, b?.dataConnection?.name)
  if (key === 'status')
    return (a: any, b: any) => compareText(a?.statusSort, b?.statusSort)
  if (key === 'lastRunAt')
    return (a: any, b: any) => compareNullableDate(a?.lastRunAt, b?.lastRunAt)
  if (key === 'nextRunAt')
    return (a: any, b: any) => compareNullableDate(a?.nextRunAt, b?.nextRunAt)
  return () => 0
}

const normalizeSortSpecs = (specs: SortSpec[]): SortSpec[] => {
  const seen = new Set<SortKey>()
  const normalized: SortSpec[] = []
  for (const spec of specs) {
    if (!spec?.key || seen.has(spec.key)) continue
    seen.add(spec.key)
    normalized.push({ key: spec.key, dir: spec.dir })
  }
  return normalized
}

const sortRows = (rows: any[]) => {
  const specs = normalizeSortSpecs(sortSpecs.value)
  const comparators = specs.map((spec) => {
    const base = buildComparatorForKey(spec.key)
    const dir = spec.dir === 'asc' ? 1 : -1
    return (a: any, b: any) => base(a, b) * dir
  })

  return [...rows].sort((a, b) => {
    for (const cmpFn of comparators) {
      const cmp = cmpFn(a, b)
      if (cmp !== 0) return cmp
    }
    return 0
  })
}

const includeEmptyGroups = computed(
  () =>
    searchText.value.length === 0 &&
    Array.isArray(statusFilter.value) &&
    statusFilter.value.length === 0
)

const groupList = computed(() => {
  const map = new Map<
    string,
    {
      name: string
      items: any[]
      orchestrationSystem?: OrchestrationSystem
      summary: ReturnType<typeof groupHealthSummary>
    }
  >()

  if (includeEmptyGroups.value) {
    orchestrationSystems.value.forEach((os) => {
      map.set(os.name, {
        name: os.name,
        items: [],
        orchestrationSystem: os,
        summary: groupHealthSummary([]),
      })
    })
  }

  filteredTaskRows.value.forEach((row) => {
    const name = row.orchestrationSystemName ?? 'Unknown'
    const orchestrationSystem = resolveOrchestrationSystem(row)
    const existing = map.get(name)
    if (existing) {
      existing.items.push(row)
      if (!existing.orchestrationSystem && orchestrationSystem) {
        existing.orchestrationSystem = orchestrationSystem
      }
    } else {
      map.set(name, {
        name,
        items: [row],
        orchestrationSystem,
        summary: groupHealthSummary([row]),
      })
    }
  })

  const groups = Array.from(map.values()).map((group) => ({
    ...group,
    items: sortRows(group.items),
    summary: groupHealthSummary(group.items),
  }))

  return groups.sort((a, b) => a.name.localeCompare(b.name))
})

const openGroupRows = computed(() => {
  if (!openGroupName.value) return []
  const group = groupList.value.find((g) => g.name === openGroupName.value)
  return group?.items ?? []
})

const totalRows = computed(() => openGroupRows.value.length)

const effectiveBodyHeight = computed(() =>
  bodyHeight.value > 0 ? bodyHeight.value : ROW_HEIGHT * 8
)

const virtualStart = computed(() =>
  Math.max(0, Math.floor(bodyScrollTop.value / ROW_HEIGHT) - OVERSCAN)
)

const virtualEnd = computed(() => {
  const base = Math.ceil(
    (bodyScrollTop.value + effectiveBodyHeight.value) / ROW_HEIGHT
  )
  return Math.min(totalRows.value, base + OVERSCAN)
})

const virtualRows = computed(() =>
  openGroupRows.value.slice(virtualStart.value, virtualEnd.value)
)

const virtualPaddingTop = computed(() => virtualStart.value * ROW_HEIGHT)
const virtualPaddingBottom = computed(() => {
  const rendered = virtualRows.value.length * ROW_HEIGHT
  return Math.max(
    0,
    totalRows.value * ROW_HEIGHT - virtualPaddingTop.value - rendered
  )
})

const isGroupOpen = (groupName: string) => openGroupName.value === groupName

const clearSelection = () => {
  if (typeof window === 'undefined') return
  window.getSelection()?.removeAllRanges()
}

const toggleGroup = (groupName: string) => {
  openGroupName.value = openGroupName.value === groupName ? null : groupName
  clearSelection()
  if (typeof window !== 'undefined') {
    window.requestAnimationFrame(clearSelection)
  }
}

const onBodyScroll = (event: Event) => {
  const target = event.target as HTMLElement
  bodyScrollTop.value = target.scrollTop
}

const getBodyScrollEl = () => {
  const value = bodyScrollRef.value
  if (Array.isArray(value)) return value[0] ?? null
  return value ?? null
}

const resetVirtualScroll = () => {
  bodyScrollTop.value = 0
  const el = getBodyScrollEl()
  if (el) {
    el.scrollTop = 0
  }
}

const observeBody = () => {
  const el = getBodyScrollEl()
  if (!el || !(el instanceof Element)) return
  const updateHeight = () => {
    bodyHeight.value = el.clientHeight
  }
  updateHeight()
  if (resizeObserver) resizeObserver.disconnect()
  resizeObserver = new ResizeObserver(updateHeight)
  resizeObserver.observe(el)
}

const upsertWorkspaceTask = (t: TaskExpanded | null) => {
  if (!t) return
  const next = [...workspaceTasks.value]
  const index = next.findIndex((p) => p.id === t.id)
  if (index !== -1) next[index] = t as any
  else next.push(t as any)
  workspaceTasks.value = next as any
}

const stopTaskPolling = (taskId: string) => {
  const timeoutId = taskPollTimeouts.get(taskId)
  if (timeoutId) {
    window.clearTimeout(timeoutId)
  }
  taskPollTimeouts.delete(taskId)
}

const scheduleTaskPoll = (taskId: string, attempt = 0) => {
  stopTaskPolling(taskId)
  if (attempt > POLL_MAX_ATTEMPTS) {
    runNowTriggeredByTaskId[taskId] = false
    return
  }

  const timeoutId = window.setTimeout(async () => {
    try {
      const updated = await hs.tasks.getItem(taskId, {
        expand_related: true,
      })
      if (updated) {
        upsertWorkspaceTask(updated as any)
        const status = updated.latestRun?.status
        if (status && status !== 'RUNNING') {
          runNowTriggeredByTaskId[taskId] = false
          stopTaskPolling(taskId)
          return
        }
      }
    } catch (error) {
      console.error('Error polling task status', error)
    }
    scheduleTaskPoll(taskId, attempt + 1)
  }, POLL_INTERVAL_MS)

  taskPollTimeouts.set(taskId, timeoutId)
}

async function runTaskNow(task: Partial<Task> & Pick<Task, 'id'>) {
  if (!canEditOrchestration.value) return
  runNowTriggeredByTaskId[task.id] = true
  try {
    await hs.tasks.runTask(task.id)
    scheduleTaskPoll(task.id, 0)
  } catch (error) {
    runNowTriggeredByTaskId[task.id] = false
    console.error('Error running task now', error)
  }
}

async function togglePaused(task: Partial<Task> & Pick<Task, 'id'>) {
  if (!canEditOrchestration.value) return
  if (!task.schedule) return
  const previous = !!task.schedule.paused
  task.schedule.paused = !previous
  try {
    await hs.tasks.update({
      id: task.id,
      schedule: task.schedule,
    } as any)
    // Avoid full-table reload; refresh just this row so next/last run times stay accurate.
    const updated = await hs.tasks.getItem(task.id, { expand_related: true })
    upsertWorkspaceTask(updated as any)
  } catch (error) {
    task.schedule.paused = previous
    console.error('Error toggling task paused state', error)
  }
}

watch(
  groupList,
  (groups) => {
    if (!groups.length) {
      openGroupName.value = null
      return
    }
    if (!hasAutoOpened.value) {
      openGroupName.value = groups[0].name
      hasAutoOpened.value = true
      return
    }
    if (
      openGroupName.value &&
      !groups.some((group) => group.name === openGroupName.value)
    ) {
      openGroupName.value = groups[0].name
    }
  },
  { immediate: true }
)

watch(
  openGroupName,
  async () => {
    await nextTick()
    observeBody()
    resetVirtualScroll()
  },
  { immediate: false }
)

onMounted(() => {
  observeBody()
})

onBeforeUnmount(() => {
  if (resizeObserver) resizeObserver.disconnect()
  taskPollTimeouts.forEach((timeoutId) => window.clearTimeout(timeoutId))
  taskPollTimeouts.clear()
})

const isInternalSystem = (item: any) => {
  const isInternalType = (value: unknown) =>
    typeof value === 'string' && value.trim().toUpperCase() === 'INTERNAL'

  const directType =
    item?.orchestrationSystem?.type ??
    item?.orchestrationSystem?.orchestrationSystemType ??
    item?.orchestrationSystem?.orchestration_system_type ??
    item?.orchestrationSystemType ??
    item?.orchestration_system_type
  if (isInternalType(directType)) return true

  const systemId = item?.orchestrationSystemId ?? item?.orchestrationSystem?.id
  const matched = orchestrationSystems.value.find((os) => os.id === systemId)
  return isInternalType((matched as any)?.type)
}

const openCreateDialog = (selectedItem: any) => {
  if (!canEditOrchestration.value) return
  selectedOrchestrationSystem.value = selectedItem
  openCreate.value = true
}

const openDeleteDialog = (selectedItem: any) => {
  if (!canEditOrchestration.value) return
  selectedOrchestrationSystem.value = selectedItem
  openDelete.value = true
}

const goToTask = async (item: any) => {
  if (item.isPlaceholder) return
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

const toggleSort = (key: SortKey) => {
  const next = normalizeSortSpecs(sortSpecs.value)
  const idx = next.findIndex((s) => s.key === key)
  if (idx === -1) {
    next.push({ key, dir: 'asc' })
    sortSpecs.value = normalizeSortSpecs(next)
    return
  }

  if (next[idx].dir === 'asc') {
    next[idx] = { key, dir: 'desc' }
    sortSpecs.value = normalizeSortSpecs(next)
    return
  }

  // Third click clears this sort key.
  next.splice(idx, 1)
  sortSpecs.value = normalizeSortSpecs(next)
}

const sortIcon = (key: SortKey) => {
  const spec = normalizeSortSpecs(sortSpecs.value).find((s) => s.key === key)
  if (!spec) return mdiArrowUpDown
  return spec.dir === 'asc' ? mdiArrowUp : mdiArrowDown
}

const sortBadge = (key: SortKey) => {
  const specs = normalizeSortSpecs(sortSpecs.value)
  if (specs.length <= 1) return null
  const idx = specs.findIndex((s) => s.key === key)
  if (idx === -1) return null
  return idx + 1
}

watch(
  sortSpecs,
  () => {
    resetVirtualScroll()
  },
  { deep: true }
)
</script>

<style scoped>
.orchestration-table :deep(th),
.orchestration-table :deep(td) {
  border-color: #e2e8f0;
}
</style>
