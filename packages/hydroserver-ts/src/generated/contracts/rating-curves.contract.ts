/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace RatingCurveContract {
  export const route = 'rating-curves' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_products_rating_curve_get_rating_curves']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_products_rating_curve_get_rating_curves']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['RatingCurveResponse']
  export type DetailResponse  = Data.components['schemas']['RatingCurveResponse']
  export type PostBody        = Data.components['schemas']['RatingCurvePostBody']
  export type PatchBody       = Data.components['schemas']['RatingCurvePatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["description","fittingMethod","name","points"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
