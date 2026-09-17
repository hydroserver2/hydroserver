/* AUTO-GENERATED. DO NOT EDIT.
   Generated from ../../django/contracts/openapi/data.openapi.json */
import type * as Data from '../data.types'

export namespace DataProductTransformationContract {
  export const route = 'data-product-transformations' as const
  export type QueryParameters = ([Data.operations['interfaces_api_views_products_transformation_get_data_product_transformations']['parameters']['query']] extends [never] ? {} : NonNullable<Data.operations['interfaces_api_views_products_transformation_get_data_product_transformations']['parameters']['query']>)
  export type SummaryResponse = Data.components['schemas']['DataProductTransformationResponse']
  export type DetailResponse  = Data.components['schemas']['ItemResponse_DataProductTransformationResponse_']
  export type PostBody        = Data.components['schemas']['DataProductTransformationPostBody']
  export type PatchBody       = Data.components['schemas']['DataProductTransformationPatchBody']
  export type DeleteBody      = never
  export const writableKeys = ["aggregationMethod","formula","inputDatastreams","minValues","outputDatastreamId","outputInterval","outputIntervalUnits","ratingCurveId","stopOnError","stopOnNoData","timezone","timezoneType"] as const
  export declare const __types: {
    SummaryResponse: SummaryResponse
    DetailResponse: DetailResponse
    PostBody: PostBody
    PatchBody: PatchBody
    DeleteBody: DeleteBody
    QueryParameters: QueryParameters
  }
}
