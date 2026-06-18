/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace QualityControlOperationContract {
  export const route = 'quality-control/histories/{history_id}/sessions/{session_id}/operations' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_quality_operation_get_qc_operations']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_quality_operation_get_qc_operations']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['QualityControlOperationResponse']
  export type DetailResponse  = Data.components['schemas']['QualityControlOperationResponse']
  export type PostBody        = Data.components['schemas']['QualityControlOperationPostBody'][]
  export type PatchBody       = Data.components['schemas']['QualityControlOperationPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["arguments","comment","order"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
