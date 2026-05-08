import { flushPromises, mount, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  dataProductGetMock,
  dataProductUpdateMock,
  monitoringGetMock,
  taskGetMock,
} = vi.hoisted(() => ({
  dataProductGetMock: vi.fn(),
  dataProductUpdateMock: vi.fn(),
  monitoringGetMock: vi.fn(),
  taskGetMock: vi.fn(),
}))

vi.mock('@hydroserver/client', () => ({
  default: {
    dataProductTasks: {
      get: dataProductGetMock,
      getItem: vi.fn(),
      getTaskRun: vi.fn(),
      getTaskRuns: vi.fn(),
      runTask: vi.fn(),
      update: dataProductUpdateMock,
      delete: vi.fn(),
    },
    monitoringTasks: {
      get: monitoringGetMock,
      getItem: vi.fn(),
      getTaskRun: vi.fn(),
      getTaskRuns: vi.fn(),
      runTask: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
    tasks: {
      get: taskGetMock,
      getItem: vi.fn(),
      getTaskRun: vi.fn(),
      getTaskRuns: vi.fn(),
      runTask: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
  },
  PermissionAction: { Edit: 'edit' },
  PermissionResource: { Workspace: 'workspace' },
  User: class User {
    email = 'editor@example.com'
  },
}))

vi.mock('@/router/router', () => ({
  default: {
    push: vi.fn(),
    replace: vi.fn(),
    resolve: vi.fn(() => ({ href: '/orchestration' })),
  },
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    fullPath: '/orchestration',
    params: {},
    query: {},
  }),
}))

vi.mock('@/utils/notifications', () => ({
  Snackbar: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('@/components/Orchestration/ingestion/Swimlanes.vue', () => ({
  default: { template: '<div />' },
}))

vi.mock('@/components/Orchestration/ingestion/IngestionTaskForm.vue', () => ({
  default: {
    props: ['oldTask', 'dataConnection', 'workspaceId'],
    template: '<div class="task-form-stub" />',
  },
}))

vi.mock('@/composables/useWorkspacePermissions', () => ({
  useWorkspacePermissions: () => ({
    checkPermissionsByWorkspaceId: vi.fn(() => true),
    hasPermission: vi.fn(() => true),
    isAdmin: vi.fn(() => false),
    isOwner: vi.fn(() => false),
  }),
}))

const makeDataProductTask = () => ({
  id: 'product-task-1',
  name: 'Rating curve task',
  description: null,
  thing: { id: 'thing-1', name: 'Site 1', workspaceId: 'workspace-1' },
  aggregationTransformations: [],
  compositeExpressionTransformations: [],
  expressionTransformations: [],
  ratingCurveTransformations: [{ id: 'rating-transform-1' }],
  latestRun: null,
  schedule: {
    enabled: true,
    startTime: null,
    nextRunAt: null,
    crontab: null,
    interval: 1,
    intervalPeriod: 'days',
  },
})

const makeEtlTask = () => ({
  id: 'etl-task-1',
  name: 'Ingestion task',
  description: null,
  dataConnection: {
    id: 'connection-1',
    name: 'Connection 1',
    workspace: { id: 'workspace-1', name: 'Workspace 1' },
  },
  mappings: [],
  taskVariables: {},
  latestRun: null,
  schedule: {
    enabled: true,
    startTime: null,
    nextRunAt: null,
    crontab: null,
    interval: 1,
    intervalPeriod: 'days',
  },
})

const globalStubs = {
  'v-dialog': {
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template:
      '<div><slot name="activator" :props="{ onClick: () => $emit(\'update:modelValue\', true) }" /><div v-if="modelValue"><slot /></div></div>',
  },
  'v-icon': { template: '<span />' },
  'v-tooltip': {
    template: '<div><slot name="activator" :props="{}" /><slot /></div>',
  },
  'v-tab': { template: '<button><slot /></button>' },
  'v-tabs': { template: '<div><slot /></div>' },
  TaskRunHistory: { template: '<div />' },
  TaskStatus: { template: '<span />' },
  IngestionTaskForm: {
    props: ['oldTask', 'dataConnection', 'workspaceId'],
    template: '<div class="task-form-stub" />',
  },
}

const seedWorkspace = async () => {
  const { useWorkspaceStore } = await import('@/store/workspaces')
  useWorkspaceStore().workspaces = [
    {
      id: 'workspace-1',
      name: 'Workspace 1',
      collaboratorRole: { name: 'editor' },
    } as any,
  ]
}

describe('TaskDetails', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    dataProductGetMock.mockReset()
    dataProductUpdateMock.mockReset()
    monitoringGetMock.mockReset()
    taskGetMock.mockReset()
    taskGetMock.mockResolvedValue({
      ok: true,
      data: makeEtlTask(),
    })
    dataProductGetMock.mockResolvedValue({
      ok: true,
      data: makeDataProductTask(),
    })
    dataProductUpdateMock.mockResolvedValue({
      ok: true,
      data: makeDataProductTask(),
    })
  })

  it('fetches rating-curve task details from the data-product task endpoint', async () => {
    const { default: RatingCurveTaskDetails } = await import(
      '@/components/Orchestration/data-products/RatingCurveTaskDetails.vue'
    )
    await seedWorkspace()

    mount(RatingCurveTaskDetails as any, {
      props: {
        embedded: true,
        taskId: 'product-task-1',
      },
      global: {
        stubs: globalStubs,
      },
    })
    await flushPromises()

    expect(dataProductGetMock).toHaveBeenCalledWith('product-task-1', {
      expand_related: true,
    })
    expect(taskGetMock).not.toHaveBeenCalled()
    expect(monitoringGetMock).not.toHaveBeenCalled()
  })

  // it('uses the data-product task service when pausing a data-product task', async () => {
  //   const { default: SimpleProductTaskDetails } = await import(
  //     '@/components/Orchestration/data-products/SimpleProductTaskDetails.vue'
  //   )
  //   await seedWorkspace()

  //   const wrapper = shallowMount(SimpleProductTaskDetails as any, {
  //     props: {
  //       taskLabel: 'rating curve',
  //       taskId: 'product-task-1',
  //       embedded: true,
  //     },
  //     global: {
  //       stubs: globalStubs,
  //     },
  //   })
  //   await flushPromises()

  //   await (wrapper.vm as any).togglePaused()
  //   await flushPromises()

  //   expect(dataProductUpdateMock).toHaveBeenCalledWith(
  //     expect.objectContaining({
  //       id: 'product-task-1',
  //       schedule: expect.objectContaining({ enabled: false }),
  //     })
  //   )
  // })

  it('loads ingestion details in the ingestion component', async () => {
    const { default: IngestionTaskDetails } = await import(
      '@/components/Orchestration/ingestion/IngestionTaskDetails.vue'
    )
    await seedWorkspace()

    const wrapper = shallowMount(IngestionTaskDetails as any, {
      props: {
        taskId: 'etl-task-1',
        embedded: true,
      },
      global: {
        stubs: globalStubs,
      },
    })
    await flushPromises()

    expect(taskGetMock).toHaveBeenCalledWith('etl-task-1', {
      expand_related: true,
    })
    expect(wrapper.text()).toContain('Ingestion task')
  })
})
