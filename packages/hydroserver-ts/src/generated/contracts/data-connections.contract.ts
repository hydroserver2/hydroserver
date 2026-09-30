/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/ogc.openapi.json */
import type * as Data from '../ogc.types'

export namespace DataConnectionContract {
  export const route = 'collections/etl-data-connections/items' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_etl_data_connection_get_data_connections']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_etl_data_connection_get_data_connections']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['DataConnectionResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_DataConnectionResponse_']
  export type PostBody        = Data.components['schemas']['DataConnectionPostBody']
  export type PatchBody       = Data.components['schemas']['DataConnectionPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["authHeaderName","authHeaderValue","description","name","notification","payload","placeholderVariables","sourceUrl","timezone","timezoneType"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
