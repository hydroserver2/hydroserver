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
  outputDatastreamId: string | null
  aggregationMethod: AggregationMethod
  outputInterval: number | null
  outputIntervalUnits: IntervalUnit
  minValues: number | null
  timezoneType?: AggregationTransformationPatchPayload['timezoneType']
  timezone?: AggregationTransformationPatchPayload['timezone']
}

export type ExpressionTransformationInput =
  Data.components['schemas']['TransformationInputPostBody']

export type ExpressionTransformationPayload =
  Data.components['schemas']['ExpressionTransformationPostBody']

export type ExpressionTransformationPatchPayload =
  Data.components['schemas']['ExpressionTransformationPatchBody']

export type ExpressionTransformationResponse =
  Data.components['schemas']['ExpressionTransformationResponse']

export type ExpressionTransformationSummaryResponse =
  Data.components['schemas']['ExpressionTransformationSummaryResponse']
