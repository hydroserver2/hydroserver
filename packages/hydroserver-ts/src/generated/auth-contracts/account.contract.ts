/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/auth.openapi.json */
import type * as Data from '../auth.types'

export namespace AccountContract {
  export const route = 'account' as const
  export type QueryParameters = ([Data.operations['interfaces_auth_views_account_get_account']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_auth_views_account_get_account']['parameters']['query']>)
  export type SummaryResponse = never
  export type DetailResponse  = Data.components['schemas']['AccountDetailResponse']
  export type PostBody        = Data.components['schemas']['AccountPostBody']
  export type PatchBody       = Data.components['schemas']['AccountPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["address","firstName","lastName","link","middleName","organization","phone","type"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
