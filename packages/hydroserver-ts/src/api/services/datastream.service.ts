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
  MonitoringSite,
  ObservedProperty,
  ProcessingLevel,
} from '../../types'
import { normalizeLinkCollection, normalizeLinkRecord } from './link-normalization'

interface VisualizationBootstrapPayload {
  monitoringSites: Array<{
    id: string
    workspaceId: string
    name: string
    code: string
  }>
  datastreams: Array<{
    id: string
    name: string
    monitoringSiteId: string
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
  monitoringSites: MonitoringSite[]
  datastreams: M[]
  observedProperties: ObservedProperty[]
  processingLevels: ProcessingLevel[]
}

type TagPostBody = Data.components['schemas']['TagPostBody']
type TagDeleteBody = Data.components['schemas']['TagDeleteBody']
type TagResponse = Data.components['schemas']['TagGetResponse']
type TagKeyResponse = Record<string, string[]>
type LinkedResourceResponse = Data.components['schemas']['LinkedResourceGetResponse']

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

  /* ------------------ Sub-resources: Linked Resources ------------------ */

  getLinkedResourceTypes = () =>
    apiMethods.fetch<string[]>(`${this._route}/linked-resource-types`)

  async getLinkedResources(datastreamId: string) {
    const url = `${this._route}/${datastreamId}/linked-resources`
    const res = await apiMethods.paginatedFetch<LinkedResourceResponse[]>(url)
    if (!res.ok) return res
    return {
      ...res,
      data: normalizeLinkCollection(res.data, this._client.host),
    } as ApiResponse<LinkedResourceResponse[]>
  }

  async createLinkedResource(datastreamId: string, data: FormData) {
    const url = `${this._route}/${datastreamId}/linked-resources`
    const res = await apiMethods.post<LinkedResourceResponse>(url, data)
    if (!res.ok) return res
    return {
      ...res,
      data: normalizeLinkRecord(res.data, this._client.host),
    } as ApiResponse<LinkedResourceResponse>
  }

  async updateLinkedResource(datastreamId: string, linkedResourceId: string, data: FormData) {
    const url = `${this._route}/${datastreamId}/linked-resources/${linkedResourceId}`
    const res = await apiMethods.patch<LinkedResourceResponse>(url, data)
    if (!res.ok) return res
    return {
      ...res,
      data: normalizeLinkRecord(res.data, this._client.host),
    } as ApiResponse<LinkedResourceResponse>
  }

  deleteLinkedResource(datastreamId: string, linkedResourceId: string) {
    const url = `${this._route}/${datastreamId}/linked-resources/${linkedResourceId}`
    return apiMethods.delete<NoContentResponse>(url)
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

    const monitoringSites = payload.monitoringSites.map((p) => Object.assign(new MonitoringSite(), p))
    const monitoringSiteById = new Map(monitoringSites.map((t) => [t.id, t]))

    const datastreams = payload.datastreams.map((p) =>
      Object.assign(new M(), {
        ...p,
        workspaceId: monitoringSiteById.get(p.monitoringSiteId)?.workspaceId ?? '',
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
      data: { monitoringSites, datastreams, observedProperties, processingLevels },
    }
  }
}
