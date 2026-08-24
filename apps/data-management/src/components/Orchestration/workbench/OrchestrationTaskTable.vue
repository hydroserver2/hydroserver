<template>
  <div class="hs-table-card task-table-shell">
    <table class="task-table hs-text-sm">
      <thead>
        <tr>
          <th colspan="2" class="task-main-header">
            <div class="task-header-filters">
              <TaskTableFilter
                label="Status"
                title="Filter by status"
                :options="statusOptions"
                :selected="statusFilter"
                @toggle="emit('toggle-status', $event)"
                @clear="emit('clear-status')"
              />
              <TaskTableFilter
                v-if="activeTab === 'aggregation'"
                label="Type"
                title="Filter by task type"
                :options="taskTypeOptions"
                :selected="taskTypeFilter"
                @toggle="emit('toggle-task-type', $event)"
                @clear="emit('clear-task-type')"
              />
            </div>
          </th>
          <th class="text-right" />
        </tr>
      </thead>

      <tbody>
        <tr v-for="task in tasks" :key="task.id">
          <td class="task-status-cell">
            <v-tooltip location="bottom" :open-delay="0" :close-delay="80">
              <template #activator="{ props: tooltipProps }">
                <span
                  v-bind="tooltipProps"
                  class="task-status-icon"
                  :style="{ color: taskStatusColor(task.statusSort) }"
                  :aria-label="task.statusSort"
                >
                  <v-icon :icon="taskStatusIcon(task.statusSort)" size="20" />
                </span>
              </template>
              <span>{{
                task.lastRunMessage || 'No run history available yet.'
              }}</span>
            </v-tooltip>
          </td>

          <td class="task-summary-cell">
            <div class="task-name">{{ task.name || '—' }}</div>
            <div class="task-meta hs-text-sm">
              <span class="task-meta-label hs-label">Last</span>
              <span class="task-time">{{ task.lastRun }}</span>
              <span aria-hidden="true">·</span>
              <span class="task-meta-label hs-label">Next</span>
              <span class="task-time">{{ task.nextRun }}</span>

              <v-chip
                v-if="activeTab === 'aggregation' && task.taskType"
                density="comfortable"
                size="small"
                rounded="lg"
                :style="taskTypeChipStyle(task.taskType)"
                class="task-type-chip hs-text-2xs font-weight-semibold"
              >
                {{ task.taskType }}
              </v-chip>

              <v-tooltip
                v-if="
                  activeTab === 'quality' && (task.qualityRuleCount ?? 0) > 0
                "
                location="bottom"
                :open-delay="0"
                :close-delay="80"
                content-class="pa-0 ma-0 bg-transparent"
              >
                <template #activator="{ props: tooltipProps }">
                  <button
                    v-bind="tooltipProps"
                    type="button"
                    class="task-quality-summary hs-text-sm"
                  >
                    {{ qualityRuleCountLabel(task) }}
                  </button>
                </template>
                <v-card
                  elevation="2"
                  rounded="lg"
                  class="ma-0 pa-0"
                  style="max-width: 360px; min-width: 240px"
                >
                  <v-card-title class="px-4 py-2">
                    <div class="task-rules-title">
                      <span class="hs-text-md">Quality rules</span>
                      <v-chip
                        size="small"
                        color="teal-darken-1"
                        variant="tonal"
                      >
                        {{ qualityRuleCountLabel(task) }}
                      </v-chip>
                    </div>
                  </v-card-title>
                  <v-divider />
                  <v-card-text class="py-2 px-4">
                    <v-row dense>
                      <template
                        v-for="rule in task.qualityRuleBreakdown ?? []"
                        :key="rule.label"
                      >
                        <v-col cols="8" class="font-weight-medium">
                          {{ rule.label }}
                        </v-col>
                        <v-col cols="4">{{ rule.count }}</v-col>
                      </template>
                    </v-row>
                  </v-card-text>
                </v-card>
              </v-tooltip>
              <span
                v-else-if="activeTab === 'quality'"
                class="task-quality-empty"
              >
                No rules
              </span>

              <v-chip
                v-if="
                  activeTab === 'quality' &&
                  (task.monitoringRulesViolated ?? 0) > 0
                "
                color="red-darken-3"
                variant="tonal"
                size="small"
                rounded="lg"
                class="task-violation-chip font-weight-bold"
              >
                {{ task.monitoringRulesViolated }}
                {{
                  task.monitoringRulesViolated === 1
                    ? 'violation'
                    : 'violations'
                }}
              </v-chip>
              <span
                v-else-if="activeTab === 'quality'"
                class="task-quality-empty"
              >
                No violations
              </span>

              <v-chip
                v-if="task.noWorkWarning"
                size="x-small"
                density="comfortable"
                color="amber-darken-3"
                variant="tonal"
                :prepend-icon="mdiAlert"
                rounded="lg"
                class="task-no-work-chip hs-label"
                :title="task.noWorkWarning.message"
              >
                {{ task.noWorkWarning.label }}
              </v-chip>
            </div>
          </td>

          <td class="text-right task-actions-cell">
            <div class="task-actions">
              <v-tooltip location="top" :open-delay="0" :close-delay="0">
                <template #activator="{ props: tooltipProps }">
                  <span v-bind="tooltipProps" class="inline-flex">
                    <v-btn
                      variant="text"
                      size="small"
                      color="black"
                      icon
                      :disabled="pauseButtonDisabled(task)"
                      aria-label="Pause or resume task"
                      @click.stop="emit('toggle-paused', task)"
                    >
                      <NoScheduleIcon v-if="!task.schedule" />
                      <v-icon
                        v-else
                        :icon="task.schedule.enabled ? mdiPause : mdiPlay"
                        size="16"
                      />
                    </v-btn>
                  </span>
                </template>
                <span>{{ pauseTooltipText(task) }}</span>
              </v-tooltip>
              <v-btn
                v-if="canEdit && !task.userClickedRunNow"
                variant="outlined"
                color="green-darken-3"
                :prepend-icon="mdiPlay"
                class="task-action-button text-none"
                rounded="lg"
                @click.stop="emit('run-now', task)"
              >
                Run now
              </v-btn>
              <span
                v-else-if="canEdit && task.userClickedRunNow"
                class="hs-text-sm font-weight-semibold text-slate-500"
              >
                Run requested
              </span>
              <v-btn
                variant="text"
                size="small"
                :style="{ color: accent }"
                :append-icon="mdiChevronRight"
                class="text-none"
                @click.stop="emit('open-task', task)"
              >
                Details
              </v-btn>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { mdiAlert, mdiChevronRight, mdiPause, mdiPlay } from '@mdi/js'
import NoScheduleIcon from '@/components/Orchestration/shared/NoScheduleIcon.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import {
  DATA_PRODUCT_TYPE_OPTIONS,
  READ_ONLY_TOOLTIP,
  STATUS_OPTIONS,
  type DataProductTaskType,
  type TaskRow,
} from './orchestrationTabs'
import {
  qualityRuleCountLabel,
  taskStatusColor,
  taskStatusIcon,
  taskTypeChipStyle as getTaskTypeChipStyle,
} from './taskPresentation'
import TaskTableFilter from './TaskTableFilter.vue'

const props = defineProps<{
  tasks: TaskRow[]
  statusFilter: string[]
  taskTypeFilter: NonNullable<DataProductTaskType>[]
  canEdit: boolean
  accent: string
}>()

const emit = defineEmits<{
  'toggle-status': [status: string]
  'clear-status': []
  'toggle-task-type': [taskType: string]
  'clear-task-type': []
  'toggle-paused': [task: TaskRow]
  'run-now': [task: TaskRow]
  'open-task': [task: TaskRow]
}>()

const { activeTab } = storeToRefs(useOrchestrationStore())

const statusOptions = STATUS_OPTIONS.map((status) => ({
  ...status,
  icon: taskStatusIcon(status.value),
  color: taskStatusColor(status.value),
}))

const taskTypeOptions = DATA_PRODUCT_TYPE_OPTIONS.map((taskType) => ({
  title: taskType,
  value: taskType,
}))

const taskTypeChipStyle = (taskType: DataProductTaskType) =>
  getTaskTypeChipStyle(taskType)

const pauseButtonDisabled = (task: TaskRow) => !props.canEdit || !task.schedule

const pauseTooltipText = (task: TaskRow) => {
  if (!props.canEdit) return READ_ONLY_TOOLTIP
  if (!task.schedule) return 'This task has no schedule configured.'
  return task.schedule.enabled ? 'Pause task' : 'Resume task'
}
</script>

<style scoped>
.task-table-shell {
  height: auto;
  max-height: 100%;
  min-height: 0;
  overflow: auto;
}

.task-table {
  width: 100%;
  min-width: 100%;
  height: auto;
  border-collapse: collapse;
  table-layout: auto;
}

.task-table thead th {
  height: 48px;
  padding: var(--hs-space-8) var(--hs-space-12);
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-regular);
  text-transform: none;
  letter-spacing: 0;
  background: var(--hs-surface-muted);
  border: 0;
}

.task-table thead tr,
.task-table tbody tr {
  border-bottom: 1px solid var(--hs-border);
}

.task-table tbody tr:hover {
  background: var(--hs-surface-muted);
}

.task-main-header {
  text-align: left;
}

.task-header-filters {
  display: flex;
  gap: var(--hs-space-8);
  align-items: center;
}

.task-status-cell {
  width: 32px;
  padding: var(--hs-space-12) 0 var(--hs-space-12) var(--hs-space-12);
  vertical-align: top;
}

.task-summary-cell {
  padding: var(--hs-space-12) var(--hs-space-12) var(--hs-space-12) 4px;
  vertical-align: top;
}

.task-actions-cell {
  width: 1%;
  padding: var(--hs-space-12);
  vertical-align: top;
  white-space: nowrap;
}

.task-name {
  color: var(--hs-text-primary);
  font-size: var(--hs-font-md);
  font-weight: var(--hs-font-weight-semibold);
  line-height: 1.3;
}

.task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-6);
  align-items: center;
  margin-top: var(--hs-space-4);
  color: var(--hs-text-secondary);
}

.task-meta-label {
  color: var(--hs-text-secondary);
}

.task-time {
  color: var(--hs-text-secondary);
  font-family: var(--hs-font-data);
  white-space: nowrap;
}

.task-status-icon {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.task-quality-summary {
  padding: 0;
  color: var(--hs-text-secondary);
  font-weight: var(--hs-font-weight-semibold);
  cursor: default;
  background: transparent;
  border: 0;
  border-bottom: 1px dotted var(--hs-text-muted);
}

.task-quality-empty {
  color: var(--hs-text-muted);
}

.task-rules-title {
  display: flex;
  gap: var(--hs-space-12);
  align-items: center;
  justify-content: space-between;
}

.task-actions {
  display: flex;
  gap: var(--hs-space-6);
  align-items: center;
  justify-content: flex-end;
}

.task-action-button {
  min-height: 32px;
  padding-inline: var(--hs-space-12);
}
</style>
