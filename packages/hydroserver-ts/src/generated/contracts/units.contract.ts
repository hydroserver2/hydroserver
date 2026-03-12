/* AUTO-GENERATED. DO NOT EDIT.
   Generated from schemas/data.openapi.json */
import type * as Data from '../data.types'

export namespace UnitContract {
  export const route = 'units' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_unit_get_units']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_unit_get_units']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['UnitSummaryResponse']
  export type DetailResponse  = Data.components['schemas']['UnitDetailResponse']
  export type PostBody        = Data.components['schemas']['UnitPostBody']
  export type PatchBody       = Data.components['schemas']['UnitPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["name","symbol","definition","type"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
