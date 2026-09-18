/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace MethodTypeContract {
  export const route = 'method-types' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_method_type_get_method_types']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_method_type_get_method_types']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['MethodTypeResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_MethodTypeResponse_']
  export type PostBody        = Data.components['schemas']['MethodTypePostBody']
  export type PatchBody       = Data.components['schemas']['MethodTypePatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["description","isActive","name"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
