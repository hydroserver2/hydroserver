/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace EtlMappingContract {
  export const route = 'etl-mappings' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_etl_mapping_get_etl_mappings']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_etl_mapping_get_etl_mappings']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['EtlMappingResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_EtlMappingResponse_']
  export type PostBody        = Data.components['schemas']['EtlMappingPostBody']
  export type PatchBody       = Data.components['schemas']['EtlMappingPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["sourceIdentifier","targetDatastreamId"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
