/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace DatastreamStatusContract {
  export const route = 'datastream-statuses' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_datastream_status_get_datastream_statuses']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_datastream_status_get_datastream_statuses']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['DatastreamStatusResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_DatastreamStatusResponse_']
  export type PostBody        = Data.components['schemas']['DatastreamStatusPostBody']
  export type PatchBody       = Data.components['schemas']['DatastreamStatusPatchBody']
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
