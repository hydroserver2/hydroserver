import type { TaskRun, TaskSchedule } from './task.model'
import type * as Data from '../../generated/data.types'

type AggregationTransformationResponse =
  Data.components['schemas']['AggregationTransformationResponse']
type DerivationTransformationResponse =
  Data.components['schemas']['DerivationTransformationResponse']
type RatingCurveTransformationResponse =
  Data.components['schemas']['RatingCurveTransformationResponse']

export class DataProductTask {
  id = ''
  name = ''
  description: string | null = null
  monitoringSiteId = ''
  schedule: TaskSchedule | null = null

  constructor(init?: Partial<DataProductTask>) {
    Object.assign(this, init)
  }
}

export interface DataProductTaskExpanded {
  id: string
  name: string
  description?: string | null
  monitoringSite: { id: string; name: string; [key: string]: unknown }
  aggregationTransformations: AggregationTransformationResponse[]
  derivationTransformations: DerivationTransformationResponse[]
  ratingCurveTransformations: RatingCurveTransformationResponse[]
  latestRun?: TaskRun | null
  schedule: TaskSchedule | null
}
