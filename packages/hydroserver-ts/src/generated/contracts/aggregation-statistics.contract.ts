/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace AggregationStatisticContract {
  export const route = 'aggregation-statistics' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_aggregation_statistic_get_aggregation_statistics']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_aggregation_statistic_get_aggregation_statistics']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['AggregationStatisticResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_AggregationStatisticResponse_']
  export type PostBody        = Data.components['schemas']['AggregationStatisticPostBody']
  export type PatchBody       = Data.components['schemas']['AggregationStatisticPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["description","name"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
