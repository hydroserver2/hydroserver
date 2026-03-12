/* AUTO-GENERATED. DO NOT EDIT.
   Generated from schemas/data.openapi.json */
import type * as Data from '../data.types'

export namespace EtlDataConnectionContract {
  export const route = 'etl-data-connections' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_data_connection_get_data_connections']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_data_connection_get_data_connections']['parameters']['query']>)
  export type SummaryResponse = never
  export type DetailResponse  = never
  export type PostBody        = Data.components['schemas']['DataConnectionPostBody']
  export type PatchBody       = Data.components['schemas']['DataConnectionPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["name","type","extractor","transformer","loader"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
