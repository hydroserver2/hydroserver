/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace UnitTypeContract {
  export const route = 'unit-types' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_unit_type_get_unit_types']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_unit_type_get_unit_types']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['UnitTypeResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_UnitTypeResponse_']
  export type PostBody        = Data.components['schemas']['UnitTypePostBody']
  export type PatchBody       = Data.components['schemas']['UnitTypePatchBody']
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
