import type { StatusType } from '@hydroserver/client'

// The one place task statuses get a color. Statuses come from the API.
export const TASK_STATUS_COLORS: Record<StatusType, string> = {
  OK: 'var(--hs-success)',
  Pending: 'var(--hs-primary)',
  'Needs attention': 'var(--hs-danger)',
  'Violations found': 'var(--hs-warning)',
  'Behind schedule': 'var(--hs-warning)',
  'Loading paused': 'var(--hs-text-secondary)',
  Unknown: 'var(--hs-default)',
}

export const taskStatusColor = (status: unknown): string =>
  TASK_STATUS_COLORS[status as StatusType] ?? TASK_STATUS_COLORS.Unknown
