import {
  UserManager,
  WebStorageStateStore,
  type User as OidcUser,
} from 'oidc-client-ts'
import type { HydroServer } from '../HydroServer'

const EXPIRING_SOON_SECONDS = 60

type SigninState = {
  returnTo?: string
}

function isBrowser() {
  return typeof window !== 'undefined'
}

function removeHydroServerStorage() {
  if (!isBrowser()) return

  for (const store of [window.localStorage, window.sessionStorage]) {
    for (const key of Object.keys(store)) {
      if (key.startsWith('hydroserver:')) {
        store.removeItem(key)
      }
    }
  }
}

export class SessionService {
  readonly accountSignupUrl: string
  readonly accountProfileUrl: string

  private readonly _client: HydroServer
  private _manager: UserManager | null = null
  private _user: OidcUser | null = null
  private _refreshPromise: Promise<OidcUser | null> | null = null
  private _eventsBound = false

  constructor(client: HydroServer) {
    this._client = client
    this.accountSignupUrl = this._client.resolveUrl('/accounts/signup/')
    this.accountProfileUrl = this._client.resolveUrl('/accounts/profile/')
  }

  get isAuthenticated(): boolean {
    return Boolean(this._user?.access_token && !this._user.expired)
  }

  get accessToken(): string | null {
    return this.isAuthenticated ? this._user!.access_token : null
  }

  async initialize(): Promise<void> {
    if (!isBrowser()) return

    const manager = this.getManager()
    let user = await manager.getUser()
    if (this.isExpiredOrExpiring(user)) {
      user = await this.refreshUser(manager)
    }
    if (!user || user.expired) {
      await manager.removeUser()
      this.setUser(null)
      return
    }
    this.setUser(user)
  }

  async login(returnTo = this.getCurrentPath()): Promise<void> {
    const manager = this.getManager()
    await manager.signinRedirect({
      state: { returnTo },
    })
  }

  async completeLogin(callbackUrl = this.getCurrentUrl()): Promise<string> {
    const manager = this.getManager()
    const user = await manager.signinRedirectCallback(callbackUrl)
    this.setUser(user)

    const returnTo = (user.state as SigninState | undefined)?.returnTo
    return (
      typeof returnTo === 'string' &&
      returnTo.startsWith('/') &&
      !returnTo.startsWith('//')
    )
      ? returnTo
      : '/'
  }

  async logout(returnTo = '/'): Promise<void> {
    const manager = this.getManager()
    await manager.removeUser()
    this.setUser(null)
    removeHydroServerStorage()

    try {
      await manager.signoutRedirect({
        post_logout_redirect_uri: this._client.resolveAppUrl(returnTo),
      })
    } catch (error) {
      console.warn('OIDC sign-out redirect failed, falling back to local logout.', error)
      if (isBrowser()) {
        window.location.assign(this._client.resolveAppUrl(returnTo))
      }
    }
  }

  async getAccessToken(): Promise<string | null> {
    if (!isBrowser()) return null

    const manager = this.getManager()
    let user = this._user ?? (await manager.getUser())
    if (!user) {
      this.setUser(null)
      return null
    }

    if (this.isExpiredOrExpiring(user)) {
      user = await this.refreshUser(manager)
    } else {
      this.setUser(user)
    }

    return user && !user.expired ? user.access_token : null
  }

  checkExpiration(): void {
    if (!this._user) return
    if (!this.isExpiredOrExpiring(this._user)) return
    void this.getAccessToken().catch(() => {})
  }

  private getManager(): UserManager {
    if (!isBrowser()) {
      throw new Error('OIDC session management requires a browser environment.')
    }

    if (!this._manager) {
      this._manager = new UserManager({
        authority: this._client.resolvedHost,
        client_id: this._client.oidc.clientId,
        redirect_uri: this._client.resolveAppUrl(this._client.oidc.redirectPath),
        post_logout_redirect_uri: this._client.resolveAppUrl(
          this._client.oidc.postLogoutRedirectPath
        ),
        response_type: 'code',
        scope: this._client.oidc.scope,
        loadUserInfo: true,
        automaticSilentRenew: false,
        userStore: new WebStorageStateStore({ store: window.sessionStorage }),
      })
    }

    if (!this._eventsBound) {
      this._manager.events.addUserLoaded((user) => {
        this.setUser(user)
      })
      this._manager.events.addUserUnloaded(() => {
        this.setUser(null)
      })
      this._manager.events.addAccessTokenExpired(() => {
        void this.getAccessToken().catch(() => {})
      })
      this._manager.events.addSilentRenewError((error) => {
        console.error('OIDC silent renew failed', error)
      })
      this._eventsBound = true
    }

    return this._manager
  }

  private async tryRefreshUser(manager: UserManager): Promise<OidcUser | null> {
    try {
      const user = await manager.signinSilent()
      this.setUser(user)
      return user
    } catch (error) {
      console.warn('Unable to refresh OIDC session.', error)
      await manager.removeUser()
      this.setUser(null)
      this._client.emit('session:expired')
      return null
    }
  }

  private refreshUser(manager: UserManager): Promise<OidcUser | null> {
    if (!this._refreshPromise) {
      this._refreshPromise = this.tryRefreshUser(manager).finally(() => {
        this._refreshPromise = null
      })
    }
    return this._refreshPromise
  }

  private setUser(user: OidcUser | null): void {
    this._user = user && !user.expired ? user : null
  }

  private isExpiredOrExpiring(user: OidcUser | null): boolean {
    if (!user) return false
    if (user.expired) return true
    return typeof user.expires_in === 'number' && user.expires_in <= EXPIRING_SOON_SECONDS
  }

  private getCurrentPath(): string {
    if (!isBrowser()) return '/'
    return (
      window.location.pathname +
      window.location.search +
      window.location.hash
    )
  }

  private getCurrentUrl(): string {
    if (!isBrowser()) {
      return this._client.resolveAppUrl(this._client.oidc.redirectPath)
    }
    return window.location.href
  }
}
