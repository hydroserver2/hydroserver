import type { TaskRun, TaskSchedule } from './task.model'
import type * as Data from '../../generated/data.types'

type AggregationTransformationResponse =
  Data.components['schemas']['AggregationTransformationResponse']
type CompositeExpressionTransformationResponse =
  Data.components['schemas']['CompositeExpressionTransformationResponse']
type ExpressionTransformationResponse =
  Data.components['schemas']['ExpressionTransformationResponse']
type RatingCurveTransformationResponse =
  Data.components['schemas']['RatingCurveTransformationResponse']

export class DataProductTask {
  id = ''
  name = ''
  description: string | null = null
  thingId = ''
  schedule: TaskSchedule | null = null

  constructor(init?: Partial<DataProductTask>) {
    Object.assign(this, init)
  }
}

export interface DataProductTaskExpanded {
  id: string
  name: string
  description?: string | null
  thing: { id: string; name: string; [key: string]: unknown }
  aggregationTransformations: AggregationTransformationResponse[]
  compositeExpressionTransformations: CompositeExpressionTransformationResponse[]
  expressionTransformations: ExpressionTransformationResponse[]
  ratingCurveTransformations: RatingCurveTransformationResponse[]
  latestRun?: TaskRun | null
  schedule: TaskSchedule | null
}
