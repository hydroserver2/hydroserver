import type { TaskRun, TaskSchedule } from './task.model'

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
  thing: { id: string; name: string; [key: string]: any }
  aggregationTransformations: any[]
  compositeExpressionTransformations: any[]
  expressionTransformations: any[]
  ratingCurveTransformations: any[]
  latestRun?: TaskRun | null
  schedule: TaskSchedule | null
}
