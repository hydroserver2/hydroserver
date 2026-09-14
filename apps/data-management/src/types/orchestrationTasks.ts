import type {
  DataProductTaskContract,
  DataProductTaskExpanded,
  MonitoringTaskContract,
  MonitoringTaskExpanded,
  TaskExpanded,
  TaskRun,
  TaskSchedule,
} from '@hydroserver/client'

export type TaskSummary = {
  id: string
  name: string
  description?: string | null
  taskVariables: Record<string, unknown>
  dataConnectionId: string
  mappingCount: number
  workspaceId: string
  latestRun?: TaskRun | null
  schedule?: TaskSchedule | null
}

export type Task = TaskExpanded | TaskSummary

export type DataProductTask =
  | DataProductTaskExpanded
  | DataProductTaskContract.SummaryResponse

export type MonitoringTask =
  | MonitoringTaskExpanded
  | MonitoringTaskContract.SummaryResponse

export type AnyTask = Task | DataProductTask | MonitoringTask
