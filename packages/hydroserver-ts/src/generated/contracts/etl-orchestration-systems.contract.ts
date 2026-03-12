/* AUTO-GENERATED. DO NOT EDIT.
   Generated from schemas/data.openapi.json */
import type * as Data from '../data.types'

export namespace EtlOrchestrationSystemContract {
  export const route = 'etl-orchestration-systems' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_orchestration_system_get_orchestration_systems']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_orchestration_system_get_orchestration_systems']['parameters']['query']>)
  export type SummaryResponse = never
  export type DetailResponse  = never
  export type PostBody        = Data.components['schemas']['OrchestrationSystemPostBody']
  export type PatchBody       = Data.components['schemas']['OrchestrationSystemPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["name","type"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
