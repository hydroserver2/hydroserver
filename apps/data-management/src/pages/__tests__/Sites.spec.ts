import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { useWorkspaceStore } from '@/store/workspaces'

const {
  hasBootstrappedWorkspacesState,
  isAppInitializingState,
  listAllItemsMock,
  listThingSiteSummariesMock,
  routerPushMock,
} =
  vi.hoisted(() => ({
    hasBootstrappedWorkspacesState: { value: false },
    isAppInitializingState: { value: false },
    listAllItemsMock: vi.fn(),
    listThingSiteSummariesMock: vi.fn(),
    routerPushMock: vi.fn(),
  }))

vi.mock('@hydroserver/client', () => ({
  User: class User {
    email = ''
  },
  PermissionAction: {
    Create: 'Create',
  },
  PermissionResource: {
    Thing: 'Thing',
  },
  default: {
    workspaces: {
      listAllItems: listAllItemsMock,
    },
  },
}))

vi.mock('@/api/thingSiteSummaries', () => ({
  listThingSiteSummaries: listThingSiteSummariesMock,
}))

vi.mock('@/bootstrap/appInitialization', () => ({
  hasBootstrappedWorkspaces: hasBootstrappedWorkspacesState,
  isAppInitializing: isAppInitializingState,
  startAppInitialization: vi.fn(),
}))

vi.mock('@/components/Maps/OpenLayersMap.vue', () => ({
  default: {
    name: 'OpenLayersMap',
    template: '<div />',
  },
}))

vi.mock('@/components/Site/SiteForm.vue', () => ({
  default: {
    name: 'SiteForm',
    template: '<div />',
  },
}))

vi.mock('@/components/Site/SiteFilterToolbar.vue', () => ({
  default: {
    name: 'SiteFilterToolbar',
    template: '<div />',
  },
}))

vi.mock('@/components/Workspace/WorkspaceToolbar.vue', () => ({
  default: {
    name: 'WorkspaceToolbar',
    template: '<div />',
  },
}))

vi.mock('@/components/base/FullScreenLoader.vue', () => ({
  default: {
    name: 'FullScreenLoader',
    template: '<div />',
  },
}))

vi.mock('@/utils/maps/markers', () => ({
  addColorToMarkers: (things: unknown[]) => things,
}))

vi.mock('@/composables/useWorkspacePermissions', () => ({
  useWorkspacePermissions: () => ({
    hasPermission: () => true,
  }),
}))

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()

  return {
    ...actual,
    useRouter: () => ({
      push: routerPushMock,
    }),
  }
})

import Sites from '../Sites.vue'

const mountSites = () =>
  shallowMount(Sites, {
    global: {
      stubs: {
        'v-btn-add': true,
      },
    },
  })

describe('Sites page', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    hasBootstrappedWorkspacesState.value = false
    isAppInitializingState.value = false
    listAllItemsMock.mockReset()
    listThingSiteSummariesMock.mockReset()
    routerPushMock.mockReset()
  })

  it('clears a stale workspace selection without requesting site summaries', async () => {
    const workspaceStore = useWorkspaceStore()
    workspaceStore.selectedWorkspace = {
      id: 'stale-workspace',
      name: 'Stale workspace',
      isPrivate: false,
    } as any

    listAllItemsMock.mockResolvedValue([])

    const wrapper = mountSites()

    await flushPromises()

    expect(listThingSiteSummariesMock).not.toHaveBeenCalled()
    expect(workspaceStore.selectedWorkspace).toBeNull()
  })

  it('loads site summaries once after bootstrapped workspaces are available', async () => {
    const workspaceStore = useWorkspaceStore()
    workspaceStore.selectedWorkspace = {
      id: 'workspace-1',
      name: 'Workspace 1',
      isPrivate: false,
    } as any

    hasBootstrappedWorkspacesState.value = true
    listThingSiteSummariesMock.mockResolvedValue([])

    mountSites()

    await flushPromises()

    expect(listThingSiteSummariesMock).toHaveBeenCalledTimes(1)
    expect(listThingSiteSummariesMock).toHaveBeenCalledWith('workspace-1')
  })
})
