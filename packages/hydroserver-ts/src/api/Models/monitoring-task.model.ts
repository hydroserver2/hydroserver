import type { TaskRun, TaskSchedule } from './task.model'

export type MonitoringRuleType =
  | 'range'
  | 'rate_of_change'
  | 'persistence'
  | 'missing_data'

export type MonitoringRuleWindowUnit = 'minutes' | 'hours' | 'days'

export interface MonitoringRule {
  id: string
  taskId: string
  datastreamId: string
  lastCheckedAt?: string | null
  maxValue?: number | null
  minValue?: number | null
  ruleType: MonitoringRuleType
  windowInterval?: number | null
  windowIntervalUnits?: MonitoringRuleWindowUnit | null
}

export class MonitoringTask {
  id = ''
  name = ''
  description: string | null = null
  recipients: string[] = []
  monitoringSiteId = ''
  ruleTypeCounts: Partial<Record<MonitoringRuleType, number>> = {}
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
  monitoringSite: { id: string; name: string; [key: string]: unknown }
  ruleTypeCounts: Partial<Record<MonitoringRuleType, number>>
  latestRun?: TaskRun | null
  schedule: TaskSchedule | null
}
