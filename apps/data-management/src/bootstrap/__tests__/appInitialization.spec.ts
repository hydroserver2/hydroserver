import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/store/user'
import { useWorkspaceStore } from '@/store/workspaces'
import type { Workspace } from '@hydroserver/client'

const {
  createHydroServerMock,
  fetchAllVocabulariesMock,
  userGetMock,
  workspaceListMock,
  sessionState,
} = vi.hoisted(() => ({
  createHydroServerMock: vi.fn(),
  fetchAllVocabulariesMock: vi.fn(),
  userGetMock: vi.fn(),
  workspaceListMock: vi.fn(),
  sessionState: {
    isAuthenticated: false,
  },
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
        list: workspaceListMock,
      },
    },
  }
})

vi.mock('@/config/settings', () => ({
  settings: {
    authenticationConfiguration: { csrfCookieName: 'hs_csrftoken' },
  },
}))

vi.mock('@/composables/useVocabulary', () => ({
  useVocabularyStore: () => ({
    fetchAllVocabularies: fetchAllVocabulariesMock,
  }),
}))

describe('app initialization bootstrap', () => {
  beforeEach(() => {
    vi.resetModules()
    setActivePinia(createPinia())
    localStorage.clear()
    sessionState.isAuthenticated = false
    createHydroServerMock.mockReset()
    fetchAllVocabulariesMock.mockReset()
    userGetMock.mockReset()
    workspaceListMock.mockReset()
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

  it('passes the configured CSRF cookie name to the HydroServer client', async () => {
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)

    const { startAppInitialization } = await import('../appInitialization')
    await startAppInitialization()

    expect(createHydroServerMock).toHaveBeenCalledWith(
      expect.objectContaining({ csrfCookieName: 'hs_csrftoken' })
    )
  })

  it('does not mark workspace bootstrap complete when initialized while logged out', async () => {
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)

    const {
      hasBootstrappedWorkspaces,
      isAccessContextReady,
      startAppInitialization,
      isAppInitializing,
    } = await import('../appInitialization')

    await startAppInitialization()

    expect(hasBootstrappedWorkspaces.value).toBe(false)
    expect(isAccessContextReady.value).toBe(false)
    expect(workspaceListMock).not.toHaveBeenCalled()
    expect(isAppInitializing.value).toBe(false)
  })

  it('loads vocabularies, user, and workspaces after first session initialization', async () => {
    sessionState.isAuthenticated = true
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)
    userGetMock.mockResolvedValue({
      ok: true,
      status: 200,
      data: { email: 'user@example.com' },
    })
    workspaceListMock.mockResolvedValue({
      ok: true,
      status: 200,
      data: [
        { id: 'workspace-2', name: 'Workspace 2' },
        { id: 'workspace-1', name: 'Workspace 1' },
      ],
    })

    const {
      hasBootstrappedWorkspaces,
      isAccessContextReady,
      startAppInitialization,
      isAppInitializing,
    } = await import('../appInitialization')

    expect(isAppInitializing.value).toBe(false)

    await startAppInitialization()

    const userStore = useUserStore()
    const workspaceStore = useWorkspaceStore()

    expect(fetchAllVocabulariesMock).toHaveBeenCalledTimes(1)
    expect(userGetMock).toHaveBeenCalledTimes(1)
    expect(workspaceListMock).toHaveBeenCalledWith({
      isAssociated: true,
      fetch_all: true,
    })
    expect(workspaceListMock).toHaveBeenCalledTimes(1)
    expect(userStore.user.email).toBe('user@example.com')
    expect(workspaceStore.workspaces.map((workspace) => workspace.id)).toEqual([
      'workspace-1',
      'workspace-2',
    ])
    expect(workspaceStore.selectedWorkspace?.id).toBe('workspace-1')
    expect(hasBootstrappedWorkspaces.value).toBe(true)
    expect(isAccessContextReady.value).toBe(true)
    expect(isAppInitializing.value).toBe(false)
  })

  it('starts user and personal workspace requests together, then expands the list for admins', async () => {
    sessionState.isAuthenticated = true
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)
    let resolveUser!: (response: unknown) => void
    userGetMock.mockReturnValue(
      new Promise((resolve) => {
        resolveUser = resolve
      })
    )
    const personalWorkspaces = [
      {
        id: 'owned-workspace',
        name: 'Owned workspace',
        owner: { email: 'admin@example.com' },
      },
    ]
    const savedWorkspace = {
      id: 'unaffiliated-private',
      name: 'Private workspace',
      owner: { email: 'other@example.com' },
    } as Workspace
    useWorkspaceStore().setWorkspaces([savedWorkspace])
    let resolveAllWorkspaces!: (response: unknown) => void
    workspaceListMock
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        data: personalWorkspaces,
      })
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveAllWorkspaces = resolve
        })
      )

    const {
      startAppInitialization,
      hasBootstrappedWorkspaces,
      isAccessContextReady,
      isAppInitializing,
    } = await import('../appInitialization')
    const startup = startAppInitialization()
    await vi.waitFor(() => expect(userGetMock).toHaveBeenCalled())
    expect(workspaceListMock).toHaveBeenCalledExactlyOnceWith({
      isAssociated: true,
      fetch_all: true,
    })

    resolveUser({
      ok: true,
      status: 200,
      data: { email: 'admin@example.com', isSuperuser: true },
    })
    await vi.waitFor(() => expect(workspaceListMock).toHaveBeenCalledTimes(2))
    expect(useWorkspaceStore().workspaces).toEqual(personalWorkspaces)
    expect(useWorkspaceStore().selectedWorkspace?.id).toBe('owned-workspace')
    expect(hasBootstrappedWorkspaces.value).toBe(true)
    expect(isAppInitializing.value).toBe(true)
    expect(isAccessContextReady.value).toBe(false)

    resolveAllWorkspaces({
      ok: true,
      status: 200,
      data: [...personalWorkspaces, savedWorkspace],
    })
    await startup

    expect(workspaceListMock).toHaveBeenNthCalledWith(2, { fetch_all: true })
    expect(useWorkspaceStore().workspaces).toHaveLength(2)
    expect(useWorkspaceStore().selectedWorkspace?.id).toBe(
      'unaffiliated-private'
    )
    expect(hasBootstrappedWorkspaces.value).toBe(true)
    expect(isAppInitializing.value).toBe(false)
    expect(isAccessContextReady.value).toBe(true)
  })

  it('retains personal workspaces but does not establish access if admin expansion fails', async () => {
    sessionState.isAuthenticated = true
    createHydroServerMock.mockResolvedValue(undefined)
    fetchAllVocabulariesMock.mockResolvedValue(undefined)
    userGetMock.mockResolvedValue({
      ok: true,
      status: 200,
      data: { email: 'admin@example.com', isSuperuser: true },
    })
    const personalWorkspaces = [
      { id: 'owned-workspace', name: 'Owned workspace' },
    ]
    const error = new Error('Full workspace list unavailable')
    workspaceListMock
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        data: personalWorkspaces,
      })
      .mockRejectedValueOnce(error)
    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)
    try {
      const {
        startAppInitialization,
        initializationError,
        hasBootstrappedWorkspaces,
        isAccessContextReady,
        accessContextError,
      } = await import('../appInitialization')
      await startAppInitialization()

      expect(useWorkspaceStore().workspaces).toEqual(personalWorkspaces)
      expect(initializationError.value).toBe(error)
      expect(hasBootstrappedWorkspaces.value).toBe(true)
      expect(isAccessContextReady.value).toBe(false)
      expect(accessContextError.value).toBe(error)
    } finally {
      consoleErrorSpy.mockRestore()
    }
  })

  it('waits for both user and workspaces without waiting for vocabularies', async () => {
    sessionState.isAuthenticated = true
    createHydroServerMock.mockResolvedValue(undefined)
    let resolveUser!: (response: unknown) => void
    let resolveWorkspaces!: (response: unknown) => void
    let resolveVocabularies!: () => void
    userGetMock.mockReturnValue(
      new Promise((resolve) => {
        resolveUser = resolve
      })
    )
    workspaceListMock.mockReturnValue(
      new Promise((resolve) => {
        resolveWorkspaces = resolve
      })
    )
    fetchAllVocabulariesMock.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveVocabularies = resolve
      })
    )

    const { startAppInitialization, isAccessContextReady, isAppInitializing } =
      await import('../appInitialization')
    const startup = startAppInitialization()
    await vi.waitFor(() => expect(workspaceListMock).toHaveBeenCalled())
    expect(isAccessContextReady.value).toBe(false)

    resolveWorkspaces({ ok: true, status: 200, data: [] })
    await vi.waitFor(() => expect(useWorkspaceStore().workspaces).toEqual([]))
    expect(isAccessContextReady.value).toBe(false)

    resolveUser({ ok: true, status: 200, data: { email: 'user@example.com' } })
    await vi.waitFor(() => expect(isAccessContextReady.value).toBe(true))
    expect(isAppInitializing.value).toBe(true)
    resolveVocabularies()
    await startup
  })

  it.each(['user', 'workspaces'])(
    'does not establish access after a failed %s request',
    async (request) => {
      sessionState.isAuthenticated = true
      createHydroServerMock.mockResolvedValue(undefined)
      fetchAllVocabulariesMock.mockResolvedValue(undefined)
      userGetMock.mockResolvedValue({
        ok: true,
        status: 200,
        data: { email: 'user@example.com' },
      })
      workspaceListMock.mockResolvedValue({ ok: true, status: 200, data: [] })
      const error = new Error('Connection lost')
      if (request === 'user') userGetMock.mockRejectedValue(error)
      else workspaceListMock.mockRejectedValue(error)
      const consoleErrorSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => undefined)
      try {
        const {
          startAppInitialization,
          isAccessContextReady,
          accessContextError,
        } = await import('../appInitialization')
        await startAppInitialization()
        expect(isAccessContextReady.value).toBe(false)
        expect(accessContextError.value).toBe(error)
      } finally {
        consoleErrorSpy.mockRestore()
      }
    }
  )

  it.each(['user', 'workspaces'])(
    'reports unsuccessful %s responses as load failures',
    async (request) => {
      sessionState.isAuthenticated = true
      createHydroServerMock.mockResolvedValue(undefined)
      fetchAllVocabulariesMock.mockResolvedValue(undefined)
      userGetMock.mockResolvedValue({
        ok: true,
        status: 200,
        data: { email: 'user@example.com' },
      })
      workspaceListMock.mockResolvedValue({ ok: true, status: 200, data: [] })
      const failure = {
        ok: false,
        status: 503,
        message: 'Temporarily unavailable',
      }
      if (request === 'user') userGetMock.mockResolvedValue(failure)
      else workspaceListMock.mockResolvedValue(failure)
      const consoleErrorSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => undefined)
      try {
        const {
          startAppInitialization,
          isAccessContextReady,
          accessContextError,
        } = await import('../appInitialization')
        await startAppInitialization()
        expect(isAccessContextReady.value).toBe(false)
        expect(accessContextError.value).toBeInstanceOf(Error)
      } finally {
        consoleErrorSpy.mockRestore()
      }
    }
  )

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
    expect(workspaceListMock).not.toHaveBeenCalled()

    consoleErrorSpy.mockRestore()
  })
})
