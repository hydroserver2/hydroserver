import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'
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
    things: {
      listAllItems: vi.fn(),
    },
  },
  DataConnection: class {},
  User: class {
    accountType = 'standard'
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
    default: { template: '<nav data-testid="nav-rail" />' },
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

vi.mock('@/components/Workspace/OrchestrationWorkspaceManager.vue', () => ({
  default: { template: '<div data-testid="workspace-manager" />' },
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

vi.mock('@/components/Orchestration/data-products/ExpressionForm.vue', () => ({
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
  WorkspaceToolbar: {
    template: '<div />',
  },
  OrchestrationNavRail: {
    template: '<nav data-testid="nav-rail" />',
  },
  OrchestrationContextSidebar: {
    template: '<aside />',
  },
  TaskListPanel: {
    template: '<section />',
  },
  OrchestrationWorkspaceManager: {
    template: '<div data-testid="workspace-manager" />',
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
  ExpressionForm: {
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

  it('keeps the nav rail and shows guidance when no workspace is selected', async () => {
    const { default: Orchestration } = await import('@/pages/Orchestration.vue')

    const wrapper = shallowMount(Orchestration, {
      global: {
        stubs,
      },
    })

    await flushPromises()

    expect(useOrchestrationStore().activeView).toBe('tasks')
    expect(wrapper.find('[data-testid="nav-rail"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="no-selected-workspace"]').exists()).toBe(
      true
    )
    expect(wrapper.text()).toContain('Create a new workspace')
    expect(wrapper.text()).toContain('edit permissions')
    expect(wrapper.find('[data-testid="workspace-manager"]').exists()).toBe(
      false
    )
    expect(replaceMock).not.toHaveBeenCalled()
  })

  it('renders workspace management when the workspaces view is selected', async () => {
    routeMock.params = { view: 'workspaces' }
    const { default: Orchestration } = await import('@/pages/Orchestration.vue')

    const wrapper = shallowMount(Orchestration, {
      global: {
        stubs,
      },
    })

    await flushPromises()

    expect(useOrchestrationStore().activeView).toBe('workspaces')
    expect(wrapper.find('[data-testid="nav-rail"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="workspace-manager"]').exists()).toBe(
      true
    )
    expect(wrapper.find('[data-testid="no-selected-workspace"]').exists()).toBe(
      false
    )
  })

  it('opens workspaces from the base orchestration route when no workspace is selected', () => {
    const route = routes.find((item) => item.name === 'Orchestration')
    const redirect = route?.redirect as () => string

    expect(redirect()).toBe('/orchestration/workspaces')

    useWorkspaceStore().selectedWorkspace = { id: 'workspace-1' } as any

    expect(redirect()).toBe('/orchestration/ingestion')
  })
})
