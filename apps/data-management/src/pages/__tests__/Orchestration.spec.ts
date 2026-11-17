import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'
import hs from '@hydroserver/client'
import { routes } from '@/router/routes'

const { routeMock, replaceMock } = vi.hoisted(() => ({
  routeMock: {
    meta: {} as Record<string, unknown>,
    params: { view: 'ingestion' } as Record<string, unknown>,
    query: {} as Record<string, unknown>,
  },
  replaceMock: vi.fn(),
}))

vi.mock('vue-router', () => ({
  RouterView: {
    template: '<div />',
  },
  useRoute: () => routeMock,
}))

vi.mock('@/router/router', () => ({
  default: {
    push: vi.fn(),
    replace: replaceMock,
  },
}))

vi.mock('@hydroserver/client', () => ({
  default: {
    dataConnections: {
      delete: vi.fn(),
      listAllItems: vi.fn(),
    },
    dataProductTasks: {
      getItem: vi.fn(),
      getTaskRun: vi.fn(),
      listAllItems: vi.fn(),
      runTask: vi.fn(),
      update: vi.fn(),
    },
    datastreams: {
      listAllItems: vi.fn(),
    },
    monitoringTasks: {
      getItem: vi.fn(),
      getTaskRun: vi.fn(),
      listAllItems: vi.fn(),
      runTask: vi.fn(),
      update: vi.fn(),
    },
    tasks: {
      getItem: vi.fn(),
      getTaskRun: vi.fn(),
      listAllItems: vi.fn(),
      runTask: vi.fn(),
      update: vi.fn(),
    },
    monitoringSites: {
      listAllItems: vi.fn(),
      listTaskSummaries: vi.fn(),
    },
  },
  DataConnection: class {},
  User: class {
    isSuperuser = false
    email = 'user@example.com'
  },
  PermissionAction: {
    Edit: 'edit',
  },
  PermissionResource: {
    Workspace: 'workspace',
  },
}))

vi.mock('@/composables/useWorkspacePermissions', () => ({
  useWorkspacePermissions: () => ({
    hasPermission: vi.fn(() => false),
    isAdmin: vi.fn(() => false),
    isOwner: vi.fn(() => false),
  }),
}))

vi.mock('@/components/Workspace/WorkspaceToolbar.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock(
  '@/components/Orchestration/workbench/OrchestrationNavRail.vue',
  () => ({
    default: {
      template:
        '<nav data-testid="nav-rail"><button data-testid="aggregation-tab" @click="$emit(\'select-tab\', \'aggregation\')" /></nav>',
    },
  })
)

vi.mock(
  '@/components/Orchestration/workbench/OrchestrationContextSidebar.vue',
  () => ({
    default: { template: '<aside />' },
  })
)

vi.mock('@/components/Orchestration/workbench/TaskListPanel.vue', () => ({
  default: { template: '<section />' },
}))

vi.mock(
  '@/components/Orchestration/connections/DataConnectionForm.vue',
  () => ({
    default: { template: '<div />' },
  })
)

vi.mock('@/components/Orchestration/ingestion/IngestionTaskForm.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock(
  '@/components/Orchestration/connections/DeleteDataConnectionCard.vue',
  () => ({
    default: { template: '<div />' },
  })
)

vi.mock('@/components/Orchestration/data-products/AggregationForm.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock('@/components/Orchestration/data-products/DerivationForm.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock('@/components/Orchestration/data-products/RatingCurveForm.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock(
  '@/components/Orchestration/monitoring/QualityManagementForm.vue',
  () => ({
    default: { template: '<div />' },
  })
)

const stubs = {
  HsMasterDetailLayout: {
    template: '<div><slot name="rail" /><slot name="sidebar" /><slot /></div>',
  },
  HsEmptyState: {
    props: ['title'],
    template:
      '<section><h2>{{ title }}</h2><slot /><slot name="actions" /></section>',
  },
  WorkspaceToolbar: {
    template: '<div />',
  },
  OrchestrationNavRail: {
    props: ['tabs'],
    template:
      '<nav data-testid="nav-rail"><span data-testid="quality-issues">{{ tabs.find(tab => tab.id === \'quality\').issues }}</span><button data-testid="aggregation-tab" @click="$emit(\'select-tab\', \'aggregation\')" /></nav>',
  },
  OrchestrationContextSidebar: {
    template: '<aside />',
  },
  TaskListPanel: {
    template: '<section />',
  },
  DataConnectionForm: {
    template: '<div />',
  },
  IngestionTaskForm: {
    template: '<div />',
  },
  DeleteDataConnectionCard: {
    template: '<div />',
  },
  AggregationForm: {
    template: '<div />',
  },
  DerivationForm: {
    template: '<div />',
  },
  RatingCurveForm: {
    template: '<div />',
  },
  QualityManagementForm: {
    template: '<div />',
  },
  'v-dialog': {
    template: '<div><slot /></div>',
  },
  'v-btn': {
    template: '<button><slot /></button>',
  },
  'v-btn-primary': {
    template: '<button><slot /></button>',
  },
}

describe('Orchestration page', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    routeMock.meta = {}
    routeMock.params = { view: 'ingestion' }
    routeMock.query = {}
    replaceMock.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it.each([
    [0, 'Violations found', 1],
    [1, 'OK', 0],
  ] as const)(
    'updates the quality badge from %i after a run becomes %s',
    async (initialIssues, status, finalIssues) => {
      vi.useFakeTimers()
      const workspace = { id: 'workspace-1', name: 'Workspace' } as any
      useWorkspaceStore().workspaces = [workspace]
      useWorkspaceStore().selectedWorkspace = workspace
      useOrchestrationStore().activeTab = 'quality'
      routeMock.params = { view: 'quality' }
      const summary = {
        id: 'site-1',
        name: 'Site',
        monitoringTaskCount: 1,
        monitoringTaskAttentionCount: initialIssues,
        productTaskCount: 0,
        productTaskAttentionCount: 0,
      }
      const task = {
        id: 'mon-1',
        name: 'Quality task',
        monitoringSiteId: 'site-1',
        status: initialIssues ? 'Violations found' : 'OK',
      }
      const pending = {
        id: 'run-1',
        status: 'PENDING',
        displayStatus: 'Pending',
      }
      const completed = {
        id: 'run-1',
        status: 'SUCCESS',
        displayStatus: status,
      }
      vi.mocked(hs.dataConnections.listAllItems).mockResolvedValue([])
      vi.mocked(hs.monitoringSites.listTaskSummaries).mockResolvedValue({
        ok: true,
        data: [summary],
      } as any)
      vi.mocked(hs.monitoringTasks.listAllItems).mockResolvedValue([
        task,
      ] as any)
      vi.mocked(hs.monitoringTasks.runTask).mockResolvedValue({
        ok: true,
        data: pending,
      } as any)
      vi.mocked(hs.monitoringTasks.getTaskRun).mockResolvedValue({
        ok: true,
        data: completed,
      } as any)
      vi.mocked(hs.monitoringTasks.getItem)
        .mockResolvedValueOnce({
          ...task,
          status: 'Pending',
          latestRun: pending,
        } as any)
        .mockResolvedValueOnce({ ...task, status, latestRun: completed } as any)
      const { default: Orchestration } =
        await import('@/pages/Orchestration.vue')
      const wrapper = shallowMount(Orchestration, { global: { stubs } })
      try {
        await flushPromises()
        expect(wrapper.get('[data-testid="quality-issues"]').text()).toBe(
          String(initialIssues)
        )
        const vm = wrapper.vm as any
        await vm.runTaskNow('monitoring', task.id)
        vi.mocked(hs.monitoringSites.listTaskSummaries).mockResolvedValue({
          ok: true,
          data: [{ ...summary, monitoringTaskAttentionCount: finalIssues }],
        } as any)
        await vi.advanceTimersByTimeAsync(3000)

        expect(vm.monitoringTasks[0].status).toBe(status)
        expect(wrapper.get('[data-testid="quality-issues"]').text()).toBe(
          String(finalIssues)
        )
        expect(vm.monitoringTasks).toHaveLength(1)
      } finally {
        wrapper.unmount()
      }
    }
  )

  it('keeps the nav rail and shows guidance when no workspace is selected', async () => {
    const { default: Orchestration } = await import('@/pages/Orchestration.vue')

    const wrapper = shallowMount(Orchestration, {
      global: {
        stubs,
      },
    })

    await flushPromises()

    expect(useOrchestrationStore().activeTab).toBe('ingestion')
    expect(wrapper.find('[data-testid="nav-rail"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="no-selected-workspace"]').exists()).toBe(
      true
    )
    expect(wrapper.text()).toContain('Create a new workspace')
    expect(wrapper.text()).toContain('edit permissions')
    expect(replaceMock).not.toHaveBeenCalled()
  })

  it('redirects the base orchestration route to the ingestion view', () => {
    const route = routes.find((item) => item.name === 'Orchestration')

    expect(route?.redirect).toBe('/orchestration/ingestion')
  })

  it('routes nav-rail selections immediately', async () => {
    const { default: Orchestration } = await import('@/pages/Orchestration.vue')
    const wrapper = shallowMount(Orchestration, {
      global: { stubs },
    })
    await flushPromises()
    replaceMock.mockClear()

    await wrapper.get('[data-testid="aggregation-tab"]').trigger('click')

    expect(replaceMock).toHaveBeenCalledTimes(1)
    expect(replaceMock).toHaveBeenCalledWith({
      name: 'OrchestrationView',
      params: { view: 'aggregation' },
      query: {},
    })
  })
})
