/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/ogc.openapi.json */
import type * as Data from '../ogc.types'

export namespace ObservedPropertyTypeContract {
  export const route = 'collections/observed-property-types/items' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_observed_property_type_get_observed_property_types']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_observed_property_type_get_observed_property_types']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['ObservedPropertyTypeResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_ObservedPropertyTypeResponse_']
  export type PostBody        = Data.components['schemas']['ObservedPropertyTypePostBody']
  export type PatchBody       = Data.components['schemas']['ObservedPropertyTypePatchBody']
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
