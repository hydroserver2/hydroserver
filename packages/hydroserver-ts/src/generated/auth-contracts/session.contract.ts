/* AUTO-GENERATED. DO NOT EDIT.
   Generated from schemas/auth.openapi.json */
import type * as Data from '../auth.types'

export namespace SessionContract {
  export const route = 'session' as const
  export type QueryParameters = ([Data.operations['interfaces_auth_views_session_get_session']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_auth_views_session_get_session']['parameters']['query']>)
  export type SummaryResponse = never
  export type DetailResponse  = never
  export type PostBody        = Data.components['schemas']['SessionPostBody']
  export type PatchBody       = Partial<Data.components['schemas']['SessionPostBody']>
  export type DeleteBody      = never
  export const writableKeys = ["email","password"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
