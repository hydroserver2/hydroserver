import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { HydroServer } from '../HydroServer'
import { SessionService } from '../services/session.service'

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
})
