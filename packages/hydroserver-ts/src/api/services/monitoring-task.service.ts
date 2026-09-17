import { HydroServerBaseService, QueryParamsOf } from './base'
import { MonitoringTaskContract as C, RunContract } from '../../generated/contracts'
import { MonitoringTask as M, MonitoringTaskExpanded } from '../Models/monitoring-task.model'
import type { TaskRun } from '../Models/task.model'
import { MonitoringSite } from '../../types'
import { apiMethods } from '../apiMethods'
import type { ApiResponse } from '../responseInterceptor'

type IncludedBuckets = {
  monitoringSites?: MonitoringSite[]
}

function mergeIncluded(
  row: M,
  included?: IncludedBuckets
): M | (M & MonitoringTaskExpanded) {
  const monitoringSite = included?.monitoringSites?.find(
    (ms) => ms.id === row.monitoringSiteId
  )
  return monitoringSite ? Object.assign(row, { monitoringSite }) : row
}

export class MonitoringTaskService extends HydroServerBaseService<typeof C, M> {
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
