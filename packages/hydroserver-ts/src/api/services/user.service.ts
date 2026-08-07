import { apiMethods } from '../apiMethods'
import { WorkspaceContract } from '../../generated/contracts'
import { type HydroServer } from '../HydroServer'
import type * as Data from '../../generated/data.types'
import { User } from '../../types'
import { ApiResponse } from '../responseInterceptor'

type Permission = Data.components['schemas']['PermissionDetailResponse']
type PermissionAction =
  Data.components['schemas']['PermissionDetailResponse']['action']
type PermissionResource =
  Data.components['schemas']['PermissionDetailResponse']['resource']

/**
 * The real Django origin to use when fetching the server-rendered shell
 * directly in dev — NOT the same as HydroServer.resolvedHost, which is
 * often deliberately relative (empty) so ordinary API calls go through the
 * same-origin nginx proxy. That proxy routes "/" to the Vite dev server,
 * not Django, so reaching the actual rendered shell requires bypassing it.
 * Mirrors the devHost convention in apps/*\/src/main.ts and
 * apps/data-management/src/config/settings.ts.
 */
function resolveDevShellHost(): string {
  const env = (import.meta as unknown as { env?: Record<string, unknown> })
    .env
  const proxyBaseUrl = env?.VITE_APP_PROXY_BASE_URL
  if (typeof proxyBaseUrl === 'string' && proxyBaseUrl) return proxyBaseUrl
  return env?.DEV ? 'http://127.0.0.1:8000' : ''
}

/**
 * Reads the `current-user` JSON embedded by the Django-rendered SPA shell
 * (interfaces/web/views.py). In dev, Vite serves its own static index.html
 * instead of the Django-rendered one, so fall back to fetching the real
 * shell directly from Django and parsing the tag out of that. The fetch
 * must carry credentials since it's commonly cross-origin in dev (the app
 * is served from the nginx-proxied origin, Django from its own dev port).
 */
function readCurrentUserScriptTag(): string | null {
  if (typeof document === 'undefined') return null

  let scriptTag = document.getElementById(
    'current-user'
  ) as HTMLScriptElement | null

  const devShellHost = resolveDevShellHost()

  if (!scriptTag && typeof XMLHttpRequest !== 'undefined' && devShellHost) {
    try {
      const xhr = new XMLHttpRequest()
      xhr.open('GET', devShellHost, false)
      xhr.withCredentials = true
      xhr.send(null)
      const html = xhr.status >= 200 && xhr.status < 300 ? xhr.responseText : null
      if (html) {
        const doc = new DOMParser().parseFromString(html, 'text/html')
        scriptTag = doc.getElementById('current-user') as HTMLScriptElement | null
      }
    } catch {
      scriptTag = null
    }
  }

  return scriptTag?.textContent ?? null
}

export class UserService {
  private readonly _client: HydroServer
  private _cachedUser: User | null | undefined = undefined

  constructor(client: HydroServer) {
    this._client = client
  }

  /**
   * Synchronous authentication check. Session mode reads the `current-user`
   * payload embedded in the SPA shell; OIDC mode defers to SessionService's
   * own token-based check, since resolveCachedUser()'s script-tag lookup
   * doesn't apply there (and would otherwise permanently cache a false
   * "not authenticated" the first time this getter is called in OIDC mode).
   */
  get isAuthenticated(): boolean {
    if (this._client.oidc) {
      return this._client.session.isAuthenticated
    }
    return this.resolveCachedUser() !== null
  }

  private resolveCachedUser(): User | null {
    if (this._cachedUser === undefined) {
      const raw = readCurrentUserScriptTag()
      try {
        this._cachedUser = raw ? (JSON.parse(raw) as User) : null
      } catch {
        this._cachedUser = null
      }
    }
    return this._cachedUser
  }

  /**
   * Returns the current user.
   *
   * Session mode: read once from the `current-user` JSON embedded in the
   * SPA shell's initial server render — no request needed. This only
   * reflects state as of the last full page load, but auth transitions
   * always go through a full navigation (login/logout redirects), so it
   * stays accurate for the SPA's lifetime.
   *
   * OIDC mode: fetched once from the OIDC UserInfo endpoint and cached.
   * HydroServer's OIDC provider adds HydroServer-specific claims
   * (organization, accountType, etc.) to that response for clients
   * requesting the `profile` scope (see core/iam/auth/oidc_adapter.py).
   * The access token is attached automatically by requestInterceptor via
   * the accessTokenProvider registered in runtime.ts.
   */
  get = async (): Promise<ApiResponse<User>> => {
    if (this._client.oidc) {
      if (this._cachedUser) {
        return { ok: true, data: this._cachedUser, status: 200, message: 'OK' }
      }

      const res = await apiMethods.fetch<User>(
        this._client.resolveUrl('/identity/o/api/userinfo')
      )
      if (res.ok) this._cachedUser = res.data
      return res
    }

    const user = this.resolveCachedUser()

    return user
      ? { ok: true, data: user, status: 200, message: 'OK' }
      : { ok: false, status: 401, message: 'Not authenticated' }
  }

  async can(
    action: PermissionAction,
    resource: PermissionResource,
    workspace: WorkspaceContract.DetailResponse
  ): Promise<boolean> {
    const res = await this.get()
    if (!res.ok) return false
    const user = res.data

    if (isAdmin(user)) return true
    if (isOwner(user, workspace)) return true

    const perms: Permission[] = workspace.collaboratorRole?.permissions ?? []
    const allowed = perms.some(
      (p) => p.action === action && (p.resource === '*' || p.resource === resource)
    )

    return allowed
  }
}

function isAdmin(user: User | null): boolean {
  return (user?.accountType as string) === 'admin'
}

function isOwner(
  user: User | null,
  workspace: WorkspaceContract.DetailResponse | null
): boolean {
  if (!user?.email || !workspace?.owner?.email) return false
  return workspace.owner.email === user.email
}
