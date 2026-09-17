import { HydroServerBaseService, QueryParamsOf } from './base'
import { TaskContract as C, RunContract } from '../../generated/contracts'
import { Task as M, TaskExpanded, type TaskRun } from '../Models/task.model'
import { DataConnection } from '../Models/data-connection.model'
import { apiMethods } from '../apiMethods'
import type { ApiResponse } from '../responseInterceptor'

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
}
