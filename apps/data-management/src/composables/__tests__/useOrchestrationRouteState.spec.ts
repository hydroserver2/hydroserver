import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorkspaceStore } from '@/store/workspaces'
import {
  detailTypeForTaskRow,
  normalizeOrchestrationTaskDetailType,
  normalizeOrchestrationView,
  ORCHESTRATION_DETAIL_ROUTE_NAMES,
  ORCHESTRATION_VIEW_ROUTE_NAME,
  useOrchestrationRouteState,
} from '../orchestration/useOrchestrationRouteState'

const { routeMock, pushMock, replaceMock } = vi.hoisted(() => ({
  routeMock: {
    meta: {} as Record<string, unknown>,
    params: {} as Record<string, unknown>,
    query: {} as Record<string, unknown>,
  },
  pushMock: vi.fn(),
  replaceMock: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => routeMock,
}))

vi.mock('@/router/router', () => ({
  default: {
    push: pushMock,
    replace: replaceMock,
  },
}))

describe('useOrchestrationRouteState', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    routeMock.meta = {}
    routeMock.params = {}
    routeMock.query = {}
    pushMock.mockReset()
    replaceMock.mockReset()
  })

  it('normalizes view and task detail route values', () => {
    expect(normalizeOrchestrationView('quality')).toBe('quality')
    expect(normalizeOrchestrationView(['aggregation'])).toBe('aggregation')
    expect(normalizeOrchestrationView('nope')).toBeNull()
    expect(normalizeOrchestrationView('')).toBeNull()

    expect(normalizeOrchestrationTaskDetailType('rating-curve')).toBe(
      'rating-curve'
    )
    expect(normalizeOrchestrationTaskDetailType(['expression'])).toBe(
      'expression'
    )
    expect(normalizeOrchestrationTaskDetailType('workspaces')).toBeNull()
  })

  it('maps task rows to their detail route types', () => {
    expect(detailTypeForTaskRow({ kind: 'etl' } as any)).toBe('ingestion')
    expect(detailTypeForTaskRow({ kind: 'monitoring' } as any)).toBe('quality')
    expect(
      detailTypeForTaskRow({
        kind: 'dataProduct',
        taskType: 'Aggregation',
      } as any)
    ).toBe('aggregation')
    expect(
      detailTypeForTaskRow({
        kind: 'dataProduct',
        taskType: 'Expression',
      } as any)
    ).toBe('expression')
    expect(detailTypeForTaskRow({ kind: 'dataProduct' } as any)).toBeNull()
  })

  it('derives current route state from detail routes and query aliases', () => {
    routeMock.meta = { orchestrationTaskDetail: 'rating-curve' }
    routeMock.params = { view: 'ingestion' }
    routeMock.query = {
      task_id: 'task-1',
      run_id: ['run-1'],
      workspaceId: 'workspace-1',
      dataConnectionId: 'connection-1',
      thingId: 'thing-1',
    }

    const state = useOrchestrationRouteState()

    expect(state.view.value).toBe('aggregation')
    expect(state.taskDetailType.value).toBe('rating-curve')
    expect(state.taskKind.value).toBe('dataProduct')
    expect(state.taskId.value).toBe('task-1')
    expect(state.runId.value).toBe('run-1')
    expect(state.workspaceId.value).toBe('workspace-1')
    expect(state.dataConnectionId.value).toBe('connection-1')
    expect(state.siteId.value).toBe('thing-1')
    expect(state.hasTaskDetails.value).toBe(true)
  })

  it('replaces the active view while preserving workspace and selected group context', async () => {
    routeMock.query = {
      workspace_id: 'workspace-1',
      task_id: 'task-1',
      run_id: 'run-1',
      data_connection_id: 'connection-1',
      site_id: 'site-1',
    }

    const state = useOrchestrationRouteState()
    await state.replaceView('ingestion', 'connection-2')

    expect(replaceMock).toHaveBeenCalledWith({
      name: ORCHESTRATION_VIEW_ROUTE_NAME,
      params: { view: 'ingestion' },
      query: {
        workspace_id: 'workspace-1',
        data_connection_id: 'connection-2',
      },
    })
  })

  it('uses the selected workspace when building query state', async () => {
    useWorkspaceStore().selectedWorkspace = { id: 'workspace-store' } as any

    const state = useOrchestrationRouteState()
    await state.replaceView('quality', 'site-2')

    expect(replaceMock).toHaveBeenCalledWith({
      name: ORCHESTRATION_VIEW_ROUTE_NAME,
      params: { view: 'quality' },
      query: {
        workspace_id: 'workspace-store',
        site_id: 'site-2',
      },
    })
  })

  it('keeps the route workspace over the selected workspace when not overridden', async () => {
    routeMock.query = {
      workspace_id: 'workspace-old',
      data_connection_id: 'connection-1',
    }
    useWorkspaceStore().selectedWorkspace = { id: 'workspace-new' } as any

    const state = useOrchestrationRouteState()
    await state.replaceSelectedGroup('ingestion', 'connection-2')

    expect(replaceMock).toHaveBeenCalledWith({
      name: ORCHESTRATION_VIEW_ROUTE_NAME,
      params: { view: 'ingestion' },
      query: {
        workspace_id: 'workspace-old',
        data_connection_id: 'connection-2',
      },
    })
  })

  it('forces the overridden workspace into the route when the selection changes', async () => {
    routeMock.query = {
      workspace_id: 'workspace-old',
      data_connection_id: 'connection-1',
    }

    const state = useOrchestrationRouteState()
    await state.replaceSelectedGroup(
      'ingestion',
      'connection-2',
      'workspace-new'
    )

    expect(replaceMock).toHaveBeenCalledWith({
      name: ORCHESTRATION_VIEW_ROUTE_NAME,
      params: { view: 'ingestion' },
      query: {
        workspace_id: 'workspace-new',
        data_connection_id: 'connection-2',
      },
    })
  })

  it('updates only the workspace query on the workspaces view when overridden', async () => {
    routeMock.query = {
      workspace_id: 'workspace-old',
      data_connection_id: 'connection-1',
      site_id: 'site-1',
    }

    const state = useOrchestrationRouteState()
    await state.replaceView('workspaces', null, 'workspace-new')

    expect(replaceMock).toHaveBeenCalledWith({
      name: ORCHESTRATION_VIEW_ROUTE_NAME,
      params: { view: 'workspaces' },
      query: {
        workspace_id: 'workspace-new',
      },
    })
  })

  it('does not replace selected group while a detail route is active', async () => {
    routeMock.meta = { orchestrationTaskDetail: 'quality' }

    const state = useOrchestrationRouteState()
    await state.replaceSelectedGroup('quality', 'site-1')

    expect(replaceMock).not.toHaveBeenCalled()
  })

  it('closes task details by clearing detail query parameters', async () => {
    routeMock.meta = { orchestrationView: 'quality' }
    routeMock.query = {
      workspace_id: 'workspace-1',
      taskId: 'task-1',
      runId: 'run-1',
      taskKind: 'monitoring',
      site_id: 'site-1',
    }

    const state = useOrchestrationRouteState()
    await state.closeTaskDetails()

    expect(replaceMock).toHaveBeenCalledWith({
      name: ORCHESTRATION_VIEW_ROUTE_NAME,
      params: { view: 'quality' },
      query: {
        workspace_id: 'workspace-1',
        site_id: 'site-1',
      },
    })
  })

  it('does not replace the route when there are no task details to close', async () => {
    const state = useOrchestrationRouteState()
    await state.closeTaskDetails()

    expect(replaceMock).not.toHaveBeenCalled()
  })

  it('pushes task details for supported task rows', async () => {
    routeMock.query = {
      workspace_id: 'workspace-1',
      task_id: 'previous-task',
      run_id: 'run-1',
      site_id: 'site-1',
    }

    const state = useOrchestrationRouteState()
    await state.pushTaskDetails({
      id: 'task-2',
      kind: 'dataProduct',
      taskType: 'Rating curve',
    } as any)

    expect(pushMock).toHaveBeenCalledWith({
      name: ORCHESTRATION_DETAIL_ROUTE_NAMES['rating-curve'],
      params: { view: 'aggregation' },
      query: {
        workspace_id: 'workspace-1',
        site_id: 'site-1',
        task_id: 'task-2',
      },
    })
  })

  it('skips pushing task details for unsupported rows', async () => {
    const state = useOrchestrationRouteState()
    await state.pushTaskDetails({ id: 'task-1', kind: 'dataProduct' } as any)

    expect(pushMock).not.toHaveBeenCalled()
  })
})
