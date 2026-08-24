<template>
  <div class="hs-table-card ingestion-table-shell">
    <table class="ingestion-table hs-text-sm">
      <thead>
        <tr>
          <th colspan="2" class="ingestion-main-header">
            <TaskTableFilter
              label="Status"
              title="Filter by status"
              :options="statusOptions"
              :selected="statusFilter"
              @toggle="emit('toggle-status', $event)"
              @clear="emit('clear-status')"
            />
          </th>
          <th class="text-right" />
        </tr>
      </thead>
      <tbody>
        <tr v-for="task in tasks" :key="task.id">
          <td class="ingestion-status-cell">
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
          <td class="ingestion-task-cell">
            <div class="ingestion-task-name">{{ task.name || '—' }}</div>
            <div class="ingestion-task-meta hs-text-sm">
              <span class="ingestion-task-meta-label hs-label">Last</span>
              <span>{{ task.lastRun }}</span>
              <span aria-hidden="true">·</span>
              <span class="ingestion-task-meta-label hs-label">Next</span>
              <span>{{ task.nextRun }}</span>
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
          <td class="text-right ingestion-actions-cell">
            <div class="task-actions">
              <v-btn
                variant="text"
                size="small"
                color="black"
                icon
                :disabled="!canEdit || !task.schedule"
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
import { mdiAlert, mdiChevronRight, mdiPause, mdiPlay } from '@mdi/js'
import NoScheduleIcon from '@/components/Orchestration/shared/NoScheduleIcon.vue'
import { STATUS_OPTIONS, type TaskRow } from './orchestrationTabs'
import { taskStatusColor, taskStatusIcon } from './taskPresentation'
import TaskTableFilter from './TaskTableFilter.vue'

defineProps<{
  tasks: TaskRow[]
  statusFilter: string[]
  canEdit: boolean
  accent: string
}>()

const emit = defineEmits<{
  'toggle-status': [status: string]
  'clear-status': []
  'toggle-paused': [task: TaskRow]
  'run-now': [task: TaskRow]
  'open-task': [task: TaskRow]
}>()

const statusOptions = STATUS_OPTIONS.map((status) => ({
  ...status,
  icon: taskStatusIcon(status.value),
  color: taskStatusColor(status.value),
}))
</script>

<style scoped>
.ingestion-table-shell {
  height: auto;
  max-height: 100%;
  min-height: 0;
  overflow: auto;
}

.ingestion-table {
  width: 100%;
  min-width: 100%;
  height: auto;
  border-collapse: collapse;
  table-layout: auto;
}

.ingestion-table thead th {
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

.ingestion-table thead tr,
.ingestion-table tbody tr {
  border-bottom: 1px solid var(--hs-border);
}

.ingestion-table tbody tr:hover {
  background: var(--hs-surface-muted);
}

.ingestion-main-header {
  text-align: left;
}

.ingestion-status-cell {
  width: 32px;
  padding: var(--hs-space-12) 0 var(--hs-space-12) var(--hs-space-12);
  vertical-align: top;
}

.ingestion-task-cell {
  padding: var(--hs-space-12) var(--hs-space-12) var(--hs-space-12) 4px;
  vertical-align: top;
}

.ingestion-actions-cell {
  width: 1%;
  padding: var(--hs-space-12);
  vertical-align: top;
  white-space: nowrap;
}

.ingestion-task-name {
  color: var(--hs-text-primary);
  font-size: var(--hs-font-md);
  font-weight: var(--hs-font-weight-semibold);
  line-height: 1.3;
}

.ingestion-task-meta {
  display: flex;
  gap: var(--hs-space-6);
  align-items: center;
  margin-top: var(--hs-space-4);
  color: var(--hs-text-secondary);
}

.ingestion-task-meta-label {
  color: var(--hs-text-secondary);
}

.task-status-icon {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  line-height: 1;
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
