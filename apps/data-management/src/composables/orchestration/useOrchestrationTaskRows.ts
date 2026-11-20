import { computed, ref, type Ref } from 'vue'
import type { TaskRun, TaskSchedule } from '@hydroserver/client'
import type {
  AnyTask,
  DataProductTask,
  MonitoringTask,
  Task,
} from '@/types/orchestrationTasks'
import {
  getDisplayedTaskStatus,
  getMonitoringRulesViolated,
  getTaskNextRunAt,
  getTaskRunMessage,
  getTaskStatusText,
} from '@/utils/orchestration/taskRunDetails'
import { formatTime } from '@/utils/time'
import type {
  DataProductTaskType,
  SortDir,
  SortKey,
  TabId,
  TaskKind,
  TaskNoWorkWarning,
  TaskRow,
} from '@/components/Orchestration/workbench/orchestrationTabs'

const ETL_NO_WORK_WARNING: TaskNoWorkWarning = {
  label: 'No mappings',
  message:
    "This task has no mappings configured, so running it won't do anything.",
}

const DATA_PRODUCT_NO_WORK_WARNING: TaskNoWorkWarning = {
  label: 'No mappings',
  message:
    "This task has no transformations configured, so running it won't do anything.",
}

const MONITORING_NO_WORK_WARNING: TaskNoWorkWarning = {
  label: 'No rules',
  message:
    "This quality task has no rules configured, so running it won't do anything.",
}

type Inputs = {
  activeTab: Ref<TabId>
  workspaceTasks: Ref<Task[]>
  dataProductTasks: Ref<DataProductTask[]>
  monitoringTasks: Ref<MonitoringTask[]>
  runNowTriggeredByTaskId: Record<string, boolean>
}

const buildRowBase = (
  task: AnyTask,
  kind: TaskKind,
  runNowTriggeredByTaskId: Record<string, boolean>
) => {
  const schedule = (task.schedule ?? null) as TaskSchedule | null
  const latestRun = ((task as any).latestRun ?? null) as TaskRun | null
  const nextRunAtDate = getTaskNextRunAt(task as any)
  const nextRunAt = nextRunAtDate
    ? nextRunAtDate.toISOString().replace(/\.\d{3}Z$/, 'Z')
    : null
  return {
    id: task.id,
    kind,
    name: task.name,
    schedule,
    latestRun,
    statusName: getTaskStatusText(task as any),
    statusSort: getDisplayedTaskStatus(task as any),
    lastRun: latestRun?.startedAt ? formatTime(latestRun.startedAt) : '-',
    nextRun: nextRunAt ? formatTime(nextRunAt) : '-',
    lastRunAt: latestRun?.startedAt ?? null,
    nextRunAt,
    lastRunMessage: getTaskRunMessage(latestRun as any),
    taskType: null as DataProductTaskType,
    noWorkWarning: null as TaskNoWorkWarning,
    userClickedRunNow: !!runNowTriggeredByTaskId[task.id],
    raw: task,
  }
}

const dataConnectionIdOf = (t: Task): string | null =>
  'dataConnectionId' in t ? t.dataConnectionId : t.dataConnection?.id ?? null

const mappingCountOf = (t: Task): number =>
  'mappingCount' in t ? t.mappingCount : 0

const monitoringSiteIdOf = (t: DataProductTask | MonitoringTask): string | null =>
  'monitoringSiteId' in t ? t.monitoringSiteId : t.monitoringSite?.id ?? null

const resolveDataProductTaskType = (
  t: DataProductTask
): DataProductTaskType => {
  const types = new Set(t.transformationTypes ?? [])
  if (types.has('aggregation')) return 'Aggregation'
  if (types.has('derivation')) return 'Derivation'
  if (types.has('rating_curve')) return 'Rating curve'
  return null
}

const getEtlNoWorkWarning = (task: Task): TaskNoWorkWarning =>
  mappingCountOf(task) > 0 ? null : ETL_NO_WORK_WARNING

const getDataProductNoWorkWarning = (
  task: DataProductTask
): TaskNoWorkWarning =>
  (task.transformationTypes ?? []).length > 0
    ? null
    : DATA_PRODUCT_NO_WORK_WARNING

const getMonitoringNoWorkWarning = (task: MonitoringTask): TaskNoWorkWarning =>
  Object.values(task.ruleTypeCounts ?? {}).some((count) => (count ?? 0) > 0)
    ? null
    : MONITORING_NO_WORK_WARNING

const humanizeRuleType = (value: string) =>
  value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())

const resolveMonitoringRules = (task: MonitoringTask) => {
  const counts = task.ruleTypeCounts ?? {}
  const total = Object.values(counts).reduce(
    (sum, count) => sum + (count ?? 0),
    0
  )
  const breakdown = Object.entries(counts)
    .filter(([, count]) => (count ?? 0) > 0)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([type, count]) => ({
      label: humanizeRuleType(type),
      count: count ?? 0,
    }))

  if (total === 0) {
    return {
      total,
      breakdown,
      summary: 'No rules',
    }
  }

  const summary = breakdown
    .map((item) => `${item.count} ${item.label}`)
    .join(', ')

  return { total, breakdown, summary }
}

const compareText = (a: unknown, b: unknown) =>
  `${a ?? ''}`.localeCompare(`${b ?? ''}`, undefined, {
    numeric: true,
    sensitivity: 'base',
  })

const compareNullableDate = (a: unknown, b: unknown) => {
  const aVal = a ? new Date(a as any).getTime() : null
  const bVal = b ? new Date(b as any).getTime() : null
  if (aVal == null && bVal == null) return 0
  if (aVal == null) return 1
  if (bVal == null) return -1
  return aVal - bVal
}

export function useOrchestrationTaskRows(inputs: Inputs) {
  const {
    activeTab,
    workspaceTasks,
    dataProductTasks,
    monitoringTasks,
    runNowTriggeredByTaskId,
  } = inputs

  const etlTaskRows = computed<TaskRow[]>(() =>
    workspaceTasks.value.map((t) => ({
      ...buildRowBase(t, 'etl', runNowTriggeredByTaskId),
      dataConnectionId: dataConnectionIdOf(t),
      monitoringSiteId: null,
      noWorkWarning: getEtlNoWorkWarning(t),
    }))
  )

  const dataProductTaskRows = computed<TaskRow[]>(() =>
    dataProductTasks.value.map((t) => ({
      ...buildRowBase(t, 'dataProduct', runNowTriggeredByTaskId),
      dataConnectionId: null,
      monitoringSiteId: monitoringSiteIdOf(t),
      taskType: resolveDataProductTaskType(t),
      noWorkWarning: getDataProductNoWorkWarning(t),
    }))
  )

  const monitoringTaskRows = computed<TaskRow[]>(() =>
    monitoringTasks.value.map((t) => {
      const rules = resolveMonitoringRules(t)
      return {
        ...buildRowBase(t, 'monitoring', runNowTriggeredByTaskId),
        dataConnectionId: null,
        monitoringSiteId: monitoringSiteIdOf(t),
        noWorkWarning: getMonitoringNoWorkWarning(t),
        qualityRuleSummary: rules.summary,
        qualityRuleCount: rules.total,
        qualityRuleBreakdown: rules.breakdown,
        monitoringRulesViolated: getMonitoringRulesViolated(
          (t as any).latestRun
        ),
      }
    })
  )

  const activeTaskRows = computed<TaskRow[]>(() => {
    if (activeTab.value === 'ingestion') return etlTaskRows.value
    if (activeTab.value === 'aggregation') return dataProductTaskRows.value
    return monitoringTaskRows.value
  })

  const sortKey = ref<SortKey>('name')
  const sortDir = ref<SortDir>('asc')

  const toggleSort = (key: SortKey) => {
    if (sortKey.value === key) {
      sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortKey.value = key
      sortDir.value = 'asc'
    }
  }

  const sortRows = (rows: TaskRow[]): TaskRow[] => {
    const out = [...rows]
    const dir = sortDir.value === 'asc' ? 1 : -1
    out.sort((a, b) => {
      let cmp = 0
      if (sortKey.value === 'name') cmp = compareText(a.name, b.name)
      else if (sortKey.value === 'status')
        cmp = compareText(a.statusSort, b.statusSort)
      else if (sortKey.value === 'lastRunAt')
        cmp = compareNullableDate(a.lastRunAt, b.lastRunAt)
      else if (sortKey.value === 'nextRunAt')
        cmp = compareNullableDate(a.nextRunAt, b.nextRunAt)
      else if (sortKey.value === 'taskType')
        cmp = compareText(a.taskType, b.taskType)
      return cmp * dir
    })
    return out
  }

  return {
    etlTaskRows,
    dataProductTaskRows,
    monitoringTaskRows,
    activeTaskRows,
    sortKey,
    sortDir,
    toggleSort,
    sortRows,
  }
}
