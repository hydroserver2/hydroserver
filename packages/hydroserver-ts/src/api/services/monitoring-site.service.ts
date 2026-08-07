import { apiMethods } from '../apiMethods'
import { HydroServerBaseService } from './base'
import { MonitoringSiteContract as C } from '../../generated/contracts'
import type * as Data from '../../generated/data.types'
import {
  MonitoringSite,
  PostHydroShareArchive,
  HydroShareArchive,
  MonitoringSiteMarker,
  SiteTypeIcon,
  MonitoringSiteMapSummary,
  MonitoringSiteTaskSummary,
  Tag,
} from '../../types'
import { ApiResponse } from '../responseInterceptor'
import { normalizeAttachmentCollection } from './attachment-link'

type TagPostBody = Data.components['schemas']['TagPostBody']
type TagDeleteBody = Data.components['schemas']['TagDeleteBody']
type TagResponse = Data.components['schemas']['TagGetResponse']
type FileAttachmentResponse =
  Data.components['schemas']['FileAttachmentGetResponse']

export class MonitoringSiteService extends HydroServerBaseService<typeof C, MonitoringSite> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = MonitoringSite

  listMarkers(): Promise<ApiResponse<MonitoringSiteMarker[]>> {
    return apiMethods.fetch<MonitoringSiteMarker[]>(`${this._route}/markers`)
  }

  listSiteSummaries(
    workspaceId?: string
  ): Promise<ApiResponse<MonitoringSiteMapSummary[]>> {
    return apiMethods.fetch<MonitoringSiteMapSummary[]>(
      this.withQuery(`${this._route}/site-summaries`, {
        workspace_id: workspaceId,
      })
    )
  }

  listTaskSummaries(params: {
    workspace_id?: string | string[]
    type?: string | string[]
  }): Promise<ApiResponse<MonitoringSiteTaskSummary[]>> {
    return apiMethods.fetch<MonitoringSiteTaskSummary[]>(
      this.withQuery(`${this._route}/task-summaries`, params)
    )
  }

  updatePrivacy = (
    id: string,
    isPrivate: boolean
  ): Promise<ApiResponse<MonitoringSite>> =>
    apiMethods.patch<MonitoringSite>(`${this._route}/${id}`, { isPrivate })

  getSiteTypes = () => apiMethods.fetch<string[]>(`${this._route}/site-types`)
  getSiteTypeIcons = () =>
    apiMethods.fetch<SiteTypeIcon[]>(`${this._route}/site-type-icons`)
  /* ----------------------- Sub-resources: Tags ----------------------- */

  getTags(monitoringSiteId: string) {
    const url = `${this._route}/${monitoringSiteId}/tags`
    return apiMethods.fetch<Tag[]>(url)
  }

  getTagKeys(params: { workspace_id?: string; monitoring_site_id?: string }) {
    const url = this.withQuery(`${this._route}/tags/keys`, params)
    return apiMethods.fetch<Record<string, string[]>>(url)
  }

  createTag(monitoringSiteId: string, tag: TagPostBody) {
    const url = `${this._route}/${monitoringSiteId}/tags`
    return apiMethods.post<TagResponse>(url, tag)
  }

  updateTag(monitoringSiteId: string, tag: TagPostBody) {
    const url = `${this._route}/${monitoringSiteId}/tags`
    return apiMethods.put<TagResponse>(url, tag)
  }

  deleteTag(monitoringSiteId: string, tag: TagDeleteBody) {
    const url = `${this._route}/${monitoringSiteId}/tags`
    return apiMethods.delete<null>(url, tag)
  }

  /* ----------------- Sub-resources: File Attachments ----------------- */

  getFileAttachmentTypes = () =>
    apiMethods.fetch<string[]>(`${this._route}/file-attachment-types`)

  async uploadAttachments(monitoringSiteId: string, data: FormData) {
    const url = `${this._route}/${monitoringSiteId}/file-attachments`
    const res = await apiMethods.post<FileAttachmentResponse>(url, data)
    if (!res.ok) return res
    return {
      ...res,
      data: normalizeAttachmentCollection(
        res.data,
        this._client.host
      ),
    } as ApiResponse<FileAttachmentResponse>
  }

  async getAttachments(monitoringSiteId: string) {
    const url = `${this._route}/${monitoringSiteId}/file-attachments`
    const res = await apiMethods.paginatedFetch<FileAttachmentResponse[]>(url)
    if (!res.ok) return res
    return {
      ...res,
      data: normalizeAttachmentCollection(
        res.data,
        this._client.host
      ),
    } as ApiResponse<FileAttachmentResponse[]>
  }

  deleteAttachment(monitoringSiteId: string, name: string) {
    const url = `${this._route}/${monitoringSiteId}/file-attachments`
    return apiMethods.delete<null>(url, { name })
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
