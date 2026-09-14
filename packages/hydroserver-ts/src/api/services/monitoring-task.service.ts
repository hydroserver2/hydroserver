import { HydroServerBaseService, QueryParamsOf } from './base'
import { MonitoringTaskContract as C, RunContract } from '../../generated/contracts'
import {
  MonitoringTask as M,
  MonitoringTaskExpanded,
  type MonitoringRule,
  type MonitoringRulePayload,
  type MonitoringRulePatchPayload,
} from '../Models/monitoring-task.model'
import type { TaskRun } from '../Models/task.model'
import { MonitoringSite } from '../../types'
import { apiMethods } from '../apiMethods'
import type { ApiResponse } from '../responseInterceptor'
import type * as Data from '../../generated/data.types'

type MonitoringRuleQueryParameters =
  Data.operations['interfaces_api_views_monitoring_rule_get_monitoring_rules']['parameters']['query']

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

  protected override getBaseUrl(): string {
    return `${this._client.host}/api/data/monitoring`
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

  listRules(taskId: string, params?: MonitoringRuleQueryParameters) {
    return apiMethods.paginatedFetch<MonitoringRule[]>(
      this.withQuery(`${this._route}/${taskId}/rules`, params)
    )
  }

  getRule(taskId: string, ruleId: string) {
    return apiMethods.fetch<MonitoringRule>(
      `${this._route}/${taskId}/rules/${ruleId}`
    )
  }

  createRule = (taskId: string, payload: MonitoringRulePayload) =>
    apiMethods.post<{ id: string }>(`${this._route}/${taskId}/rules`, payload)

  updateRule = (taskId: string, ruleId: string, payload: MonitoringRulePatchPayload) =>
    apiMethods.patch<null>(`${this._route}/${taskId}/rules/${ruleId}`, payload)

  deleteRule(taskId: string, ruleId: string) {
    return apiMethods.delete<null>(`${this._route}/${taskId}/rules/${ruleId}`)
  }
}
