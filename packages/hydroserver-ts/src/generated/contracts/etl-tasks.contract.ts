/* AUTO-GENERATED. DO NOT EDIT.
   Generated from schemas/data.openapi.json */
import type * as Data from '../data.types'

export namespace EtlTaskContract {
  export const route = 'etl-tasks' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_task_get_tasks']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_task_get_tasks']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['TaskMappingPathResponse']
  export type DetailResponse  = Data.components['schemas']['TaskMappingPathResponse']
  export type PostBody        = Data.components['schemas']['TaskPostBody']
  export type PatchBody       = Data.components['schemas']['TaskPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["name","type","extractorVariables","transformerVariables","loaderVariables","dataConnectionId","orchestrationSystemId","schedule","mappings"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
