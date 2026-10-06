/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/ogc.openapi.json */
import type * as Data from '../ogc.types'

export namespace ObservedPropertyContract {
  export const route = 'collections/observed-properties/items' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_observed_property_get_observed_properties']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_observed_property_get_observed_properties']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['ObservedPropertyResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_ObservedPropertyResponse_']
  export type PostBody        = Data.components['schemas']['ObservedPropertyPostBody']
  export type PatchBody       = Data.components['schemas']['ObservedPropertyPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["code","definition","description","name","type"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
