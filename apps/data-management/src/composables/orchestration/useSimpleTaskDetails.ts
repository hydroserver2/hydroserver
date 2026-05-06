import { computed, onMounted, ref } from 'vue'
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

export function useSimpleTaskDetails(
  kind: TaskKind,
  props: { taskId?: string | null; runId?: string | null; embedded?: boolean },
  emit: Emit
) {
  const route = useRoute()
  const service = serviceForKind(kind)
  const task = ref<any>(null)
  const runs = ref<TaskRun[]>([])
  const loading = ref(false)
  const loadingRuns = ref(false)
  const runNowRequested = ref(false)
  const { workspaces } = storeToRefs(useWorkspaceStore())
  const { setSelectedWorkspaceById } = useWorkspaceStore()
  const { checkPermissionsByWorkspaceId } = useWorkspacePermissions()

  const taskId = computed(() => {
    if (props.taskId) return props.taskId
    const param = route.params.id
    return Array.isArray(param) ? (param[0] ?? '') : `${param ?? ''}`
  })

  const workspaceId = computed(() => {
    const value = task.value
    return (
      value?.workspace?.id ??
      value?.dataConnection?.workspace?.id ??
      value?.thing?.workspaceId ??
      value?.workspaceId ??
      null
    )
  })

  const workspace = computed(() => {
    const embedded =
      task.value?.workspace ?? task.value?.dataConnection?.workspace
    if (embedded?.id) return embedded
    return workspaces.value.find((item) => item.id === workspaceId.value)
  })

  const canEdit = computed(() => {
    if (!workspace.value) return false
    return checkPermissionsByWorkspaceId(
      workspaceId.value,
      PermissionResource.Workspace,
      PermissionAction.Edit
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
          key: `${violation.ruleId ?? violation.datastreamId ?? 'violation'}-${index}`,
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

  async function load() {
    if (!taskId.value) return
    loading.value = true
    try {
      const response = await service.get(taskId.value, { expand_related: true })
      if (!response.ok)
        throw new Error(response.message || 'Unable to load task.')
      task.value = response.data
      if (workspaceId.value) setSelectedWorkspaceById(workspaceId.value)
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
      if (response.data?.id) task.value.latestRun = response.data
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
