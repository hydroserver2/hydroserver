import { HydroServerBaseService } from './base'
import {
  DataProductTaskContract as C,
  RunContract,
} from '../../generated/contracts'
import { DataProductTask as M } from '../Models/data-product-task.model'
import { apiMethods } from '../apiMethods'
import type {
  AggregationTransformationPatchPayload,
  AggregationTransformationPayload,
  CompositeExpressionTransformationPatchPayload,
  CompositeExpressionTransformationPayload,
} from './data-product-transformation.types'

export class DataProductTaskService extends HydroServerBaseService<
  typeof C,
  M
> {
  static route = C.route
  static writableKeys = C.writableKeys
  static Model = M

  protected override getBaseUrl(): string {
    return `${this._client.host}/api/data/products`
  }

  runTask(taskId: string) {
    return apiMethods.post(`${this._route}/${taskId}/trigger`)
  }

  getTaskRuns(taskId: string, params?: RunContract.QueryParameters) {
    return apiMethods.paginatedFetch(
      this.withQuery(`${this._route}/${taskId}/runs`, params)
    )
  }

  getTaskRun(taskId: string, runId: string) {
    return apiMethods.fetch(`${this._route}/${taskId}/runs/${runId}`)
  }

  /* -------------------- Expression Transformations ------------------- */

  createExpressionTransformation(
    taskId: string,
    payload: {
      outputDatastreamId: string
      inputDatastreamId: string
      variableName: string
      formula: string
    }
  ) {
    return apiMethods.post(
      `${this._route}/${taskId}/transformations/expression`,
      payload
    )
  }

  listExpressionTransformations(taskId: string) {
    return apiMethods.fetch(
      `${this._route}/${taskId}/transformations/expression`
    )
  }

  updateExpressionTransformation(
    taskId: string,
    transformationId: string,
    payload: Partial<{
      outputDatastreamId: string
      inputDatastreamId: string
      variableName: string | null
      formula: string
    }>
  ) {
    return apiMethods.patch(
      `${this._route}/${taskId}/transformations/expression/${transformationId}`,
      payload
    )
  }

  deleteExpressionTransformation(taskId: string, transformationId: string) {
    return apiMethods.delete(
      `${this._route}/${taskId}/transformations/expression/${transformationId}`
    )
  }

  /* ------------------ Rating Curve Transformations ------------------- */

  createRatingCurveTransformation(
    taskId: string,
    payload: {
      outputDatastreamId: string
      inputDatastreamId: string
      ratingCurveId: string
    }
  ) {
    return apiMethods.post(
      `${this._route}/${taskId}/transformations/rating-curve`,
      payload
    )
  }

  listRatingCurveTransformations(taskId: string) {
    return apiMethods.fetch(
      `${this._route}/${taskId}/transformations/rating-curve`
    )
  }

  updateRatingCurveTransformation(
    taskId: string,
    transformationId: string,
    payload: Partial<{
      outputDatastreamId: string
      inputDatastreamId: string
      ratingCurveId: string
    }>
  ) {
    return apiMethods.patch(
      `${this._route}/${taskId}/transformations/rating-curve/${transformationId}`,
      payload
    )
  }

  deleteRatingCurveTransformation(taskId: string, transformationId: string) {
    return apiMethods.delete(
      `${this._route}/${taskId}/transformations/rating-curve/${transformationId}`
    )
  }

  /* ------------------- Aggregation Transformations ------------------- */

  createAggregationTransformation(
    taskId: string,
    payload: AggregationTransformationPayload
  ) {
    return apiMethods.post(
      `${this._route}/${taskId}/transformations/aggregation`,
      payload
    )
  }

  listAggregationTransformations(taskId: string) {
    return apiMethods.fetch(
      `${this._route}/${taskId}/transformations/aggregation`
    )
  }

  updateAggregationTransformation(
    taskId: string,
    transformationId: string,
    payload: AggregationTransformationPatchPayload
  ) {
    return apiMethods.patch(
      `${this._route}/${taskId}/transformations/aggregation/${transformationId}`,
      payload
    )
  }

  deleteAggregationTransformation(taskId: string, transformationId: string) {
    return apiMethods.delete(
      `${this._route}/${taskId}/transformations/aggregation/${transformationId}`
    )
  }

  /* ------------- Composite Expression Transformations ---------------- */

  createCompositeExpressionTransformation(
    taskId: string,
    payload: CompositeExpressionTransformationPayload
  ) {
    return apiMethods.post(
      `${this._route}/${taskId}/transformations/composite-expression`,
      payload
    )
  }

  listCompositeExpressionTransformations(taskId: string) {
    return apiMethods.fetch(
      `${this._route}/${taskId}/transformations/composite-expression`
    )
  }

  updateCompositeExpressionTransformation(
    taskId: string,
    transformationId: string,
    payload: CompositeExpressionTransformationPatchPayload
  ) {
    return apiMethods.patch(
      `${this._route}/${taskId}/transformations/composite-expression/${transformationId}`,
      payload
    )
  }

  deleteCompositeExpressionTransformation(
    taskId: string,
    transformationId: string
  ) {
    return apiMethods.delete(
      `${this._route}/${taskId}/transformations/composite-expression/${transformationId}`
    )
  }
}
