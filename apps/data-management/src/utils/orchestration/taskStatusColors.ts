import type { StatusType } from '@hydroserver/client'

// The one place task statuses get a color. Statuses come from the API.
export const TASK_STATUS_COLORS: Record<StatusType, string> = {
  OK: '#2E7D32',
  Pending: '#1565C0',
  'Needs attention': '#B71C1C',
  'Violations found': 'var(--hs-warning)',
  'Behind schedule': '#BF360C',
  'Loading paused': '#546E7A',
  Unknown: '#6B7280',
}

export const taskStatusColor = (status: unknown): string =>
  TASK_STATUS_COLORS[status as StatusType] ?? TASK_STATUS_COLORS.Unknown
