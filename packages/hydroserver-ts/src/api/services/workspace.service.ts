import { apiMethods } from '../apiMethods'
import { HydroServerBaseService } from './base'
import { WorkspaceContract as C } from '../../generated/contracts'
import {
  Collaborator,
  CollaboratorRole,
  ServiceAccount,
  Workspace as M,
} from '../../types'
import type * as Data from '../../generated/data.types'
import { ApiResponse } from '../responseInterceptor'

type RoleQueryParameters =
  NonNullable<
    Data.operations['interfaces_api_views_iam_role_get_roles']['parameters']['query']
  >

/**
 * Transport layer for /workspaces routes. Builds URLs, handles pagination,
 * and returns rich WorkspaceModel instances.
 */
export class WorkspaceService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  // ---------- sub-resources: collaborators ----------
  getCollaborators(workspaceId: string) {
    const url = `${this._route}/${workspaceId}/collaborators`
    return apiMethods.fetch<Collaborator[]>(url)
  }

  addCollaborator(workspaceId: string, email: string, roleId: string) {
    const url = `${this._route}/${workspaceId}/collaborators`
    return apiMethods.post<Collaborator>(url, { email, roleId })
  }

  updateCollaboratorRole(workspaceId: string, email: string, roleId: string) {
    const url = `${this._route}/${workspaceId}/collaborators`
    return apiMethods.put<Collaborator>(url, { email, roleId })
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
    return apiMethods.fetch<ServiceAccount[]>(url)
  }

  getServiceAccount = (workspaceId: string, serviceAccountId: string) =>
    apiMethods.fetch<ServiceAccount>(
      `${this._route}/${workspaceId}/service-accounts/${serviceAccountId}?expand_related=true`
    )

  createServiceAccount = async (
    serviceAccount: ServiceAccount,
    roleId: string
  ): Promise<ApiResponse<ServiceAccount>> => {
    const res = await apiMethods.post<ServiceAccount>(
      `${this._route}/${serviceAccount.workspaceId}/service-accounts?expand_related=true`,
      {
        name: serviceAccount.name,
        description: serviceAccount.description,
        isActive: serviceAccount.isActive,
        keyExpiresAt: serviceAccount.keyExpiresAt || null,
      }
    )
    if (!res.ok) return res

    const collaboratorRes = await this.addCollaborator(
      serviceAccount.workspaceId,
      res.data.email,
      roleId
    )
    if (!collaboratorRes.ok) return collaboratorRes

    return res
  }

  updateServiceAccount = async (
    newAccount: ServiceAccount,
    oldAccount?: ServiceAccount
  ): Promise<ApiResponse<ServiceAccount>> => {
    return await apiMethods.patch<ServiceAccount>(
      `${this._route}/${newAccount.workspaceId}/service-accounts/${newAccount.id}?expand_related=true`,
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
  }

  regenerateServiceAccountKey = async (
    workspaceId: string,
    serviceAccountId: string
  ) =>
    apiMethods.put<ServiceAccount>(
      `${this._route}/${workspaceId}/service-accounts/${serviceAccountId}/regenerate?expand_related=true`
    )

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
