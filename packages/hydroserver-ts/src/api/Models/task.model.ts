import type { DataConnection } from './data-connection.model'

export class Task {
  id = ''
  name = ''
  description: string | null = null
  taskVariables: Record<string, any> = {}
  dataConnectionId = ''
  mappings: TaskMapping[] = []
  schedule: TaskSchedule | null = null

  constructor(init?: Partial<Task>) {
    Object.assign(this, init)
  }
}

export interface TaskExpanded {
  id: string
  name: string
  description?: string | null
  taskVariables: Record<string, any>
  dataConnection: DataConnection
  mappings: TaskMapping[]
  latestRun?: TaskRun | null
  schedule: TaskSchedule | null
}

export type IntervalPeriod = 'minutes' | 'hours' | 'days'

export type TaskRunResult = Record<string, unknown>

export type TaskRun = {
  status: string
  message?: string | null
  result: TaskRunResult | null
  startedAt?: string
  finishedAt?: string
  id: string
}

export type TaskSchedule = {
  enabled: boolean
  startTime: string | null
  nextRunAt: string | null
  crontab: string | null
  interval: number | null
  intervalPeriod: IntervalPeriod | null
}

export interface EtlMapping {
  sourceIdentifier: string
  targetDatastream: { id: string; name: string; [key: string]: any }
}

export interface EtlMappingPostBody {
  sourceIdentifier: string
  targetDatastreamId: string
}

export type TaskMapping = EtlMapping | EtlMappingPostBody

export const TASK_STATUS_OPTIONS = [
  { color: 'green', title: 'OK' },
  { color: 'blue', title: 'Pending' },
  { color: 'red', title: 'Needs attention' },
  { color: 'orange-darken-4', title: 'Behind schedule' },
  { color: 'gray', title: 'Unknown' },
  { color: 'gray', title: 'Loading paused' },
] as const
export type StatusType = (typeof TASK_STATUS_OPTIONS)[number]['title']

export interface Status {
  lastRunSuccessful?: boolean
  lastRunMessage?: string
  lastRun?: string
  nextRun?: string
  enabled: boolean
}
