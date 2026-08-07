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

export type DerivationTransformationInput =
  Data.components['schemas']['TransformationInputPostBody']

export type DerivationTransformationPayload =
  Data.components['schemas']['DerivationTransformationPostBody']

export type DerivationTransformationPatchPayload =
  Data.components['schemas']['DerivationTransformationPatchBody']

export type DerivationTransformationResponse =
  Data.components['schemas']['DerivationTransformationResponse']

export type DerivationTransformationSummaryResponse =
  Data.components['schemas']['DerivationTransformationSummaryResponse']
