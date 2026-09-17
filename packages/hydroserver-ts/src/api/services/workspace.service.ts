import { apiMethods } from '../apiMethods'
import { HydroServerBaseService, QueryParamsOf } from './base'
import { WorkspaceContract as C } from '../../generated/contracts'
import {
  Collaborator,
  CollaboratorRole,
  ServiceAccount,
  UserInfo,
  Workspace as M,
} from '../../types'
import type * as Data from '../../generated/data.types'
import { ApiResponse } from '../responseInterceptor'

type RoleQueryParameters = NonNullable<
  Data.operations['interfaces_api_views_iam_role_get_roles']['parameters']['query']
>

const WORKSPACE_INCLUDE = 'owner,pendingTransferTo,collaboratorRole' as const

type RawWorkspace = {
  id: string
  name: string
  isPrivate: boolean
  ownerEmail: string
  pendingTransferToEmail?: string | null
  collaboratorRoleId?: string | null
}

type IncludedBuckets = {
  owners?: UserInfo[]
  pendingTransferRecipients?: UserInfo[]
  collaboratorRoles?: CollaboratorRole[]
}

const COLLABORATOR_INCLUDE = 'role,user,serviceAccount' as const

type RawCollaborator = {
  roleId: string
  userEmail: string | null
  serviceAccountEmail: string | null
}

type CollaboratorIncludedBuckets = {
  roles?: CollaboratorRole[]
  users?: UserInfo[]
  serviceAccounts?: { id: string; name: string; email: string }[]
}

/**
 * Builds a Collaborator from a raw collaborator row plus its sideloaded
 * role/user/serviceAccount buckets.
 */
function mergeCollaborator(
  row: RawCollaborator,
  included?: CollaboratorIncludedBuckets
): Collaborator {
  const roles = included?.roles ?? []
  const users = included?.users ?? []
  const serviceAccounts = included?.serviceAccounts ?? []
  const collaborator = new Collaborator()
  collaborator.user = row.userEmail
    ? (users.find((u) => u.email === row.userEmail) ?? null)
    : null
  collaborator.serviceAccount = row.serviceAccountEmail
    ? (serviceAccounts.find((sa) => sa.email === row.serviceAccountEmail) ?? null)
    : null
  collaborator.role = roles.find((r) => r.id === row.roleId) ?? collaborator.role
  return collaborator
}

/**
 * Builds a Workspace from a raw row plus its sideloaded
 * owner/pendingTransferTo/collaboratorRole buckets.
 */
function mergeIncluded(row: RawWorkspace, included?: IncludedBuckets): M {
  const owners = included?.owners ?? []
  const recipients = included?.pendingTransferRecipients ?? []
  const roles = included?.collaboratorRoles ?? []

  const workspace = new M()
  workspace.id = row.id
  workspace.name = row.name
  workspace.isPrivate = row.isPrivate
  workspace.owner = owners.find((o) => o.email === row.ownerEmail) ?? null
  workspace.pendingTransferTo = row.pendingTransferToEmail
    ? (recipients.find((u) => u.email === row.pendingTransferToEmail) ?? null)
    : null
  workspace.collaboratorRole = row.collaboratorRoleId
    ? (roles.find((r) => r.id === row.collaboratorRoleId) ?? null)
    : null
  return workspace
}

/**
 * Transport layer for /workspaces routes. Builds URLs, handles pagination,
 * and returns rich WorkspaceModel instances.
 */
export class WorkspaceService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  list = async (
    params: Partial<QueryParamsOf<typeof C>> & { fetch_all?: boolean } = {}
  ): Promise<ApiResponse<M[]>> => {
    const { fetch_all, ...query } = params
    const url = this.withQuery(this._route, { ...query, include: WORKSPACE_INCLUDE })
    const res = fetch_all
      ? await apiMethods.paginatedFetch<RawWorkspace[]>(url)
      : await apiMethods.fetch<RawWorkspace[]>(url)
    if (!res.ok) return res as ApiResponse<M[]>
    const included = res.included as IncludedBuckets | undefined
    return { ...res, data: res.data.map((row) => mergeIncluded(row, included)) }
  }

  get = async (id: string): Promise<ApiResponse<M>> => {
    const url = this.withQuery(`${this._route}/${id}`, {
      include: WORKSPACE_INCLUDE,
    })
    const res = await apiMethods.fetch<RawWorkspace>(url)
    if (!res.ok) return res as ApiResponse<M>
    return {
      ...res,
      data: mergeIncluded(res.data, res.included as IncludedBuckets | undefined),
    }
  }

  // ---------- sub-resources: collaborators ----------
  async getCollaborators(
    workspaceId: string
  ): Promise<ApiResponse<Collaborator[]>> {
    const url = this.withQuery(`${this._route}/${workspaceId}/collaborators`, {
      include: COLLABORATOR_INCLUDE,
    })
    const res = await apiMethods.paginatedFetch<RawCollaborator[]>(url)
    if (!res.ok) return res as ApiResponse<Collaborator[]>
    const included = res.included as CollaboratorIncludedBuckets | undefined
    return {
      ...res,
      data: res.data.map((row) => mergeCollaborator(row, included)),
    }
  }

  async addCollaborator(
    workspaceId: string,
    email: string,
    roleId: string
  ): Promise<ApiResponse<Collaborator>> {
    const url = `${this._route}/${workspaceId}/collaborators`
    const res = await apiMethods.post<{ id: number }>(url, { email, roleId })
    if (!res.ok) return res

    const listRes = await this.getCollaborators(workspaceId)
    if (!listRes.ok) return listRes
    const added = listRes.data.find(
      (c) => c.user?.email === email || c.serviceAccount?.email === email
    )
    if (!added) {
      return {
        ok: false,
        status: 404,
        message: 'Collaborator not found after being added.',
      }
    }
    return { ...listRes, data: added }
  }

  updateCollaboratorRole(workspaceId: string, email: string, roleId: string) {
    const url = `${this._route}/${workspaceId}/collaborators`
    return apiMethods.put<null>(url, { email, roleId })
  }

  removeCollaborator = (workspaceId: string, email: string) =>
    apiMethods.delete<null>(`${this._route}/${workspaceId}/collaborators`, {
      email,
    })

  // ---------- sub-resources: ownership transfer ----------
  transferOwnership = (workspaceId: string, newOwner: string) =>
    apiMethods.post<string>(`${this._route}/${workspaceId}/transfer`, {
      newOwner,
    })

  acceptOwnershipTransfer = (workspaceId: string) =>
    apiMethods.put<string>(`${this._route}/${workspaceId}/transfer`)

  rejectOwnershipTransfer = (id: string) =>
    apiMethods.delete<string>(`${this._route}/${id}/transfer`)

  // ---------- sub-resources: service accounts ----------
  getServiceAccounts(workspaceId: string) {
    const url = `${this._route}/${workspaceId}/service-accounts`
    return apiMethods.paginatedFetch<ServiceAccount[]>(url)
  }

  getServiceAccount = (workspaceId: string, serviceAccountId: string) =>
    apiMethods.fetch<ServiceAccount>(
      `${this._route}/${workspaceId}/service-accounts/${serviceAccountId}`
    )

  createServiceAccount = async (
    serviceAccount: ServiceAccount,
    roleId: string
  ): Promise<ApiResponse<ServiceAccount>> => {
    const res = await apiMethods.post<{ id: string; key: string }>(
      `${this._route}/${serviceAccount.workspaceId}/service-accounts`,
      {
        name: serviceAccount.name,
        description: serviceAccount.description,
        isActive: serviceAccount.isActive,
        keyExpiresAt: serviceAccount.keyExpiresAt || null,
        roleId,
      }
    )
    if (!res.ok) return res as ApiResponse<ServiceAccount>
    const fullRes = await this.getServiceAccount(
      serviceAccount.workspaceId,
      res.data.id
    )
    if (!fullRes.ok) return fullRes
    return { ...fullRes, data: { ...fullRes.data, key: res.data.key } }
  }

  updateServiceAccount = async (
    newAccount: ServiceAccount,
    oldAccount?: ServiceAccount
  ): Promise<ApiResponse<ServiceAccount>> => {
    const res = await apiMethods.patch<null>(
      `${this._route}/${newAccount.workspaceId}/service-accounts/${newAccount.id}`,
      {
        name: newAccount.name,
        description: newAccount.description,
        isActive: newAccount.isActive,
        keyExpiresAt: newAccount.keyExpiresAt || null,
      },
      oldAccount
        ? {
            name: oldAccount.name,
            description: oldAccount.description,
            isActive: oldAccount.isActive,
            keyExpiresAt: oldAccount.keyExpiresAt || null,
          }
        : oldAccount
    )
    if (!res.ok) return res as ApiResponse<ServiceAccount>
    return this.getServiceAccount(newAccount.workspaceId, newAccount.id)
  }

  regenerateServiceAccountKey = async (
    workspaceId: string,
    account: ServiceAccount
  ): Promise<ApiResponse<ServiceAccount>> => {
    const res = await apiMethods.put<{ key: string }>(
      `${this._route}/${workspaceId}/service-accounts/${account.id}/regenerate`
    )
    if (!res.ok) return res as ApiResponse<ServiceAccount>
    return {
      ok: true,
      status: res.status,
      message: res.message,
      data: { ...account, key: res.data.key },
    }
  }

  deleteServiceAccount = async (
    workspaceId: string,
    serviceAccountId: string
  ) =>
    apiMethods.delete<null>(
      `${this._route}/${workspaceId}/service-accounts/${serviceAccountId}`
    )

  getRoles = (params?: RoleQueryParameters) => {
    const url = this.withQuery(`${this._client.baseRoute}/roles`, params)
    return apiMethods.paginatedFetch<CollaboratorRole[]>(url)
  }

  getRole = (id: string) =>
    apiMethods.fetch<CollaboratorRole>(`${this._client.baseRoute}/roles/${id}`)
}
