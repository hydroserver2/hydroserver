import { apiMethods } from '../apiMethods'
import { HydroServerBaseService } from './base'
import { MonitoringSiteContract as C } from '../../generated/contracts'
import type * as Data from '../../generated/ogc.types'
import {
  MonitoringSite,
  PostHydroShareArchive,
  HydroShareArchive,
  MonitoringSiteMarker,
  SiteTypeIcon,
  MonitoringSiteMapSummary,
  MonitoringSiteTaskSummary,
} from '../../types'
import { ApiResponse } from '../responseInterceptor'
import {
  normalizeLinkCollection,
  normalizeLinkRecord,
} from './link-normalization'

type LinkedResourceResponse = Data.components['schemas']['LinkedResourceGetResponse']

export class MonitoringSiteService extends HydroServerBaseService<typeof C, MonitoringSite> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = MonitoringSite

  listMarkers(): Promise<ApiResponse<MonitoringSiteMarker[]>> {
    return apiMethods.fetch<MonitoringSiteMarker[]>(`${this._collectionRoute}/markers`)
  }

  listSiteSummaries(
    workspaceId?: string
  ): Promise<ApiResponse<MonitoringSiteMapSummary[]>> {
    return apiMethods.fetch<MonitoringSiteMapSummary[]>(
      this.withQuery(`${this._collectionRoute}/site-summaries`, {
        workspaceId,
      })
    )
  }

  listTaskSummaries(params: {
    workspaceId?: string | string[]
    type?: string | string[]
  }): Promise<ApiResponse<MonitoringSiteTaskSummary[]>> {
    return apiMethods.fetch<MonitoringSiteTaskSummary[]>(
      this.withQuery(`${this._collectionRoute}/task-summaries`, params)
    )
  }

  updatePrivacy = (
    id: string,
    isPrivate: boolean
  ): Promise<ApiResponse<MonitoringSite>> => this.patchAndRefetch(id, { isPrivate })

  getSiteTypeIcons = () =>
    apiMethods.fetch<SiteTypeIcon[]>(`${this._collectionRoute}/site-type-icons`)
  /* ----------------------- Sub-resources: Tags ----------------------- */

  getTagKeys(params: { workspaceId?: string; monitoringSiteId?: string }) {
    const url = this.withQuery(`${this._collectionRoute}/tags/keys`, params)
    return apiMethods.fetch<Record<string, string[]>>(url)
  }

  setTag(monitoringSiteId: string, key: string, value: string) {
    return this.patchAndRefetch(monitoringSiteId, { tags: { [key]: value } })
  }

  deleteTag(monitoringSiteId: string, key: string) {
    return this.patchAndRefetch(monitoringSiteId, { tags: { [key]: null } })
  }

  private async patchAndRefetch(
    id: string,
    body: Record<string, unknown>
  ): Promise<ApiResponse<MonitoringSite>> {
    const res = await apiMethods.patch<null>(`${this._route}/${id}`, body)
    if (!res.ok) return res as ApiResponse<MonitoringSite>
    return this.get(id)
  }

  /* ------------------ Sub-resources: Linked Resources ------------------ */

  async getLinkedResources(monitoringSiteId: string) {
    const url = `${this._route}/${monitoringSiteId}/linked-resources`
    const res = await apiMethods.paginatedFetch<LinkedResourceResponse[]>(url)
    if (!res.ok) return res
    return {
      ...res,
      data: normalizeLinkCollection(res.data, this._client.host),
    } as ApiResponse<LinkedResourceResponse[]>
  }

  async createLinkedResource(
    monitoringSiteId: string,
    data: FormData
  ): Promise<ApiResponse<LinkedResourceResponse>> {
    const url = `${this._route}/${monitoringSiteId}/linked-resources`
    const res = await apiMethods.post<{ id: string }>(url, data)
    if (!res.ok) return res
    return this.getLinkedResource(monitoringSiteId, res.data.id)
  }

  async updateLinkedResource(
    monitoringSiteId: string,
    linkedResourceId: string,
    data: FormData
  ): Promise<ApiResponse<LinkedResourceResponse>> {
    const url = `${this._route}/${monitoringSiteId}/linked-resources/${linkedResourceId}`
    const res = await apiMethods.patch<null>(url, data)
    if (!res.ok) return res
    return this.getLinkedResource(monitoringSiteId, linkedResourceId)
  }

  async getLinkedResource(
    monitoringSiteId: string,
    linkedResourceId: string
  ): Promise<ApiResponse<LinkedResourceResponse>> {
    const url = `${this._route}/${monitoringSiteId}/linked-resources/${linkedResourceId}`
    const res = await apiMethods.fetch<LinkedResourceResponse>(url)
    if (!res.ok) return res
    return { ...res, data: normalizeLinkRecord(res.data, this._client.host) }
  }

  deleteLinkedResource(monitoringSiteId: string, linkedResourceId: string) {
    const url = `${this._route}/${monitoringSiteId}/linked-resources/${linkedResourceId}`
    return apiMethods.delete<null>(url)
  }

  /* --------------- Sub-resources: HydroShare Archive ----------------- */

  async createHydroShareArchive(archive: PostHydroShareArchive) {
    const url = `${this._route}/${archive.monitoringSiteId}/archive`
    return await apiMethods.post<HydroShareArchive>(url, archive)
  }

  async updateHydroShareArchive(
    archive: HydroShareArchive,
    old?: HydroShareArchive
  ) {
    const url = `${this._route}/${archive.monitoringSiteId}/archive`
    return await apiMethods.patch<HydroShareArchive>(url, archive, old)
  }

  getHydroShareArchive(monitoringSiteId: string) {
    const url = `${this._route}/${monitoringSiteId}/archive`
    return apiMethods.fetch<HydroShareArchive>(url)
  }

  deleteHydroShareArchive(monitoringSiteId: string) {
    const url = `${this._route}/${monitoringSiteId}/archive`
    return apiMethods.delete<null>(url)
  }

  triggerHydroShareArchive(monitoringSiteId: string) {
    const url = `${this._route}/${monitoringSiteId}/archive/trigger`
    return apiMethods.post<string>(url, {})
  }

  /* ---------------------- Ownership management ----------------------- */

  removeOwner(monitoringSiteId: string, email: string) {
    const url = `${this._route}/${monitoringSiteId}/ownership`
    return apiMethods.patch<MonitoringSite>(url, { email, removeOwner: true })
  }

  addSecondaryOwner(monitoringSiteId: string, email: string) {
    const url = `${this._route}/${monitoringSiteId}/ownership`
    return apiMethods.patch<MonitoringSite>(url, { email, makeOwner: true })
  }

  transferPrimaryOwnership(monitoringSiteId: string, email: string) {
    const url = `${this._route}/${monitoringSiteId}/ownership`
    return apiMethods.patch<MonitoringSite>(url, { email, transferPrimary: true })
  }
}
