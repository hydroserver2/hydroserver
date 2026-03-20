import { apiMethods } from '../apiMethods'
import { HydroServerBaseService } from './base'
import { ThingContract as C } from '../../generated/contracts'
import type * as Data from '../../generated/data.types'
import { Thing, PostHydroShareArchive, HydroShareArchive } from '../../types'
import { ApiResponse } from '../responseInterceptor'
import { normalizeAttachmentCollection } from './attachment-link'

type TagPostBody = Data.components['schemas']['TagPostBody']
type TagDeleteBody = Data.components['schemas']['TagDeleteBody']

export class ThingService extends HydroServerBaseService<typeof C, Thing> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = Thing

  updatePrivacy = (
    id: string,
    isPrivate: boolean
  ): Promise<ApiResponse<Thing>> =>
    apiMethods.patch(`${this._route}/${id}`, { isPrivate })

  getSiteTypes = () => apiMethods.fetch(`${this._route}/site-types`)
  getSamplingFeatureTypes = () =>
    apiMethods.fetch(`${this._route}/sampling-feature-types`)

  /* ----------------------- Sub-resources: Tags ----------------------- */

  getTags(thingId: string) {
    const url = `${this._route}/${thingId}/tags`
    return apiMethods.fetch(url)
  }

  getTagKeys(params: { workspace_id?: string; thing_id?: string }) {
    const url = this.withQuery(`${this._route}/tags/keys`, params)
    return apiMethods.fetch(url)
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
    apiMethods.fetch(`${this._route}/file-attachment-types`)

  async uploadAttachments(thingId: string, data: FormData) {
    const url = `${this._route}/${thingId}/file-attachments`
    const res = await apiMethods.post(url, data)
    return {
      ...res,
      data: normalizeAttachmentCollection(res.data as any, this._client.host),
    } as ApiResponse
  }

  async getAttachments(thingId: string) {
    const url = `${this._route}/${thingId}/file-attachments`
    const res = await apiMethods.paginatedFetch(url)
    return {
      ...res,
      data: normalizeAttachmentCollection(res.data as any, this._client.host),
    } as ApiResponse
  }

  deleteAttachment(thingId: string, name: string) {
    const url = `${this._route}/${thingId}/file-attachments`
    return apiMethods.delete(url, { name })
  }

  /* --------------- Sub-resources: HydroShare Archive ----------------- */

  async createHydroShareArchive(archive: PostHydroShareArchive) {
    const url = `${this._route}/${archive.thingId}/archive`
    return await apiMethods.post(url, archive)
  }

  async updateHydroShareArchive(
    archive: HydroShareArchive,
    old?: HydroShareArchive
  ) {
    const url = `${this._route}/${archive.thingId}/archive`
    return await apiMethods.patch(url, archive, old)
  }

  getHydroShareArchive(thingId: string) {
    const url = `${this._route}/${thingId}/archive`
    return apiMethods.fetch(url)
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
