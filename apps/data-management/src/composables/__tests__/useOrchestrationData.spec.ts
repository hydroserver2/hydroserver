import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useOrchestrationData } from '../orchestration/useOrchestrationData'
import { useWorkspaceStore } from '@/store/workspaces'

const {
  dataConnectionsListMock,
  dataConnectionsResponseMock,
  tasksListMock,
  dataProductTasksListMock,
  monitoringTasksListMock,
  monitoringSitesTaskSummariesMock,
} = vi.hoisted(() => ({
  dataConnectionsListMock: vi.fn(),
  dataConnectionsResponseMock: vi.fn(),
  tasksListMock: vi.fn(),
  dataProductTasksListMock: vi.fn(),
  monitoringTasksListMock: vi.fn(),
  monitoringSitesTaskSummariesMock: vi.fn(),
}))

vi.mock('@hydroserver/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@hydroserver/client')>()

  return {
    ...actual,
    default: {
      ...actual.default,
      dataConnections: {
        listAllItems: dataConnectionsListMock,
        list: dataConnectionsResponseMock,
      },
      tasks: { listAllItems: tasksListMock },
      dataProductTasks: { listAllItems: dataProductTasksListMock },
      monitoringTasks: { listAllItems: monitoringTasksListMock },
      monitoringSites: { listTaskSummaries: monitoringSitesTaskSummariesMock },
    },
  }
})

describe('useOrchestrationData', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads orchestration summaries for a workspace', async () => {
    dataConnectionsListMock.mockResolvedValue([{ id: 'dc-1', name: 'Source' }])
    monitoringSitesTaskSummariesMock.mockResolvedValue({
      ok: true,
      data: [{ id: 'monitoringSite-1', name: 'Site' }],
    })

    const data = useOrchestrationData()
    await data.fetchAll('workspace-1')

    expect(data.loading.value).toBe(false)
    expect(data.dataConnections.value.map((item) => item.id)).toEqual(['dc-1'])
    expect(data.workspaceTasks.value).toEqual([])
    expect(data.dataProductTasks.value).toEqual([])
    expect(data.monitoringTasks.value).toEqual([])
    expect(data.monitoringSites.value.map((item) => item.id)).toEqual([
      'monitoringSite-1',
    ])
    expect(dataConnectionsListMock).toHaveBeenCalledWith({
      workspaceId: 'workspace-1',
      sortby: 'name',
    })
    expect(monitoringSitesTaskSummariesMock).toHaveBeenCalledWith({
      workspaceId: ['workspace-1'],
    })
    expect(tasksListMock).not.toHaveBeenCalled()
    expect(dataProductTasksListMock).not.toHaveBeenCalled()
    expect(monitoringTasksListMock).not.toHaveBeenCalled()
  })

  it('ignores stale fetchAll responses', async () => {
    let resolveFirst!: (items: unknown[]) => void
    const firstRequest = new Promise((resolve) => {
      resolveFirst = resolve
    })

    dataConnectionsListMock
      .mockReturnValueOnce(firstRequest)
      .mockResolvedValueOnce([{ id: 'dc-2' }])
    monitoringSitesTaskSummariesMock.mockResolvedValue({ ok: true, data: [] })

    const data = useOrchestrationData()
    const staleLoad = data.fetchAll('workspace-1')
    await data.fetchAll('workspace-2')
    resolveFirst([{ id: 'dc-1' }])
    await staleLoad

    expect(data.dataConnections.value.map((item) => item.id)).toEqual(['dc-2'])
    expect(data.loading.value).toBe(false)
  })

  it('loads detailed tasks only for the selected group', async () => {
    tasksListMock.mockResolvedValue([{ id: 'etl-1' }])
    dataProductTasksListMock.mockResolvedValue([{ id: 'dp-1' }])
    monitoringTasksListMock.mockResolvedValue([{ id: 'mon-1' }])

    const data = useOrchestrationData()

    await data.fetchTasksForGroup('ingestion', 'dc-1', 'workspace-1')
    expect(data.workspaceTasks.value.map((item) => item.id)).toEqual(['etl-1'])
    expect(tasksListMock).toHaveBeenCalledWith({
      workspaceId: ['workspace-1'],
      dataConnectionId: ['dc-1'],
      sortby: ['name'],
    })

    await data.fetchTasksForGroup(
      'aggregation',
      'monitoringSite-1',
      'workspace-1'
    )
    expect(data.dataProductTasks.value.map((item) => item.id)).toEqual(['dp-1'])
    expect(dataProductTasksListMock).toHaveBeenCalledWith({
      workspaceId: ['workspace-1'],
      monitoringSiteId: ['monitoringSite-1'],
      sortby: ['name'],
    })

    await data.fetchTasksForGroup('quality', 'monitoringSite-1', 'workspace-1')
    expect(data.monitoringTasks.value.map((item) => item.id)).toEqual(['mon-1'])
    expect(monitoringTasksListMock).toHaveBeenCalledWith({
      workspaceId: ['workspace-1'],
      monitoringSiteId: ['monitoringSite-1'],
      sortby: ['name'],
    })
  })

  it('does not restore tasks from a request after its group is cleared', async () => {
    let resolveTasks!: (items: unknown[]) => void
    tasksListMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveTasks = resolve
      })
    )

    const data = useOrchestrationData()
    const staleLoad = data.fetchTasksForGroup(
      'ingestion',
      'dc-old',
      'workspace-1'
    )

    await data.fetchTasksForGroup('ingestion', null, 'workspace-1')
    resolveTasks([{ id: 'etl-stale' }])
    await staleLoad

    expect(data.workspaceTasks.value).toEqual([])
    expect(data.loadedTaskGroup.value).toBeNull()
    expect(data.taskLoading.value).toBe(false)
  })

  it('invalidates a pending task request when workspace summaries reload', async () => {
    let resolveTasks!: (items: unknown[]) => void
    tasksListMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveTasks = resolve
      })
    )
    dataConnectionsListMock.mockResolvedValue([])
    monitoringSitesTaskSummariesMock.mockResolvedValue({ ok: true, data: [] })

    const data = useOrchestrationData()
    const staleLoad = data.fetchTasksForGroup(
      'ingestion',
      'dc-old',
      'workspace-old'
    )

    await data.fetchAll('workspace-new')
    resolveTasks([{ id: 'etl-stale' }])
    await staleLoad

    expect(data.workspaceTasks.value).toEqual([])
    expect(data.loadedTaskGroup.value).toBeNull()
    expect(data.taskLoading.value).toBe(false)
  })

  it('refreshes data connections without replacing other loaded data', async () => {
    dataConnectionsListMock.mockResolvedValue([{ id: 'dc-3' }])

    const data = useOrchestrationData()
    data.workspaceTasks.value = [{ id: 'etl-1' }] as any

    await data.refreshDataConnections('workspace-1')

    expect(data.dataConnections.value.map((item) => item.id)).toEqual(['dc-3'])
    expect(data.workspaceTasks.value.map((item) => item.id)).toEqual(['etl-1'])
  })

  it.each(['etl', 'dataProduct', 'monitoring'] as const)(
    'refreshes %s summary counts without clearing loaded tasks',
    async (kind) => {
      useWorkspaceStore().selectedWorkspace = { id: 'workspace-1' } as any
      const summary = {
        id: 'parent-1',
        taskAttentionCount: 1,
        monitoringTaskAttentionCount: 1,
        productTaskAttentionCount: 1,
      }
      dataConnectionsResponseMock.mockResolvedValue({
        ok: true,
        data: [summary],
      })
      monitoringSitesTaskSummariesMock.mockResolvedValue({
        ok: true,
        data: [summary],
      })
      const data = useOrchestrationData()
      data.workspaceTasks.value = [{ id: 'etl-1' }] as any
      data.monitoringTasks.value = [{ id: 'mon-1' }] as any
      await data.refreshTaskSummaries(kind)

      const summaries =
        kind === 'etl' ? data.dataConnections : data.monitoringSites
      expect(summaries.value).toEqual([summary])
      expect(data.workspaceTasks.value.map((task) => task.id)).toEqual([
        'etl-1',
      ])
      expect(data.monitoringTasks.value.map((task) => task.id)).toEqual([
        'mon-1',
      ])
    }
  )

  it('preserves badge counts and reports a failed summary request for retry', async () => {
    useWorkspaceStore().selectedWorkspace = { id: 'workspace-1' } as any
    const data = useOrchestrationData()
    const summary = { id: 'site-1', monitoringTaskAttentionCount: 1 }
    data.monitoringSites.value = [summary] as any
    monitoringSitesTaskSummariesMock.mockResolvedValue({
      ok: false,
      message: 'Offline',
    })

    await expect(data.refreshTaskSummaries('monitoring')).rejects.toThrow(
      'Offline'
    )
    expect(data.monitoringSites.value).toEqual([summary])
  })

  it('ignores a summary refresh from a previous workspace', async () => {
    const workspaceStore = useWorkspaceStore()
    workspaceStore.selectedWorkspace = { id: 'workspace-1' } as any
    let resolveSummary!: (value: unknown) => void
    monitoringSitesTaskSummariesMock.mockReturnValue(
      new Promise((resolve) => {
        resolveSummary = resolve
      })
    )
    const data = useOrchestrationData()
    const request = data.refreshTaskSummaries('monitoring')
    workspaceStore.selectedWorkspace = { id: 'workspace-2' } as any
    data.monitoringSites.value = [{ id: 'site-2' }] as any
    resolveSummary({ ok: true, data: [{ id: 'site-1' }] })
    await request

    expect(data.monitoringSites.value.map((site) => site.id)).toEqual([
      'site-2',
    ])
  })
})
