import {
  mdiAlertCircleOutline,
  mdiCheckCircleOutline,
  mdiClockAlertOutline,
  mdiClockOutline,
  mdiHelpCircleOutline,
  mdiPauseCircleOutline,
} from '@mdi/js'
import {
  getDataProductTypeColors,
  type DataProductTaskType,
  type TaskRow,
} from './orchestrationTabs'

export const taskTypeChipStyle = (taskType: DataProductTaskType) => {
  const colors = getDataProductTypeColors(taskType)
  return colors ? { background: colors.bg, color: colors.text } : {}
}

export const taskStatusIcon = (status: unknown) => {
  if (status === 'OK') return mdiCheckCircleOutline
  if (status === 'Needs attention') return mdiAlertCircleOutline
  if (status === 'Behind schedule') return mdiClockAlertOutline
  if (status === 'Loading paused') return mdiPauseCircleOutline
  if (status === 'Pending') return mdiClockOutline
  return mdiHelpCircleOutline
}

export const taskStatusColor = (status: unknown) => {
  if (status === 'OK') return '#2E7D32'
  if (status === 'Needs attention') return '#B71C1C'
  if (status === 'Behind schedule') return '#BF360C'
  if (status === 'Loading paused') return '#546E7A'
  if (status === 'Pending') return '#1565C0'
  return '#6B7280'
}

export const qualityRuleCountLabel = (task: TaskRow) => {
  const count = task.qualityRuleCount ?? 0
  return `${count} rule${count === 1 ? '' : 's'}`
}
