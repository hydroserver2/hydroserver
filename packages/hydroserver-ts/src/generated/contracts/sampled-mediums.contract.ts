/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace SampledMediumContract {
  export const route = 'sampled-mediums' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_sampled_medium_get_sampled_mediums']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_sampled_medium_get_sampled_mediums']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['SampledMediumResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_SampledMediumResponse_']
  export type PostBody        = Data.components['schemas']['SampledMediumPostBody']
  export type PatchBody       = Data.components['schemas']['SampledMediumPatchBody']
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
