import type { TaskRun, TaskSchedule } from './task.model'
import type { TransformationType } from '../services/data-product-transformation.types'

export class DataProductTask {
  id = ''
  name = ''
  description: string | null = null
  monitoringSiteId = ''
  transformationTypes: TransformationType[] = []
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
  transformationTypes: TransformationType[]
  latestRun?: TaskRun | null
  schedule: TaskSchedule | null
}
