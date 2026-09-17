/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace MonitoringRuleContract {
  export const route = 'monitoring-rules' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_monitoring_rule_get_monitoring_rules']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_monitoring_rule_get_monitoring_rules']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['MonitoringRuleResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_MonitoringRuleResponse_']
  export type PostBody        = Data.components['schemas']['MonitoringRulePostBody']
  export type PatchBody       = Data.components['schemas']['MonitoringRulePatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["maxValue","minValue","windowInterval","windowIntervalUnits"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
