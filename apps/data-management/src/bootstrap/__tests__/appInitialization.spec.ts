import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { useUserStore } from '@/store/user'
import { useWorkspaceStore } from '@/store/workspaces'

const {
  createHydroServerMock,
  fetchAllVocabulariesMock,
  userGetMock,
  listAllItemsMock,
  sessionState,
  testPinia,
} = vi.hoisted(() => ({
  createHydroServerMock: vi.fn(),
  fetchAllVocabulariesMock: vi.fn(),
  userGetMock: vi.fn(),
  listAllItemsMock: vi.fn(),
  sessionState: {
    isAuthenticated: false,
  },
  testPinia: { value: null as Pinia | null },
}))

vi.mock('@hydroserver/client', () => {
  class User {
    email = ''
  }

  return {
    User,
    createHydroServer: createHydroServerMock,
    default: {
      session: sessionState,
      user: {
        get: userGetMock,
      },
      workspaces: {
        listAllItems: listAllItemsMock,
      },
    },
  }
})

vi.mock('@/composables/useVocabulary', () => ({
  useVocabularyStore: () => ({
    fetchAllVocabularies: fetchAllVocabulariesMock,
  }),
}))

vi.mock('@/plugins/pinia', () => ({
  default: testPinia.value,
}))

describe('app initialization bootstrap', () => {
  beforeEach(() => {
    vi.resetModules()
    const pinia = createPinia()
    setActivePinia(pinia)
    testPinia.value = pinia
    localStorage.clear()
    sessionState.isAuthenticated = false
    createHydroServerMock.mockReset()
    fetchAllVocabulariesMock.mockReset()
    userGetMock.mockReset()
    listAllItemsMock.mockReset()
  })

  it('waits for HydroServer session initialization before resolving router guards', async () => {
    let resolveHydroServer!: () => void
    createHydroServerMock.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveHydroServer = resolve
        })
    )
    fetchAllVocabulariesMock.mockResolvedValue(undefined)

    const {
      startAppInitialization,
      waitForHydroServerInitialization,
      isHydroServerReady,
    } = await import('../appInitialization')

    void startAppInitialization()

    let waitResolved = false
    const guardWait = waitForHydroServerInitialization().then(() => {
      waitResolved = true
    })

    await Promise.resolve()
    expect(waitResolved).toBe(false)
    expect(isHydroServerReady.value).toBe(false)

    resolveHydroServer()
    await guardWait

    expect(waitResolved).toBe(true)
    expect(isHydroServerReady.value).toBe(true)
    expect(fetchAllVocabulariesMock).toHaveBeenCalledTimes(1)
  })

  it('does not mark workspace bootstrap complete when initialized while logged out', async () => {
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)

    const {
      hasBootstrappedWorkspaces,
      startAppInitialization,
      isAppInitializing,
    } = await import('../appInitialization')

    await startAppInitialization()

    expect(hasBootstrappedWorkspaces.value).toBe(false)
    expect(listAllItemsMock).not.toHaveBeenCalled()
    expect(isAppInitializing.value).toBe(false)
  })

  it('loads vocabularies, user, and workspaces after first session initialization', async () => {
    sessionState.isAuthenticated = true
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)
    userGetMock.mockResolvedValue({
      status: 200,
      data: { email: 'user@example.com' },
    })
    listAllItemsMock.mockResolvedValue([
      { id: 'workspace-2', name: 'Workspace 2' },
      { id: 'workspace-1', name: 'Workspace 1' },
    ])

    const {
      hasBootstrappedWorkspaces,
      startAppInitialization,
      isAppInitializing,
    } = await import('../appInitialization')

    expect(isAppInitializing.value).toBe(false)

    await startAppInitialization()

    const userStore = useUserStore()
    const workspaceStore = useWorkspaceStore()

    expect(fetchAllVocabulariesMock).toHaveBeenCalledTimes(1)
    expect(userGetMock).toHaveBeenCalledTimes(1)
    expect(listAllItemsMock).toHaveBeenCalledWith({
      is_associated: true,
      expand_related: true,
    })
    expect(userStore.user.email).toBe('user@example.com')
    expect(workspaceStore.workspaces.map((workspace) => workspace.id)).toEqual([
      'workspace-1',
      'workspace-2',
    ])
    expect(workspaceStore.selectedWorkspace?.id).toBe('workspace-1')
    expect(hasBootstrappedWorkspaces.value).toBe(true)
    expect(isAppInitializing.value).toBe(false)
  })

  it('records initialization errors and skips background app bootstrap when HydroServer setup fails', async () => {
    const initializationFailure = new Error('unable to initialize')
    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    createHydroServerMock.mockRejectedValue(initializationFailure)

    const {
      initializationError,
      isAppInitializing,
      isHydroServerReady,
      startAppInitialization,
      waitForHydroServerInitialization,
    } = await import('../appInitialization')

    await startAppInitialization()
    await waitForHydroServerInitialization()

    expect(isHydroServerReady.value).toBe(false)
    expect(isAppInitializing.value).toBe(false)
    expect(initializationError.value).toBe(initializationFailure)
    expect(fetchAllVocabulariesMock).not.toHaveBeenCalled()
    expect(userGetMock).not.toHaveBeenCalled()
    expect(listAllItemsMock).not.toHaveBeenCalled()

    consoleErrorSpy.mockRestore()
  })
})
