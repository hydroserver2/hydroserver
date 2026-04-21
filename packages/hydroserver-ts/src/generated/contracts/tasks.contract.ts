/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace TaskContract {
  export const route = 'tasks' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_etl_task_get_etl_tasks']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_etl_task_get_etl_tasks']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['EtlTaskResponse']
  export type DetailResponse  = never
  export type PostBody        = Data.components['schemas']['EtlTaskPostBody']
  export type PatchBody       = Data.components['schemas']['EtlTaskPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["description","mappings","name","schedule","taskVariables"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
