/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../services/api/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace SensorContract {
  export const route = 'sensors' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sensor_get_sensors']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sensor_get_sensors']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['SensorSummaryResponse']
  export type DetailResponse  = Data.components['schemas']['SensorDetailResponse']
  export type PostBody        = Data.components['schemas']['SensorPostBody']
  export type PatchBody       = Data.components['schemas']['SensorPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["description","encodingType","manufacturer","methodCode","methodLink","methodType","model","modelLink","name"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
