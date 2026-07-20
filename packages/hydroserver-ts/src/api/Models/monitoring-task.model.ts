import type { TaskRun, TaskSchedule } from './task.model'
import type { Datastream } from '../../types'

export type MonitoringRuleType =
  | 'range'
  | 'rate_of_change'
  | 'persistence'
  | 'missing_data'

export type MonitoringRuleWindowUnit = 'minutes' | 'hours' | 'days'

export interface MonitoringRule {
  id: string
  datastream: Datastream
  lastCheckedAt?: string | null
  maxValue?: number | null
  minValue?: number | null
  ruleType: MonitoringRuleType
  windowInterval?: number | null
  windowIntervalUnits?: MonitoringRuleWindowUnit | null
}

export interface MonitoringRulePayload {
  datastreamId: string
  ruleType: MonitoringRuleType
  maxValue?: number | null
  minValue?: number | null
  windowInterval?: number | null
  windowIntervalUnits?: MonitoringRuleWindowUnit | null
}

export type MonitoringRulePatchPayload = Omit<
  Partial<MonitoringRulePayload>,
  'datastreamId' | 'ruleType'
>

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
  thing: { id: string; name: string; [key: string]: unknown }
  monitoredDatastreams: Array<{
    id: string
    rules?: MonitoringRule[]
    [key: string]: unknown
  }>
  latestRun?: TaskRun | null
  schedule: TaskSchedule | null
}
