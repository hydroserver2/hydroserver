import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import hs, {
  PermissionAction,
  PermissionResource,
  type TaskRun,
} from '@hydroserver/client'
import router from '@/router/router'
import { useWorkspaceStore } from '@/store/workspaces'
import { useWorkspacePermissions } from '@/composables/useWorkspacePermissions'
import { Snackbar } from '@/utils/notifications'
import { formatTimeWithZone } from '@/utils/time'
import {
  getDisplayedTaskStatus,
  getMonitoringRunViolations,
  getTaskRunMessage,
  getTaskRunRuntimeUrl,
  getTaskStatusText,
} from '@/utils/orchestration/taskRunDetails'
import {
  serviceForKind,
  type TaskKind,
} from '@/components/Orchestration/workbench/orchestrationTabs'

type Emit = {
  (e: 'close'): void
  (e: 'deleted'): void
  (e: 'updated'): void
}

const POLL_INTERVAL_MS = 3000
const POLL_DURATION_MS = 21_000
const ACTIVE_RUN_STATUSES = new Set(['PENDING', 'STARTED'])

export function useSimpleTaskDetails(
  kind: TaskKind,
  props: {
    taskId?: string | null
    runId?: string | null
    embedded?: boolean
    initialTask?: any
  },
  emit: Emit
) {
  const route = useRoute()
  const service = serviceForKind(kind)
  const isDetailedTask = (candidate: any) => {
    if (!candidate) return false
    if (kind === 'etl') {
      return !!candidate.dataConnection && Array.isArray(candidate.mappings)
    }
    if (kind === 'dataProduct') {
      return (
        !!candidate.thing && Array.isArray(candidate.ratingCurveTransformations)
      )
    }
    return !!candidate.thing && Array.isArray(candidate.monitoredDatastreams)
  }
  const task = ref<any>(
    isDetailedTask(props.initialTask) ? props.initialTask : null
  )
  const runs = ref<TaskRun[]>([])
  const loading = ref(false)
  const loadingRuns = ref(false)
  const runNowRequested = ref(false)
  const runPollTimeouts = new Map<string, number>()
  const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
  const { hasPermission } = useWorkspacePermissions()

  const taskId = computed(() => {
    if (props.taskId) return props.taskId
    const param = route.params.id
    return Array.isArray(param) ? param[0] ?? '' : `${param ?? ''}`
  })

  const workspaceId = computed(() => selectedWorkspace.value?.id ?? null)

  const canEdit = computed(() => {
    if (!selectedWorkspace.value) return false
    return hasPermission(
      PermissionResource.Workspace,
      PermissionAction.Edit,
      selectedWorkspace.value
    )
  })

  const readOnlyTooltip =
    'You have read-only access to this workspace. Ask an editor or owner to make changes.'

  const backLabel = computed(
    () => task.value?.dataConnection?.name ?? task.value?.thing?.name ?? 'Back'
  )
  const statusName = computed(() =>
    task.value ? getTaskStatusText(task.value) : 'Unknown'
  )
  const statusSort = computed(() =>
    task.value ? getDisplayedTaskStatus(task.value) : 'Unknown'
  )
  const scheduleText = computed(() => {
    const schedule = task.value?.schedule
    if (!schedule) return ''
    if (schedule.interval && schedule.intervalPeriod) {
      return `Every ${schedule.interval} ${schedule.intervalPeriod}`
    }
    if (schedule.crontab) return `Cron: ${schedule.crontab}`
    return ''
  })
  const pauseDisabledReason = computed(() => {
    if (!canEdit.value) return readOnlyTooltip
    if (!task.value?.schedule) return 'This task has no schedule to pause.'
    return ''
  })
  const runNowDisabledReason = computed(() => {
    if (!canEdit.value) return readOnlyTooltip
    if (runNowRequested.value) return 'A run has already been requested.'
    return ''
  })

  const runRows = computed(() => {
    const seen = new Set<string>()
    return [task.value?.latestRun, ...runs.value]
      .filter((run): run is TaskRun => {
        if (!run?.id) return false
        if (seen.has(run.id)) return false
        seen.add(run.id)
        return true
      })
      .map((run) => ({
        id: run.id,
        domId: `task-run-${run.id}`,
        startedAt: formatTimeWithZone(run.startedAt),
        message: getTaskRunMessage(run),
        runtimeUrl: getTaskRunRuntimeUrl(run) ?? null,
        violations: getMonitoringRunViolations(run).map((violation, index) => ({
          key: `${
            violation.ruleId ?? violation.datastreamId ?? 'violation'
          }-${index}`,
          datastreamName: violation.datastreamId ?? 'Datastream',
          ruleTypeLabel: `${violation.ruleType ?? ''}`.replace(/_/g, ' '),
          violationCount: violation.violationCount,
          firstViolationAt: violation.firstViolationAt
            ? formatTimeWithZone(violation.firstViolationAt)
            : null,
          lastViolationAt: violation.lastViolationAt
            ? formatTimeWithZone(violation.lastViolationAt)
            : null,
        })),
        raw: run,
      }))
  })

  function upsertRun(run: TaskRun) {
    if (!run?.id) return
    if (task.value?.latestRun?.id === run.id) {
      task.value = { ...task.value, latestRun: run }
    }

    const index = runs.value.findIndex((existing) => existing.id === run.id)
    if (index === -1) {
      runs.value = [run, ...runs.value]
      return
    }

    const next = [...runs.value]
    next[index] = run
    runs.value = next
  }

  function stopPollingRun(runId: string) {
    const timeoutId = runPollTimeouts.get(runId)
    if (timeoutId) window.clearTimeout(timeoutId)
    runPollTimeouts.delete(runId)
  }

  function stopAllRunPolling() {
    runPollTimeouts.forEach((timeoutId) => window.clearTimeout(timeoutId))
    runPollTimeouts.clear()
  }

  function pollRunUntilComplete(runId: string, startedPollingAt = Date.now()) {
    if (!task.value?.id || !runId) return
    stopPollingRun(runId)

    if (Date.now() - startedPollingAt >= POLL_DURATION_MS) {
      runNowRequested.value = false
      return
    }

    const timeoutId = window.setTimeout(async () => {
      if (!task.value?.id) {
        runNowRequested.value = false
        stopPollingRun(runId)
        return
      }

      if (Date.now() - startedPollingAt >= POLL_DURATION_MS) {
        runNowRequested.value = false
        stopPollingRun(runId)
        return
      }

      try {
        const response = await service.getTaskRun(task.value.id, runId)
        const updatedRun = response.ok
          ? (response.data as TaskRun) ?? null
          : null
        if (updatedRun?.id) {
          upsertRun(updatedRun)
          if (!ACTIVE_RUN_STATUSES.has(updatedRun.status)) {
            runNowRequested.value = false
            stopPollingRun(runId)
            return
          }
        }
      } catch (error) {
        console.error('Error polling task run status', error)
      }

      pollRunUntilComplete(runId, startedPollingAt)
    }, POLL_INTERVAL_MS)

    runPollTimeouts.set(runId, timeoutId)
  }

  async function load() {
    if (!taskId.value) return
    loading.value = true
    try {
      const response = await service.get(taskId.value, { expand_related: true })
      if (!response.ok)
        throw new Error(response.message || 'Unable to load task.')
      task.value = response.data
      if (
        task.value?.latestRun?.id &&
        ACTIVE_RUN_STATUSES.has(task.value.latestRun.status)
      ) {
        pollRunUntilComplete(task.value.latestRun.id)
      }
    } catch (error: any) {
      Snackbar.error(error?.message || 'Unable to load task.')
    } finally {
      loading.value = false
    }
  }

  async function fetchRuns() {
    if (!task.value?.id) return
    loadingRuns.value = true
    try {
      const response = await service.getTaskRuns(task.value.id, {
        order_by: ['-startedAt'],
        page: 1,
        page_size: 50,
      } as any)
      if (!response.ok)
        throw new Error(response.message || 'Unable to fetch runs.')
      runs.value = response.data ?? []
      const activeLatestRun = task.value?.latestRun
      if (
        activeLatestRun?.id &&
        ACTIVE_RUN_STATUSES.has(activeLatestRun.status)
      ) {
        pollRunUntilComplete(activeLatestRun.id)
      }
    } catch (error: any) {
      Snackbar.error(error?.message || 'Unable to fetch runs.')
    } finally {
      loadingRuns.value = false
    }
  }

  async function togglePaused() {
    if (!canEdit.value || !task.value?.schedule) return
    const schedule = {
      ...task.value.schedule,
      enabled: !task.value.schedule.enabled,
    }
    const response = await service.update({
      id: task.value.id,
      schedule,
    } as any)
    if (!response.ok) {
      Snackbar.error(response.message || 'Unable to update schedule.')
      return
    }
    task.value = { ...task.value, schedule }
    emit('updated')
  }

  async function runNow() {
    if (!canEdit.value || !task.value?.id || runNowRequested.value) return
    runNowRequested.value = true
    try {
      const response = await service.runTask(task.value.id)
      if (!response.ok)
        throw new Error(response.message || 'Unable to run task.')
      if (response.data?.id) {
        task.value.latestRun = response.data
        upsertRun(response.data)
        pollRunUntilComplete(response.data.id)
      }
      Snackbar.success('Run requested.')
    } catch (error: any) {
      runNowRequested.value = false
      Snackbar.error(error?.message || 'Unable to run task.')
    }
  }

  async function deleteTask() {
    if (!canEdit.value || !task.value?.id) return
    const response = await service.delete(task.value.id)
    if (!response.ok) {
      Snackbar.error(response.message || 'Unable to delete task.')
      return
    }
    Snackbar.success('Task deleted.')
    emit('deleted')
    if (props.embedded || props.taskId) emit('close')
    else await router.push({ name: 'Orchestration' })
  }

  function close() {
    if (props.embedded || props.taskId) emit('close')
    else router.push({ name: 'Orchestration' })
  }

  function copy(value?: string | null) {
    if (!value) return
    navigator.clipboard?.writeText(value)
    Snackbar.success('Copied to clipboard.')
  }

  function onUpdated() {
    emit('updated')
    void load()
  }

  onMounted(async () => {
    await load()
    await fetchRuns()
  })

  onBeforeUnmount(stopAllRunPolling)

  return {
    task,
    loading,
    loadingRuns,
    runRows,
    canEdit,
    readOnlyTooltip,
    backLabel,
    statusName,
    statusSort,
    scheduleText,
    pauseDisabledReason,
    runNowDisabledReason,
    runNowRequested,
    workspaceId,
    close,
    copy,
    deleteTask,
    fetchRuns,
    onUpdated,
    runNow,
    togglePaused,
  }
}
