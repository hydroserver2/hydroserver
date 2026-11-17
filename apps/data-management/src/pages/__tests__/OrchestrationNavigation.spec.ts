import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { routes } from '@/router/routes'
import Orchestration from '@/pages/Orchestration.vue'
import { useWorkspaceStore } from '@/store/workspaces'

const { navigation, connectionsMock, tasksMock, productsMock, monitoringMock } =
  vi.hoisted(() => ({
    navigation: { router: null as import('vue-router').Router | null },
    connectionsMock: vi.fn(),
    tasksMock: vi.fn(),
    productsMock: vi.fn(),
    monitoringMock: vi.fn(),
  }))

vi.mock('@/router/router', () => ({
  default: {
    replace: (to: import('vue-router').RouteLocationRaw) =>
      navigation.router!.replace(to),
    push: (to: import('vue-router').RouteLocationRaw) =>
      navigation.router!.push(to),
  },
}))

vi.mock('@hydroserver/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@hydroserver/client')>()
  return {
    ...actual,
    default: {
      ...actual.default,
      dataConnections: { listAllItems: connectionsMock },
      tasks: { listAllItems: tasksMock },
      dataProductTasks: { listAllItems: productsMock },
      monitoringTasks: { listAllItems: monitoringMock },
      monitoringSites: {
        listTaskSummaries: vi.fn().mockResolvedValue({
          ok: true,
          data: [{ id: 'site-1', name: 'River station' }],
        }),
      },
    },
  }
})

vi.mock('@/composables/useWorkspacePermissions', () => ({
  useWorkspacePermissions: () => ({ hasPermission: () => true }),
}))

const details = defineComponent({
  emits: ['close'],
  template:
    '<button data-testid="close-details" @click="$emit(\'close\')">Close details</button>',
})

const cases = [
  {
    view: 'ingestion',
    detail: 'ingestion',
    groupQuery: 'data_connection_id',
    groupId: 'dc-1',
    event: 'select-connection',
    listMock: tasksMock,
  },
  {
    view: 'aggregation',
    detail: 'aggregation',
    groupQuery: 'site_id',
    groupId: 'site-1',
    event: 'select-site',
    listMock: productsMock,
  },
  {
    view: 'quality',
    detail: 'quality',
    groupQuery: 'site_id',
    groupId: 'site-1',
    event: 'select-site',
    listMock: monitoringMock,
  },
] as const

async function openDetails(
  testCase: (typeof cases)[number] = cases[0],
  includeGroup = true
) {
  const route = routes.find((record) => record.name === 'OrchestrationView')!
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: route.path,
        name: route.name,
        meta: route.meta,
        component: Orchestration,
        children: route.children!.map((child) => ({
          path: child.path,
          name: child.name,
          meta: child.meta,
          component: details,
        })),
      },
    ],
  })
  navigation.router = router
  const group = includeGroup
    ? `&${testCase.groupQuery}=${testCase.groupId}`
    : ''
  await router.push(
    `/orchestration/${testCase.view}/details/${testCase.detail}?workspace_id=workspace-1&task_id=task-1${group}`
  )
  await router.isReady()
  const wrapper = mount(RouterView, {
    global: {
      plugins: [router],
      stubs: {
        HsMasterDetailLayout: {
          template: '<div><slot name="sidebar" /><slot /></div>',
        },
        OrchestrationContextSidebar: {
          name: 'OrchestrationContextSidebar',
          emits: ['select-connection', 'select-site'],
          template: '<aside />',
        },
        TaskListPanel: {
          props: ['sortedVisibleTasks', 'loading'],
          template:
            '<section data-testid="task-list"><span v-if="loading">Loading tasks</span><span v-for="task in sortedVisibleTasks" :key="task.id">{{ task.name }}</span></section>',
        },
        'v-dialog': true,
        'v-alert': true,
        'v-btn-primary': true,
      },
    },
  })
  await flushPromises()
  return { router, wrapper }
}

describe('orchestration details-to-list navigation', () => {
  let wrapper: Awaited<ReturnType<typeof openDetails>>['wrapper'] | undefined

  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    useWorkspaceStore().setWorkspaces([
      { id: 'workspace-1', name: 'Workspace 1' } as any,
    ])
    connectionsMock.mockResolvedValue([
      { id: 'dc-1', name: 'Source 1', payload: { type: 'CSV' } },
      { id: 'dc-2', name: 'Source 2', payload: { type: 'CSV' } },
    ])
    const task = {
      id: 'task-1',
      name: 'Expected task',
      dataConnectionId: 'dc-1',
      monitoringSiteId: 'site-1',
      taskVariables: {},
    }
    tasksMock.mockResolvedValue([task])
    productsMock.mockResolvedValue([task])
    monitoringMock.mockResolvedValue([task])
  })

  afterEach(() => wrapper?.unmount())

  it.each(cases)(
    'loads $view tasks on the first click of the already-selected group after a direct details URL',
    async (testCase) => {
      const opened = await openDetails(testCase)
      wrapper = opened.wrapper
      expect(wrapper.find('[data-testid="close-details"]').exists()).toBe(true)
      expect(testCase.listMock).not.toHaveBeenCalled()

      wrapper
        .getComponent({ name: 'OrchestrationContextSidebar' })
        .vm.$emit(testCase.event, testCase.groupId)
      await flushPromises()

      expect(opened.router.currentRoute.value.query.task_id).toBeUndefined()
      expect(testCase.listMock).toHaveBeenCalledTimes(1)
      expect(wrapper.get('[data-testid="task-list"]').text()).toContain(
        'Expected task'
      )
    }
  )

  it.each([true, false])(
    'loads tasks when closing direct details (group included: %s)',
    async (includeGroup) => {
      const opened = await openDetails(cases[0], includeGroup)
      wrapper = opened.wrapper
      await wrapper.get('[data-testid="close-details"]').trigger('click')
      await flushPromises()

      expect(tasksMock).toHaveBeenCalledTimes(1)
      expect(wrapper.get('[data-testid="task-list"]').text()).toContain(
        'Expected task'
      )
      expect(opened.router.currentRoute.value.query.data_connection_id).toBe(
        'dc-1'
      )
    }
  )

  it('loads tasks when browser history returns from direct details to the same group', async () => {
    const opened = await openDetails()
    wrapper = opened.wrapper
    const listRoute = {
      name: 'OrchestrationView',
      params: { view: 'ingestion' },
      query: { workspace_id: 'workspace-1', data_connection_id: 'dc-1' },
    }
    // Exercise navigation that doesn't invoke the sidebar or details close handler.
    await opened.router.push(listRoute)
    await flushPromises()
    expect(wrapper.get('[data-testid="task-list"]').text()).toContain(
      'Expected task'
    )
    opened.router.back()
    await flushPromises()
    expect(wrapper.find('[data-testid="close-details"]').exists()).toBe(true)
    opened.router.forward()
    await flushPromises()
    expect(wrapper.get('[data-testid="task-list"]').text()).toContain(
      'Expected task'
    )
  })

  it('loads the list if details are closed before workspace summaries finish loading', async () => {
    let resolveConnections!: (items: unknown[]) => void
    connectionsMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveConnections = resolve
      })
    )
    const opened = await openDetails()
    wrapper = opened.wrapper
    await wrapper.get('[data-testid="close-details"]').trigger('click')
    await flushPromises()

    expect(tasksMock).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="task-list"]').text()).toContain(
      'Loading tasks'
    )
    resolveConnections([
      { id: 'dc-1', name: 'Source 1', payload: { type: 'CSV' } },
    ])
    await flushPromises()

    expect(tasksMock).toHaveBeenCalledTimes(1)
    expect(wrapper.get('[data-testid="task-list"]').text()).toContain(
      'Expected task'
    )
  })
})
