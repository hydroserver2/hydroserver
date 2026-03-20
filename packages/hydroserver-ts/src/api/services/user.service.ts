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

export class UserService {
  private readonly _client: HydroServer
  readonly accountBase: string
  readonly providerBase: string

  constructor(client: HydroServer) {
    this._client = client
    this.accountBase = `${this._client.authBase}/browser/account`
    this.providerBase = `${this._client.authBase}/browser/provider`
  }

  get = async (): Promise<ApiResponse<User>> =>
    apiMethods.fetch(this.accountBase)

  create = async (user: User): Promise<ApiResponse<User>> => {
    const res = await apiMethods.post(this.accountBase, user)
    this._client.session._setSession(res)
    this._client.session.unverifiedEmail = user.email
    return res
  }

  update = async (user: User, oldUser?: User): Promise<ApiResponse<User>> =>
    apiMethods.patch(this.accountBase, user, oldUser)

  updateItem = async (user: User, oldUser?: User): Promise<User | null> => {
    const res = await apiMethods.patch(this.accountBase, user, oldUser)
    return res.ok ? res.data : null
  }

  delete = async () => apiMethods.delete(this.accountBase)

  /* ---------------------------- Email verification --------------------------- */
  async sendVerificationEmail(email: string) {
    return apiMethods.put(`${this.accountBase}/email/verify`, { email })
  }

  async verifyEmailWithCode(key: string) {
    const res = await apiMethods.post(`${this.accountBase}/email/verify`, {
      key,
    })
    this._client.session._setSession(res)
    return res
  }

  /* ---------------------------- Password helpers --------------------------- */
  requestPasswordReset(email: string) {
    const url = `${this.accountBase}/password/request`
    return apiMethods.post(url, { email })
  }

  resetPassword(key: string, password: string) {
    const url = `${this.accountBase}/password/reset`
    return apiMethods.post(url, { key, password })
  }

  /* ----------------------- Organization/User types ------------------------- */
  getOrganizationTypes() {
    const url = `${this.accountBase}/organization-types`
    return apiMethods.fetch(url)
  }

  getUserTypes() {
    const url = `${this.accountBase}/user-types`
    return apiMethods.fetch(url)
  }

  /* ------------------------------ Providers -------------------------------- */
  listProviderConnections() {
    const url = `${this.providerBase}/connections`
    return apiMethods.fetch(url)
  }

  disconnectProvider(provider: string) {
    const url = toUrl(`${this.providerBase}/connections`, { provider })
    return apiMethods.delete(url)
  }

  redirectToProvider(provider: string, next?: string) {
    const url = toUrl(`${this.providerBase}/redirect`, { provider, next })
    return apiMethods.fetch(url)
  }

  async can(
    action: PermissionAction,
    resource: PermissionResource,
    workspace: WorkspaceContract.DetailResponse
  ): Promise<boolean> {
    const res = await this.get()
    const user = res.data

    if (isAdmin(user)) return true
    if (isOwner(user, workspace)) return true

    const perms: Permission[] = workspace.collaboratorRole?.permissions ?? []
    const allowed =
      hasGlobalPermission(perms) ||
      perms.some((p) => p.action === action && p.resource === resource)

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

function hasGlobalPermission(perms: Permission[]): boolean {
  return perms.some((p) => p.resource === '*' && p.action === '*')
}

function toUrl(
  base: string,
  params?: Record<string, string | number | boolean | undefined | null>
): string {
  if (!params) return base
  const url = new URL(base, globalThis.location?.origin ?? undefined)
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null) continue
    url.searchParams.set(k, String(v))
  }
  return url.toString()
}
