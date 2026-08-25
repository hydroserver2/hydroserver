/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace MonitoringSiteContract {
  export const route = 'monitoring-sites' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_sta_monitoring_site_get_monitoring_sites']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_sta_monitoring_site_get_monitoring_sites']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['MonitoringSiteSummaryResponse']
  export type DetailResponse  = Data.components['schemas']['MonitoringSiteDetailResponse']
  export type PostBody        = Data.components['schemas']['MonitoringSitePostBody']
  export type PatchBody       = Data.components['schemas']['MonitoringSitePatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["adminArea1","adminArea2","code","country","dataDisclaimer","description","elevationDatum","elevation_m","isPrivate","latitude","longitude","name","tags","type"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
