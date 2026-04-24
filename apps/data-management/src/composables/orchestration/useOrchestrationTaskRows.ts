import { computed, ref, type Ref } from 'vue'
import type {
  DataProductTaskExpanded,
  MonitoringTaskExpanded,
  TaskExpanded,
  TaskRun,
} from '@hydroserver/client'
import {
  getDisplayedTaskStatus,
  getTaskRunMessage,
  getTaskStatusText,
} from '@/utils/orchestration/taskRunDetails'
import { formatTime } from '@/utils/time'
import type {
  SortDir,
  SortKey,
  TabId,
  TaskKind,
  TaskRow,
} from '@/components/Orchestration/workbench/orchestrationTabs'

type AnyTask = TaskExpanded | DataProductTaskExpanded | MonitoringTaskExpanded

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
  return {
    id: task.id,
    kind,
    name: task.name,
    schedule,
    latestRun,
    statusName: getTaskStatusText(task as any),
    statusSort: getDisplayedTaskStatus(task as any),
    lastRun: latestRun?.startedAt ? formatTime(latestRun.startedAt) : '-',
    nextRun: schedule?.nextRunAt ? formatTime(schedule.nextRunAt) : '-',
    lastRunAt: latestRun?.startedAt ?? null,
    nextRunAt: schedule?.nextRunAt ?? null,
    lastRunMessage: getTaskRunMessage(latestRun as any),
    userClickedRunNow: !!runNowTriggeredByTaskId[task.id],
    raw: task,
  }
}

// ETL tasks don't carry their site on the task itself; infer it from the first mapping's
// target datastream, cross-referencing the workspace datastream list for thingId.
const resolveEtlTaskThingId = (
  task: TaskExpanded,
  datastreamThingMap: Record<string, string>
): string | null => {
  for (const mapping of task.mappings ?? []) {
    const ds = mapping.targetDatastream as any
    const dsThingId = ds?.thingId ?? ds?.thing_id
    if (dsThingId) return dsThingId
    const fromMap = datastreamThingMap[ds?.id]
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
    }))
  )

  const dataProductTaskRows = computed<TaskRow[]>(() =>
    dataProductTasks.value.map((t) => ({
      ...buildRowBase(t, 'dataProduct', runNowTriggeredByTaskId),
      dataConnectionId: null,
      thingId: t.thing?.id ?? null,
    }))
  )

  const monitoringTaskRows = computed<TaskRow[]>(() =>
    monitoringTasks.value.map((t) => ({
      ...buildRowBase(t, 'monitoring', runNowTriggeredByTaskId),
      dataConnectionId: null,
      thingId: t.thing?.id ?? null,
    }))
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
