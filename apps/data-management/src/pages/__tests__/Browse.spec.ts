import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { useWorkspaceStore } from '@/store/workspaces'

const {
  hasBootstrappedWorkspacesState,
  startAppInitializationMock,
  listAllItemsMock,
  listSiteSummariesMock,
  session,
} = vi.hoisted(() => ({
  hasBootstrappedWorkspacesState: { value: false },
  startAppInitializationMock: vi.fn(),
  listAllItemsMock: vi.fn(),
  listSiteSummariesMock: vi.fn(),
  session: { isAuthenticated: true },
}))

vi.mock('@hydroserver/client', () => ({
  User: class User {
    email = ''
  },
  PermissionAction: { Create: 'create', Edit: 'edit', Delete: 'delete' },
  PermissionResource: { MonitoringSite: 'MonitoringSite' },
  default: {
    session,
    workspaces: { listAllItems: listAllItemsMock },
    monitoringSites: { listSiteSummaries: listSiteSummariesMock },
  },
}))

vi.mock('@/bootstrap/appInitialization', () => ({
  hasBootstrappedWorkspaces: hasBootstrappedWorkspacesState,
  startAppInitialization: startAppInitializationMock,
}))

vi.mock('@/components/Maps/OpenLayersMap.vue', () => ({
  default: { name: 'OpenLayersMap', template: '<div />' },
}))
vi.mock('@/components/Browse/BrowseFilterTool.vue', () => ({
  default: { name: 'BrowseFilterTool', template: '<div />' },
}))
vi.mock('@/components/Site/SiteForm.vue', () => ({
  default: { name: 'SiteForm', template: '<div />' },
}))
vi.mock('@/components/Site/SiteDeleteModal.vue', () => ({
  default: { name: 'SiteDeleteModal', template: '<div />' },
}))
vi.mock('@/components/Site/SiteAccessControl.vue', () => ({
  default: { name: 'SiteAccessControl', template: '<div />' },
}))
vi.mock('@hydroserver/design-system/vue', () => ({
  HsFullScreenLoader: { name: 'HsFullScreenLoader', template: '<div />' },
}))
vi.mock('@/composables/useWorkspacePermissions', () => ({
  useWorkspacePermissions: () => ({ hasPermission: () => true }),
}))

import Browse from '../Browse.vue'

describe('Browse page', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.stubGlobal('matchMedia', () => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
    hasBootstrappedWorkspacesState.value = false
    session.isAuthenticated = true
    startAppInitializationMock.mockReset().mockResolvedValue(undefined)
    listAllItemsMock.mockReset().mockResolvedValue([])
    listSiteSummariesMock.mockReset().mockResolvedValue({ ok: true, data: [] })
  })

  it('uses the workspaces app startup loaded instead of fetching them again', async () => {
    hasBootstrappedWorkspacesState.value = true

    shallowMount(Browse)
    await flushPromises()

    expect(startAppInitializationMock).toHaveBeenCalled()
    expect(listAllItemsMock).not.toHaveBeenCalled()
  })

  it('fetches the workspaces itself when app startup could not', async () => {
    const workspaces = [{ id: 'ws-1', name: 'Workspace 1' }]
    listAllItemsMock.mockResolvedValue(workspaces)

    shallowMount(Browse)
    await flushPromises()

    expect(listAllItemsMock).toHaveBeenCalledWith({ isAssociated: true })
    expect(useWorkspaceStore().workspaces).toEqual(workspaces)
  })

  it('waits for app startup before deciding whether to fetch', async () => {
    let finishStartup = () => {}
    startAppInitializationMock.mockReturnValue(
      new Promise<void>((resolve) => {
        finishStartup = () => {
          hasBootstrappedWorkspacesState.value = true
          resolve()
        }
      })
    )

    shallowMount(Browse)
    await flushPromises()
    expect(listAllItemsMock).not.toHaveBeenCalled()

    finishStartup()
    await flushPromises()
    expect(listAllItemsMock).not.toHaveBeenCalled()
  })

  it('does not fetch workspaces for an anonymous visitor', async () => {
    session.isAuthenticated = false

    shallowMount(Browse)
    await flushPromises()

    expect(listAllItemsMock).not.toHaveBeenCalled()
  })
})
