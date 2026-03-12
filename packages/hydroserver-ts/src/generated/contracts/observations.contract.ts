/* AUTO-GENERATED. DO NOT EDIT.
   Generated from schemas/data.openapi.json */
import type * as Data from '../data.types'

export namespace ObservationContract {
  export const route = 'observations' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_observation_get_observations']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_observation_get_observations']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['ObservationSummaryResponse']
  export type DetailResponse  = Data.components['schemas']['ObservationDetailResponse']
  export type PostBody        = Data.components['schemas']['ObservationPostBody']
  export type PatchBody       = Partial<Data.components['schemas']['ObservationPostBody']>
  export type DeleteBody      = never
  export const writableKeys = ["phenomenonTime","result","resultQualifierCodes"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
