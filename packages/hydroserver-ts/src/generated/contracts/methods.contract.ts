/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/ogc.openapi.json */
import type * as Data from '../ogc.types'

export namespace MethodContract {
  export const route = 'collections/methods/items' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_method_get_methods']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_method_get_methods']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['MethodResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_MethodResponse_']
  export type PostBody        = Data.components['schemas']['MethodPostBody']
  export type PatchBody       = Data.components['schemas']['MethodPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["code","definition","description","name","sensorModel","sensorModelDefinition","sensorModelManufacturer","type"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
