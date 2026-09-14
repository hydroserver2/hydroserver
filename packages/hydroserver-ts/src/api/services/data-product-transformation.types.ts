import type * as Data from '../../generated/data.types'

export type DataProductTransformation =
  Data.components['schemas']['DataProductTransformationResponse']

export type DataProductTransformationPayload =
  Data.components['schemas']['DataProductTransformationPostBody']

export type DataProductTransformationPatchPayload =
  Data.components['schemas']['DataProductTransformationPatchBody']

export type TransformationInput =
  Data.components['schemas']['TransformationInputResponse']

export type TransformationInputPayload =
  Data.components['schemas']['TransformationInputPostBody']

export type TransformationType = DataProductTransformation['transformationType']

export type AggregationMethod = NonNullable<
  DataProductTransformation['aggregationMethod']
>

export type IntervalUnit = NonNullable<
  DataProductTransformation['outputIntervalUnits']
>

export type AggregationTransformationValues = {
  inputDatastreamId: string | null
  outputDatastreamId: string | null
  aggregationMethod: AggregationMethod
  outputInterval: number | null
  outputIntervalUnits: IntervalUnit
  minValues: number | null
  timezoneType?: DataProductTransformation['timezoneType']
  timezone?: DataProductTransformation['timezone']
}
