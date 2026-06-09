import { apiMethods } from '../apiMethods'
import { HydroServerBaseService } from './base'
import { ThingContract as C } from '../../generated/contracts'
import type * as Data from '../../generated/data.types'
import {
  Thing,
  PostHydroShareArchive,
  HydroShareArchive,
  ThingMarker,
  ThingSiteSummary,
  ThingTaskSummary,
  Tag,
  FileAttachment,
} from '../../types'
import { ApiResponse } from '../responseInterceptor'
import { normalizeAttachmentCollection } from './attachment-link'

type TagPostBody = Data.components['schemas']['TagPostBody']
type TagDeleteBody = Data.components['schemas']['TagDeleteBody']

export class ThingService extends HydroServerBaseService<typeof C, Thing> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = Thing

  listMarkers(): Promise<ApiResponse<ThingMarker[]>> {
    return apiMethods.fetch<ThingMarker[]>(`${this._route}/markers`)
  }

  listSiteSummaries(workspaceId: string): Promise<ApiResponse<ThingSiteSummary[]>> {
    return apiMethods.fetch<ThingSiteSummary[]>(
      this.withQuery(`${this._route}/site-summaries`, { workspace_id: workspaceId })
    )
  }

  listTaskSummaries(params: {
    workspace_id?: string | string[]
    site_type?: string | string[]
  }): Promise<ApiResponse<ThingTaskSummary[]>> {
    return apiMethods.fetch<ThingTaskSummary[]>(
      this.withQuery(`${this._route}/task-summaries`, params)
    )
  }

  updatePrivacy = (
    id: string,
    isPrivate: boolean
  ): Promise<ApiResponse<Thing>> =>
    apiMethods.patch<Thing>(`${this._route}/${id}`, { isPrivate })

  getSiteTypes = () => apiMethods.fetch<string[]>(`${this._route}/site-types`)
  getSamplingFeatureTypes = () =>
    apiMethods.fetch<string[]>(`${this._route}/sampling-feature-types`)

  /* ----------------------- Sub-resources: Tags ----------------------- */

  getTags(thingId: string) {
    const url = `${this._route}/${thingId}/tags`
    return apiMethods.fetch<Tag[]>(url)
  }

  getTagKeys(params: { workspace_id?: string; thing_id?: string }) {
    const url = this.withQuery(`${this._route}/tags/keys`, params)
    return apiMethods.fetch<Record<string, string[]>>(url)
  }

  createTag(thingId: string, tag: TagPostBody) {
    const url = `${this._route}/${thingId}/tags`
    return apiMethods.post(url, tag)
  }

  updateTag(thingId: string, tag: TagPostBody) {
    const url = `${this._route}/${thingId}/tags`
    return apiMethods.put(url, tag)
  }

  deleteTag(thingId: string, tag: TagDeleteBody) {
    const url = `${this._route}/${thingId}/tags`
    return apiMethods.delete(url, tag)
  }

  /* ----------------- Sub-resources: File Attachments ----------------- */

  getFileAttachmentTypes = () =>
    apiMethods.fetch<string[]>(`${this._route}/file-attachment-types`)

  async uploadAttachments(thingId: string, data: FormData) {
    const url = `${this._route}/${thingId}/file-attachments`
    const res = await apiMethods.post(url, data)
    if (!res.ok) return res
    return {
      ...res,
      data: normalizeAttachmentCollection(
        res.data as { link?: string }[],
        this._client.host
      ),
    } as ApiResponse<FileAttachment>
  }

  async getAttachments(thingId: string) {
    const url = `${this._route}/${thingId}/file-attachments`
    const res = await apiMethods.paginatedFetch(url)
    if (!res.ok) return res
    return {
      ...res,
      data: normalizeAttachmentCollection(
        res.data as { link?: string }[],
        this._client.host
      ),
    } as ApiResponse<FileAttachment[]>
  }

  deleteAttachment(thingId: string, name: string) {
    const url = `${this._route}/${thingId}/file-attachments`
    return apiMethods.delete(url, { name })
  }

  /* --------------- Sub-resources: HydroShare Archive ----------------- */

  async createHydroShareArchive(archive: PostHydroShareArchive) {
    const url = `${this._route}/${archive.thingId}/archive`
    return await apiMethods.post<HydroShareArchive>(url, archive)
  }

  async updateHydroShareArchive(
    archive: HydroShareArchive,
    old?: HydroShareArchive
  ) {
    const url = `${this._route}/${archive.thingId}/archive`
    return await apiMethods.patch<HydroShareArchive>(url, archive, old)
  }

  getHydroShareArchive(thingId: string) {
    const url = `${this._route}/${thingId}/archive`
    return apiMethods.fetch<HydroShareArchive>(url)
  }

  deleteHydroShareArchive(thingId: string) {
    const url = `${this._route}/${thingId}/archive`
    return apiMethods.delete(url)
  }

  triggerHydroShareArchive(thingId: string) {
    const url = `${this._route}/${thingId}/archive/trigger`
    return apiMethods.post(url, {})
  }

  /* ---------------------- Ownership management ----------------------- */

  removeOwner(thingId: string, email: string) {
    const url = `${this._route}/${thingId}/ownership`
    return apiMethods.patch(url, { email, removeOwner: true })
  }

  addSecondaryOwner(thingId: string, email: string) {
    const url = `${this._route}/${thingId}/ownership`
    return apiMethods.patch(url, { email, makeOwner: true })
  }

  transferPrimaryOwnership(thingId: string, email: string) {
    const url = `${this._route}/${thingId}/ownership`
    return apiMethods.patch(url, { email, transferPrimary: true })
  }
}
