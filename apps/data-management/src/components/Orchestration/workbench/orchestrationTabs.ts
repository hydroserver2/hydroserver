import {
  mdiCallMerge,
  mdiDatabaseArrowDownOutline,
  mdiShieldCheckOutline,
} from '@mdi/js'
import type { StatusType, TaskRun, TaskSchedule } from '@hydroserver/client'
import type { AnyTask } from '@/types/orchestrationTasks'
import hs from '@hydroserver/client'
import { TASK_STATUS_COLORS } from '@/utils/orchestration/taskStatusColors'

export type TabId = 'ingestion' | 'aggregation' | 'quality'
export type TaskKind = 'etl' | 'dataProduct' | 'monitoring'
export type SortKey = 'name' | 'status' | 'lastRunAt' | 'nextRunAt' | 'taskType'
export type SortDir = 'asc' | 'desc'

export type DataProductTaskType =
  'Aggregation' | 'Derivation' | 'Rating curve' | null

export type TaskNoWorkWarning = {
  label: string
  message: string
} | null

export const DATA_PRODUCT_TYPE_COLORS: Record<
  NonNullable<DataProductTaskType>,
  { text: string; bg: string }
> = {
  Aggregation: { text: '#6A1B9A', bg: '#F3E5F5' },
  Derivation: { text: '#006064', bg: '#E0F7FA' },
  'Rating curve': { text: '#283593', bg: '#E8EAF6' },
}

export const DATA_PRODUCT_TYPE_OPTIONS = [
  'Aggregation',
  'Derivation',
  'Rating curve',
] as const satisfies readonly NonNullable<DataProductTaskType>[]

export function getDataProductTypeColors(taskType: DataProductTaskType) {
  return taskType ? DATA_PRODUCT_TYPE_COLORS[taskType] : null
}

export type TaskRow = {
  id: string
  kind: TaskKind
  name: string
  schedule: TaskSchedule | null
  latestRun: TaskRun | null | undefined
  statusName: StatusType
  lastRun: string
  nextRun: string
  lastRunAt: string | null
  nextRunAt: string | null
  lastRunMessage: string
  dataConnectionId: string | null
  monitoringSiteId: string | null
  taskType: DataProductTaskType
  qualityRuleSummary?: string
  qualityRuleCount?: number
  qualityRuleBreakdown?: Array<{ label: string; count: number }>
  monitoringRulesViolated?: number
  noWorkWarning: TaskNoWorkWarning
  userClickedRunNow: boolean
  raw: AnyTask
}

export type TabDefinition = {
  id: TabId
  short: string
  icon: string
  accent: string
  accentLight: string
  issues: number
}

export const TAB_TO_KIND: Record<TabId, TaskKind> = {
  ingestion: 'etl',
  aggregation: 'dataProduct',
  quality: 'monitoring',
}

export const INGESTION_ACCENT = '#1565C0'
const INGESTION_ACCENT_LIGHT = '#E3F2FD'
const AGGREGATION_ACCENT = '#6A1B9A'
const AGGREGATION_ACCENT_LIGHT = '#F3E5F5'
export const QUALITY_ACCENT = '#00695C'
export const QUALITY_ACCENT_LIGHT = '#E0F2F1'

export const TAB_META: Record<
  TabId,
  Pick<TabDefinition, 'id' | 'short' | 'icon' | 'accent' | 'accentLight'>
> = {
  ingestion: {
    id: 'ingestion',
    short: 'Ingestion',
    icon: mdiDatabaseArrowDownOutline,
    accent: INGESTION_ACCENT,
    accentLight: INGESTION_ACCENT_LIGHT,
  },
  aggregation: {
    id: 'aggregation',
    short: 'Aggregations & products',
    icon: mdiCallMerge,
    accent: AGGREGATION_ACCENT,
    accentLight: AGGREGATION_ACCENT_LIGHT,
  },
  quality: {
    id: 'quality',
    short: 'Quality',
    icon: mdiShieldCheckOutline,
    accent: QUALITY_ACCENT,
    accentLight: QUALITY_ACCENT_LIGHT,
  },
}

export const STATUS_OPTIONS = [
  { title: 'OK', value: 'OK' },
  { title: 'Needs attention', value: 'Needs attention' },
  { title: 'Violations found', value: 'Violations found' },
  { title: 'Behind schedule', value: 'Behind schedule' },
  { title: 'Loading paused', value: 'Loading paused' },
  { title: 'Pending', value: 'Pending' },
  { title: 'Unknown', value: 'Unknown' },
] as const

export const getTaskStatusOptions = (tab: TabId) =>
  STATUS_OPTIONS.filter(
    ({ value }) => tab === 'quality' || value !== 'Violations found'
  )

export const READ_ONLY_TOOLTIP =
  'You have read-only access to this workspace. Ask an editor or owner to make changes.'

const DOT_PRIORITY: readonly StatusType[] = [
  'Needs attention',
  'Violations found',
  'Behind schedule',
  'Loading paused',
  'Pending',
  'OK',
]

export const DOT_EMPTY = '#CAC4D0'
export const DOT_DEFAULT_OK = TASK_STATUS_COLORS.OK
const ISSUE_STATUSES = new Set<StatusType>([
  'Needs attention',
  'Violations found',
  'Behind schedule',
])

export const taskHasIssue = (row: TaskRow): boolean =>
  ISSUE_STATUSES.has(row.statusName)

export const countTaskIssues = (rows: TaskRow[]): number =>
  rows.filter(taskHasIssue).length

export const worstDotColor = (rows: TaskRow[]): string => {
  if (rows.length === 0) return DOT_EMPTY
  for (const status of DOT_PRIORITY) {
    if (rows.some((r) => r.statusName === status)) {
      return TASK_STATUS_COLORS[status]
    }
  }
  return DOT_DEFAULT_OK
}

export const serviceForKind = (kind: TaskKind) => {
  if (kind === 'etl') return hs.tasks
  if (kind === 'dataProduct') return hs.dataProductTasks
  return hs.monitoringTasks
}
