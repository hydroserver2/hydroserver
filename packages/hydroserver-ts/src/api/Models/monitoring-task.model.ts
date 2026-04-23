import type { TaskRun, TaskSchedule } from './task.model'

export class MonitoringTask {
  id = ''
  name = ''
  description: string | null = null
  recipients: string[] = []
  thingId = ''
  schedule: TaskSchedule | null = null

  constructor(init?: Partial<MonitoringTask>) {
    Object.assign(this, init)
  }
}

export interface MonitoringTaskExpanded {
  id: string
  name: string
  description?: string | null
  recipients: string[]
  thing: { id: string; name: string; [key: string]: any }
  monitoredDatastreams: Array<{ id: string; [key: string]: any }>
  latestRun?: TaskRun | null
  schedule: TaskSchedule | null
}
