import { onBeforeUnmount, reactive, type Ref } from 'vue'
import type { TaskRun } from '@hydroserver/client'
import { isOrchestrationEnabled } from '@/composables/orchestration/orchestrationAvailability'
import { Snackbar } from '@/utils/notifications'
import {
  serviceForKind,
  type TaskKind,
} from '@/components/Orchestration/workbench/orchestrationTabs'
import type {
  AnyTask,
  DataProductTask,
  MonitoringTask,
  Task,
} from '@/types/orchestrationTasks'

const POLL_INTERVAL_MS = 3000
const POLL_DURATION_MS = 21_000
const TERMINAL_STATUSES = ['SUCCESS', 'FAILURE']
const ACTIVE_RUN_STATUSES = new Set(['PENDING', 'STARTED'])

type Lists = {
  etl: Ref<Task[]>
  dataProduct: Ref<DataProductTask[]>
  monitoring: Ref<MonitoringTask[]>
}

type Options = {
  lists: Lists
  currentWorkspaceId: () => string
  onTaskStatusChanged?: (kind: TaskKind, workspaceId: string) => Promise<void>
}

export function useTaskRunNowPolling({
  lists,
  currentWorkspaceId,
  onTaskStatusChanged,
}: Options) {
  const runNowTriggeredByTaskId = reactive<Record<string, boolean>>({})
  const taskPollTimeouts = new Map<string, number>()
  const runNowStartedAt = new Map<string, number>()
  let pollingGeneration = 0

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
    runNowStartedAt.delete(taskId)
  }

  const stopAll = () => {
    pollingGeneration += 1
    taskPollTimeouts.forEach((id) => window.clearTimeout(id))
    taskPollTimeouts.clear()
    runNowStartedAt.clear()
    for (const id of Object.keys(runNowTriggeredByTaskId)) {
      delete runNowTriggeredByTaskId[id]
    }
  }

  const refreshTask = async (
    kind: TaskKind,
    taskId: string,
    workspaceId = currentWorkspaceId(),
    generation = pollingGeneration
  ): Promise<boolean> => {
    try {
      const svc = serviceForKind(kind)
      const updated = (await svc.getItem(taskId)) as any
      if (
        workspaceId !== currentWorkspaceId() ||
        generation !== pollingGeneration
      )
        return true
      if (!updated) return false
      upsertTask(kind, updated)
      await onTaskStatusChanged?.(kind, workspaceId)
      return true
    } catch (error) {
      console.error('Error refreshing task status', error)
      return false
    }
  }

  const retryTaskRefresh = async (
    kind: TaskKind,
    taskId: string,
    workspaceId: string,
    generation: number,
    startedAt = Date.now()
  ) => {
    if (
      workspaceId !== currentWorkspaceId() ||
      generation !== pollingGeneration
    )
      return
    const refreshed = await refreshTask(kind, taskId, workspaceId, generation)
    if (
      workspaceId !== currentWorkspaceId() ||
      generation !== pollingGeneration
    )
      return
    if (refreshed) return
    if (Date.now() - startedAt >= POLL_DURATION_MS) {
      Snackbar.error(
        'Unable to refresh task status. Reload the page to try again.'
      )
      return
    }
    const timeoutId = window.setTimeout(() => {
      taskPollTimeouts.delete(taskId)
      void retryTaskRefresh(kind, taskId, workspaceId, generation, startedAt)
    }, POLL_INTERVAL_MS)
    taskPollTimeouts.set(taskId, timeoutId)
  }

  const schedulePoll = (
    kind: TaskKind,
    taskId: string,
    requestedRunId: string,
    startedAt: number,
    workspaceId = currentWorkspaceId(),
    generation = pollingGeneration
  ) => {
    stopPollingFor(taskId)

    if (Date.now() - startedAt >= POLL_DURATION_MS) {
      runNowTriggeredByTaskId[taskId] = false
      return
    }

    const svc = serviceForKind(kind)

    const timeoutId = window.setTimeout(async () => {
      if (
        workspaceId !== currentWorkspaceId() ||
        generation !== pollingGeneration
      ) {
        if (generation !== pollingGeneration) return
        runNowTriggeredByTaskId[taskId] = false
        stopPollingFor(taskId)
        return
      }

      if (Date.now() - startedAt >= POLL_DURATION_MS) {
        runNowTriggeredByTaskId[taskId] = false
        stopPollingFor(taskId)
        return
      }

      try {
        const runResponse = await svc.getTaskRun(taskId, requestedRunId)
        const updatedRun = runResponse.ok
          ? ((runResponse.data as TaskRun) ?? null)
          : null

        if (
          workspaceId !== currentWorkspaceId() ||
          generation !== pollingGeneration
        ) {
          if (generation !== pollingGeneration) return
          runNowTriggeredByTaskId[taskId] = false
          stopPollingFor(taskId)
          return
        }

        if (updatedRun?.id) {
          syncLatestRun(kind, taskId, updatedRun)
          const status = updatedRun.status ?? null
          if (!status || !ACTIVE_RUN_STATUSES.has(status)) {
            runNowTriggeredByTaskId[taskId] = false
            stopPollingFor(taskId)
            if (status && TERMINAL_STATUSES.includes(status)) {
              await retryTaskRefresh(kind, taskId, workspaceId, generation)
            }
            return
          }
        }
      } catch (error) {
        console.error('Error polling task status', error)
      }

      if (generation === pollingGeneration)
        schedulePoll(
          kind,
          taskId,
          requestedRunId,
          startedAt,
          workspaceId,
          generation
        )
    }, POLL_INTERVAL_MS)

    taskPollTimeouts.set(taskId, timeoutId)
  }

  const startPollingTaskRun = (
    kind: TaskKind,
    taskId: string,
    runId: string,
    startedAt = Date.now()
  ) => {
    runNowTriggeredByTaskId[taskId] = true
    runNowStartedAt.set(taskId, startedAt)
    schedulePoll(kind, taskId, runId, startedAt, currentWorkspaceId())
  }

  const startPollingForLatestRun = (
    kind: TaskKind,
    taskId: string,
    startedAt = Date.now(),
    workspaceId = currentWorkspaceId(),
    generation = pollingGeneration
  ) => {
    stopPollingFor(taskId)
    runNowTriggeredByTaskId[taskId] = true
    runNowStartedAt.set(taskId, startedAt)

    if (Date.now() - startedAt >= POLL_DURATION_MS) {
      runNowTriggeredByTaskId[taskId] = false
      return
    }

    const svc = serviceForKind(kind)
    const timeoutId = window.setTimeout(async () => {
      if (
        workspaceId !== currentWorkspaceId() ||
        generation !== pollingGeneration
      ) {
        if (generation !== pollingGeneration) return
        runNowTriggeredByTaskId[taskId] = false
        stopPollingFor(taskId)
        return
      }

      try {
        const updated = (await svc.getItem(taskId)) as AnyTask | null

        if (
          workspaceId !== currentWorkspaceId() ||
          generation !== pollingGeneration
        ) {
          if (generation !== pollingGeneration) return
          runNowTriggeredByTaskId[taskId] = false
          stopPollingFor(taskId)
          return
        }

        if (updated) {
          upsertTask(kind, updated)
          const latestRun = (updated as any).latestRun as
            TaskRun | null | undefined

          if (latestRun?.id) {
            if (ACTIVE_RUN_STATUSES.has(latestRun.status)) {
              startPollingTaskRun(kind, taskId, latestRun.id, startedAt)
            } else {
              runNowTriggeredByTaskId[taskId] = false
              stopPollingFor(taskId)
              await retryTaskRefresh(kind, taskId, workspaceId, generation)
            }
            return
          }
        }
      } catch (error) {
        console.error('Error polling task for latest run', error)
      }

      if (generation === pollingGeneration)
        startPollingForLatestRun(
          kind,
          taskId,
          startedAt,
          workspaceId,
          generation
        )
    }, POLL_INTERVAL_MS)

    taskPollTimeouts.set(taskId, timeoutId)
  }

  const runTaskNow = async (kind: TaskKind, taskId: string) => {
    if (!isOrchestrationEnabled()) return
    const workspaceId = currentWorkspaceId()
    const generation = pollingGeneration
    runNowTriggeredByTaskId[taskId] = true
    const startedAt = Date.now()
    runNowStartedAt.set(taskId, startedAt)
    try {
      const svc = serviceForKind(kind)
      const response = await svc.runTask(taskId)
      if (
        workspaceId !== currentWorkspaceId() ||
        generation !== pollingGeneration
      )
        return
      if (!response.ok) {
        throw new Error(response.message || 'Unable to run task now.')
      }
      const requestedRun = response.ok
        ? ((response.data as TaskRun) ?? null)
        : null
      if (requestedRun?.id) {
        syncLatestRun(kind, taskId, requestedRun)
        await refreshTask(kind, taskId, workspaceId, generation)
        if (
          workspaceId !== currentWorkspaceId() ||
          generation !== pollingGeneration
        )
          return
        startPollingTaskRun(kind, taskId, requestedRun.id, startedAt)
      } else {
        runNowTriggeredByTaskId[taskId] = false
        runNowStartedAt.delete(taskId)
      }
    } catch (error) {
      runNowTriggeredByTaskId[taskId] = false
      runNowStartedAt.delete(taskId)
      console.error('Error running task now', error)
    }
  }

  const toggleSchedulePaused = async (
    kind: TaskKind,
    taskId: string,
    schedule: NonNullable<AnyTask['schedule']>
  ) => {
    const workspaceId = currentWorkspaceId()
    const generation = pollingGeneration
    const previousEnabled = !!schedule.enabled
    schedule.enabled = !previousEnabled
    try {
      const svc = serviceForKind(kind)
      await svc.update({ id: taskId, schedule } as any)
      await retryTaskRefresh(kind, taskId, workspaceId, generation)
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
    startPollingTaskRun,
    startPollingForLatestRun,
    toggleSchedulePaused,
  }
}
