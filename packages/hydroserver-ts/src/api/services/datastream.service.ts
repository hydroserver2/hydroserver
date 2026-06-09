import { apiMethods } from '../apiMethods'
import { HydroServerBaseService } from './base'
import {
  DatastreamContract as C,
  ObservationContract,
} from '../../generated/contracts'
import type * as Data from '../../generated/data.types'
import type { ApiResponse } from '../responseInterceptor'
import {
  Datastream as M,
  Thing,
  ObservedProperty,
  ProcessingLevel,
} from '../../types'
import { normalizeAttachmentCollection } from './attachment-link'

interface VisualizationBootstrapPayload {
  things: Array<{
    id: string
    workspaceId: string
    name: string
    samplingFeatureCode: string
  }>
  datastreams: Array<{
    id: string
    name: string
    thingId: string
    observedPropertyId: string
    processingLevelId: string
    unitId: string
    noDataValue: number
    valueCount?: number | null
    phenomenonBeginTime?: string | null
    phenomenonEndTime?: string | null
    intendedTimeSpacing?: number
    intendedTimeSpacingUnit?: 'seconds' | 'minutes' | 'hours' | 'days' | null
  }>
  observedProperties: Array<{ id: string; name: string; code: string }>
  processingLevels: Array<{ id: string; definition?: string | null }>
}

export interface VisualizationBootstrap {
  things: Thing[]
  datastreams: M[]
  observedProperties: ObservedProperty[]
  processingLevels: ProcessingLevel[]
}

type TagPostBody = Data.components['schemas']['TagPostBody']
type TagDeleteBody = Data.components['schemas']['TagDeleteBody']
type TagResponse = Data.components['schemas']['TagGetResponse']
type TagKeyResponse = Record<string, string[]>
type FileAttachmentResponse =
  Data.components['schemas']['FileAttachmentGetResponse']

type ObservationListResponse =
  Data.operations['interfaces_api_views_sta_observation_get_observations']['responses'][200]['content']['application/json']
type ObservationResponse =
  | Data.components['schemas']['ObservationSummaryResponse']
  | Data.components['schemas']['ObservationDetailResponse']
type ObservationBulkPostQueryParameters =
  Data.components['schemas']['ObservationBulkPostQueryParameters']
type ObservationBulkPostBody =
  Data.components['schemas']['ObservationBulkPostBody']
type ObservationBulkDeleteBody =
  Data.components['schemas']['ObservationBulkDeleteBody']
type ObservationPostBody = Data.components['schemas']['ObservationPostBody']
type NoContentResponse = null
/**
 * Transport layer for /datastreams routes.
 * Inherits CRUD + handle helpers from HydroServerBaseService and adds:
 * - CSV export primitive
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
    return apiMethods.fetch<TagResponse[]>(url)
  }

  getTagKeys(params: { workspace_id?: string; datastream_id?: string }) {
    const url = this.withQuery(`${this._route}/tags/keys`, params)
    return apiMethods.fetch<TagKeyResponse>(url)
  }

  createTag(datastreamId: string, tag: TagPostBody) {
    const url = `${this._route}/${datastreamId}/tags`
    return apiMethods.post<TagResponse>(url, tag)
  }

  updateTag(datastreamId: string, tag: TagPostBody) {
    const url = `${this._route}/${datastreamId}/tags`
    return apiMethods.put<TagResponse>(url, tag)
  }

  deleteTag(datastreamId: string, tag: TagDeleteBody) {
    const url = `${this._route}/${datastreamId}/tags`
    return apiMethods.delete<NoContentResponse>(url, tag)
  }

  /* ----------------- Sub-resources: File Attachments ----------------- */

  getFileAttachmentTypes = () =>
    apiMethods.fetch<string[]>(`${this._route}/file-attachment-types`)

  async uploadAttachments(datastreamId: string, data: FormData) {
    const url = `${this._route}/${datastreamId}/file-attachments`
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

  async getAttachments(datastreamId: string) {
    const url = `${this._route}/${datastreamId}/file-attachments`
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

  deleteAttachment(datastreamId: string, name: string) {
    const url = `${this._route}/${datastreamId}/file-attachments`
    return apiMethods.delete<NoContentResponse>(url, { name })
  }

  /* ============================== CSV =============================== */

  /** Fetch CSV as a Blob for a single datastream. */
  async fetchCsvBlob(id: string): Promise<ApiResponse<Blob>> {
    const url = `${this._route}/${encodeURIComponent(id)}/csv`
    return apiMethods.fetch<Blob>(url, {
      headers: { Accept: 'text/csv' },
    })
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
    return apiMethods.paginatedFetch<ObservationListResponse>(url)
  }

  createObservation(datastreamId: string, body: ObservationPostBody) {
    const url = `${this._route}/${datastreamId}/observations`
    return apiMethods.post<ObservationResponse>(url, body)
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
    return apiMethods.post<NoContentResponse>(url, body)
  }

  deleteObservations(datastreamId: string, body?: ObservationBulkDeleteBody) {
    const url = `${this._route}/${datastreamId}/observations/bulk-delete`
    return apiMethods.post<NoContentResponse>(
      url,
      body || { phenomenonTimeStart: null, phenomenonTimeEnd: null }
    )
  }

  getObservation(datastreamId: string, observationId: string) {
    const url = `${this._route}/${encodeURIComponent(
      datastreamId
    )}/observations/${encodeURIComponent(observationId)}`
    return apiMethods.fetch<ObservationResponse>(url)
  }

  deleteObservation(datastreamId: string, observationId: string) {
    const url = `${this._route}/${datastreamId}/observations/${observationId}`
    return apiMethods.delete<NoContentResponse>(url)
  }

  getStatuses = () =>
    apiMethods.paginatedFetch<string[]>(`${this._route}/statuses`)

  getAggregationStatistics = () =>
    apiMethods.paginatedFetch<string[]>(`${this._route}/aggregation-statistics`)

  getSampledMediums = () =>
    apiMethods.paginatedFetch<string[]>(`${this._route}/sampled-mediums`)

  async getVisualizationBootstrap(): Promise<
    ApiResponse<VisualizationBootstrap>
  > {
    const res = await apiMethods.fetch<VisualizationBootstrapPayload>(
      `${this._route}/visualization-bootstrap`
    )
    if (!res.ok) return res

    const payload = res.data

    const things = payload.things.map((p) => Object.assign(new Thing(), p))
    const thingById = new Map(things.map((t) => [t.id, t]))

    const datastreams = payload.datastreams.map((p) =>
      Object.assign(new M(), {
        ...p,
        workspaceId: thingById.get(p.thingId)?.workspaceId ?? '',
      })
    )
    const observedProperties = payload.observedProperties.map((p) =>
      Object.assign(new ObservedProperty(), p)
    )
    const processingLevels = payload.processingLevels.map((p) =>
      Object.assign(new ProcessingLevel(), p)
    )

    return {
      ...res,
      data: { things, datastreams, observedProperties, processingLevels },
    }
  }
}
