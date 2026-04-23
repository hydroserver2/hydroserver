<template>
  <div v-if="task" class="task-details">
    <!-- Header -->
    <header class="task-details-header">
      <button
        v-if="backLabel"
        type="button"
        class="task-details-back"
        @click="onBack"
      >
        <v-icon :icon="mdiArrowLeft" size="16" />
        <span>{{ backLabel }}</span>
      </button>

      <div class="task-details-header-row">
        <div class="task-details-title-group">
          <h2 class="task-details-title">{{ task.name }}</h2>
          <TaskStatus
            :status="statusName"
            :paused="!task.schedule?.enabled"
          />
          <span v-if="schedulePill" class="schedule-pill">
            {{ schedulePill }}
          </span>
        </div>

        <div class="task-details-actions">
          <v-tooltip
            location="top"
            :disabled="!pauseToggleDisabledReason"
          >
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <button
                  type="button"
                  class="header-btn"
                  :disabled="!!pauseToggleDisabledReason"
                  @click.stop="togglePaused(task)"
                >
                  <v-icon
                    :icon="task.schedule?.enabled ? mdiPause : mdiPlay"
                    size="14"
                  />
                  <span>{{
                    task.schedule?.enabled ? 'Pause' : 'Resume'
                  }}</span>
                </button>
              </span>
            </template>
            <span>{{ pauseToggleDisabledReason }}</span>
          </v-tooltip>

          <v-tooltip location="top" :disabled="canEditTask">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <button
                  type="button"
                  class="header-btn"
                  :disabled="!canEditTask"
                  @click="openEdit = true"
                >
                  <v-icon :icon="mdiPencil" size="14" />
                  <span>Edit</span>
                </button>
              </span>
            </template>
            <span>{{ readOnlyTooltip }}</span>
          </v-tooltip>

          <v-tooltip location="top" :disabled="canEditTask">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <button
                  type="button"
                  class="header-btn header-btn--danger"
                  :disabled="!canEditTask"
                  @click="openDelete = true"
                >
                  <v-icon :icon="mdiTrashCanOutline" size="14" />
                  <span>Delete</span>
                </button>
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
                <button
                  type="button"
                  class="header-btn header-btn--run"
                  :disabled="!canEditTask || runNowRequested"
                  @click="runTaskNow"
                >
                  <v-icon
                    :icon="runNowRequested ? mdiCheck : mdiPlay"
                    size="14"
                  />
                  <span>{{
                    runNowRequested ? 'Run requested' : 'Run now'
                  }}</span>
                </button>
              </span>
            </template>
            <span>{{ runNowDisabledReason }}</span>
          </v-tooltip>
        </div>
      </div>

      <!-- Tabs -->
      <div class="task-details-tabs">
        <button
          type="button"
          class="task-details-tab"
          :class="{ 'task-details-tab--active': activePanel === 'runs' }"
          @click="activePanel = 'runs'"
        >
          Run history
        </button>
        <button
          type="button"
          class="task-details-tab"
          :class="{ 'task-details-tab--active': activePanel === 'mappings' }"
          @click="activePanel = 'mappings'"
        >
          Mappings
        </button>
      </div>
    </header>

    <!-- Body -->
    <div class="task-details-body">
      <!-- Run history -->
      <div
        v-show="activePanel === 'runs'"
        class="task-details-panel"
      >
        <template v-if="showRunHistoryLoading">
          <div class="run-loading">
            <v-progress-circular
              indeterminate
              size="20"
              width="2"
              color="blue-grey-darken-1"
            />
            <span>Loading run history…</span>
          </div>
        </template>

        <template v-else-if="runHistoryRows.length">
          <template v-for="run in runHistoryRows" :key="run.id">
            <div
              :id="runDomId(run.id)"
              class="run-entry"
              :class="{ 'run-highlight': highlightedRunId === run.id }"
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
                <div class="run-entry-runid-right">
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
                  size="small"
                  @click="toggleRunLogs(run.id)"
                >
                  {{
                    openRunLogs[run.id]
                      ? 'Hide run details'
                      : 'View run details'
                  }}
                </v-btn>
              </div>

              <v-expand-transition>
                <div
                  v-if="openRunLogs[run.id]"
                  class="run-entry-details"
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

                    <div class="run-entry-detail-row run-entry-detail-row-inline">
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
                      <div class="run-section-label">
                        {{ section.title }}
                      </div>
                      <div
                        v-if="section.type === 'lines'"
                        class="grid gap-1.5"
                      >
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
            </div>
          </template>

          <div v-if="runHistoryHasMore" class="flex justify-center py-2">
            <v-btn
              variant="outlined"
              color="blue-grey-darken-2"
              :loading="loadingMoreTaskRuns"
              size="small"
              @click="loadMoreRunHistory"
            >
              Load older runs
            </v-btn>
          </div>

          <div class="run-entry-refresh">
            <v-btn
              variant="text"
              :prepend-icon="mdiHistory"
              size="small"
              class="text-none"
              @click="refreshRunHistory"
            >
              Refresh history
            </v-btn>
          </div>
        </template>

        <div v-else class="run-empty">No run history available yet.</div>
      </div>

      <!-- Mappings -->
      <div
        v-show="activePanel === 'mappings'"
        class="task-details-panel"
      >
        <Swimlanes v-if="task?.mappings?.length" :task="task" />
        <div v-else class="mappings-empty">
          No mappings configured for this task.
        </div>
      </div>
    </div>
  </div>
  <div v-else class="task-details-loading">Loading…</div>

  <v-dialog v-model="openEdit" width="80rem" v-if="task">
    <TaskForm
      :old-task="task"
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
  watch,
} from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Snackbar } from '@/utils/notifications'
import hs, {
  PermissionAction,
  PermissionResource,
  TaskExpanded,
  TaskRun,
} from '@hydroserver/client'
import router from '@/router/router'
import DeleteTaskCard from '@/components/Orchestration/DeleteTaskCard.vue'
import { formatTimeWithZone } from '@/utils/time'
import {
  buildTaskRunDetailSections,
  getTaskRunMessage,
  getTaskRunStatusText as getRunStatusText,
  getTaskRunRuntimeUrl,
  getTaskStatusText,
} from '@/utils/orchestration/taskRunDetails'
import { getRunNowPollDecision } from '@/utils/orchestration/runNowPolling'
import TaskStatus from '@/components/Orchestration/TaskStatus.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import {
  mdiArrowLeft,
  mdiCheck,
  mdiCodeBraces,
  mdiContentCopy,
  mdiHistory,
  mdiPause,
  mdiPencil,
  mdiPlay,
  mdiTrashCanOutline,
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
const { ensureWorkspaceDatastreams, ensureWorkspaceThings } = orchestrationStore

const { workspaces } = storeToRefs(useWorkspaceStore())
const { setSelectedWorkspaceById } = useWorkspaceStore()
const { hasPermission, isAdmin, isOwner } = useWorkspacePermissions()

type TaskDetailsPanel = 'runs' | 'mappings'
const activePanel = ref<TaskDetailsPanel>('runs')

const canRunNow = computed(() => !!task.value)

const canEditTask = computed(() => {
  const workspace = task.value?.dataConnection?.workspace
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
  const hasDataConnection =
    !!candidate.dataConnection &&
    typeof candidate.dataConnection === 'object' &&
    typeof (candidate.dataConnection as any).id === 'string' &&
    (candidate.dataConnection as any).id.length > 0
  const hasMappings = Array.isArray(candidate.mappings)

  return hasId && hasDataConnection && hasMappings
}

const routeToAccessDenied = async () => {
  await router.replace({
    name: 'AccessDenied',
    query: {
      from: route.fullPath,
    },
  })
}

const backLabel = computed(() => {
  const dc: any = task.value?.dataConnection
  if (dc?.name) return dc.name
  return 'Back to job orchestration'
})

const onBack = () => {
  if (props.embedded || props.taskId) {
    emit('close')
    return
  }
  router.push({ name: 'Orchestration' })
}

const statusName = computed(() =>
  task.value ? getTaskStatusText(task.value as any) : 'Unknown'
)

const schedulePill = computed(() => {
  const schedule = task.value?.schedule
  if (!schedule) return ''
  const { interval, intervalPeriod, crontab } = schedule
  if (interval && intervalPeriod) return `Every ${interval} ${intervalPeriod}`
  if (crontab) return `Cron: ${crontab}`
  return ''
})

const runDomId = (runId: string) => `task-run-${runId}`

const shortId = (id: string) => {
  const value = `${id || ''}`
  if (!value) return '–'
  return value.split('-')[0] || value.slice(0, 8)
}

const formatDurationMs = (ms: number) => {
  if (!Number.isFinite(ms) || ms < 0) return '–'
  if (ms < 60_000) return `${(ms / 1000).toFixed(2)}s`
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

const runLinkHref = (runId: string) =>
  router.resolve({
    name: 'Orchestration',
    query: {
      workspaceId:
        (task.value as any)?.workspace?.id ??
        task.value?.dataConnection?.workspace?.id,
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
  if (effectiveRunId.value && !runHistoryFetchFinished.value) return true
  if (!runHistoryFetchFinished.value && runHistoryRows.value.length === 0)
    return true
  return false
})

const getRuntimeUrl = (run?: TaskRun | null) => getTaskRunRuntimeUrl(run)

const resolveRuntimeUrlFromTask = (run?: TaskRun | null) => {
  const dc: any = task.value?.dataConnection
  const sourceUrl = dc?.sourceUrl
  if (!sourceUrl || typeof sourceUrl !== 'string') return null

  const placeholders: Array<{ name: string; type?: string }> =
    dc.placeholderVariables ?? []

  const values: Record<string, string> = {}
  for (const placeholder of placeholders) {
    const name = placeholder?.name
    if (!name) continue

    if (placeholder?.type === 'per_task') {
      const value = (task.value?.taskVariables as any)?.[name]
      if (value !== undefined && value !== null && value !== '') {
        values[name] = String(value)
      }
      continue
    }

    if (placeholder?.type === 'run_time') {
      const startedAt = run?.startedAt ?? task.value?.latestRun?.startedAt
      if (startedAt) values[name] = String(startedAt)
    }
  }

  return sourceUrl.replace(
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
  task.value = { ...task.value, latestRun: run }
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
        const updatedRun = runResponse.ok
          ? ((runResponse.data as TaskRun) ?? null)
          : null
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
  target: Partial<TaskExpanded> & Pick<TaskExpanded, 'id'>
) {
  if (!canEditTask.value) return
  if (!target.schedule) return
  target.schedule.enabled = !target.schedule.enabled
  await hs.tasks.update(target as any)
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
  const workspaceId =
    (task.value as any)?.workspace?.id ??
    task.value?.dataConnection?.workspace?.id
  if (!workspaceId) return
  try {
    await Promise.all([
      ensureWorkspaceDatastreams(workspaceId),
      ensureWorkspaceThings(workspaceId),
    ])
  } catch (error) {
    console.error('Error fetching workspace datastreams', error)
  }
}

const onDelete = async () => {
  if (!canEditTask.value) return
  try {
    await hs.tasks.delete(task.value!.id)
    openDelete.value = false
    if (props.embedded || props.taskId) {
      emit('close')
    } else {
      await router.push({ name: 'Orchestration' })
    }
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

  const fetchedTaskWorkspaceId =
    (fetchedTask as any).workspace?.id ??
    fetchedTask.dataConnection?.workspace?.id
  if (
    fetchedTaskWorkspaceId &&
    workspaces.value.length &&
    !workspaces.value.some(
      (workspace) => workspace.id === fetchedTaskWorkspaceId
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

  const taskWorkspaceId =
    (task.value as any)?.workspace?.id ??
    task.value?.dataConnection?.workspace?.id
  if (taskWorkspaceId && workspaces.value.length) {
    setSelectedWorkspaceById(taskWorkspaceId)
  }

  if (effectiveRunId.value) {
    await openRunHistoryAndScroll(effectiveRunId.value)
  }
}

const onTaskUpdated = async (updated: TaskExpanded) => {
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

    stopRunNowPolling()
    openRunLogs.value = {}
    taskRuns.value = []
    runHistoryFetchFinished.value = false
    runHistoryHasMore.value = false
    runHistoryPage.value = 1
    loadingMoreTaskRuns.value = false
    runNowRequested.value = false
    activePanel.value = effectiveRunId.value ? 'runs' : 'runs'

    await fetchData()
  },
  { immediate: true }
)

watch(
  workspaces,
  (list) => {
    if (!list?.length) return
    const wid =
      (task.value as any)?.workspace?.id ??
      task.value?.dataConnection?.workspace?.id
    if (wid) {
      if (!list.some((workspace) => workspace.id === wid)) {
        void routeToAccessDenied()
        return
      }
      setSelectedWorkspaceById(wid)
    }
  },
  { immediate: true }
)

watch(
  effectiveRunId,
  async (runId) => {
    if (!runId) return
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
.task-details {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  height: 100%;
  background: #ffffff;
  overflow: hidden;
}

.task-details-header {
  padding: 12px 22px 0;
  border-bottom: 1px solid #e8e8e8;
  background: #ffffff;
  flex-shrink: 0;
}

.task-details-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  color: #1565c0;
  padding: 3px 6px;
  border-radius: 6px;
  margin-bottom: 8px;
}
.task-details-back:hover {
  background: rgba(0, 0, 0, 0.05);
}

.task-details-header-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding-bottom: 12px;
}

.task-details-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}

.task-details-title {
  font-size: 18px;
  font-weight: 400;
  color: #1c1b1f;
  margin: 0;
  overflow-wrap: anywhere;
}

.schedule-pill {
  font-size: 11px;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 2px 7px;
  color: #49454f;
}

.task-details-actions {
  margin-left: auto;
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.header-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: 1px solid #cac4d0;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 12px;
  font-family: inherit;
  color: #1c1b1f;
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}
.header-btn:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.05);
}
.header-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.header-btn--run {
  border-color: #2e7d32;
  color: #2e7d32;
  font-weight: 500;
  padding: 6px 14px;
}
.header-btn--run:hover:not(:disabled) {
  background: rgba(46, 125, 50, 0.08);
}
.header-btn--danger {
  color: #b3261e;
}
.header-btn--danger:hover:not(:disabled) {
  background: rgba(179, 38, 30, 0.08);
  border-color: #b3261e;
}

.task-details-tabs {
  display: flex;
  gap: 4px;
}
.task-details-tab {
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  color: #49454f;
  padding: 8px 14px;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 0.12s, border-color 0.12s;
}
.task-details-tab:hover {
  color: #1c1b1f;
}
.task-details-tab--active {
  color: #1565c0;
  border-bottom-color: #1565c0;
}

.task-details-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px;
  background: #ffffff;
  min-height: 0;
}

.task-details-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.run-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 0;
  color: #475569;
  font-size: 13px;
}

.run-empty {
  padding: 40px 20px;
  text-align: center;
  color: #5f5a67;
  font-size: 13px;
}

.mappings-empty {
  padding: 40px 20px;
  text-align: center;
  color: #5f5a67;
  font-size: 13px;
}

.run-entry {
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #ebebeb;
}

.run-entry-top {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 16px;
  padding: 12px 14px 8px;
}

.run-entry-top-left {
  display: flex;
  align-items: flex-start;
  flex: 0 0 auto;
}

.run-entry-runid-right {
  flex: 0 0 auto;
  margin-left: auto;
  padding-top: 2px;
  font-size: 0.75rem;
  font-weight: 700;
  color: #0e7490;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}

.run-entry-status {
  flex: 0 0 auto;
  letter-spacing: 0.01em;
}

.run-entry-summary {
  flex: 1 1 auto;
  min-width: 0;
  font-weight: 500;
  color: #475569;
  font-size: 0.88rem;
  line-height: 1.35;
  word-break: break-word;
  white-space: normal;
}

.run-entry-meta {
  padding: 8px 14px 10px;
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
  font-size: 0.85rem;
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

.run-entry-duration {
  font-size: 0.78rem;
  font-weight: 700;
  color: #334155;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 2px 10px;
  white-space: nowrap;
}

.run-entry-footer {
  padding: 8px 14px 10px;
  border-top: 1px solid #f1f5f9;
}

.run-entry-details {
  border-top: 1px solid #f1f5f9;
  padding: 10px 14px 14px;
}

.run-entry-detail-row {
  display: grid;
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

.run-section-label {
  border: 1px solid #e2e8f0;
  background: #f1f5f9;
  color: #475569;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.run-entry-refresh {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}

.run-highlight {
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

.task-details-loading {
  padding: 40px 20px;
  text-align: center;
  color: #5f5a67;
  font-size: 13px;
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
</style>
