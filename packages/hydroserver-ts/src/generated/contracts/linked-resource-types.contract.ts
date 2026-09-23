/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace LinkedResourceTypeContract {
  export const route = 'linked-resource-types' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_linked_resource_type_get_linked_resource_types']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_linked_resource_type_get_linked_resource_types']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['LinkedResourceTypeResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_LinkedResourceTypeResponse_']
  export type PostBody        = Data.components['schemas']['LinkedResourceTypePostBody']
  export type PatchBody       = Data.components['schemas']['LinkedResourceTypePatchBody']
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
