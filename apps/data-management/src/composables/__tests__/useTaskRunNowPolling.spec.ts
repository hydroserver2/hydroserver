import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useTaskRunNowPolling } from '../orchestration/useTaskRunNowPolling'

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

    expect(serviceMocks.getItem).toHaveBeenCalledWith('mon-1', {
      expand_related: true,
    })
    expect(serviceMocks.runTask).not.toHaveBeenCalled()
    expect(monitoringTasks.value[0].latestRun).toMatchObject({
      id: 'run-1',
      status: 'SUCCESS',
    })
    expect(polling.runNowTriggeredByTaskId['mon-1']).toBe(false)
  })
})
