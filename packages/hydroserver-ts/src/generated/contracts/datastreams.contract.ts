/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace DatastreamContract {
  export const route = 'datastreams' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_datastream_get_datastreams']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_datastream_get_datastreams']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['DatastreamSummaryResponse']
  export type DetailResponse  = Data.components['schemas']['DatastreamDetailResponse']
  export type PostBody        = Data.components['schemas']['DatastreamPostBody']
  export type PatchBody       = Data.components['schemas']['DatastreamPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["aggregationStatistic","description","intendedTimeSpacing","intendedTimeSpacingUnit","isPrivate","isVisible","name","noDataValue","observationType","observedPropertyId","phenomenonBeginTime","phenomenonEndTime","processingLevelId","resultBeginTime","resultEndTime","resultType","sampledMedium","sensorId","status","thingId","timeAggregationInterval","timeAggregationIntervalUnit","unitId","valueCount"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
