import { apiMethods } from '../apiMethods'
import { HydroServerBaseService, QueryParamsOf } from './base'
import {
  DatastreamContract as C,
  ObservationContract,
} from '../../generated/contracts'
import type * as Data from '../../generated/data.types'
import type { ApiResponse } from '../responseInterceptor'
import {
  Datastream as M,
  DatastreamExtended,
  MonitoringSite,
  Workspace,
  Method,
  ObservedProperty,
  ProcessingLevel,
  Unit,
} from '../../types'
import { normalizeLinkCollection } from './link-normalization'

const DATASTREAM_EXPAND_INCLUDE =
  'workspace,monitoringSite,method,observedProperty,processingLevel,unit' as const

type IncludedBuckets = {
  workspaces?: Workspace[]
  monitoringSites?: MonitoringSite[]
  methods?: Method[]
  observedProperties?: ObservedProperty[]
  processingLevels?: ProcessingLevel[]
  units?: Unit[]
}

function mergeIncluded(row: M, included?: IncludedBuckets): M & DatastreamExtended {
  const workspaces = included?.workspaces ?? []
  const monitoringSites = included?.monitoringSites ?? []
  const methods = included?.methods ?? []
  const observedProperties = included?.observedProperties ?? []
  const processingLevels = included?.processingLevels ?? []
  const units = included?.units ?? []

  return Object.assign(row, {
    workspace: workspaces.find((w) => w.id === row.workspaceId) ?? new Workspace(),
    monitoringSite:
      monitoringSites.find((ms) => ms.id === row.monitoringSiteId) ??
      new MonitoringSite(),
    method: methods.find((m) => m.id === row.methodId) ?? new Method(),
    observedProperty:
      observedProperties.find((op) => op.id === row.observedPropertyId) ??
      new ObservedProperty(),
    processingLevel:
      processingLevels.find((pl) => pl.id === row.processingLevelId) ??
      new ProcessingLevel(),
    unit: units.find((u) => u.id === row.unitId) ?? new Unit(),
  })
}

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
    unitSymbol: string
    noDataValue: number
    aggregationStatistic: string
    timeAggregationInterval: number
    timeAggregationIntervalUnit: 'seconds' | 'minutes' | 'hours' | 'days'
    valueCount?: number | null
    phenomenonBeginTime?: string | null
    phenomenonEndTime?: string | null
    intendedTimeSpacing?: number
    intendedTimeSpacingUnit?: 'seconds' | 'minutes' | 'hours' | 'days' | null
  }>
  observedProperties: Array<{ id: string; name: string; code: string }>
  processingLevels: Array<{ id: string; name: string }>
}

export interface VisualizationBootstrap {
  monitoringSites: MonitoringSite[]
  datastreams: M[]
  observedProperties: ObservedProperty[]
  processingLevels: ProcessingLevel[]
}

type TagKeyResponse = Record<string, string[]>
type LinkedResourceResponse = Data.components['schemas']['LinkedResourceGetResponse']

type ObservationResponse = Data.components['schemas']['ObservationResponse']
type ObservationListResponse =
  | ObservationResponse[]
  | Data.components['schemas']['ObservationRowData']
  | Data.components['schemas']['ObservationColumnarData']
type CreatedResponse = Data.components['schemas']['CreatedResponse']
type ObservationBulkPostQueryParameters =
  Data.components['schemas']['ObservationBulkPostQueryParameters']
type ObservationBulkPostBody = Omit<
  Data.components['schemas']['ObservationBulkPostBody'],
  'datastreamId'
>
type ObservationBulkDeleteBody = Omit<
  Data.components['schemas']['ObservationBulkDeleteBody'],
  'datastreamId'
>
type ObservationPostBody = Omit<
  Data.components['schemas']['ObservationPostBody'],
  'datastreamId'
>
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

  /* ------------------------ List / Get overrides ----------------------- */

  list = async (
    params: Partial<QueryParamsOf<typeof C>> & {
      fetch_all?: boolean
      expand_related?: boolean
    } = {}
  ): Promise<ApiResponse<M[]>> => {
    const { fetch_all, expand_related, ...query } = params
    const url = this.withQuery(this._route, {
      ...query,
      ...(expand_related ? { include: DATASTREAM_EXPAND_INCLUDE } : {}),
    })
    const res = fetch_all
      ? await apiMethods.paginatedFetch<M[]>(url)
      : await apiMethods.fetch<M[]>(url)
    if (!res.ok) return res
    if (!expand_related) return res

    const included = res.included as IncludedBuckets | undefined
    return { ...res, data: res.data.map((row) => mergeIncluded(row, included)) }
  }

  get = async (
    id: string,
    params?: { expand_related?: boolean }
  ): Promise<ApiResponse<M>> => {
    const url = this.withQuery(`${this._route}/${id}`, {
      ...(params?.expand_related ? { include: DATASTREAM_EXPAND_INCLUDE } : {}),
    })
    const res = await apiMethods.fetch<M>(url)
    if (!res.ok) return res
    if (!params?.expand_related) return res

    return {
      ...res,
      data: mergeIncluded(res.data, res.included as IncludedBuckets | undefined),
    }
  }

  listItems = async (
    params?: Partial<QueryParamsOf<typeof C>> & {
      fetch_all?: boolean
      expand_related?: boolean
    }
  ) => {
    const res = await this.list(params ?? {})
    return res.ok ? res.data : []
  }

  listAllItems = async (
    params?: Partial<QueryParamsOf<typeof C>> & { expand_related?: boolean }
  ) => {
    return this.listItems({ ...params, fetch_all: true })
  }

  /* ----------------------- Sub-resources: Tags ----------------------- */

  getTagKeys(params: { workspace_id?: string; datastream_id?: string }) {
    const url = this.withQuery(`${this._route}/tags/keys`, params)
    return apiMethods.fetch<TagKeyResponse>(url)
  }

  setTag(datastreamId: string, key: string, value: string) {
    return this.patchAndRefetch(datastreamId, { tags: { [key]: value } })
  }

  deleteTag(datastreamId: string, key: string) {
    return this.patchAndRefetch(datastreamId, { tags: { [key]: null } })
  }

  private async patchAndRefetch(
    datastreamId: string,
    body: Record<string, unknown>
  ): Promise<ApiResponse<M>> {
    const res = await apiMethods.patch<null>(`${this._route}/${datastreamId}`, body)
    if (!res.ok) return res as ApiResponse<M>
    return this.get(datastreamId)
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

  async createLinkedResource(
    datastreamId: string,
    data: FormData
  ): Promise<ApiResponse<LinkedResourceResponse>> {
    const url = `${this._route}/${datastreamId}/linked-resources`
    const res = await apiMethods.post<{ id: string }>(url, data)
    if (!res.ok) return res
    return this.findLinkedResource(datastreamId, res.data.id)
  }

  async updateLinkedResource(
    datastreamId: string,
    linkedResourceId: string,
    data: FormData
  ): Promise<ApiResponse<LinkedResourceResponse>> {
    const url = `${this._route}/${datastreamId}/linked-resources/${linkedResourceId}`
    const res = await apiMethods.patch<null>(url, data)
    if (!res.ok) return res
    return this.findLinkedResource(datastreamId, linkedResourceId)
  }

  private async findLinkedResource(
    datastreamId: string,
    linkedResourceId: string
  ): Promise<ApiResponse<LinkedResourceResponse>> {
    const res = await this.getLinkedResources(datastreamId)
    if (!res.ok) return res
    const found = res.data.find((r) => r.id === linkedResourceId)
    if (!found) {
      return {
        ok: false,
        status: 404,
        message: 'Linked resource not found after save.',
      }
    }
    return { ...res, data: found }
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
    const url = this.withQuery(`${this._client.baseRoute}/observations`, {
      ...params,
      datastream_id: datastreamId,
    })
    return apiMethods.paginatedFetch<ObservationListResponse>(url)
  }

  createObservation(datastreamId: string, body: ObservationPostBody) {
    const url = `${this._client.baseRoute}/observations`
    return apiMethods.post<CreatedResponse>(url, {
      ...body,
      datastreamId,
    })
  }

  createObservations(
    datastreamId: string,
    body: ObservationBulkPostBody,
    params?: ObservationBulkPostQueryParameters
  ) {
    const url = this.withQuery(
      `${this._client.baseRoute}/observations/bulk-create`,
      params
    )
    return apiMethods.post<NoContentResponse>(url, { ...body, datastreamId })
  }

  deleteObservations(datastreamId: string, body?: ObservationBulkDeleteBody) {
    const url = `${this._client.baseRoute}/observations/bulk-delete`
    return apiMethods.post<NoContentResponse>(url, {
      ...(body || { phenomenonTimeStart: null, phenomenonTimeEnd: null }),
      datastreamId,
    })
  }

  getObservation(_datastreamId: string, observationId: string) {
    const url = `${this._client.baseRoute}/observations/${encodeURIComponent(
      observationId
    )}`
    return apiMethods.fetch<ObservationResponse>(url)
  }

  deleteObservation(_datastreamId: string, observationId: string) {
    const url = `${this._client.baseRoute}/observations/${observationId}`
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
