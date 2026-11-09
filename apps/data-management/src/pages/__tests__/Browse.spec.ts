import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { useWorkspaceStore } from '@/store/workspaces'
import { useUserStore } from '@/store/user'

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
  PermissionAction: {
    View: 'view',
    Create: 'create',
    Edit: 'edit',
    Delete: 'delete',
  },
  PermissionResource: {
    MonitoringSite: 'MonitoringSite',
    Workspace: 'Workspace',
    Global: '*',
  },
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
  default: {
    name: 'BrowseFilterTool',
    props: [
      'canRegisterSite',
      'editableWorkspaceIds',
      'deletableWorkspaceIds',
      'myWorkspaceIds',
    ],
    template: '<div />',
  },
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
import Browse from '../Browse.vue'

describe('Browse page', () => {
  beforeEach(() => {
    localStorage.clear()
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

  it('lets an unaffiliated admin create, edit, and delete sites in every workspace', async () => {
    useUserStore().user.email = 'admin@example.com'
    useUserStore().user.isSuperuser = true
    listAllItemsMock.mockResolvedValue([
      {
        id: 'ws-public',
        name: 'Public',
        owner: { email: 'other@example.com' },
        isPrivate: false,
      },
      {
        id: 'ws-private',
        name: 'Private',
        owner: { email: 'other@example.com' },
        isPrivate: true,
      },
    ])

    const wrapper = shallowMount(Browse)
    await flushPromises()

    expect(listAllItemsMock).toHaveBeenCalledWith({})
    const filters = wrapper.findComponent({ name: 'BrowseFilterTool' })
    expect(filters.props('canRegisterSite')).toBe(true)
    expect(filters.props('editableWorkspaceIds')).toEqual([
      'ws-private',
      'ws-public',
    ])
    expect(filters.props('deletableWorkspaceIds')).toEqual([
      'ws-private',
      'ws-public',
    ])
    expect(filters.props('myWorkspaceIds')).toEqual([])
    wrapper.unmount()
  })

  it('keeps site mutations unavailable to a read-only collaborator', async () => {
    useUserStore().user.email = 'viewer@example.com'
    listAllItemsMock.mockResolvedValue([
      {
        id: 'ws-1',
        name: 'Workspace',
        owner: { email: 'other@example.com' },
        collaboratorRole: { permissions: [{ resource: '*', action: 'view' }] },
      },
    ])

    const wrapper = shallowMount(Browse)
    await flushPromises()

    expect(listAllItemsMock).toHaveBeenCalledWith({ isAssociated: true })
    const filters = wrapper.findComponent({ name: 'BrowseFilterTool' })
    expect(filters.props('canRegisterSite')).toBe(false)
    expect(filters.props('editableWorkspaceIds')).toEqual([])
    expect(filters.props('deletableWorkspaceIds')).toEqual([])
    expect(filters.props('myWorkspaceIds')).toEqual(['ws-1'])
    wrapper.unmount()
  })

  it('does not fetch workspaces for an anonymous visitor', async () => {
    session.isAuthenticated = false

    shallowMount(Browse)
    await flushPromises()

    expect(listAllItemsMock).not.toHaveBeenCalled()
  })
})
