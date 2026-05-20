import {
  mdiCallMerge,
  mdiDatabaseArrowDownOutline,
  mdiShieldCheckOutline,
} from '@mdi/js'
import type {
  DataProductTaskExpanded,
  MonitoringTaskExpanded,
  TaskExpanded,
  TaskRun,
  TaskSchedule,
} from '@hydroserver/client'
import hs from '@hydroserver/client'
import {
  getDisplayedTaskStatus,
  getTaskStatusText,
} from '@/utils/orchestration/taskRunDetails'

export type TabId = 'ingestion' | 'aggregation' | 'quality'
export type TaskKind = 'etl' | 'dataProduct' | 'monitoring'
export type ActiveView = 'tasks' | 'workspaces'
export type SortKey =
  | 'name'
  | 'status'
  | 'lastRunAt'
  | 'nextRunAt'
  | 'taskType'
export type SortDir = 'asc' | 'desc'

export type DataProductTaskType =
  | 'Aggregation'
  | 'Expression'
  | 'Derivation'
  | 'Rating curve'
  | null

export type TaskNoWorkWarning = {
  label: string
  message: string
} | null

export const DATA_PRODUCT_TYPE_COLORS: Record<
  NonNullable<DataProductTaskType>,
  { text: string; bg: string }
> = {
  Aggregation: { text: '#6A1B9A', bg: '#F3E5F5' },
  Expression: { text: '#006064', bg: '#E0F7FA' },
  Derivation: { text: '#FF8F00', bg: '#FFF8E1' },
  'Rating curve': { text: '#283593', bg: '#E8EAF6' },
}

export const DATA_PRODUCT_TYPE_OPTIONS = [
  'Aggregation',
  'Expression',
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
  statusName: ReturnType<typeof getTaskStatusText>
  statusSort: ReturnType<typeof getDisplayedTaskStatus>
  lastRun: string
  nextRun: string
  lastRunAt: string | null
  nextRunAt: string | null
  lastRunMessage: string
  dataConnectionId: string | null
  thingId: string | null
  taskType: DataProductTaskType
  qualityRuleSummary?: string
  qualityRuleCount?: number
  qualityRuleBreakdown?: Array<{ label: string; count: number }>
  monitoringRulesViolated?: number
  noWorkWarning: TaskNoWorkWarning
  userClickedRunNow: boolean
  raw: TaskExpanded | DataProductTaskExpanded | MonitoringTaskExpanded
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
export const INGESTION_ACCENT_LIGHT = '#E3F2FD'
export const AGGREGATION_ACCENT = '#6A1B9A'
export const AGGREGATION_ACCENT_LIGHT = '#F3E5F5'
export const QUALITY_ACCENT = '#00695C'
export const QUALITY_ACCENT_LIGHT = '#E0F2F1'
export const WORKSPACE_ACCENT = '#2E7D32'
export const WORKSPACE_ACCENT_LIGHT = '#E8F5E9'

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
  { title: 'Behind schedule', value: 'Behind schedule' },
  { title: 'Loading paused', value: 'Loading paused' },
  { title: 'Pending', value: 'Pending' },
  { title: 'Unknown', value: 'Unknown' },
] as const

export const READ_ONLY_TOOLTIP =
  'You have read-only access to this workspace. Ask an editor or owner to make changes.'

export const DOT_PALETTE: Record<string, string> = {
  'Needs attention': '#B71C1C',
  'Behind schedule': '#BF360C',
  'Loading paused': '#546E7A',
  Pending: '#1565C0',
  OK: '#2E7D32',
}

const DOT_PRIORITY: readonly string[] = [
  'Needs attention',
  'Behind schedule',
  'Loading paused',
  'Pending',
  'OK',
]

const DOT_EMPTY = '#CAC4D0'
const DOT_DEFAULT_OK = '#2E7D32'
const ISSUE_STATUSES = new Set(['Needs attention', 'Behind schedule'])

export const taskHasIssue = (row: TaskRow): boolean =>
  ISSUE_STATUSES.has(row.statusSort)

export const countTaskIssues = (rows: TaskRow[]): number =>
  rows.filter(taskHasIssue).length

export const worstDotColor = (rows: TaskRow[]): string => {
  if (rows.length === 0) return DOT_EMPTY
  for (const status of DOT_PRIORITY) {
    if (rows.some((r) => r.statusSort === status)) {
      return DOT_PALETTE[status] ?? DOT_DEFAULT_OK
    }
  }
  return DOT_DEFAULT_OK
}

export const serviceForKind = (kind: TaskKind) => {
  if (kind === 'etl') return hs.tasks
  if (kind === 'dataProduct') return hs.dataProductTasks
  return hs.monitoringTasks
}
