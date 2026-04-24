import { onBeforeUnmount, reactive, type Ref } from 'vue'
import type {
  DataProductTaskExpanded,
  MonitoringTaskExpanded,
  TaskExpanded,
  TaskRun,
} from '@hydroserver/client'
import { serviceForKind, type TaskKind } from '@/components/Orchestration/workbench/orchestrationTabs'

const POLL_INTERVAL_MS = 4000
const POLL_MAX_ATTEMPTS = 150

type AnyTask = TaskExpanded | DataProductTaskExpanded | MonitoringTaskExpanded

type Lists = {
  etl: Ref<TaskExpanded[]>
  dataProduct: Ref<DataProductTaskExpanded[]>
  monitoring: Ref<MonitoringTaskExpanded[]>
}

type Options = {
  lists: Lists
  currentWorkspaceId: () => string
}

export function useTaskRunNowPolling({ lists, currentWorkspaceId }: Options) {
  const runNowTriggeredByTaskId = reactive<Record<string, boolean>>({})
  const taskPollTimeouts = new Map<string, number>()

  const listFor = (kind: TaskKind) => {
    if (kind === 'etl') return lists.etl
    if (kind === 'dataProduct') return lists.dataProduct
    return lists.monitoring
  }

  const upsertTask = (kind: TaskKind, task: AnyTask | null) => {
    if (!task) return
    const target = listFor(kind)
    const next = [...target.value]
    const index = next.findIndex((p) => p.id === task.id)
    if (index !== -1) next[index] = task as any
    else next.push(task as any)
    target.value = next as any
  }

  const findTask = (kind: TaskKind, taskId: string): AnyTask | null =>
    (listFor(kind).value as AnyTask[]).find((t) => t.id === taskId) ?? null

  const syncLatestRun = (kind: TaskKind, taskId: string, run: TaskRun) => {
    const existing = findTask(kind, taskId)
    if (!existing) return
    upsertTask(kind, { ...(existing as any), latestRun: run })
  }

  const stopPollingFor = (taskId: string) => {
    const timeoutId = taskPollTimeouts.get(taskId)
    if (timeoutId) window.clearTimeout(timeoutId)
    taskPollTimeouts.delete(taskId)
  }

  const stopAll = () => {
    taskPollTimeouts.forEach((id) => window.clearTimeout(id))
    taskPollTimeouts.clear()
    for (const id of Object.keys(runNowTriggeredByTaskId)) {
      delete runNowTriggeredByTaskId[id]
    }
  }

  const refreshAfterCompletion = async (kind: TaskKind, taskId: string) => {
    try {
      const svc = serviceForKind(kind)
      const updated = (await svc.getItem(taskId, {
        expand_related: true,
      })) as any
      if (updated) upsertTask(kind, updated)
    } catch (error) {
      console.error('Error refreshing task after run completion', error)
    }
  }

  const schedulePoll = (
    kind: TaskKind,
    taskId: string,
    requestedRunId: string | null,
    previousRunId: string | null,
    attempt = 0,
    workspaceId = currentWorkspaceId()
  ) => {
    stopPollingFor(taskId)
    if (attempt > POLL_MAX_ATTEMPTS) {
      runNowTriggeredByTaskId[taskId] = false
      return
    }

    const svc = serviceForKind(kind)

    const timeoutId = window.setTimeout(async () => {
      if (workspaceId !== currentWorkspaceId()) {
        runNowTriggeredByTaskId[taskId] = false
        stopPollingFor(taskId)
        return
      }

      try {
        if (requestedRunId) {
          const runResponse = await svc.getTaskRun(taskId, requestedRunId)
          const updatedRun = runResponse.ok
            ? (runResponse.data as TaskRun) ?? null
            : null

          if (workspaceId !== currentWorkspaceId()) {
            runNowTriggeredByTaskId[taskId] = false
            stopPollingFor(taskId)
            return
          }

          if (updatedRun?.id) {
            syncLatestRun(kind, taskId, updatedRun)
            if (updatedRun.status && updatedRun.status !== 'RUNNING') {
              runNowTriggeredByTaskId[taskId] = false
              stopPollingFor(taskId)
              await refreshAfterCompletion(kind, taskId)
              return
            }
          }
        } else {
          const updated = (await svc.getItem(taskId, {
            expand_related: true,
          })) as any

          if (workspaceId !== currentWorkspaceId()) {
            runNowTriggeredByTaskId[taskId] = false
            stopPollingFor(taskId)
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
                syncLatestRun(kind, taskId, updated.latestRun)
              if (status !== 'RUNNING') {
                runNowTriggeredByTaskId[taskId] = false
                stopPollingFor(taskId)
                await refreshAfterCompletion(kind, taskId)
                return
              }
            }
          }
        }
      } catch (error) {
        console.error('Error polling task status', error)
      }
      schedulePoll(
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

  const runTaskNow = async (kind: TaskKind, taskId: string) => {
    const previousRunId = (findTask(kind, taskId) as any)?.latestRun?.id ?? null
    runNowTriggeredByTaskId[taskId] = true
    try {
      const svc = serviceForKind(kind)
      const response = await svc.runTask(taskId)
      if (!response.ok) {
        throw new Error(response.message || 'Unable to run task now.')
      }
      const requestedRun = response.ok
        ? (response.data as TaskRun) ?? null
        : null
      if (requestedRun?.id) syncLatestRun(kind, taskId, requestedRun)
      schedulePoll(
        kind,
        taskId,
        requestedRun?.id ?? null,
        previousRunId,
        0,
        currentWorkspaceId()
      )
    } catch (error) {
      runNowTriggeredByTaskId[taskId] = false
      console.error('Error running task now', error)
    }
  }

  const toggleSchedulePaused = async (
    kind: TaskKind,
    taskId: string,
    schedule: NonNullable<AnyTask['schedule']>
  ) => {
    const previousEnabled = !!schedule.enabled
    schedule.enabled = !previousEnabled
    try {
      const svc = serviceForKind(kind)
      await svc.update({ id: taskId, schedule } as any)
      const updated = (await svc.getItem(taskId)) as any
      if (updated) upsertTask(kind, updated)
    } catch (error) {
      schedule.enabled = previousEnabled
      console.error('Error toggling task paused state', error)
    }
  }

  onBeforeUnmount(() => stopAll())

  return {
    runNowTriggeredByTaskId,
    stopAll,
    runTaskNow,
    toggleSchedulePaused,
  }
}
