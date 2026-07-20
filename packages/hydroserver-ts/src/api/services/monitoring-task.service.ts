import { HydroServerBaseService } from './base'
import { MonitoringTaskContract as C, RunContract } from '../../generated/contracts'
import {
  MonitoringTask as M,
  type MonitoringRule,
  type MonitoringRulePayload,
  type MonitoringRulePatchPayload,
} from '../Models/monitoring-task.model'
import type { TaskRun } from '../Models/task.model'
import { apiMethods } from '../apiMethods'
import type * as Data from '../../generated/data.types'

type MonitoringRuleQueryParameters =
  Data.operations['interfaces_api_views_monitoring_rule_get_monitoring_rules']['parameters']['query']

export class MonitoringTaskService extends HydroServerBaseService<typeof C, M> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  protected override getBaseUrl(): string {
    return `${this._client.host}/api/data/monitoring`
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

  createRule(taskId: string, payload: MonitoringRulePayload) {
    return apiMethods.post<MonitoringRule>(
      `${this._route}/${taskId}/rules`,
      payload
    )
  }

  updateRule(
    taskId: string,
    ruleId: string,
    payload: MonitoringRulePatchPayload
  ) {
    return apiMethods.patch<MonitoringRule>(
      `${this._route}/${taskId}/rules/${ruleId}`,
      payload
    )
  }

  deleteRule(taskId: string, ruleId: string) {
    return apiMethods.delete<null>(`${this._route}/${taskId}/rules/${ruleId}`)
  }
}
