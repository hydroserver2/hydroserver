import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { useUserStore } from '@/store/user'
import { useWorkspaceStore } from '@/store/workspaces'

const {
  createHydroServerMock,
  fetchAllVocabulariesMock,
  userGetMock,
  listAllItemsMock,
  onMock,
  sessionState,
  testPinia,
} = vi.hoisted(() => ({
  createHydroServerMock: vi.fn(),
  fetchAllVocabulariesMock: vi.fn(),
  userGetMock: vi.fn(),
  listAllItemsMock: vi.fn(),
  onMock: vi.fn(),
  sessionState: {
    isAuthenticated: false,
    hasAccessToken: false,
    account: null as Record<string, unknown> | null,
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
      on: onMock,
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
    sessionState.hasAccessToken = false
    sessionState.account = null
    createHydroServerMock.mockReset()
    fetchAllVocabulariesMock.mockReset()
    userGetMock.mockReset()
    listAllItemsMock.mockReset()
    onMock.mockReset()
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

  it('hydrates authenticated ui state from the browser session when no oidc user is cached', async () => {
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)
    sessionState.isAuthenticated = true
    sessionState.account = {
      email: 'browser@example.com',
      firstName: 'Browser',
      lastName: 'Session',
    }

    const {
      hasBootstrappedWorkspaces,
      startAppInitialization,
    } = await import('../appInitialization')

    await startAppInitialization()

    const userStore = useUserStore()

    expect(userStore.user.email).toBe('browser@example.com')
    expect(userStore.user.firstName).toBe('Browser')
    expect(hasBootstrappedWorkspaces.value).toBe(false)
    expect(userGetMock).not.toHaveBeenCalled()
    expect(listAllItemsMock).not.toHaveBeenCalled()
  })

  it('loads vocabularies, user, and workspaces after first session initialization', async () => {
    sessionState.isAuthenticated = true
    sessionState.hasAccessToken = true
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
    expect(onMock).toHaveBeenCalledWith('session:changed', expect.any(Function))
    expect(onMock).toHaveBeenCalledWith('session:expired', expect.any(Function))
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

  it('returns an already resolved wait promise before initialization starts', async () => {
    const { waitForHydroServerInitialization } = await import('../appInitialization')

    await expect(waitForHydroServerInitialization()).resolves.toBeUndefined()
  })

  it('resets the user when the authenticated user request returns 401', async () => {
    sessionState.isAuthenticated = true
    sessionState.hasAccessToken = true
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)
    userGetMock.mockResolvedValue({
      status: 401,
      data: { email: 'ignored@example.com' },
    })
    listAllItemsMock.mockResolvedValue([
      { id: 'workspace-1', name: 'Workspace 1' },
    ])

    const { startAppInitialization } = await import('../appInitialization')

    await startAppInitialization()

    const userStore = useUserStore()
    expect(userStore.user.email).toBe('')
  })

  it('records user fetch failures without breaking workspace bootstrap', async () => {
    const userError = new Error('user request failed')
    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)

    sessionState.isAuthenticated = true
    sessionState.hasAccessToken = true
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)
    userGetMock.mockRejectedValue(userError)
    listAllItemsMock.mockResolvedValue([
      { id: 'workspace-1', name: 'Workspace 1' },
    ])

    const {
      hasBootstrappedWorkspaces,
      initializationError,
      startAppInitialization,
    } = await import('../appInitialization')

    await startAppInitialization()

    expect(initializationError.value).toBe(userError)
    expect(hasBootstrappedWorkspaces.value).toBe(true)
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Error fetching user',
      userError
    )

    consoleErrorSpy.mockRestore()
  })

  it('records workspace fetch failures without breaking user bootstrap', async () => {
    const workspaceError = new Error('workspace request failed')
    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)

    sessionState.isAuthenticated = true
    sessionState.hasAccessToken = true
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)
    userGetMock.mockResolvedValue({
      status: 200,
      data: { email: 'user@example.com' },
    })
    listAllItemsMock.mockRejectedValue(workspaceError)

    const {
      hasBootstrappedWorkspaces,
      initializationError,
      startAppInitialization,
    } = await import('../appInitialization')

    await startAppInitialization()

    const userStore = useUserStore()
    expect(userStore.user.email).toBe('user@example.com')
    expect(hasBootstrappedWorkspaces.value).toBe(false)
    expect(initializationError.value).toBe(workspaceError)
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Error fetching workspaces',
      workspaceError
    )

    consoleErrorSpy.mockRestore()
  })

  it('records vocabulary fetch failures', async () => {
    const vocabularyError = new Error('vocabulary request failed')
    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)

    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockRejectedValue(vocabularyError)

    const { initializationError, startAppInitialization } = await import(
      '../appInitialization'
    )

    await startAppInitialization()

    expect(initializationError.value).toBe(vocabularyError)
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Error fetching vocabularies',
      vocabularyError
    )

    consoleErrorSpy.mockRestore()
  })

  it('reuses the initialization promise and only attaches session listeners once', async () => {
    sessionState.isAuthenticated = false
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)

    const { startAppInitialization } = await import('../appInitialization')

    const first = startAppInitialization()
    const second = startAppInitialization()

    await first
    await second

    expect(first).toBe(second)
    expect(createHydroServerMock).toHaveBeenCalledTimes(1)
    expect(onMock).toHaveBeenCalledTimes(2)
  })

  it('refreshes authenticated state when session change and expiry callbacks fire', async () => {
    sessionState.isAuthenticated = true
    sessionState.hasAccessToken = true
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)
    userGetMock.mockResolvedValue({
      status: 200,
      data: { email: 'callback@example.com' },
    })
    listAllItemsMock.mockResolvedValue([
      { id: 'workspace-1', name: 'Workspace 1' },
    ])

    const { startAppInitialization } = await import('../appInitialization')

    await startAppInitialization()

    const sessionChanged = onMock.mock.calls.find(
      ([eventName]) => eventName === 'session:changed'
    )?.[1] as (() => void) | undefined
    const sessionExpired = onMock.mock.calls.find(
      ([eventName]) => eventName === 'session:expired'
    )?.[1] as (() => void) | undefined

    expect(sessionChanged).toBeTypeOf('function')
    expect(sessionExpired).toBeTypeOf('function')

    sessionChanged?.()
    sessionExpired?.()
    await Promise.resolve()
    await Promise.resolve()

    expect(userGetMock).toHaveBeenCalledTimes(3)
    expect(listAllItemsMock).toHaveBeenCalledTimes(3)
  })
})
