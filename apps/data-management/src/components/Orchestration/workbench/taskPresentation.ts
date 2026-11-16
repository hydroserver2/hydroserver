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
  if (status === 'Needs attention' || status === 'Violations found')
    return mdiAlertCircleOutline
  if (status === 'Behind schedule') return mdiClockAlertOutline
  if (status === 'Loading paused') return mdiPauseCircleOutline
  if (status === 'Pending') return mdiClockOutline
  return mdiHelpCircleOutline
}

export { taskStatusColor } from '@/utils/orchestration/taskStatusColors'

export const qualityRuleCountLabel = (task: TaskRow) => {
  const count = task.qualityRuleCount ?? 0
  return `${count} rule${count === 1 ? '' : 's'}`
}
