<template>
  <v-data-table-virtual
    :headers="tableHeaders"
    :items="tasks"
    :sort-by="defaultSortBy"
    item-value="id"
    multi-sort
    fixed-header
    hover
    class="task-table hs-table-card hs-text-sm"
    density="compact"
  >
    <template #header.name><div>Task name</div></template>
    <template #header.statusSort>
      <TaskTableFilter
        label="Status"
        title="Filter by status"
        :options="statusOptions"
        :selected="statusFilter"
        @toggle="emit('toggle-status', $event)"
        @clear="emit('clear-status')"
      />
    </template>
    <template #header.taskType>
      <TaskTableFilter
        label="Type"
        title="Filter by task type"
        :options="taskTypeOptions"
        :selected="taskTypeFilter"
        @toggle="emit('toggle-task-type', $event)"
        @clear="emit('clear-task-type')"
      />
    </template>
    <template #header.actions><div>Actions</div></template>

    <template #item.name="{ item }">
      <span class="task-name font-weight-medium">{{ item.name || '—' }}</span>
    </template>

    <template #item.statusSort="{ item }">
      <div class="task-status-cell">
        <div class="task-run-cell">
          <v-tooltip
            location="bottom"
            :open-delay="0"
            :close-delay="80"
            content-class="pa-0 ma-0 bg-transparent"
            max-width="640"
          >
            <template #activator="{ props: tooltipProps }">
              <span
                v-bind="tooltipProps"
                class="task-status-icon"
                :style="{ color: taskStatusColor(item.statusSort) }"
                :aria-label="item.statusSort"
              >
                <v-icon :icon="taskStatusIcon(item.statusSort)" size="20" />
              </span>
            </template>
            <v-card
              elevation="6"
              rounded="lg"
              class="ma-0 pa-0 border border-slate-200"
              style="max-width: 560px; min-width: 360px"
            >
              <v-card-text class="px-4 py-3">
                <div
                  class="mb-1 hs-label uppercase tracking-[0.12em] text-slate-600"
                >
                  Last run summary
                </div>
                <div
                  class="hs-text-md font-weight-semibold leading-snug text-slate-900"
                >
                  {{ item.lastRunMessage || 'No run history available yet.' }}
                </div>
                <div
                  class="mt-3 flex items-center gap-1.5 hs-text-sm font-weight-semibold text-slate-500"
                >
                  <v-icon
                    :icon="taskStatusIcon(item.statusSort)"
                    size="14"
                    :style="{ color: taskStatusColor(item.statusSort) }"
                  />
                  <span>{{ item.statusSort }}</span>
                </div>
              </v-card-text>
            </v-card>
          </v-tooltip>
          <div class="task-run-times">
            <div class="task-run-time">
              <span class="task-run-label hs-label">Last</span>
              <span class="task-time hs-text-sm">{{ item.lastRun }}</span>
            </div>
            <div class="task-run-time">
              <span class="task-run-label hs-label">Next</span>
              <span class="task-time hs-text-sm">{{ item.nextRun }}</span>
            </div>
          </div>
        </div>
        <v-tooltip
          v-if="item.noWorkWarning"
          location="top"
          :open-delay="0"
          :close-delay="80"
          content-class="pa-0 ma-0 bg-transparent"
          max-width="320"
        >
          <template #activator="{ props: tooltipProps }">
            <v-chip
              v-bind="tooltipProps"
              size="x-small"
              density="comfortable"
              color="amber-darken-3"
              variant="tonal"
              :prepend-icon="mdiAlert"
              rounded="lg"
              class="task-no-work-chip hs-label"
            >
              {{ item.noWorkWarning.label }}
            </v-chip>
          </template>
          <v-card
            elevation="6"
            rounded="lg"
            class="ma-0 pa-0 border border-slate-200"
            style="max-width: 320px"
          >
            <v-card-text
              class="px-4 py-3 hs-text-sm leading-snug text-slate-800"
            >
              {{ item.noWorkWarning.message }}
            </v-card-text>
          </v-card>
        </v-tooltip>
      </div>
    </template>

    <template #item.lastRunAt="{ item }">
      <span class="task-time hs-text-sm">{{ item.lastRun }}</span>
    </template>

    <template #item.nextRunAt="{ item }">
      <span class="task-time hs-text-sm">{{ item.nextRun }}</span>
    </template>

    <template #item.taskType="{ item }">
      <v-chip
        v-if="item.taskType"
        density="comfortable"
        size="small"
        rounded="lg"
        :style="taskTypeChipStyle(item.taskType)"
        class="task-type-chip hs-text-2xs font-weight-semibold"
      >
        {{ item.taskType }}
      </v-chip>
      <span v-else class="text-slate-400">—</span>
    </template>

    <template #item.qualityRuleSummary="{ item }">
      <v-tooltip
        v-if="(item.qualityRuleCount ?? 0) > 0"
        location="bottom"
        :open-delay="0"
        :close-delay="80"
        content-class="pa-0 ma-0 bg-transparent"
      >
        <template #activator="{ props: tooltipProps }">
          <span
            v-bind="tooltipProps"
            class="task-rules-count hs-text-sm font-weight-semibold"
          >
            {{ qualityRuleCountLabel(item) }}
          </span>
        </template>

        <v-card
          elevation="2"
          rounded="lg"
          class="ma-0 pa-0"
          style="max-width: 360px; min-width: 240px"
        >
          <v-card-title class="px-4 py-2">
            <v-row no-gutters align="center" style="width: 100%">
              <v-col>
                <div
                  class="hs-text-md"
                  style="white-space: normal; word-break: break-word"
                >
                  Quality rules
                </div>
              </v-col>
              <v-col cols="auto">
                <v-chip size="small" color="teal-darken-1" variant="tonal">
                  {{ qualityRuleCountLabel(item) }}
                </v-chip>
              </v-col>
            </v-row>
          </v-card-title>

          <v-divider />

          <v-card-text class="py-2 px-4">
            <v-row dense>
              <template
                v-for="rule in item.qualityRuleBreakdown ?? []"
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
      <span v-else class="text-slate-400">No rules</span>
    </template>

    <template #item.monitoringRulesViolated="{ item }">
      <v-chip
        v-if="(item.monitoringRulesViolated ?? 0) > 0"
        color="red-darken-3"
        variant="tonal"
        size="small"
        rounded="lg"
        class="task-violation-chip font-weight-bold"
      >
        {{ item.monitoringRulesViolated }}
        {{ item.monitoringRulesViolated === 1 ? 'rule' : 'rules' }}
      </v-chip>
      <span v-else class="text-slate-400">None</span>
    </template>

    <template #item.actions="{ item }">
      <div class="task-actions">
        <v-tooltip location="top" :open-delay="0" :close-delay="0">
          <template #activator="{ props: tooltipProps }">
            <span v-bind="tooltipProps" class="inline-flex">
              <v-btn
                variant="text"
                size="small"
                color="black"
                icon
                :disabled="pauseButtonDisabled(item)"
                aria-label="Pause or resume task"
                @click.stop="emit('toggle-paused', item)"
              >
                <NoScheduleIcon v-if="!item.schedule" />
                <v-icon
                  v-else
                  :icon="item.schedule.enabled ? mdiPause : mdiPlay"
                  size="16"
                />
              </v-btn>
            </span>
          </template>
          <span>{{ pauseTooltipText(item) }}</span>
        </v-tooltip>
        <v-btn
          v-if="canEdit && !item.userClickedRunNow"
          variant="outlined"
          color="green-darken-3"
          :prepend-icon="mdiPlay"
          class="task-action-button text-none"
          rounded="lg"
          @click.stop="emit('run-now', item)"
        >
          Run now
        </v-btn>
        <span
          v-else-if="canEdit && item.userClickedRunNow"
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
          @click.stop="emit('open-task', item)"
        >
          Details
        </v-btn>
      </div>
    </template>
  </v-data-table-virtual>
</template>

<script setup lang="ts">
import { computed } from 'vue'
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
const defaultSortBy = [{ key: 'name', order: 'asc' }] as const

const statusOptions = STATUS_OPTIONS.map((status) => ({
  ...status,
  icon: taskStatusIcon(status.value),
  color: taskStatusColor(status.value),
}))

const taskTypeOptions = DATA_PRODUCT_TYPE_OPTIONS.map((taskType) => ({
  title: taskType,
  value: taskType,
}))

const tableHeaders = computed(() => {
  const headers = [
    { title: 'Task name', key: 'name' },
    { title: 'Status', key: 'statusSort' },
  ]

  if (activeTab.value === 'aggregation') {
    headers.push({ title: 'Type', key: 'taskType' })
  }

  if (activeTab.value === 'quality') {
    headers.push(
      { title: 'Rules', key: 'qualityRuleSummary' },
      { title: 'Violations', key: 'monitoringRulesViolated' }
    )
  }

  headers.push({
    title: 'Actions',
    key: 'actions',
    align: 'end',
    sortable: false,
  } as any)

  return headers
})

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
.task-table {
  height: 100%;
}

.task-table :deep(.v-table__wrapper) {
  max-height: 100%;
}

.task-table :deep(thead tr) {
  border-bottom: 1px solid var(--hs-border);
}

.task-table :deep(th) {
  padding: var(--hs-space-8) var(--hs-space-12);
  color: var(--hs-text-secondary);
  font-size: var(--hs-font-sm);
  font-weight: var(--hs-font-weight-regular);
  text-align: left;
  text-transform: none;
  letter-spacing: 0;
  background: var(--hs-surface-muted);
}

.task-table :deep(tbody tr) {
  border-bottom: 1px solid var(--hs-border);
}

.task-table :deep(tbody tr:hover) {
  background: var(--hs-surface-muted);
}

.task-table :deep(td) {
  padding: 13px var(--hs-space-12);
}

.task-name {
  color: var(--hs-text-primary);
}

.task-status-cell {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-4);
  align-items: flex-start;
}

.task-run-cell,
.task-status-icon,
.task-actions {
  display: inline-flex;
  align-items: center;
}

.task-run-cell {
  gap: var(--hs-space-8);
  min-width: 0;
}

.task-status-icon {
  flex: 0 0 auto;
  justify-content: center;
  line-height: 1;
}

.task-run-times {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  min-width: 0;
}

.task-run-time {
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr);
  gap: 0.35rem;
  align-items: baseline;
  line-height: 1.15;
}

.task-time {
  color: var(--hs-text-secondary);
  font-family: var(--hs-font-data);
  line-height: 1.15;
  white-space: nowrap;
}

.task-run-label {
  color: var(--hs-text-muted);
  line-height: 1.15;
  text-transform: uppercase;
}

.task-rules-count {
  max-width: 320px;
  color: var(--hs-text-secondary);
  white-space: nowrap;
  cursor: default;
}

.task-actions {
  justify-content: flex-end;
  gap: var(--hs-space-6);
}

.task-action-button {
  min-height: 32px;
  padding-inline: var(--hs-space-12);
}
</style>
