/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace QualityControlHistoryContract {
  export const route = 'quality-control/histories' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_quality_history_get_qc_histories']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_quality_history_get_qc_histories']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['QualityControlHistorySummaryResponse']
  export type DetailResponse  = Data.components['schemas']['QualityControlHistoryDetailResponse']
  export type PostBody        = Data.components['schemas']['QualityControlHistoryPostBody']
  export type PatchBody       = Partial<Data.components['schemas']['QualityControlHistoryPostBody']>
  export type DeleteBody      = never
  export const writableKeys = ["managedDatastreamId","sourceDatastreamId"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
