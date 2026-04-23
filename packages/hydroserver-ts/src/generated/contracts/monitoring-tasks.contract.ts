/* Contract for Monitoring Tasks (Data Quality).
   Parallels the auto-generated tasks.contract.ts. */
import type * as Data from '../data.types'

export namespace MonitoringTaskContract {
  export const route = 'tasks' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_monitoring_task_get_monitoring_tasks']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_monitoring_task_get_monitoring_tasks']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['MonitoringTaskResponse']
  export type DetailResponse  = never
  export type PostBody        = Data.components['schemas']['MonitoringTaskPostBody']
  export type PatchBody       = Data.components['schemas']['MonitoringTaskPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ['description', 'name', 'recipients', 'schedule'] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
