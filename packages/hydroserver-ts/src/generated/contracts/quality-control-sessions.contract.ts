/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/ogc.openapi.json */
import type * as Data from '../ogc.types'

export namespace QualityControlSessionContract {
  export const route = 'collections/quality-control-histories/items/{history_id}/sessions' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_quality_session_get_qc_sessions']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_quality_session_get_qc_sessions']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['QualityControlSessionResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_QualityControlSessionResponse_']
  export type PostBody        = Data.components['schemas']['QualityControlSessionPostBody']
  export type PatchBody       = Data.components['schemas']['QualityControlSessionPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["description"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
