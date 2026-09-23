/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace MonitoringSiteTypeContract {
  export const route = 'monitoring-site-types' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_monitoring_site_type_get_monitoring_site_types']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_monitoring_site_type_get_monitoring_site_types']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['MonitoringSiteTypeResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_MonitoringSiteTypeResponse_']
  export type PostBody        = Data.components['schemas']['MonitoringSiteTypePostBody']
  export type PatchBody       = Data.components['schemas']['MonitoringSiteTypePatchBody']
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
