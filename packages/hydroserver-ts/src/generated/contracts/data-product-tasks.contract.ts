/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace DataProductTaskContract {
  export const route = 'tasks' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_products_task_get_data_product_tasks']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_products_task_get_data_product_tasks']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['DataProductTaskResponse']
  export type DetailResponse  = Data.components['schemas']['DataProductTaskResponse']
  export type PostBody        = Data.components['schemas']['DataProductTaskPostBody']
  export type PatchBody       = Data.components['schemas']['DataProductTaskPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["description","name","schedule"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
