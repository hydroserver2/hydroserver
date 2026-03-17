/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../services/api/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace ThingContract {
  export const route = 'things' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_thing_get_things']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_thing_get_things']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['ThingSummaryResponse']
  export type DetailResponse  = Data.components['schemas']['ThingDetailResponse']
  export type PostBody        = Data.components['schemas']['ThingPostBody']
  export type PatchBody       = Data.components['schemas']['ThingPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["dataDisclaimer","description","isPrivate","location","name","samplingFeatureCode","samplingFeatureType","siteType"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
