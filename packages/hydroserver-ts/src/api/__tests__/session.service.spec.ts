import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'
import { SessionService } from '../services/session.service'

const apiFetchMock = vi.hoisted(() => vi.fn())

const managerState = vi.hoisted(() => ({
  getUser: vi.fn(),
  signinSilent: vi.fn(),
  signinRedirect: vi.fn(),
  signinRedirectCallback: vi.fn(),
  removeUser: vi.fn(),
  signoutRedirect: vi.fn(),
  events: {
    addUserLoaded: vi.fn(),
    addUserUnloaded: vi.fn(),
    addAccessTokenExpired: vi.fn(),
    addSilentRenewError: vi.fn(),
  },
  stores: [] as Storage[],
}))

vi.mock('../apiMethods', () => ({
  apiMethods: {
    fetch: apiFetchMock,
  },
}))

vi.mock('oidc-client-ts', () => ({
  UserManager: class MockUserManager {
    getUser = managerState.getUser
    signinSilent = managerState.signinSilent
    signinRedirect = managerState.signinRedirect
    signinRedirectCallback = managerState.signinRedirectCallback
    removeUser = managerState.removeUser
    signoutRedirect = managerState.signoutRedirect
    events = managerState.events
  },
  WebStorageStateStore: class MockWebStorageStateStore {
    store: Storage

    constructor({ store }: { store: Storage }) {
      managerState.stores.push(store)
      this.store = store
    }
  },
}))

describe('SessionService', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    managerState.getUser.mockReset()
    managerState.signinSilent.mockReset()
    managerState.signinRedirect.mockReset()
    managerState.signinRedirectCallback.mockReset()
    managerState.removeUser.mockReset()
    managerState.signoutRedirect.mockReset()
    managerState.events.addUserLoaded.mockReset()
    managerState.events.addUserUnloaded.mockReset()
    managerState.events.addAccessTokenExpired.mockReset()
    managerState.events.addSilentRenewError.mockReset()
    managerState.stores.length = 0

    window.localStorage.clear()
    window.sessionStorage.clear()
    window.history.replaceState({}, '', '/current')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deduplicates concurrent refresh requests', async () => {
    const expiringUser = { access_token: 'old-token', expired: false, expires_in: 30 }
    const refreshedUser = {
      access_token: 'new-token',
      expired: false,
      expires_in: 3600,
    }

    managerState.getUser.mockResolvedValue(expiringUser)
    managerState.signinSilent.mockImplementation(
      () =>
        new Promise((resolve) => {
          setTimeout(() => resolve(refreshedUser), 0)
        })
    )

    const session = new SessionService(
      new HydroServer({ host: 'https://hydro.example.com' })
    )

    const [tokenA, tokenB] = await Promise.all([
      session.getAccessToken(),
      session.getAccessToken(),
    ])

    expect(tokenA).toBe('new-token')
    expect(tokenB).toBe('new-token')
    expect(managerState.signinSilent).toHaveBeenCalledTimes(1)
  })

  it('rejects protocol-relative callback redirects', async () => {
    managerState.signinRedirectCallback.mockResolvedValue({
      access_token: 'token-123',
      expired: false,
      expires_in: 3600,
      state: { returnTo: '//evil.example/phishing' },
    })

    const session = new SessionService(
      new HydroServer({ host: 'https://hydro.example.com' })
    )

    await expect(session.completeLogin()).resolves.toBe('/')
  })

  it('stores OIDC state in sessionStorage', () => {
    const session = new SessionService(
      new HydroServer({ host: 'https://hydro.example.com' })
    )

    ;(session as any).getManager()

    expect(managerState.stores).toEqual([window.sessionStorage])
  })

  it('swallows refresh errors in checkExpiration', async () => {
    const expiringUser = { access_token: 'old-token', expired: false, expires_in: 30 }
    managerState.getUser.mockResolvedValue(expiringUser)
    managerState.signinSilent.mockRejectedValue(new Error('refresh failed'))
    managerState.removeUser.mockResolvedValue(undefined)

    const session = new SessionService(
      new HydroServer({ host: 'https://hydro.example.com' })
    )

    await session.initialize()

    expect(() => session.checkExpiration()).not.toThrow()
  })

  it('builds account urls with the current app route as next', () => {
    window.history.replaceState({}, '', '/orchestration?workspaceId=abc#runs')

    const session = new SessionService(
      new HydroServer({ host: 'https://hydro.example.com' })
    )

    expect(session.accountSignupUrl).toBe(
      'https://hydro.example.com/accounts/signup/?next=http%3A%2F%2Flocalhost%3A3000%2Forchestration%3FworkspaceId%3Dabc%23runs&handoff=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fhandoff%3FreturnTo%3Dhttp%253A%252F%252Flocalhost%253A3000%252Forchestration%253FworkspaceId%253Dabc%2523runs'
    )
    expect(session.accountProfileUrl).toBe(
      'https://hydro.example.com/accounts/profile/?next=http%3A%2F%2Flocalhost%3A3000%2Forchestration%3FworkspaceId%3Dabc%23runs&handoff=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fhandoff%3FreturnTo%3Dhttp%253A%252F%252Flocalhost%253A3000%252Forchestration%253FworkspaceId%253Dabc%2523runs'
    )
  })

  it('does not block initialization on a silent bootstrap when no cached user exists', async () => {
    managerState.getUser.mockResolvedValue(null)
    apiFetchMock.mockResolvedValue({ ok: false, data: null })
    const client = new HydroServer({ host: 'https://hydro.example.com' })
    const emitSpy = vi.spyOn(client, 'emit')
    const session = new SessionService(client)

    await session.initialize()

    expect(managerState.signinSilent).not.toHaveBeenCalled()
    expect(managerState.removeUser).toHaveBeenCalledTimes(1)
    expect(session.isAuthenticated).toBe(false)
    expect(emitSpy).not.toHaveBeenCalledWith('session:changed', true)
  })

  it('loads the browser session account using credentialed requests', async () => {
    apiFetchMock.mockResolvedValue({
      ok: true,
      data: {
        account: {
          email: 'user@example.com',
          firstName: 'Signed',
          lastName: 'In',
        },
      },
    })

    const session = new SessionService(
      new HydroServer({ host: 'https://hydro.example.com' })
    )

    await expect(session.getBrowserSessionAccount()).resolves.toMatchObject({
      email: 'user@example.com',
      firstName: 'Signed',
      lastName: 'In',
    })
    expect(apiFetchMock).toHaveBeenCalledWith(
      'https://hydro.example.com/api/auth/browser/session',
      { credentials: 'include' }
    )
  })

  it('treats the browser session as authenticated after initialization', async () => {
    managerState.getUser.mockResolvedValue(null)
    apiFetchMock.mockResolvedValue({
      ok: true,
      data: {
        account: {
          email: 'user@example.com',
          firstName: 'Signed',
        },
      },
    })

    const session = new SessionService(
      new HydroServer({ host: 'https://hydro.example.com' })
    )

    await session.initialize()

    expect(session.isAuthenticated).toBe(true)
    expect(session.hasAccessToken).toBe(false)
    expect(session.account).toMatchObject({
      email: 'user@example.com',
      firstName: 'Signed',
    })
  })

  it('redirects through login when a protected route needs an access token', async () => {
    managerState.getUser.mockResolvedValue(null)
    apiFetchMock.mockResolvedValue({
      ok: true,
      data: {
        account: {
          email: 'user@example.com',
        },
      },
    })

    const session = new SessionService(
      new HydroServer({ host: 'https://hydro.example.com' })
    )
    await session.initialize()

    await expect(session.ensureAuthorized('/sites')).resolves.toBe(false)
    expect(managerState.signinRedirect).toHaveBeenCalledWith({
      state: { returnTo: '/sites' },
    })
  })
})
