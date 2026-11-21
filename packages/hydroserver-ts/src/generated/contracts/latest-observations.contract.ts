/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/ogc.openapi.json */
import type * as Data from '../ogc.types'

export namespace LatestObservationContract {
  export const route = 'collections/latest-observations/items' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_latest_observation_get_latest_observations']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_latest_observation_get_latest_observations']['parameters']['query']>)
  export type SummaryResponse = never
  export type DetailResponse  = Data.components['schemas']['ItemResponse_ObservationResponse_']
  export type PostBody        = never
  export type PatchBody       = never
  export type DeleteBody      = never
  export const writableKeys = [] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
