import { computed } from 'vue'
import { useRoute, type LocationQuery } from 'vue-router'
import router from '@/router/router'
import type {
  DataProductTaskType,
  TabId,
  TaskKind,
  TaskRow,
} from '@/components/Orchestration/workbench/orchestrationTabs'

export type OrchestrationView = TabId | 'workspaces'

export type OrchestrationTaskDetailType =
  | 'ingestion'
  | 'aggregation'
  | 'expression'
  | 'derivation'
  | 'rating-curve'
  | 'quality'

export const ORCHESTRATION_VIEW_ROUTE_NAME = 'OrchestrationView'

export const ORCHESTRATION_DETAIL_ROUTE_NAMES: Record<
  OrchestrationTaskDetailType,
  string
> = {
  ingestion: 'OrchestrationIngestionDetails',
  aggregation: 'OrchestrationAggregationDetails',
  expression: 'OrchestrationExpressionDetails',
  derivation: 'OrchestrationDerivationDetails',
  'rating-curve': 'OrchestrationRatingCurveDetails',
  quality: 'OrchestrationQualityDetails',
}

const VALID_VIEWS = new Set<OrchestrationView>([
  'ingestion',
  'aggregation',
  'quality',
  'workspaces',
])

const VALID_DETAIL_TYPES = new Set<OrchestrationTaskDetailType>([
  'ingestion',
  'aggregation',
  'expression',
  'derivation',
  'rating-curve',
  'quality',
])

const DETAIL_VIEW: Record<OrchestrationTaskDetailType, OrchestrationView> = {
  ingestion: 'ingestion',
  aggregation: 'aggregation',
  expression: 'aggregation',
  derivation: 'aggregation',
  'rating-curve': 'aggregation',
  quality: 'quality',
}

export const DETAIL_KIND: Record<OrchestrationTaskDetailType, TaskKind> = {
  ingestion: 'etl',
  aggregation: 'dataProduct',
  expression: 'dataProduct',
  derivation: 'dataProduct',
  'rating-curve': 'dataProduct',
  quality: 'monitoring',
}

const DATA_PRODUCT_DETAIL_TYPE: Record<
  NonNullable<DataProductTaskType>,
  OrchestrationTaskDetailType
> = {
  Aggregation: 'aggregation',
  Expression: 'expression',
  Derivation: 'derivation',
  'Rating curve': 'rating-curve',
}

const firstString = (value: unknown): string | null => {
  if (Array.isArray(value)) return firstString(value[0])
  return typeof value === 'string' && value.trim() ? value : null
}

export const normalizeOrchestrationView = (
  value: unknown
): OrchestrationView | null => {
  const candidate = firstString(value)
  return candidate && VALID_VIEWS.has(candidate as OrchestrationView)
    ? (candidate as OrchestrationView)
    : null
}

export const normalizeOrchestrationTaskDetailType = (
  value: unknown
): OrchestrationTaskDetailType | null => {
  const candidate = firstString(value)
  return candidate &&
    VALID_DETAIL_TYPES.has(candidate as OrchestrationTaskDetailType)
    ? (candidate as OrchestrationTaskDetailType)
    : null
}

export const detailTypeForTaskRow = (
  row: TaskRow
): OrchestrationTaskDetailType | null => {
  if (row.kind === 'etl') return 'ingestion'
  if (row.kind === 'monitoring') return 'quality'
  if (!row.taskType) return null
  return DATA_PRODUCT_DETAIL_TYPE[row.taskType] ?? null
}

const withoutTaskDetails = (query: LocationQuery) => {
  const nextQuery = { ...query }
  delete nextQuery.task_id
  delete nextQuery.run_id
  delete nextQuery.taskId
  delete nextQuery.runId
  delete nextQuery.taskKind
  return nextQuery
}

export function useOrchestrationRouteState() {
  const route = useRoute()

  const taskDetailType = computed(() =>
    normalizeOrchestrationTaskDetailType(route.meta.orchestrationTaskDetail)
  )

  const view = computed<OrchestrationView>(() => {
    const detailView = taskDetailType.value
      ? DETAIL_VIEW[taskDetailType.value]
      : null
    return (
      detailView ??
      normalizeOrchestrationView(route.meta.orchestrationView) ??
      normalizeOrchestrationView(route.params.view) ??
      'ingestion'
    )
  })

  const taskKind = computed<TaskKind | null>(() =>
    taskDetailType.value ? DETAIL_KIND[taskDetailType.value] : null
  )

  const taskId = computed(() => firstString(route.query.task_id))
  const runId = computed(() => firstString(route.query.run_id))

  const hasTaskDetails = computed(
    () => taskDetailType.value !== null && taskId.value !== null
  )

  const replaceView = async (nextView: OrchestrationView) => {
    await router.replace({
      name: ORCHESTRATION_VIEW_ROUTE_NAME,
      params: { view: nextView },
      query: {},
    })
  }

  const closeTaskDetails = async () => {
    if (
      !taskDetailType.value &&
      !route.query.task_id &&
      !route.query.run_id &&
      !route.query.taskId &&
      !route.query.runId &&
      !route.query.taskKind
    ) {
      return
    }

    await router.replace({
      name: ORCHESTRATION_VIEW_ROUTE_NAME,
      params: { view: view.value },
      query: withoutTaskDetails(route.query),
    })
  }

  const pushTaskDetails = async (row: TaskRow) => {
    const detailType = detailTypeForTaskRow(row)
    if (!detailType) return

    await router.push({
      name: ORCHESTRATION_DETAIL_ROUTE_NAMES[detailType],
      params: { view: DETAIL_VIEW[detailType] },
      query: {
        ...withoutTaskDetails(route.query),
        task_id: row.id,
      },
    })
  }

  return {
    view,
    taskDetailType,
    taskKind,
    taskId,
    runId,
    hasTaskDetails,
    replaceView,
    closeTaskDetails,
    pushTaskDetails,
  }
}
