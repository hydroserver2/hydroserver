/* AUTO-GENERATED. DO NOT EDIT.
   Generated from schemas/data.openapi.json */
import type * as Data from '../data.types'

export namespace WorkspaceContract {
  export const route = 'workspaces' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_workspace_get_workspaces']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_workspace_get_workspaces']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['WorkspaceSummaryResponse']
  export type DetailResponse  = Data.components['schemas']['WorkspaceDetailResponse']
  export type PostBody        = Data.components['schemas']['WorkspacePostBody']
  export type PatchBody       = Data.components['schemas']['WorkspacePatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["name","isPrivate"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
