import type * as Data from '../../generated/data.types'

export type AggregationTransformationPayload =
  Data.components['schemas']['AggregationTransformationPostBody']

export type AggregationTransformationPatchPayload =
  Data.components['schemas']['AggregationTransformationPatchBody']

export type AggregationTransformationResponse =
  Data.components['schemas']['AggregationTransformationResponse']

export type AggregationMethod =
  AggregationTransformationPayload['aggregationMethod']

export type IntervalUnit = AggregationTransformationPayload['outputIntervalUnits']

export type AggregationTransformationValues = {
  inputDatastreamId: string | null
  aggregationMethod: AggregationMethod
  outputInterval: number | null
  outputIntervalUnits: IntervalUnit
  minValues: number | null
  timezoneType?: AggregationTransformationPatchPayload['timezoneType']
  timezone?: AggregationTransformationPatchPayload['timezone']
}

export type CompositeExpressionInput =
  Data.components['schemas']['TransformationInputPostBody']

export type CompositeExpressionTransformationPayload =
  Data.components['schemas']['CompositeExpressionTransformationPostBody']

export type CompositeExpressionTransformationPatchPayload =
  Data.components['schemas']['CompositeExpressionTransformationPatchBody']

export type CompositeExpressionTransformationResponse =
  Data.components['schemas']['CompositeExpressionTransformationResponse']
