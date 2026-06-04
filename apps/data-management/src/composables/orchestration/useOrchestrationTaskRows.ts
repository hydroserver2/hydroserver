import { computed, ref, type Ref } from 'vue'
import type {
  DataProductTaskExpanded,
  MonitoringTaskExpanded,
  TaskExpanded,
  TaskMapping,
  TaskRun,
} from '@hydroserver/client'
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

type AnyTask = TaskExpanded | DataProductTaskExpanded | MonitoringTaskExpanded

const targetDatastream = (mapping: TaskMapping) =>
  'targetDatastream' in mapping ? mapping.targetDatastream : null

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
  workspaceTasks: Ref<TaskExpanded[]>
  dataProductTasks: Ref<DataProductTaskExpanded[]>
  monitoringTasks: Ref<MonitoringTaskExpanded[]>
  datastreamThingByDatastreamId: Ref<Record<string, string>>
  runNowTriggeredByTaskId: Record<string, boolean>
}

const buildRowBase = (
  task: AnyTask,
  kind: TaskKind,
  runNowTriggeredByTaskId: Record<string, boolean>
) => {
  const schedule = task.schedule ?? null
  const latestRun = (task as any).latestRun as TaskRun | null | undefined
  const nextRunAtDate = getTaskNextRunAt(task as any)
  const hasValidCachedNextRun =
    !!schedule?.nextRunAt && !Number.isNaN(new Date(schedule.nextRunAt).getTime())
  const nextRunAt = hasValidCachedNextRun
    ? schedule?.nextRunAt ?? null
    : nextRunAtDate?.toISOString() ?? null
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

const resolveDataProductTaskType = (
  t: DataProductTaskExpanded
): DataProductTaskType => {
  if (t.aggregationTransformations?.length) return 'Aggregation'
  if (t.expressionTransformations?.length) return 'Expression'
  if (t.compositeExpressionTransformations?.length) return 'Derivation'
  if (t.ratingCurveTransformations?.length) return 'Rating curve'
  return null
}

const hasEtlMapping = (mapping: TaskMapping) => {
  const anyMapping = mapping as any
  if (anyMapping.targetDatastream?.id || anyMapping.targetDatastreamId) {
    return true
  }
  return Array.isArray(anyMapping.paths) && anyMapping.paths.length > 0
}

const getEtlNoWorkWarning = (task: TaskExpanded): TaskNoWorkWarning =>
  Array.isArray(task.mappings) && task.mappings.some(hasEtlMapping)
    ? null
    : ETL_NO_WORK_WARNING

const getDataProductNoWorkWarning = (
  task: DataProductTaskExpanded
): TaskNoWorkWarning =>
  [
    task.aggregationTransformations,
    task.compositeExpressionTransformations,
    task.expressionTransformations,
    task.ratingCurveTransformations,
  ].some((transformations) => (transformations ?? []).length > 0)
    ? null
    : DATA_PRODUCT_NO_WORK_WARNING

const getMonitoringNoWorkWarning = (
  task: MonitoringTaskExpanded
): TaskNoWorkWarning =>
  (task.monitoredDatastreams ?? []).some(
    (monitored) => (monitored.rules ?? []).length > 0
  )
    ? null
    : MONITORING_NO_WORK_WARNING

const humanizeRuleType = (value: string) =>
  value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())

const resolveMonitoringRules = (task: MonitoringTaskExpanded) => {
  const ruleCounts = new Map<string, number>()
  for (const monitored of task.monitoredDatastreams ?? []) {
    for (const rule of monitored.rules ?? []) {
      const type = `${(rule as any).ruleType ?? ''}`
      if (!type) continue
      ruleCounts.set(type, (ruleCounts.get(type) ?? 0) + 1)
    }
  }

  const total = [...ruleCounts.values()].reduce((sum, count) => sum + count, 0)
  const breakdown = [...ruleCounts.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([type, count]) => ({
      label: humanizeRuleType(type),
      count,
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

// ETL tasks don't carry their site on the task itself; infer it from the first mapping's
// target datastream, cross-referencing the workspace datastream list for thingId.
const resolveEtlTaskThingId = (
  task: TaskExpanded,
  datastreamThingMap: Record<string, string>
): string | null => {
  for (const mapping of task.mappings ?? []) {
    const ds = targetDatastream(mapping)
    const dsThingId = ds?.thingId ?? ds?.thing_id
    if (dsThingId) return dsThingId
    const fromMap = ds?.id ? datastreamThingMap[ds.id] : null
    if (fromMap) return fromMap
  }
  return null
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
    datastreamThingByDatastreamId,
    runNowTriggeredByTaskId,
  } = inputs

  const etlTaskRows = computed<TaskRow[]>(() =>
    workspaceTasks.value.map((t) => ({
      ...buildRowBase(t, 'etl', runNowTriggeredByTaskId),
      dataConnectionId: (t as any).dataConnection?.id ?? null,
      thingId: resolveEtlTaskThingId(t, datastreamThingByDatastreamId.value),
      noWorkWarning: getEtlNoWorkWarning(t),
    }))
  )

  const dataProductTaskRows = computed<TaskRow[]>(() =>
    dataProductTasks.value.map((t) => ({
      ...buildRowBase(t, 'dataProduct', runNowTriggeredByTaskId),
      dataConnectionId: null,
      thingId: t.thing?.id ?? null,
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
        thingId: t.thing?.id ?? null,
        noWorkWarning: getMonitoringNoWorkWarning(t),
        qualityRuleSummary: rules.summary,
        qualityRuleCount: rules.total,
        qualityRuleBreakdown: rules.breakdown,
        monitoringRulesViolated: getMonitoringRulesViolated(t.latestRun),
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
