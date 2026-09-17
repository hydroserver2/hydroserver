/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace MonitoringTaskContract {
  export const route = 'monitoring-tasks' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_monitoring_task_get_monitoring_tasks']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_monitoring_task_get_monitoring_tasks']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['MonitoringTaskResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_MonitoringTaskResponse_']
  export type PostBody        = Data.components['schemas']['MonitoringTaskPostBody']
  export type PatchBody       = Data.components['schemas']['MonitoringTaskPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["description","name","recipients","schedule"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
