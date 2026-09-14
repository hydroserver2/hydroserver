import { HydroServerBaseService, QueryParamsOf } from './base'
import { TaskContract as C, RunContract } from '../../generated/contracts'
import { Task as M, TaskExpanded, type TaskRun } from '../Models/task.model'
import { DataConnection } from '../Models/data-connection.model'
import { apiMethods } from '../apiMethods'
import type { ApiResponse } from '../responseInterceptor'
import type * as Data from '../../generated/data.types'
import type {
  EtlMapping,
  EtlMappingPayload,
  EtlMappingPatchPayload,
} from './etl-mapping.types'

type EtlMappingQueryParameters =
  Data.operations['interfaces_api_views_etl_mapping_get_etl_mappings']['parameters']['query']

type IncludedBuckets = {
  dataConnections?: DataConnection[]
}

function mergeIncluded(row: M, included?: IncludedBuckets): M | (M & TaskExpanded) {
  const dataConnection = included?.dataConnections?.find(
    (dc) => dc.id === row.dataConnectionId
  )
  return dataConnection ? Object.assign(row, { dataConnection }) : row
}

export class TaskService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  protected override getBaseUrl(): string {
    return this._client.etlDataBase
  }

  get = async (
    id: string,
    params?: Pick<QueryParamsOf<typeof C>, 'include'>
  ): Promise<ApiResponse<M>> => {
    const url = this.withQuery(`${this._route}/${id}`, params)
    const res = await apiMethods.fetch<M>(url)
    if (!res.ok) return res
    return { ...res, data: mergeIncluded(res.data, res.included as IncludedBuckets) }
  }

  runTask(taskId: string) {
    return apiMethods.post<TaskRun>(`${this._route}/${taskId}/trigger`)
  }

  getTaskRuns(taskId: string, params?: RunContract.QueryParameters) {
    return apiMethods.paginatedFetch<TaskRun[]>(
      this.withQuery(`${this._route}/${taskId}/runs`, params)
    )
  }

  getTaskRun(taskId: string, runId: string) {
    return apiMethods.fetch<TaskRun>(`${this._route}/${taskId}/runs/${runId}`)
  }

  /* -------------------------------- Mappings -------------------------------- */

  listMappings(taskId: string, params?: EtlMappingQueryParameters) {
    return apiMethods.paginatedFetch<EtlMapping[]>(
      this.withQuery(`${this._route}/${taskId}/mappings`, params)
    )
  }

  getMapping = (
    taskId: string,
    mappingId: string
  ): Promise<ApiResponse<EtlMapping>> =>
    apiMethods.fetch<EtlMapping>(`${this._route}/${taskId}/mappings/${mappingId}`)

  createMapping = (taskId: string, payload: EtlMappingPayload) =>
    apiMethods.post<{ id: string }>(`${this._route}/${taskId}/mappings`, payload)

  updateMapping = (
    taskId: string,
    mappingId: string,
    payload: EtlMappingPatchPayload
  ) =>
    apiMethods.patch<null>(
      `${this._route}/${taskId}/mappings/${mappingId}`,
      payload
    )

  deleteMapping(taskId: string, mappingId: string) {
    return apiMethods.delete<null>(`${this._route}/${taskId}/mappings/${mappingId}`)
  }
}
