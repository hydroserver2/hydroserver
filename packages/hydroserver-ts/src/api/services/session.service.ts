import { User } from '../../types'
import type { HydroServer } from '../HydroServer'
import { apiMethods } from '../apiMethods'
import Storage from '../../utils/storage'
import { getCSRFToken } from '../getCSRFToken'
import { ApiResponse } from '../responseInterceptor'

export interface Provider {
  id: string
  name: string
  iconLink: string | null
  signupEnabled: boolean
  connectEnabled: boolean
}

export type SessionSnapshot = {
  isAuthenticated: boolean
  expiresAt: string | null
  flows: Array<{ id: string; providers?: string[] }>
  oAuthProviders: Provider[]
  signupEnabled: boolean
}

const DEFAULT_SESSION_SNAPSHOT: SessionSnapshot = {
  isAuthenticated: false,
  expiresAt: null,
  flows: [],
  oAuthProviders: [],
  signupEnabled: false,
}

export const emailStorage = new Storage<string>('hydroserver:unverifiedEmail')

export class SessionService {
  readonly sessionBase: string
  readonly providerBase: string

  private _client: HydroServer
  private snapshot: SessionSnapshot = { ...DEFAULT_SESSION_SNAPSHOT }

  constructor(client: HydroServer) {
    this._client = client
    this.sessionBase = `${this._client.authBase}/browser/session`
    this.providerBase = `${this._client.authBase}/browser/provider`
  }

  get isAuthenticated(): boolean {
    return this.snapshot.isAuthenticated
  }
  get expiresAt(): string | null {
    return this.snapshot.expiresAt
  }
  /**
   * Determines if signing up on the website is available at all.
   * Some organizations will want an admin signing up for their users
   * to be the only way to create an account.
   *
   * Not to be confused with `oAuthProviders.signupEnabled` that tells us if
   * that particular OAuth service can be used to create an account.
   */
  get signupEnabled() {
    return this.snapshot.signupEnabled
  }
  /**
   * An array of OAuth providers that the user can use to authenticate.
   * In some cases, such as with HydroShare, this allows connecting to the provider
   * for data archival instead of direct authentication.
   *
   * This array determines which login with OAuth buttons are available on the login and signup pages.
   */
  get oAuthProviders() {
    return this.snapshot.oAuthProviders || []
  }
  get flows(): Array<{ id: string; providers?: string[] }> {
    return this.snapshot.flows
  }
  get flowIds() {
    return this.flows.map((f) => f.id)
  }
  get inEmailVerificationFlow(): boolean {
    return this.flowIds.includes('verify_email')
  }
  get inProviderSignupFlow(): boolean {
    return this.flowIds.includes('provider_signup')
  }
  /**
   * Persist the state of unverified email since it won't be saved in the db
   * during the verify_email flow. Used for
   * re-emailing the verification code to the user upon request.
   */
  get unverifiedEmail() {
    return emailStorage.get() || ''
  }
  set unverifiedEmail(email: string) {
    emailStorage.set(email)
  }

  async initialize(): Promise<void> {
    const res = await apiMethods.fetch(this.sessionBase)
    this._setSession(res)
  }

  get = async () => apiMethods.fetch(this.sessionBase)

  async login(email: string, password: string) {
    const res = await apiMethods.post(this.sessionBase, {
      email,
      password,
    })
    this._setSession(res)
    return res
  }

  async signup(user: User) {
    return this._client.user.create(user)
  }

  private _loggingOut = false
  async logout() {
    if (this._loggingOut) return
    try {
      this._loggingOut = true
      for (const store of [localStorage, sessionStorage]) {
        for (const key of Object.keys(store)) {
          if (key.startsWith('hydroserver:')) {
            store.removeItem(key)
          }
        }
      }
      const res = await apiMethods.delete(this.sessionBase)
      this._setSession(res)
    } catch (error) {
      console.error('Error logging out.', error)
    } finally {
      this._loggingOut = false
    }
  }

  _setSession(res: ApiResponse) {
    const meta = res?.meta ?? {}
    const data = res?.data ?? {}

    this.snapshot = {
      isAuthenticated: Boolean(meta.is_authenticated),
      expiresAt: meta.expires ?? null,
      flows: Array.isArray(data.flows) ? data.flows : [],
      oAuthProviders: Array.isArray(meta.oAuthProviders ?? [])
        ? meta.oAuthProviders
        : [],
      signupEnabled: Boolean(meta.signupEnabled ?? false),
    }
  }

  checkExpiration() {
    if (!this.snapshot.isAuthenticated) return
    if (!this.snapshot.expiresAt) return

    const expirationTime = new Date(this.snapshot.expiresAt).getTime()
    if (Number.isFinite(expirationTime) && Date.now() >= expirationTime) {
      this._client.emit('session:expired')
      this.logout()
    }
  }

  /**
   * Initiates a synchronous form submission to redirect the user for OAuth login in a Django AllAuth
   * environment. This allows the server to return a 302 redirect that the browser will follow,
   * preserving session cookies and enabling AllAuth to handle the full OAuth handshake.
   *
   * @param {string} provider - The ID of the OAuth provider (e.g. "google", "hydroshare").
   * @param {string} callbackUrl - The URL to which the user is redirected after the OAuth flow completes.
   * @param {string} process - Enum: "login" or "connect" The process to be executed when the user successfully authenticates.
   *                           When set to login, the user will be logged into the account to which the provider account is connected,
   *                           or if no such account exists, a signup will occur. If set to connect, the provider account will
   *                           be connected to the list of provider accounts for the currently authenticated user.
   */
  providerRedirect = (
    provider: string,
    callbackUrl: string,
    process: string
  ) => {
    const data: Record<string, string> = {
      provider: provider,
      callback_url: callbackUrl,
      process: process,
    }
    const csrfToken = getCSRFToken()
    const form = document.createElement('form')
    form.method = 'POST'
    form.action = `${this.providerBase}/redirect`
    if (csrfToken) {
      const csrfInput = document.createElement('input')
      csrfInput.type = 'hidden'
      csrfInput.name = 'csrfmiddlewaretoken'
      csrfInput.value = csrfToken
      form.appendChild(csrfInput)
    }
    for (const key in data) {
      const input = document.createElement('input')
      input.type = 'hidden'
      input.name = key
      input.value = data[key]
      form.appendChild(input)
    }
    document.body.appendChild(form)
    form.submit()
  }

  fetchConnectedProviders = async () =>
    apiMethods.fetch(`${this._client.providerBase}/connections`)

  providerSignup = async (user: User) => {
    const res = await apiMethods.post(
      `${this._client.providerBase}/signup`,
      user
    )
    console.log('provider signup', res)
    this._setSession(res.data)
    return res
  }

  deleteProvider = async (provider: string, account: string) =>
    apiMethods.delete(`${this._client.providerBase}/connections`, {
      provider: provider,
      account: account,
    })
}
