import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useTaskRunNowPolling } from '../orchestration/useTaskRunNowPolling'
import { Snackbar } from '@/utils/notifications'

vi.mock('@/utils/notifications', () => ({
  Snackbar: { error: vi.fn() },
}))

const serviceMocks = vi.hoisted(() => ({
  getItem: vi.fn(),
  getTaskRun: vi.fn(),
  runTask: vi.fn(),
  update: vi.fn(),
}))

vi.mock('@/components/Orchestration/workbench/orchestrationTabs', () => ({
  serviceForKind: vi.fn(() => serviceMocks),
}))

describe('useTaskRunNowPolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(Snackbar.error).mockClear()
    serviceMocks.getItem.mockReset()
    serviceMocks.getTaskRun.mockReset()
    serviceMocks.runTask.mockReset()
    serviceMocks.update.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('waits for an existing backend-created monitoring run without triggering another run', async () => {
    const monitoringTasks = ref([
      {
        id: 'mon-1',
        name: 'Quality task',
        latestRun: null,
        schedule: null,
      },
    ] as any)

    serviceMocks.getItem.mockResolvedValue({
      id: 'mon-1',
      name: 'Quality task',
      latestRun: {
        id: 'run-1',
        status: 'SUCCESS',
        result: { rulesViolated: 0 },
        startedAt: '2026-03-13T12:00:00Z',
      },
      schedule: null,
    })

    const polling = useTaskRunNowPolling({
      lists: {
        etl: ref([]),
        dataProduct: ref([]),
        monitoring: monitoringTasks,
      },
      currentWorkspaceId: () => 'workspace-1',
    })

    polling.startPollingForLatestRun('monitoring', 'mon-1')
    await vi.advanceTimersByTimeAsync(3000)

    expect(serviceMocks.getItem).toHaveBeenCalledWith('mon-1')
    expect(serviceMocks.runTask).not.toHaveBeenCalled()
    expect(monitoringTasks.value[0].latestRun).toMatchObject({
      id: 'run-1',
      status: 'SUCCESS',
    })
    expect(polling.runNowTriggeredByTaskId['mon-1']).toBe(false)
  })

  it('refreshes backend task statuses after triggering and completing a run', async () => {
    const onTaskStatusChanged = vi.fn().mockResolvedValue(undefined)
    const task = {
      id: 'mon-1',
      name: 'Quality task',
      status: 'Needs attention',
    }
    const monitoringTasks = ref([task] as any)
    const pending = { id: 'run-1', status: 'PENDING', displayStatus: 'Pending' }
    const completed = {
      id: 'run-1',
      status: 'SUCCESS',
      displayStatus: 'Violations found',
    }
    serviceMocks.runTask.mockResolvedValue({ ok: true, data: pending })
    serviceMocks.getTaskRun.mockResolvedValue({ ok: true, data: completed })
    serviceMocks.getItem
      .mockResolvedValueOnce({ ...task, status: 'Pending', latestRun: pending })
      .mockResolvedValueOnce({
        ...task,
        status: 'Violations found',
        latestRun: completed,
      })

    const polling = useTaskRunNowPolling({
      lists: {
        etl: ref([]),
        dataProduct: ref([]),
        monitoring: monitoringTasks,
      },
      currentWorkspaceId: () => 'workspace-1',
      onTaskStatusChanged,
    })

    await polling.runTaskNow('monitoring', task.id)
    expect(monitoringTasks.value[0].status).toBe('Pending')
    await vi.advanceTimersByTimeAsync(3000)
    expect(monitoringTasks.value[0].status).toBe('Violations found')
    expect(serviceMocks.getItem).toHaveBeenCalledTimes(2)
    expect(polling.runNowTriggeredByTaskId[task.id]).toBe(false)
    expect(onTaskStatusChanged).toHaveBeenCalledTimes(2)
    expect(onTaskStatusChanged).toHaveBeenLastCalledWith(
      'monitoring',
      'workspace-1'
    )
  })

  it.each(['null', 'exception', 'summary'])(
    'retries a failed %s refresh after run completion',
    async (failure) => {
      const pending = { id: 'run-1', status: 'PENDING' }
      const completed = {
        id: 'run-1',
        status: 'SUCCESS',
        displayStatus: 'Violations found',
      }
      const task = { id: 'mon-1', status: 'Pending', latestRun: pending }
      const updated = {
        ...task,
        status: 'Violations found',
        latestRun: completed,
      }
      const monitoring = ref([task] as any)
      const onTaskStatusChanged = vi.fn().mockResolvedValue(undefined)
      serviceMocks.runTask.mockResolvedValue({ ok: true, data: pending })
      serviceMocks.getTaskRun.mockResolvedValue({ ok: true, data: completed })
      serviceMocks.getItem.mockResolvedValueOnce(task)
      if (failure === 'exception')
        serviceMocks.getItem.mockRejectedValueOnce(new Error('Offline'))
      else if (failure === 'null')
        serviceMocks.getItem.mockResolvedValueOnce(null)
      else {
        serviceMocks.getItem.mockResolvedValueOnce(updated)
        onTaskStatusChanged
          .mockResolvedValueOnce(undefined)
          .mockRejectedValueOnce(new Error('Offline'))
      }
      serviceMocks.getItem.mockResolvedValue(updated)

      const polling = useTaskRunNowPolling({
        lists: { etl: ref([]), dataProduct: ref([]), monitoring },
        currentWorkspaceId: () => 'workspace-1',
        onTaskStatusChanged,
      })
      await polling.runTaskNow('monitoring', task.id)
      await vi.advanceTimersByTimeAsync(6000)

      expect(monitoring.value[0].status).toBe('Violations found')
      expect(serviceMocks.getTaskRun).toHaveBeenCalledTimes(1)
      expect(serviceMocks.getItem).toHaveBeenCalledTimes(3)
      expect(onTaskStatusChanged).toHaveBeenLastCalledWith(
        'monitoring',
        'workspace-1'
      )
      expect(vi.getTimerCount()).toBe(0)
      expect(Snackbar.error).not.toHaveBeenCalled()
    }
  )

  it('shows how to recover when task status refresh retries are exhausted', async () => {
    const task = { id: 'mon-1', status: 'Pending' }
    serviceMocks.getTaskRun.mockResolvedValue({
      ok: true,
      data: { id: 'run-1', status: 'SUCCESS' },
    })
    serviceMocks.getItem.mockResolvedValue(null)
    const polling = useTaskRunNowPolling({
      lists: {
        etl: ref([]),
        dataProduct: ref([]),
        monitoring: ref([task] as any),
      },
      currentWorkspaceId: () => 'workspace-1',
    })
    polling.startPollingTaskRun('monitoring', task.id, 'run-1')
    await vi.advanceTimersByTimeAsync(30_000)

    expect(Snackbar.error).toHaveBeenCalledOnce()
    expect(Snackbar.error).toHaveBeenCalledWith(
      'Unable to refresh task status. Reload the page to try again.'
    )
    expect(vi.getTimerCount()).toBe(0)
  })

  it('does not restore tasks or start retries after polling is stopped', async () => {
    let resolveRefresh!: (value: unknown) => void
    serviceMocks.getItem.mockReturnValue(
      new Promise((resolve) => {
        resolveRefresh = resolve
      })
    )
    serviceMocks.runTask.mockResolvedValue({
      ok: true,
      data: { id: 'run-1', status: 'PENDING' },
    })
    const monitoring = ref([{ id: 'mon-1', status: 'OK' }] as any)
    const onTaskStatusChanged = vi.fn()
    const polling = useTaskRunNowPolling({
      lists: { etl: ref([]), dataProduct: ref([]), monitoring },
      currentWorkspaceId: () => 'workspace-1',
      onTaskStatusChanged,
    })
    const request = polling.runTaskNow('monitoring', 'mon-1')
    await Promise.resolve()
    polling.stopAll()
    monitoring.value = []
    resolveRefresh({ id: 'mon-1', status: 'Pending' })
    await request

    expect(monitoring.value).toEqual([])
    expect(onTaskStatusChanged).not.toHaveBeenCalled()
    expect(vi.getTimerCount()).toBe(0)
  })
})
