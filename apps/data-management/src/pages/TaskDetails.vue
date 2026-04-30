<template>
  <div
    v-if="task"
    :class="[
      'task-details-shell bg-[#eef2f6]',
      props.embedded ? 'mt-0 mb-0' : 'my-4',
    ]"
  >
    <TaskDetailsNavRail v-model="activePanel" />

    <div class="task-details-content">
      <div
        :class="[
          'mb-4 rounded-lg border border-slate-200 bg-white px-4 py-2 shadow-sm',
          props.embedded ? 'mt-4' : 'mt-2',
        ]"
      >
        <v-row class="ma-0" align="center">
          <v-col cols="auto">
            <v-tooltip text="Back to job orchestration" location="bottom">
              <template #activator="{ props: tooltipProps }">
                <v-btn
                  v-bind="tooltipProps"
                  variant="text"
                  color="black"
                  :icon="mdiArrowLeft"
                  class="mr-2"
                  aria-label="Back to job orchestration"
                  @click="onBack"
                />
              </template>
            </v-tooltip>
          </v-col>
          <v-col cols="auto">
            <div class="leading-tight">
              <div
                class="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-slate-500"
              >
                Task
              </div>
              <div
                class="text-2xl font-extrabold tracking-tight text-slate-900"
              >
                {{ task.name }}
              </div>
            </div>
          </v-col>
          <v-spacer />
          <v-col cols="auto" class="d-flex ga-2">
            <v-tooltip location="top" :disabled="canEditTask">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn
                    variant="outlined"
                    :prepend-icon="mdiPencil"
                    rounded="xl"
                    color="secondary"
                    class="mr-1"
                    :disabled="!canEditTask"
                    @click="openEdit = true"
                  >
                    Edit task
                  </v-btn>
                </span>
              </template>
              <span>{{ readOnlyTooltip }}</span>
            </v-tooltip>
            <v-tooltip location="top" :disabled="canEditTask">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn-delete
                    variant="outlined"
                    rounded="xl"
                    :prepend-icon="mdiTrashCanOutline"
                    color="red-darken-3"
                    class="mr-1"
                    :disabled="!canEditTask"
                    @click="openDelete = true"
                  >
                    Delete task
                  </v-btn-delete>
                </span>
              </template>
              <span>{{ readOnlyTooltip }}</span>
            </v-tooltip>
            <v-tooltip
              v-if="canRunNow"
              location="top"
              :disabled="!runNowDisabledReason"
            >
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn
                    variant="outlined"
                    rounded="xl"
                    color="green-darken-3"
                    class="mr-1"
                    :append-icon="mdiPlay"
                    :disabled="!canEditTask || runNowRequested"
                    @click="runTaskNow"
                  >
                    {{ runNowRequested ? 'Run requested' : 'Run now' }}
                  </v-btn>
                </span>
              </template>
              <span>{{ runNowDisabledReason }}</span>
            </v-tooltip>
            <v-tooltip
              location="top"
              :disabled="!pauseToggleDisabledReason"
            >
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn
                    variant="text"
                    color="black"
                    :prepend-icon="task.schedule?.paused ? mdiPlay : mdiPause"
                    :disabled="!!pauseToggleDisabledReason"
                    @click.stop="togglePaused(task)"
                  >
                    Pause/Run
                  </v-btn>
                </span>
              </template>
              <span>{{ pauseToggleDisabledReason }}</span>
            </v-tooltip>
          </v-col>
        </v-row>
      </div>

      <v-toolbar
        v-show="activePanel === 'details'"
        color="cyan-darken-3"
        rounded="t-lg"
        class="section-toolbar"
      >
        <h6 class="text-h6 ml-4">Task details</h6>
        <v-spacer />
        <v-btn
          variant="text"
          color="white"
          :prepend-icon="mdiDownload"
          class="mr-2"
          :disabled="!task"
          @click="downloadTaskJsonConfiguration"
        >
          Download task configuration
        </v-btn>
      </v-toolbar>
      <v-data-table
        v-show="activePanel === 'details'"
        :headers="taskHeaders"
        :items="taskTableRows"
        :items-per-page="-1"
        hide-default-header
        hide-default-footer
        density="compact"
        class="elevation-3 rounded-b-lg section-card"
      >
        <template #item="{ item, columns }">
          <tr v-if="item.section">
            <td
              :colspan="columns.length"
              class="section-subheading detail-subheading"
            >
              {{ item.label }}
            </td>
          </tr>
          <tr v-else>
            <td class="text-body-2">
              <v-icon v-if="item?.icon" :icon="item.icon" class="mr-2" />
              <strong>{{ item?.label }}</strong>
            </td>
            <td class="text-body-2">
              <template v-if="item.label === 'Status'">
                <TaskStatus :status="item.status" :paused="!!item.paused" />
              </template>
              <template v-else>
                {{ item.value }}
              </template>
            </td>
          </tr>
        </template>
      </v-data-table>

      <!-- Run history cards float directly on the page background (no surrounding container). -->
      <div v-show="activePanel === 'runs'" class="flex flex-col gap-1">
        <v-toolbar color="cyan-darken-3" rounded="lg" class="section-toolbar">
          <h6 class="ml-4 text-h6">Run history</h6>
          <v-spacer />
          <v-btn
            variant="text"
            color="white"
            :prepend-icon="mdiHistory"
            class="mr-2"
            @click="refreshRunHistory"
          >
            Refresh history
          </v-btn>
        </v-toolbar>

        <template v-if="showRunHistoryLoading">
          <v-card variant="outlined" class="run-entry pa-4">
            <div class="mb-4 rounded-md bg-slate-50 px-4 py-3">
              <div class="flex items-center gap-3 text-sm text-slate-600">
                <v-progress-circular
                  indeterminate
                  size="20"
                  width="2"
                  color="blue-grey-darken-1"
                />
                <span class="font-medium">Loading run history...</span>
              </div>
            </div>
            <v-skeleton-loader type="paragraph, paragraph, paragraph" />
          </v-card>
        </template>

        <template v-else-if="runHistoryRows.length">
          <template v-for="run in runHistoryRows" :key="run.id">
            <v-card
              :id="runDomId(run.id)"
              class="run-entry"
              variant="outlined"
              :class="{
                'run-highlight': highlightedRunId === run.id,
              }"
            >
              <div class="run-entry-top">
                <div class="run-entry-top-left">
                  <TaskStatus
                    :status="getRunStatusText(run.raw)"
                    :paused="false"
                    class="run-entry-status"
                  />
                </div>
                <div class="run-entry-summary" :title="run.message">
                  {{ run.message }}
                </div>
                <div class="run-entry-runid-top run-entry-runid-right">
                  Run {{ shortId(run.id) }}
                </div>
              </div>

              <div class="run-entry-meta">
                <div class="run-entry-meta-row">
                  <div class="run-entry-times-inline">
                    <span class="run-entry-time">
                      <span class="run-entry-meta-label">Started</span>
                      {{ run.startedAt }}
                    </span>
                  </div>
                  <div class="run-entry-duration">
                    {{ runDurationText(run.raw) }}
                  </div>
                </div>
              </div>

              <div class="run-entry-footer">
                <v-btn
                  variant="tonal"
                  color="cyan-darken-3"
                  :prepend-icon="mdiCodeBraces"
                  class="text-none"
                  @click="toggleRunLogs(run.id)"
                >
                  {{
                    openRunLogs[run.id]
                      ? 'Hide run details'
                      : 'View run details'
                  }}
                </v-btn>
              </div>

              <!-- Logs expand outside of the footer (keeps the "View logs" area clean). -->
              <v-expand-transition>
                <div
                  v-if="openRunLogs[run.id]"
                  class="border-t border-slate-100 px-4 pt-3 pb-4"
                >
                  <div class="mb-3 grid gap-2">
                    <div v-if="run.runtimeUrl" class="run-entry-detail-row">
                      <div class="run-entry-detail-label">
                        Runtime source URI
                      </div>
                      <div class="run-entry-detail-value">
                        <div class="run-entry-detail-linkwrap">
                          <a
                            class="text-slate-600 underline break-all hover:text-blue-700"
                            :href="run.runtimeUrl"
                            target="_blank"
                            rel="noopener"
                          >
                            {{ run.runtimeUrl }}
                          </a>
                          <v-tooltip
                            text="Copy runtime source URI"
                            location="bottom"
                          >
                            <template #activator="{ props: tooltipProps }">
                              <v-btn
                                v-bind="tooltipProps"
                                icon
                                variant="text"
                                size="small"
                                color="blue-grey-darken-2"
                                @click="copyToClipboard(run.runtimeUrl)"
                                aria-label="Copy runtime source URI"
                              >
                                <v-icon :icon="mdiContentCopy" />
                              </v-btn>
                            </template>
                          </v-tooltip>
                        </div>
                      </div>
                    </div>

                    <div
                      class="run-entry-detail-row run-entry-detail-row-inline"
                    >
                      <div class="run-entry-detail-inline">
                        <div class="run-entry-detail-label">
                          Copy run as URL
                        </div>
                        <v-tooltip text="Copy run as URL" location="bottom">
                          <template #activator="{ props: tooltipProps }">
                            <v-btn
                              v-bind="tooltipProps"
                              icon
                              variant="text"
                              size="small"
                              color="blue-grey-darken-2"
                              @click="copyToClipboard(runLinkUrl(run.id))"
                              aria-label="Copy run as URL"
                            >
                              <v-icon :icon="mdiContentCopy" />
                            </v-btn>
                          </template>
                        </v-tooltip>
                      </div>
                    </div>
                  </div>

                  <div class="grid gap-3">
                    <div
                      v-for="(section, idx) in buildLogSections(run.raw)"
                      :key="`${section.title}-${idx}`"
                      class="grid gap-2"
                    >
                      <div
                        class="rounded-md border border-slate-200 bg-slate-100 px-2 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-slate-600"
                      >
                        {{ section.title }}
                      </div>
                      <div v-if="section.type === 'lines'" class="grid gap-1.5">
                        <div
                          v-for="(entry, entryIdx) in section.entries"
                          :key="entryIdx"
                          class="grid grid-cols-[minmax(240px,260px)_minmax(70px,90px)_1fr] items-start gap-2.5 font-mono text-xs text-slate-700 max-md:grid-cols-1"
                        >
                          <span
                            v-if="entry.timestamp"
                            class="tabular-nums text-slate-600 whitespace-nowrap"
                          >
                            {{ entry.timestamp }}
                          </span>
                          <span
                            v-if="entry.level"
                            :class="[
                              'self-start rounded-full border border-transparent px-2 py-0.5 text-center text-[0.7rem] font-semibold uppercase tracking-[0.04em] max-md:justify-self-start',
                              logLevelClass(entry.level),
                            ]"
                          >
                            {{ entry.level }}
                          </span>
                          <span class="whitespace-pre-wrap break-words">{{
                            entry.message
                          }}</span>
                        </div>
                      </div>
                      <pre
                        v-else
                        class="m-0 rounded-md border border-[#cfd8dc] bg-slate-100 p-3 text-xs leading-snug text-slate-800 whitespace-pre-wrap break-words"
                        >{{ section.text }}</pre
                      >
                    </div>
                  </div>
                </div>
              </v-expand-transition>
            </v-card>
          </template>

          <div v-if="runHistoryHasMore" class="flex justify-center py-2">
            <v-btn
              variant="outlined"
              color="blue-grey-darken-2"
              :loading="loadingMoreTaskRuns"
              @click="loadMoreRunHistory"
            >
              Load older runs
            </v-btn>
          </div>
        </template>

        <v-card
          v-else
          variant="outlined"
          class="run-entry pa-4 text-medium-emphasis"
        >
          No run history available yet.
        </v-card>
      </div>

      <v-toolbar
        v-show="activePanel === 'details'"
        color="cyan-darken-3"
        rounded="t-lg"
        class="section-toolbar mt-6"
        v-if="showDataConnectionSection"
      >
        <h6 class="text-h6 ml-4">Data connection</h6>
      </v-toolbar>
      <v-data-table
        v-show="activePanel === 'details'"
        v-if="showDataConnectionSection"
        :headers="pipelineHeaders"
        :items="pipelineRows"
        :items-per-page="-1"
        hide-default-header
        hide-default-footer
        density="compact"
        class="elevation-3 rounded-b-lg section-card pipeline-card"
      >
        <template #item="{ item, columns }">
          <tr
            v-if="item.section"
            :class="['pipeline-section', item.sectionClass]"
          >
            <td :colspan="columns.length" class="section-subheading">
              {{ item.label }}
            </td>
          </tr>
          <tr v-else>
            <td class="text-body-2">
              <v-icon
                v-if="item.icon"
                :icon="item.icon"
                size="16"
                class="mr-1"
              />
              <strong>{{ item.name || '–' }}</strong>
            </td>
            <td class="text-body-2">
              <template v-if="item.chips?.length">
                <div class="flex flex-wrap gap-1 py-1">
                  <v-chip
                    v-for="chip in item.chips"
                    :key="chip"
                    size="small"
                    color="blue-grey"
                    variant="tonal"
                    rounded
                  >
                    {{ chip }}
                  </v-chip>
                </div>
              </template>
              <template v-else>
                {{ item.value ?? '–' }}
              </template>
            </td>
          </tr>
        </template>
      </v-data-table>

      <v-toolbar
        v-show="activePanel === 'mappings'"
        color="cyan-darken-3"
        rounded="t-lg"
        class="section-toolbar mt-4"
      >
        <h6 class="text-h6 ml-4">Mappings</h6>
      </v-toolbar>
      <div
        v-show="activePanel === 'mappings'"
        v-if="task?.mappings?.length"
        class="elevation-3 rounded-b-lg section-card swimlanes-card"
      >
        <Swimlanes
          :task="task"
          :show-actions="canEditTask"
          @edit="openEdit = true"
          @delete="openDelete = true"
        />
      </div>
      <v-sheet
        v-show="activePanel === 'mappings'"
        v-else
        class="elevation-1 rounded-b-lg pa-6 text-medium-emphasis section-card"
      >
        No mappings configured for this task.
      </v-sheet>

      <div class="mb-8" />

      <!-- <PayloadTable /> -->
    </div>
  </div>
  <v-container v-else>Loading...</v-container>

  <v-dialog v-model="openEdit" width="80rem" v-if="task">
    <TaskForm
      :old-task="task"
      :orchestration-system="task?.orchestrationSystem"
      @close="openEdit = false"
      @updated="onTaskUpdated"
    />
  </v-dialog>

  <v-dialog v-model="openDelete" width="40rem">
    <DeleteTaskCard
      :task="task!"
      @close="openDelete = false"
      @delete="onDelete"
    />
  </v-dialog>
</template>

<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onBeforeUnmount,
  ref,
  toRaw,
  watch,
} from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Snackbar } from '@/utils/notifications'
import TaskDetailsNavRail, {
  type TaskDetailsPanel,
} from '@/components/Orchestration/TaskDetailsNavRail.vue'
import hs, {
  PermissionAction,
  PermissionResource,
  TaskExpanded,
  TaskRun,
  WORKFLOW_TYPES,
} from '@hydroserver/client'
import router from '@/router/router'
import DeleteTaskCard from '@/components/Orchestration/DeleteTaskCard.vue'
import { formatTimeWithZone } from '@/utils/time'
import {
  buildTaskRunDetailSections,
  getTaskRunMessage,
  getTaskRunStatusText as getRunStatusText,
  getTaskRunRuntimeUrl,
} from '@/utils/orchestration/taskRunDetails'
import { getRunNowPollDecision } from '@/utils/orchestration/runNowPolling'
import TaskStatus from '@/components/Orchestration/TaskStatus.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import {
  mdiBroadcast,
  mdiArrowLeft,
  mdiCalendarClock,
  mdiCardAccountDetails,
  mdiHistory,
  mdiCodeBraces,
  mdiInformationOutline,
  mdiDatabaseSettings,
  mdiClockOutline,
  mdiFormatListNumbered,
  mdiContentCopy,
  mdiPause,
  mdiCogOutline,
  mdiEmailOutline,
  mdiPencil,
  mdiPlay,
  mdiTable,
  mdiDotsHorizontal,
  mdiRenameBoxOutline,
  mdiTrashCanOutline,
  mdiDownload,
} from '@mdi/js'

const TaskForm = defineAsyncComponent(
  () => import('@/components/Orchestration/TaskForm.vue')
)
const Swimlanes = defineAsyncComponent(
  () => import('@/components/Orchestration/Swimlanes.vue')
)

const props = withDefaults(
  defineProps<{
    taskId?: string | null
    runId?: string | null
    embedded?: boolean
  }>(),
  {
    taskId: null,
    runId: null,
    embedded: false,
  }
)

const emit = defineEmits<{
  (e: 'close'): void
}>()

const route = useRoute()
const openEdit = ref(false)
const openDelete = ref(false)
const openRunLogs = ref<Record<string, boolean>>({})
const task = ref<TaskExpanded | null>(null)
const taskRuns = ref<TaskRun[]>([])
const loadingTaskRuns = ref(false)
const loadingMoreTaskRuns = ref(false)
const runHistoryFetchFinished = ref(false)
const runHistoryHasMore = ref(false)
const runHistoryPage = ref(1)
const runNowRequested = ref(false)
const highlightedRunId = ref<string | null>(null)
let highlightTimeoutId: number | null = null
const orchestrationStore = useOrchestrationStore()
const { workspaceTasks } = storeToRefs(orchestrationStore)
const { ensureWorkspaceDatastreams } = orchestrationStore

const { workspaces } = storeToRefs(useWorkspaceStore())
const { setSelectedWorkspaceById } = useWorkspaceStore()
const { checkPermissionsByWorkspaceId } = useWorkspacePermissions()

// When opened from the orchestration slide-over, default to showing run history.
const activePanel = ref<TaskDetailsPanel>(props.embedded ? 'runs' : 'details')

const isInternalOrchestrationType = (value: unknown) =>
  typeof value === 'string' && value.trim().toUpperCase() === 'INTERNAL'

const canRunNow = computed(() => {
  const orchestrationSystem = task.value?.orchestrationSystem as
    | Record<string, unknown>
    | undefined
  const type =
    orchestrationSystem?.type ??
    orchestrationSystem?.orchestrationSystemType ??
    orchestrationSystem?.orchestration_system_type
  return isInternalOrchestrationType(type)
})

const canEditTask = computed(() => {
  const workspaceId = task.value?.workspace?.id
  if (!workspaceId) return false

  return checkPermissionsByWorkspaceId(
    workspaceId,
    PermissionResource.Workspace,
    PermissionAction.Edit
  )
})
const readOnlyTooltip =
  'You have read-only access to this workspace. Ask an editor or owner to make changes.'

const runNowDisabledReason = computed(() => {
  if (!canEditTask.value) return readOnlyTooltip
  if (runNowRequested.value) return 'A run has already been requested.'
  return ''
})

const pauseToggleDisabledReason = computed(() => {
  if (!canEditTask.value) return readOnlyTooltip
  if (!task.value?.schedule) return 'This task has no schedule to pause.'
  return ''
})

const effectiveTaskId = computed(() => {
  const propId = props.taskId
  if (typeof propId === 'string' && propId.trim()) return propId

  const param = route.params.id
  if (typeof param === 'string') return param
  if (Array.isArray(param)) return param[0] ?? ''
  return ''
})

const effectiveRunId = computed(() => {
  const propId = props.runId
  if (typeof propId === 'string' && propId.trim()) return propId

  const queryValue = route.query.runId
  if (typeof queryValue === 'string' && queryValue.trim()) return queryValue
  return null
})

const isTaskExpandedPayload = (value: unknown): value is TaskExpanded => {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<TaskExpanded>
  const hasId = typeof candidate.id === 'string' && candidate.id.length > 0
  const hasWorkspace =
    !!candidate.workspace &&
    typeof candidate.workspace === 'object' &&
    typeof (candidate.workspace as any).id === 'string' &&
    (candidate.workspace as any).id.length > 0
  const hasOrchestrationSystem =
    !!candidate.orchestrationSystem &&
    typeof candidate.orchestrationSystem === 'object' &&
    typeof (candidate.orchestrationSystem as any).id === 'string' &&
    (candidate.orchestrationSystem as any).id.length > 0
  const hasMappings = Array.isArray(candidate.mappings)
  const hasTaskType =
    candidate.type === 'ETL' || candidate.type === 'Aggregation'

  return (
    hasId &&
    hasWorkspace &&
    hasOrchestrationSystem &&
    hasMappings &&
    hasTaskType
  )
}

const routeToAccessDenied = async () => {
  await router.replace({
    name: 'AccessDenied',
    query: {
      from: route.fullPath,
    },
  })
}

const onBack = () => {
  if (props.embedded || props.taskId) {
    emit('close')
    return
  }
  router.push({ name: 'Orchestration' })
}

const runDomId = (runId: string) => `task-run-${runId}`

const shortId = (id: string) => {
  const value = `${id || ''}`
  if (!value) return '–'
  return value.split('-')[0] || value.slice(0, 8)
}

const formatDurationMs = (ms: number) => {
  if (!Number.isFinite(ms) || ms < 0) return '–'
  // Show sub-second precision for short runs (e.g., 0.3s).
  if (ms < 60_000) {
    return `${(ms / 1000).toFixed(2)}s`
  }
  const totalSeconds = Math.floor(ms / 1000)
  const seconds = totalSeconds % 60
  const totalMinutes = Math.floor(totalSeconds / 60)
  const minutes = totalMinutes % 60
  const totalHours = Math.floor(totalMinutes / 60)
  const hours = totalHours % 24
  const days = Math.floor(totalHours / 24)

  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

const runDurationText = (run?: TaskRun | null) => {
  if (!run) return 'Duration –'
  if (run.status === 'RUNNING') return 'Running'
  const start = run.startedAt ? new Date(run.startedAt as any).getTime() : NaN
  const end = run.finishedAt ? new Date(run.finishedAt as any).getTime() : NaN
  if (!Number.isFinite(start) || !Number.isFinite(end)) return 'Duration –'
  return `Duration ${formatDurationMs(end - start)}`
}

const sanitizeFilename = (value: string) =>
  (value || 'task')
    .trim()
    .replace(/[^a-zA-Z0-9._-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')

const downloadTextFile = (filename: string, text: string, mime: string) => {
  if (typeof window === 'undefined') return
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}

const downloadTaskJsonConfiguration = () => {
  if (!task.value) return
  // Export exactly what the app receives for the task (no reshaping), but pretty-printed.
  // `toRaw` avoids Vue proxy serialization edge cases.
  const payload = toRaw(task.value) as any
  const plain = JSON.parse(JSON.stringify(payload))

  const base =
    sanitizeFilename(task.value.name || 'task') ||
    `task-${shortId(task.value.id)}`
  const filename = `${base}-configuration.json`
  downloadTextFile(filename, JSON.stringify(plain, null, 2), 'application/json')
  Snackbar.success('Downloaded JSON configuration.')
}

const runLinkHref = (runId: string) =>
  router.resolve({
    name: 'Orchestration',
    query: {
      workspaceId: task.value?.workspace?.id,
      taskId: effectiveTaskId.value,
      runId,
    },
  }).href

const runLinkUrl = (runId: string) => {
  const href = runLinkHref(runId)
  if (typeof window === 'undefined') return href
  return new URL(href, window.location.origin).toString()
}

const scrollToRunAnchor = async (runId: string) => {
  const id = runDomId(runId)
  // Transitions can delay DOM insertion; retry a few frames.
  for (let attempt = 0; attempt < 12; attempt += 1) {
    await nextTick()
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      highlightedRunId.value = runId
      if (highlightTimeoutId) window.clearTimeout(highlightTimeoutId)
      highlightTimeoutId = window.setTimeout(() => {
        highlightedRunId.value = null
        highlightTimeoutId = null
      }, 2500)
      return
    }
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
  }
}

const showRunHistoryLoading = computed(() => {
  if (activePanel.value !== 'runs') return false
  if (loadingTaskRuns.value) return true
  // If the user deep-linked to a runId, avoid flashing the empty-state while the first fetch is pending.
  if (effectiveRunId.value && !runHistoryFetchFinished.value) return true
  // If the user opened the run history but we haven't finished the first fetch, show loading until we know.
  if (!runHistoryFetchFinished.value && runHistoryRows.value.length === 0)
    return true
  return false
})

const getRuntimeUrl = (run?: TaskRun | null) => {
  return getTaskRunRuntimeUrl(run)
}

const resolveRuntimeUrlFromTask = (run?: TaskRun | null) => {
  const sourceUri = (task.value as any)?.dataConnection?.extractor?.settings
    ?.sourceUri
  if (!sourceUri || typeof sourceUri !== 'string') return null

  const placeholders =
    ((task.value as any)?.dataConnection?.extractor?.settings
      ?.placeholderVariables as any[]) || []

  const values: Record<string, string> = {}
  for (const placeholder of placeholders) {
    const name = placeholder?.name
    if (!name) continue

    if (placeholder?.type === 'perTask') {
      const value = (task.value as any)?.extractorVariables?.[name]
      if (value !== undefined && value !== null && value !== '') {
        values[name] = String(value)
      }
      continue
    }

    if (placeholder?.type !== 'runTime') continue

    const runTimeValue =
      placeholder?.runTimeValue ?? placeholder?.run_time_value
    if (runTimeValue === 'jobExecutionTime') {
      const startedAt = run?.startedAt ?? task.value?.latestRun?.startedAt
      if (startedAt) values[name] = String(startedAt)
      continue
    }
  }

  return sourceUri.replace(
    /\{([^}]+)\}/g,
    (_, key) => values[key] ?? `{${key}}`
  )
}

const logLevelClass = (level?: string) => {
  const value = (level || '').toLowerCase()
  if (
    value.includes('error') ||
    value.includes('critical') ||
    value.includes('fail')
  ) {
    return 'bg-rose-50 text-rose-700 border-rose-200'
  }
  if (value.includes('warn') || value.includes('skip')) {
    return 'bg-amber-50 text-amber-700 border-amber-200'
  }
  if (value.includes('success') || value.includes('ok')) {
    return 'bg-emerald-50 text-emerald-700 border-emerald-200'
  }
  if (value.includes('debug')) {
    return 'bg-slate-100 text-slate-600 border-slate-200'
  }
  return 'bg-sky-50 text-sky-700 border-sky-200'
}

const buildLogSections = (run?: TaskRun | null) =>
  buildTaskRunDetailSections(run)

const toggleRunLogs = (runId: string) => {
  openRunLogs.value[runId] = !openRunLogs.value[runId]
}

const copyToClipboard = async (value?: string | null) => {
  if (!value) return
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(value)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = value
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      textarea.remove()
    }
    Snackbar.success('Copied to clipboard.')
  } catch (error) {
    Snackbar.error('Unable to copy to clipboard.')
  }
}

const scheduleString = computed(() => {
  const schedule = task.value?.schedule
  if (!schedule) return '–'

  const { interval, intervalPeriod, crontab, startTime } = schedule
  let description: string | null = null

  if (interval && intervalPeriod) {
    description = `Every ${interval} ${intervalPeriod}`
  } else if (crontab) {
    description = `Crontab: ${crontab}`
  }

  if (!description) return '–'
  if (startTime) description += ` starting ${formatTimeWithZone(startTime)}`

  return description
})

const taskTypeLabel = computed(() => {
  return (
    (task.value as any)?.type ??
    (task.value as any)?.taskType ??
    (task.value as any)?.task_type ??
    '–'
  )
})

const isAggregationTask = computed(() => {
  return `${taskTypeLabel.value}`.trim().toUpperCase() === 'AGGREGATION'
})

const taskHeaders = [
  { key: 'label', title: 'Label' },
  { key: 'value', title: 'Value' },
]

const pipelineHeaders = [
  { key: 'name', title: 'Field' },
  { key: 'value', title: 'Value' },
]

function summarize(obj: any): string {
  if (!obj || typeof obj !== 'object') return '–'
  const keys = Object.keys(obj ?? {}).filter(
    (k) => obj[k] !== null && obj[k] !== undefined && obj[k] !== ''
  )
  return keys.length ? keys.join(', ') : '–'
}

const taskInformation = computed(() => {
  if (!task.value) return []

  return [
    {
      icon: mdiCardAccountDetails,
      label: 'ID',
      value: task.value.id,
    },
    {
      icon: mdiInformationOutline,
      label: 'Task type',
      value: taskTypeLabel.value,
    },
    {
      icon: mdiCalendarClock,
      label: 'Schedule',
      value: scheduleString,
    },
    // Removed duplicate Last run / Next run / Status from this summary card.
  ].filter(Boolean)
})

const taskTemplateInformation = computed(() => {
  const dataConnection: any = task.value?.dataConnection
  const taskType = (task.value as any)?.type ?? dataConnection?.type ?? '–'
  const notificationRecipientEmails = Array.isArray(
    dataConnection?.notificationRecipientEmails
  )
    ? dataConnection.notificationRecipientEmails
    : []

  const rows: any[] = [
    {
      icon: mdiInformationOutline,
      label: 'Template',
      name: 'Workflow type',
      value: taskType,
    },
  ]

  if (!dataConnection) return rows

  return [
    ...rows,
    {
      icon: mdiCardAccountDetails,
      label: 'Data connection ID',
      name: 'Data connection ID',
      value: dataConnection.id,
    },
    {
      icon: mdiRenameBoxOutline,
      label: 'Data connection',
      name: 'Data connection name',
      value: dataConnection.name,
    },
    {
      icon: mdiEmailOutline,
      label: 'Data connection recipients',
      name: 'Notification recipients',
      value: notificationRecipientEmails.length ? null : '–',
      chips: notificationRecipientEmails,
    },
  ].filter(
    (row) =>
      (row.value !== undefined && row.value !== null) || 'chips' in row
  )
})

const extractorInformation = computed(() => {
  const extractor: any = task.value?.dataConnection?.extractor
  if (!extractor) return []

  const placeholders: Array<{
    name: string
    type?: string
    runTimeValue?: string
  }> = extractor.settings?.placeholderVariables ?? []
  const perTaskList = placeholders
    .filter((p) => p.type === 'perTask')
    .map((p) => `${p.name}: ${task.value?.extractorVariables?.[p.name] ?? '–'}`)
  const runtimeList = placeholders
    .filter((p) => p.type === 'runTime')
    .map((p) => `${p.name}: ${p.runTimeValue ?? '–'}`)

  return [
    {
      icon: mdiCogOutline,
      label: 'Extractor',
      name: 'Type',
      value: extractor.type ?? '–',
    },
    {
      icon: mdiCodeBraces,
      label: 'Extractor',
      name: 'Source URL',
      value: extractor.settings?.sourceUri ?? '–',
    },
    {
      icon: mdiInformationOutline,
      label: 'Extractor',
      name: 'Per-task variables',
      value: perTaskList.length ? null : '–',
      list: perTaskList,
    },
    {
      icon: mdiInformationOutline,
      label: 'Extractor',
      name: 'Runtime variables',
      value: runtimeList.length ? null : '–',
      list: runtimeList,
    },
  ].filter((row) => row.value !== undefined && row.value !== null)
})

const extractorVariables = computed(() => {
  const extractor: any = task.value?.dataConnection?.extractor
  if (!extractor) return []
  const placeholders: Array<{
    name: string
    type?: string
    runTimeValue?: any
  }> = extractor.settings?.placeholderVariables ?? []

  return placeholders.map((p) => ({
    type: p.type ?? '–',
    name: p.name,
    value:
      p.type === 'perTask'
        ? task.value?.extractorVariables?.[p.name] ?? '–'
        : p.runTimeValue ?? '–',
  }))
})

const taskTableRows = computed(() => {
  const baseRows = taskInformation.value
  const rows: any[] = [...baseRows]

  if (orchestrationSystemInformation.value.length) {
    rows.push({
      section: true,
      label: 'Linked orchestration system',
    })
    rows.push(
      ...orchestrationSystemInformation.value.map((r) => ({
        ...r,
        label: r.label,
      }))
    )
  }

  return rows
})

const pipelineRows = computed(() => {
  const rows: any[] = []
  const pushSection = (label: string, sectionClass: string) =>
    rows.push({ section: true, label, sectionClass })
  const pushInfo = (items: any[], sectionClass: string) =>
    items.forEach((i) =>
      rows.push({
        label: i.label,
        name: i.name ?? '–',
        value: i.value ?? '–',
        icon: i.icon,
        sectionClass,
      })
    )

  if (taskTemplateInformation.value.length) {
    // pushSection('General', 'template-subheading')
    pushInfo(taskTemplateInformation.value, 'template-subheading')
  }

  if (extractorInformation.value.length) {
    pushSection('Extractor', 'extractor-subheading')
    pushInfo(extractorInformation.value, 'extractor-subheading')
  }
  if (extractorVariables.value.length) {
    pushSection('Extractor variables', 'extractor-subheading')
    extractorVariables.value.forEach((v) =>
      rows.push({
        label: v.type,
        name: v.name,
        value: v.value,
        sectionClass: 'extractor-subheading',
      })
    )
  }

  if (transformerInformation.value.length) {
    pushSection('Transformer', 'transformer-subheading')
    pushInfo(transformerInformation.value, 'transformer-subheading')
  }

  if (loaderInformation.value.length) {
    pushSection('Loader', 'loader-subheading')
    pushInfo(loaderInformation.value, 'loader-subheading')
  }

  return rows
})

const showDataConnectionSection = computed(() => {
  return !isAggregationTask.value && pipelineRows.value.length > 0
})

const transformerInformation = computed(() => {
  const transformer: any = task.value?.dataConnection?.transformer
  if (!transformer) return []

  const rows: any[] = [
    {
      icon: mdiCogOutline,
      label: 'Transformer',
      name: 'Type',
      value: transformer.type ?? '–',
    },
  ]

  const settings: any = transformer.settings ?? {}
  if (transformer.type === 'JSON') {
    rows.push(
      {
        icon: mdiCodeBraces,
        label: 'Transformer',
        name: 'JMESPath',
        value: settings.JMESPath ?? '–',
      },
      {
        icon: mdiClockOutline,
        label: 'Transformer',
        name: 'Timestamp key',
        value: settings.timestamp?.key ?? '–',
      },
      {
        icon: mdiCalendarClock,
        label: 'Transformer',
        name: 'Timestamp format',
        value: settings.timestamp?.format ?? '–',
      },
      {
        icon: mdiClockOutline,
        label: 'Transformer',
        name: 'Timezone mode',
        value: settings.timestamp?.timezoneMode ?? '–',
      }
    )
  } else if (transformer.type === 'CSV') {
    rows.push(
      {
        icon: mdiFormatListNumbered,
        label: 'Transformer',
        name: 'Identifier type',
        value: settings.identifierType ?? '–',
      },
      {
        icon: mdiTable,
        label: 'Transformer',
        name: 'Header row',
        value: settings.headerRow ?? '–',
      },
      {
        icon: mdiTable,
        label: 'Transformer',
        name: 'Data start row',
        value: settings.dataStartRow ?? '–',
      },
      {
        icon: mdiDotsHorizontal,
        label: 'Transformer',
        name: 'Delimiter',
        value: settings.delimiter ?? '–',
      },
      {
        icon: mdiClockOutline,
        label: 'Transformer',
        name: 'Timestamp key',
        value: settings.timestamp?.key ?? '–',
      },
      {
        icon: mdiCalendarClock,
        label: 'Transformer',
        name: 'Timestamp format',
        value: settings.timestamp?.format ?? '–',
      },
      {
        icon: mdiClockOutline,
        label: 'Transformer',
        name: 'Timezone mode',
        value: settings.timestamp?.timezoneMode ?? '–',
      }
    )
  } else {
    rows.push({
      icon: mdiDatabaseSettings,
      label: 'Transformer',
      name: 'Settings',
      value: summarize(settings),
    })
  }

  return rows.filter((row) => row.value !== undefined && row.value !== null)
})

const loaderInformation = computed(() => {
  const loader: any = task.value?.dataConnection?.loader
  if (!loader) return []

  return [
    {
      icon: mdiCogOutline,
      label: 'Loader',
      name: 'Type',
      value: loader.type ?? '–',
    },
    // {
    //   icon: mdiDatabaseSettings,
    //   label: 'Loader',
    //   name: 'Settings',
    //   value: summarize(loader.settings),
    // },
  ].filter((row) => row.value !== undefined && row.value !== null)
})

const orchestrationSystemInformation = computed(() => {
  if (!task.value) return []

  return [
    {
      icon: mdiRenameBoxOutline,
      label: 'Name',
      value: task.value.orchestrationSystem.name,
    },
    {
      icon: mdiBroadcast,
      label: 'Type',
      value:
        WORKFLOW_TYPES.find(
          (t) => t.value === task.value?.orchestrationSystem.type
        )?.title ?? task.value.orchestrationSystem.type,
    },
  ].filter(Boolean)
})

const runHistoryRows = computed(() => {
  const seen = new Set<string>()

  return taskRuns.value
    .filter((run) => {
      if (!run?.id) return false
      if (seen.has(run.id)) return false
      seen.add(run.id)
      return true
    })
    .map((run) => ({
      id: run.id,
      startedAt: formatTimeWithZone(run.startedAt),
      finishedAt: formatTimeWithZone(run.finishedAt),
      message: getTaskRunMessage(run),
      runtimeUrl: getRuntimeUrl(run) ?? resolveRuntimeUrlFromTask(run),
      raw: run,
    }))
})

const RUN_HISTORY_PAGE_SIZE = 15
const RUN_POLL_INTERVAL_MS = 4000
const RUN_POLL_MAX_ATTEMPTS = 150
let runNowPollTimeoutId: number | null = null
let runNowPollSessionId = 0

const clearRunNowPollingTimeout = () => {
  if (runNowPollTimeoutId != null) {
    window.clearTimeout(runNowPollTimeoutId)
    runNowPollTimeoutId = null
  }
}

const stopRunNowPolling = () => {
  clearRunNowPollingTimeout()
  runNowPollSessionId += 1
}

const upsertTaskRun = (run: TaskRun) => {
  const next = [...taskRuns.value]
  const index = next.findIndex((item) => item.id === run.id)
  if (index !== -1) next[index] = run
  else next.unshift(run)
  taskRuns.value = next
}

const syncLatestRun = (run: TaskRun) => {
  if (!task.value) return
  task.value = {
    ...task.value,
    latestRun: run,
  }
  upsertWorkspaceTask(task.value)
}

const refreshTaskAfterRunCompletion = async (taskId: string, runId: string) => {
  try {
    const updated = (await hs.tasks.getItem(taskId, {
      expand_related: true,
    })) as unknown as TaskExpanded

    if (updated) {
      task.value = updated
      upsertWorkspaceTask(updated)
    }

    if (activePanel.value === 'runs') {
      await fetchTaskRuns({ page: 1, background: true })
      if (effectiveRunId.value === runId) {
        await openRunHistoryAndScroll(runId)
      }
    }
  } catch (error) {
    console.error('Error refreshing task after run completion', error)
  }
}

const publishQueuedRunUpdate = (updatedTask: TaskExpanded, observedRun: TaskRun) => {
  task.value = updatedTask
  upsertWorkspaceTask(updatedTask)
  upsertTaskRun(observedRun)
}

const scheduleRunNowPoll = (
  taskId: string,
  requestedRunId: string | null,
  previousRunId: string | null,
  attempt = 0,
  hasPublishedQueuedRun = false,
  pollSessionId = runNowPollSessionId
) => {
  clearRunNowPollingTimeout()
  if (attempt > RUN_POLL_MAX_ATTEMPTS) {
    runNowRequested.value = false
    return
  }

  runNowPollTimeoutId = window.setTimeout(async () => {
    if (pollSessionId !== runNowPollSessionId) return

    try {
      if (requestedRunId) {
        const runResponse = await hs.tasks.getTaskRun(taskId, requestedRunId)
        const updatedRun = runResponse.ok ? ((runResponse.data as TaskRun) ?? null) : null
        const decision = getRunNowPollDecision({
          requestedRunId,
          observedRunId: updatedRun?.id ?? null,
          observedStatus: updatedRun?.status,
          hasPublishedQueuedRun,
        })

        if (pollSessionId !== runNowPollSessionId) return

        if (decision.publishTerminalRun && updatedRun?.id) {
          runNowRequested.value = false
          stopRunNowPolling()
          await refreshTaskAfterRunCompletion(taskId, updatedRun.id)
          return
        }

        hasPublishedQueuedRun = decision.hasPublishedQueuedRun
      } else {
        const updated = (await hs.tasks.getItem(taskId, {
          expand_related: true,
        })) as unknown as TaskExpanded

        if (pollSessionId !== runNowPollSessionId) return

        if (updated?.latestRun) {
          const decision = getRunNowPollDecision({
            previousRunId,
            observedRunId: updated.latestRun.id ?? null,
            observedStatus: updated.latestRun.status,
            hasPublishedQueuedRun,
          })

          if (decision.publishQueuedRun) {
            publishQueuedRunUpdate(updated, updated.latestRun)
          }

          if (decision.publishTerminalRun && updated.latestRun.id) {
            runNowRequested.value = false
            stopRunNowPolling()
            await refreshTaskAfterRunCompletion(taskId, updated.latestRun.id)
            return
          }

          hasPublishedQueuedRun = decision.hasPublishedQueuedRun
        }
      }
    } catch (error) {
      console.error('Error polling task after run-now', error)
    }

    if (pollSessionId !== runNowPollSessionId) return

    scheduleRunNowPoll(
      taskId,
      requestedRunId,
      previousRunId,
      attempt + 1,
      hasPublishedQueuedRun,
      pollSessionId
    )
  }, RUN_POLL_INTERVAL_MS)
}

const runTaskNow = async () => {
  if (!task.value) return
  if (!canEditTask.value) return
  if (!canRunNow.value) return
  if (runNowRequested.value) return

  runNowRequested.value = true
  try {
    const taskId = task.value.id
    const previousRunId = task.value.latestRun?.id ?? null
    stopRunNowPolling()
    const pollSessionId = runNowPollSessionId
    const response = await hs.tasks.runTask(taskId)
    if (!response.ok) {
      throw new Error(response.message || 'Unable to run task now.')
    }
    const requestedRun = response.ok ? (response.data as TaskRun | null) : null
    if (requestedRun?.id) {
      syncLatestRun(requestedRun)
      upsertTaskRun(requestedRun)
    }
    Snackbar.success('Run requested.')
    scheduleRunNowPoll(
      taskId,
      requestedRun?.id ?? null,
      previousRunId,
      0,
      !!requestedRun?.id,
      pollSessionId
    )
  } catch (error: any) {
    runNowRequested.value = false
    Snackbar.error(error?.message || 'Unable to run task now.')
    console.error('Error running task now', error)
  }
}

async function togglePaused(
  task: Partial<TaskExpanded> & Pick<TaskExpanded, 'id'>
) {
  if (!canEditTask.value) return
  if (!task.schedule) return
  task.schedule.paused = !task.schedule.paused
  await hs.tasks.update(task)
}

function upsertWorkspaceTask(t: TaskExpanded | null) {
  if (!t) return
  const next = [...workspaceTasks.value]
  const index = next.findIndex((p) => p.id === t.id)
  if (index !== -1) next[index] = t
  else next.push(t)
  workspaceTasks.value = next
}

async function ensureMappingDatastreams() {
  const workspaceId = task.value?.workspace?.id
  if (!workspaceId) return
  try {
    await ensureWorkspaceDatastreams(workspaceId)
  } catch (error) {
    console.error('Error fetching workspace datastreams', error)
  }
}

const onDelete = async () => {
  if (!canEditTask.value) return
  try {
    await hs.tasks.delete(task.value!.id)
    await router.push({ name: 'Orchestration' })
    Snackbar.success('Task deleted.')
  } catch (error: any) {
    Snackbar.error(error.message)
    console.error('Error deleting task', error)
  }
}

const fetchTaskRuns = async ({
  page = 1,
  append = false,
  background = false,
}: {
  page?: number
  append?: boolean
  background?: boolean
} = {}) => {
  if (!task.value) return

  if (append) {
    loadingMoreTaskRuns.value = true
  } else if (!background) {
    loadingTaskRuns.value = true
    runHistoryFetchFinished.value = false
  }
  try {
    const response = await hs.tasks.getTaskRuns(task.value.id, {
      order_by: ['-startedAt'],
      page,
      page_size: RUN_HISTORY_PAGE_SIZE,
    } as any)
    const nextRuns = (response.data as TaskRun[]) || []
    taskRuns.value = append ? [...taskRuns.value, ...nextRuns] : nextRuns
    runHistoryPage.value = page
    runHistoryHasMore.value = nextRuns.length === RUN_HISTORY_PAGE_SIZE
  } catch (error: any) {
    Snackbar.error(error.message || 'Unable to fetch run history.')
    console.error('Error fetching task runs', error)
  } finally {
    if (append) {
      loadingMoreTaskRuns.value = false
    } else if (!background) {
      loadingTaskRuns.value = false
      runHistoryFetchFinished.value = true
    } else {
      runHistoryFetchFinished.value = true
    }
  }
}

const refreshRunHistory = async () => {
  if (!task.value) return
  await fetchTaskRuns({ page: 1 })
  if (effectiveRunId.value) {
    await openRunHistoryAndScroll(effectiveRunId.value)
  }
}

const loadMoreRunHistory = async () => {
  if (
    !task.value ||
    loadingTaskRuns.value ||
    loadingMoreTaskRuns.value ||
    !runHistoryHasMore.value
  ) {
    return
  }
  await fetchTaskRuns({ page: runHistoryPage.value + 1, append: true })
}

const openRunHistoryAndScroll = async (runId: string) => {
  if (!runId) return
  if (
    (!runHistoryFetchFinished.value || !taskRuns.value.length) &&
    !loadingTaskRuns.value
  ) {
    await fetchTaskRuns({ page: 1 })
  }

  while (
    !taskRuns.value.some((run) => run.id === runId) &&
    runHistoryHasMore.value &&
    !loadingMoreTaskRuns.value
  ) {
    await loadMoreRunHistory()
  }

  await scrollToRunAnchor(runId)
}

const fetchData = async () => {
  if (!effectiveTaskId.value) return

  let taskResponse: Awaited<ReturnType<typeof hs.tasks.get>>
  try {
    taskResponse = await hs.tasks.get(effectiveTaskId.value, {
      expand_related: true,
    })
  } catch (error: unknown) {
    Snackbar.error('Unable to fetch task details.')
    console.error('Error fetching task details', error)
    return
  }

  if (taskResponse.status === 403) {
    await routeToAccessDenied()
    return
  }

  if (!taskResponse.ok) {
    Snackbar.error(taskResponse.message || 'Unable to fetch task details.')
    console.error('Error fetching task details', taskResponse)
    return
  }

  if (!isTaskExpandedPayload(taskResponse.data)) {
    Snackbar.error('Unable to fetch task details.')
    console.error('Unexpected task details payload', taskResponse)
    return
  }

  const fetchedTask = taskResponse.data

  if (
    fetchedTask.workspace?.id &&
    workspaces.value.length &&
    !workspaces.value.some(
      (workspace) => workspace.id === fetchedTask.workspace.id
    )
  ) {
    await routeToAccessDenied()
    return
  }

  task.value = fetchedTask

  upsertWorkspaceTask(task.value)
  if (activePanel.value === 'runs') {
    if (effectiveRunId.value) {
      await fetchTaskRuns({ page: 1 })
    } else {
      void fetchTaskRuns({ page: 1 })
    }
  }
  if (activePanel.value === 'mappings') {
    void ensureMappingDatastreams()
  }

  // If the user deep-linked to a task/run in a different workspace, select it so the list matches.
  if (task.value?.workspace?.id && workspaces.value.length) {
    setSelectedWorkspaceById(task.value.workspace.id)
  }

  if (effectiveRunId.value) {
    await openRunHistoryAndScroll(effectiveRunId.value)
  }
}

const onTaskUpdated = async (updated: TaskExpanded) => {
  // Keep UI responsive with the returned task, then refresh to ensure relations are expanded
  task.value = updated
  upsertWorkspaceTask(updated)
  await fetchData()
  openEdit.value = false
}

watch(
  effectiveTaskId,
  async (newId, oldId) => {
    if (!newId) return
    if (newId === oldId) return

    // Reset task-specific UI state when switching tasks without unmounting.
    stopRunNowPolling()
    openRunLogs.value = {}
    taskRuns.value = []
    runHistoryFetchFinished.value = false
    runHistoryHasMore.value = false
    runHistoryPage.value = 1
    loadingMoreTaskRuns.value = false
    runNowRequested.value = false
    if (props.embedded && !effectiveRunId.value) {
      activePanel.value = 'runs'
    } else if (!effectiveRunId.value) {
      activePanel.value = 'details'
    }

    await fetchData()
  },
  { immediate: true }
)

watch(
  workspaces,
  (list) => {
    if (!list?.length) return
    if (task.value?.workspace?.id) {
      if (
        !list.some((workspace) => workspace.id === task.value?.workspace?.id)
      ) {
        void routeToAccessDenied()
        return
      }
      setSelectedWorkspaceById(task.value.workspace.id)
    }
  },
  { immediate: true }
)

watch(
  effectiveRunId,
  async (runId) => {
    if (!runId) return
    // Ensure the page loads in run history mode when deep-linked.
    activePanel.value = 'runs'
    if (!task.value) return
    await openRunHistoryAndScroll(runId)
  },
  { immediate: true }
)

watch(
  activePanel,
  async (panel) => {
    if (panel === 'runs') {
      if (
        task.value &&
        !loadingTaskRuns.value &&
        (!runHistoryFetchFinished.value || taskRuns.value.length === 0)
      ) {
        await fetchTaskRuns({ page: 1 })
      }
      return
    }
    if (panel === 'mappings') {
      await ensureMappingDatastreams()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  stopRunNowPolling()
  if (highlightTimeoutId) window.clearTimeout(highlightTimeoutId)
  highlightTimeoutId = null
})
</script>

<style scoped>
.task-details-shell {
  display: flex;
  width: 100%;
  min-height: 100%;
  height: 100%;
  overflow: hidden;
}

.task-details-content {
  flex: 1;
  min-width: 0;
  width: 100%;
  padding: 0 16px;
  box-sizing: border-box;
  height: 100%;
  overflow-y: auto;
}
.section-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
}
.section-toolbar {
  color: white;
}
.variable-list {
  display: grid;
  row-gap: 4px;
}
.section-subheading {
  font-weight: 700;
  padding: 6px 12px;
  background: #eceff1;
  color: #263238;
  border: 1px solid #cfd8dc;
}
.section-card :deep(.v-data-table__wrapper) {
  padding: 10px 12px;
}
.section-card :deep(.v-table__wrapper) {
  background: transparent;
}
.section-card :deep(tr) {
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}
.section-card :deep(td) {
  padding: 10px 12px;
}
.swimlanes-card {
  padding: 16px 18px;
}
.swimlanes-card :deep(.swimlanes) {
  margin-bottom: 0;
}

.run-entry {
  border-radius: 14px;
  overflow: hidden;
  background: #ffffff;
  border-color: #e2e8f0;
  box-shadow: 0 1px 0 rgba(2, 6, 23, 0.04);
}

.run-entry-top {
  display: flex;
  /* Allow the summary message to grow vertically without awkward centering. */
  align-items: flex-start;
  justify-content: flex-start;
  gap: 16px;
  padding: 14px 16px 10px;
}

.run-entry-top-left {
  display: flex;
  align-items: flex-start;
  flex: 0 0 auto;
  /* No background/border wrapper around the status. */
  padding: 0;
  border-radius: 0;
  background: transparent;
  border: none;
}

.run-entry-idrow {
  display: flex;
  align-items: center;
  gap: 10px;
}

.run-entry-runid-top {
  font-size: 0.75rem;
  font-weight: 700;
  color: #0e7490; /* cyan-700 */
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}

.run-entry-runid-right {
  flex: 0 0 auto;
  margin-left: auto;
  padding-top: 2px; /* visually aligns with summary first line */
}

.run-entry-status {
  flex: 0 0 auto;
  font-size: 0.9rem;
  font-weight: 900;
  --v-chip-height: 32px;
  letter-spacing: 0.01em;
}

.run-entry-status.v-chip {
  /* Apply visuals on the actual v-chip root to avoid radius mismatch with Vuetify internals. */
  border: 1px solid rgba(2, 6, 23, 0.12);
  box-shadow: 0 1px 0 rgba(2, 6, 23, 0.04), 0 4px 12px rgba(2, 6, 23, 0.1);
  border-radius: 9999px;
  overflow: hidden;
}

.run-entry-status :deep(.v-chip__underlay),
.run-entry-status :deep(.v-chip__overlay) {
  /* Ensure the colored underlay + interaction overlay match the chip radius exactly. */
  border-radius: inherit;
}

.run-entry-summary {
  flex: 1 1 auto;
  min-width: 0;
  font-weight: 600;
  color: #475569;
  font-size: 0.9rem;
  line-height: 1.3;
  word-break: break-word;
  white-space: normal;
}

.run-entry-meta {
  background: #ffffff;
  padding: 10px 16px 12px;
  border-top: 1px solid #f1f5f9;
}

.run-entry-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.run-entry-times-inline {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
  color: #475569;
  font-size: 0.9rem;
}

.run-entry-meta-label {
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  margin-right: 6px;
  font-size: 0.68rem;
  white-space: nowrap;
}

.run-entry-runid {
  font-weight: 800;
  color: #0f172a;
  letter-spacing: 0.02em;
}

.run-entry-duration {
  font-size: 0.8rem;
  font-weight: 700;
  color: #334155;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 2px 10px;
  white-space: nowrap;
}

.run-entry-sep {
  color: #cbd5e1;
}

.run-entry-detail-row {
  display: grid;
  /* Give labels enough room so they don't collide with long URLs. */
  grid-template-columns: minmax(160px, 190px) 1fr;
  gap: 10px;
  align-items: start;
}

.run-entry-detail-row-inline {
  grid-template-columns: 1fr;
}

.run-entry-detail-inline {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
}

.run-entry-detail-label {
  font-size: 0.7rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #64748b;
  white-space: nowrap;
  padding-top: 2px;
}

.run-entry-detail-value {
  display: flex;
  justify-content: flex-start;
  min-width: 0;
}

.run-entry-detail-linkwrap {
  max-width: 100%;
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  align-items: flex-start;
  gap: 8px;
}

.run-entry-detail-linkwrap a {
  min-width: 0;
  text-align: left;
}

.run-entry-footer {
  background: #ffffff;
  padding: 10px 16px 12px;
  border-top: 1px solid #f1f5f9;
}

@media (max-width: 768px) {
  .run-entry-detail-row {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .run-entry-detail-label {
    margin-bottom: 4px;
  }
}

.run-highlight {
  border-radius: 14px;
  animation: runHighlightPulse 2.5s ease-out;
}

@keyframes runHighlightPulse {
  0% {
    background: rgba(255, 235, 59, 0.35);
  }
  100% {
    background: #ffffff;
  }
}
</style>
