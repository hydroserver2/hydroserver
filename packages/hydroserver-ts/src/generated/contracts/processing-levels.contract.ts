/* AUTO-GENERATED. DO NOT EDIT.
   Generated from schemas/data.openapi.json */
import type * as Data from '../data.types'

export namespace ProcessingLevelContract {
  export const route = 'processing-levels' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_processing_level_get_processing_levels']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_processing_level_get_processing_levels']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['ProcessingLevelSummaryResponse']
  export type DetailResponse  = Data.components['schemas']['ProcessingLevelDetailResponse']
  export type PostBody        = Data.components['schemas']['ProcessingLevelPostBody']
  export type PatchBody       = Data.components['schemas']['ProcessingLevelPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["code","definition","explanation"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
