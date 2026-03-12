/* AUTO-GENERATED. DO NOT EDIT.
   Generated from schemas/data.openapi.json */
import type * as Data from '../data.types'

export namespace ObservedPropertyContract {
  export const route = 'observed-properties' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_observed_property_get_observed_properties']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_observed_property_get_observed_properties']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['ObservedPropertySummaryResponse']
  export type DetailResponse  = Data.components['schemas']['ObservedPropertyDetailResponse']
  export type PostBody        = Data.components['schemas']['ObservedPropertyPostBody']
  export type PatchBody       = Data.components['schemas']['ObservedPropertyPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["name","definition","description","type","code"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
