import { apiMethods } from '../apiMethods'
import { HydroServerBaseService } from './base'
import {
  DatastreamContract as C,
  ObservationContract,
} from '../../generated/contracts'
import type * as Data from '../../generated/data.types'
import type { ApiResponse } from '../responseInterceptor'
import { Datastream as M } from '../../types'
import JSZip from 'jszip'
import { normalizeAttachmentCollection } from './attachment-link'

type WithId = { id: string }

type TagPostBody = Data.components['schemas']['TagPostBody']
type TagDeleteBody = Data.components['schemas']['TagDeleteBody']

type ObservationBulkPostQueryParameters = {
  /**
   * Mode
   * @description Specifies how new observations are added to the datastream. `insert` allows observations at any timestamp. `append` adds only future observations (after the latest existing timestamp). `backfill` adds only historical observations (before the earliest existing timestamp). `replace` deletes all observations in the range of provided observations before inserting new ones.
   */
  mode?: ('insert' | 'append' | 'backfill' | 'replace') | null
}

type ObservationBulkPostBody = {
  fields: ('phenomenonTime' | 'result')[]
  data: unknown[][]
}

type ObservationBulkDeleteBody = {
  phenomenonTimeStart?: string | null
  phenomenonTimeEnd?: string | null
}

type ObservationPostBody = {
  phenomenonTime: string
  result: number
}
/**
 * Transport layer for /datastreams routes.
 * Inherits CRUD + handle helpers from HydroServerBaseService and adds:
 * - CSV download helpers (single + zip)
 * - Enumeration endpoints (/statuses, /aggregation-statistics, /sampled-mediums)
 * - Observation sub-resource endpoints under /datastreams/{id}/observations
 */
export class DatastreamService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  /* ----------------------- Sub-resources: Tags ----------------------- */

  getTags(datastreamId: string) {
    const url = `${this._route}/${datastreamId}/tags`
    return apiMethods.fetch(url)
  }

  getTagKeys(params: { workspace_id?: string; datastream_id?: string }) {
    const url = this.withQuery(`${this._route}/tags/keys`, params)
    return apiMethods.fetch(url)
  }

  createTag(datastreamId: string, tag: TagPostBody) {
    const url = `${this._route}/${datastreamId}/tags`
    return apiMethods.post(url, tag)
  }

  updateTag(datastreamId: string, tag: TagPostBody) {
    const url = `${this._route}/${datastreamId}/tags`
    return apiMethods.put(url, tag)
  }

  deleteTag(datastreamId: string, tag: TagDeleteBody) {
    const url = `${this._route}/${datastreamId}/tags`
    return apiMethods.delete(url, tag)
  }

  /* ----------------- Sub-resources: File Attachments ----------------- */

  getFileAttachmentTypes = () =>
    apiMethods.fetch(`${this._route}/file-attachment-types`)

  async uploadAttachments(datastreamId: string, data: FormData) {
    const url = `${this._route}/${datastreamId}/file-attachments`
    const res = await apiMethods.post(url, data)
    return {
      ...res,
      data: normalizeAttachmentCollection(res.data as any, this._client.host),
    } as ApiResponse
  }

  async getAttachments(datastreamId: string) {
    const url = `${this._route}/${datastreamId}/file-attachments`
    const res = await apiMethods.paginatedFetch(url)
    return {
      ...res,
      data: normalizeAttachmentCollection(res.data as any, this._client.host),
    } as ApiResponse
  }

  deleteAttachment(datastreamId: string, name: string) {
    const url = `${this._route}/${datastreamId}/file-attachments`
    return apiMethods.delete(url, { name })
  }

  /* ============================== CSV =============================== */

  /** Fetch CSV as a Blob for a datastream (no auto-download). */
  async fetchCsvBlob(id: string): Promise<ApiResponse<Blob>> {
    const url = `${this._route}/${encodeURIComponent(id)}/csv`
    return apiMethods.fetch(url, {
      headers: { Accept: 'text/csv' },
    }) as Promise<ApiResponse<Blob>>
  }

  /** Trigger a browser download for a single datastream CSV. */
  async downloadCsv(id: string, filename?: string): Promise<void> {
    const res = await this.fetchCsvBlob(id)
    const blob =
      res.data instanceof Blob
        ? res.data
        : new Blob([res.data as any], { type: 'text/csv' })
    triggerDownload(blob, filename ?? `datastream_${id}.csv`)
  }

  /** Download many datastream CSVs as a single ZIP. */
  async downloadCsvBatchZip(
    datastreams: Array<string | WithId>,
    zipName = 'datastreams.zip'
  ): Promise<void> {
    const zip = new JSZip()

    for (const ds of datastreams) {
      const id = typeof ds === 'string' ? ds : ds.id
      const res = await this.fetchCsvBlob(id)
      const blob =
        res.data instanceof Blob
          ? res.data
          : new Blob([res.data as any], { type: 'text/csv' })
      zip.file(`datastream_${id}.csv`, blob)
    }

    const archive = await zip.generateAsync({ type: 'blob' })
    triggerDownload(archive, zipName)
  }

  /* ======================= Observation APIs ======================== */
  getObservations(
    datastreamId: string,
    params: ObservationContract.QueryParameters
  ) {
    const url = this.withQuery(
      `${this._route}/${datastreamId}/observations`,
      params
    )
    return apiMethods.paginatedFetch(url)
  }

  createObservation(datastreamId: string, body: ObservationPostBody) {
    const url = `${this._route}/${datastreamId}/observations`
    return apiMethods.post(url, body)
  }

  createObservations(
    datastreamId: string,
    body: ObservationBulkPostBody,
    params?: ObservationBulkPostQueryParameters
  ) {
    const url = this.withQuery(
      `${this._route}/${datastreamId}/observations/bulk-create`,
      params
    )
    return apiMethods.post(url, body)
  }

  deleteObservations(datastreamId: string, body?: ObservationBulkDeleteBody) {
    const url = `${this._route}/${datastreamId}/observations/bulk-delete`
    return apiMethods.post(
      url,
      body || { phenomenonTimeStart: null, phenomenonTimeEnd: null }
    )
  }

  getObservation(datastreamId: string, observationId: string) {
    const url = `${this._route}/${encodeURIComponent(
      datastreamId
    )}/observations/${encodeURIComponent(observationId)}`
    return apiMethods.fetch(url)
  }

  deleteObservation(datastreamId: string, observationId: string) {
    const url = `${this._route}/${datastreamId}/observations/${observationId}`
    return apiMethods.delete(url)
  }

  getStatuses = () => apiMethods.paginatedFetch(`${this._route}/statuses`)

  getAggregationStatistics = () =>
    apiMethods.paginatedFetch(`${this._route}/aggregation-statistics`)

  getSampledMediums = () =>
    apiMethods.paginatedFetch(`${this._route}/sampled-mediums`)
}

/* ---------------------------- local helpers ---------------------------- */
export function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
