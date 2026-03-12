/* AUTO-GENERATED. DO NOT EDIT.
   Generated from schemas/data.openapi.json */
import type * as Data from '../data.types'

export namespace RunContract {
  export const route = 'runs' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_run_get_task_runs']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_run_get_task_runs']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['TaskRunResponse']
  export type DetailResponse  = never
  export type PostBody        = Data.components['schemas']['TaskRunPostBody']
  export type PatchBody       = Data.components['schemas']['TaskRunPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["status","result","startedAt","finishedAt"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
