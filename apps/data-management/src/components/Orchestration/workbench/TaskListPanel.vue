<template>
  <section class="detail">
    <header class="detail-header">
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="detail-title">{{ detailTitle }}</h2>
          <span
            v-if="detailTypeBadge"
            class="detail-badge"
            :style="{ color: accent, background: accentLight }"
          >
            {{ detailTypeBadge }}
          </span>
        </div>
        <div class="detail-subtitle">
          <HealthPills :tasks="visibleTasks" />
        </div>
      </div>
      <div class="detail-actions">
        <template v-if="activeTab === 'ingestion' && selectedConnection">
          <v-tooltip location="top" :disabled="canEdit">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn
                  variant="flat"
                  :prepend-icon="mdiPlus"
                  :style="{ background: accent, color: 'white' }"
                  :disabled="!canEdit"
                  class="detail-action-btn detail-action-btn--primary text-none"
                  rounded="lg"
                  @click="$emit('add-task')"
                >
                  Add task
                </v-btn>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
        </template>
        <template v-else-if="activeTab === 'aggregation'">
          <v-tooltip location="top" :disabled="canEdit">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn
                  variant="outlined"
                  class="detail-action-btn detail-action-btn--header text-none"
                  :style="{ color: '#1565C0', borderColor: '#1565C0' }"
                  :disabled="!canEdit"
                  rounded="lg"
                  @click="$emit('add-aggregation')"
                >
                  + Aggregation
                </v-btn>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
          <v-tooltip location="top" :disabled="canEdit">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn
                  variant="outlined"
                  class="detail-action-btn detail-action-btn--header text-none"
                  :style="{ color: '#1565C0', borderColor: '#1565C0' }"
                  :disabled="!canEdit"
                  rounded="lg"
                  @click="$emit('add-expression')"
                >
                  + Expression
                </v-btn>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
          <v-tooltip location="top" :disabled="canEdit">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn
                  variant="outlined"
                  class="detail-action-btn detail-action-btn--header text-none"
                  :style="{ color: '#1565C0', borderColor: '#1565C0' }"
                  :disabled="!canEdit"
                  rounded="lg"
                  @click="$emit('add-derivation')"
                >
                  + Derivation
                </v-btn>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
          <v-tooltip location="top" :disabled="canEdit">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn
                  variant="outlined"
                  class="detail-action-btn detail-action-btn--header text-none"
                  :style="{ color: '#1565C0', borderColor: '#1565C0' }"
                  :disabled="!canEdit"
                  rounded="lg"
                  @click="$emit('add-rating-curve')"
                >
                  + Rating curve
                </v-btn>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
        </template>
        <template v-else-if="activeTab === 'quality'">
          <v-tooltip location="top" :disabled="canEdit">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn
                  variant="flat"
                  :prepend-icon="mdiPlus"
                  :style="{ background: accent, color: 'white' }"
                  :disabled="!canEdit"
                  class="detail-action-btn detail-action-btn--primary text-none"
                  rounded="lg"
                  @click="$emit('add-quality')"
                >
                  Add quality task
                </v-btn>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
        </template>
      </div>
    </header>

    <div
      v-if="hasSelection && visibleTasks.length > 0"
      class="detail-filterbar"
    >
      <v-text-field
        :model-value="taskSearch"
        :prepend-inner-icon="mdiMagnify"
        placeholder="Search tasks"
        hide-details
        clearable
        density="compact"
        variant="outlined"
        class="detail-search"
        @update:model-value="taskSearch = $event ?? ''"
      />
      <v-autocomplete
        :model-value="statusFilter"
        :items="STATUS_OPTIONS"
        item-title="title"
        item-value="value"
        label="Status filters"
        multiple
        clearable
        hide-details
        density="compact"
        variant="outlined"
        :prepend-inner-icon="mdiFilterVariant"
        autocomplete="off"
        name="orchestration-status-filter"
        spellcheck="false"
        class="detail-status-filter"
        @update:model-value="statusFilter = $event ?? []"
      >
        <template #selection="{ item, index }">
          <v-chip
            color="primary-lighten-2"
            rounded
            density="comfortable"
            closable
            class="mr-1"
            @click:close="removeStatusFilter(index)"
          >
            <span>{{ item.title }}</span>
          </v-chip>
        </template>
      </v-autocomplete>
      <v-autocomplete
        v-if="activeTab === 'aggregation'"
        :model-value="taskTypeFilter"
        :items="DATA_PRODUCT_TYPE_OPTIONS"
        label="Task type filters"
        multiple
        clearable
        hide-details
        density="compact"
        variant="outlined"
        :prepend-inner-icon="mdiFilterVariant"
        autocomplete="off"
        name="orchestration-task-type-filter"
        spellcheck="false"
        class="detail-task-type-filter"
        @update:model-value="taskTypeFilter = $event ?? []"
      >
        <template #selection="{ item, index }">
          <v-chip
            rounded="lg"
            density="comfortable"
            closable
            class="mr-1 task-type-chip"
            :style="taskTypeSelectionStyle(item.title)"
            @click:close="removeTaskTypeFilter(index)"
          >
            <span>{{ item.title }}</span>
          </v-chip>
        </template>
      </v-autocomplete>
    </div>

    <div class="detail-body">
      <div v-if="loading" class="detail-loading">
        <v-progress-circular
          indeterminate
          size="22"
          width="2"
          color="blue-grey-darken-1"
        />
        <span>Loading…</span>
      </div>

      <div v-else-if="!hasSelection" class="detail-empty">
        <h4>{{ emptyHeading }}</h4>
        <p>{{ emptyMessage }}</p>
      </div>

      <div v-else-if="visibleTasks.length === 0" class="detail-empty">
        <h4>No tasks</h4>
        <p>{{ emptyTasksMessage }}</p>
      </div>

      <div v-else-if="sortedVisibleTasks.length === 0" class="detail-empty">
        <h4>No tasks match your filter</h4>
        <p>Clear search, status, or task type filters to see all tasks.</p>
      </div>

      <v-data-table
        v-else
        :headers="tableHeaders"
        :items="sortedVisibleTasks"
        :sort-by="defaultSortBy"
        item-value="id"
        multi-sort
        fixed-header
        hover
        hide-default-footer
        :items-per-page="-1"
        class="tasks-table"
        density="compact"
      >
        <template #item.name="{ item }">
          <span class="task-name">{{ item.name || '—' }}</span>
        </template>

        <template #item.statusSort="{ item }">
          <div v-if="activeTab === 'quality'" class="quality-run-stack">
            <v-tooltip
              location="bottom"
              :open-delay="0"
              :close-delay="80"
              content-class="pa-0 ma-0 bg-transparent"
              max-width="520"
            >
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <TaskStatus :status="item.statusSort" :paused="false" />
                </span>
              </template>
              <v-card
                elevation="6"
                rounded="lg"
                class="ma-0 pa-0 border border-slate-200"
                style="max-width: 520px"
              >
                <v-card-text class="px-4 py-3">
                  <div class="mb-1 flex items-center justify-between gap-3">
                    <div
                      class="text-[0.7rem] font-extrabold uppercase tracking-[0.12em] text-slate-600"
                    >
                      Last run summary
                    </div>
                    <div
                      v-if="item.lastRun && item.lastRun !== '-'"
                      class="text-xs font-medium text-slate-500"
                    >
                      {{ item.lastRun }}
                    </div>
                  </div>
                  <div class="text-sm leading-snug text-slate-800">
                    {{ item.lastRunMessage || 'No run history available yet.' }}
                  </div>
                </v-card-text>
              </v-card>
            </v-tooltip>
            <div class="quality-run-time">
              <span class="quality-run-label">Last</span>
              <span class="task-time">{{ item.lastRun }}</span>
            </div>
            <div class="quality-run-time">
              <span class="quality-run-label">Next</span>
              <span class="task-time">{{ item.nextRun }}</span>
            </div>
          </div>
          <v-tooltip
            v-else
            location="bottom"
            :open-delay="0"
            :close-delay="80"
            content-class="pa-0 ma-0 bg-transparent"
            max-width="520"
          >
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <TaskStatus :status="item.statusSort" :paused="false" />
              </span>
            </template>
            <v-card
              elevation="6"
              rounded="lg"
              class="ma-0 pa-0 border border-slate-200"
              style="max-width: 520px"
            >
              <v-card-text class="px-4 py-3">
                <div class="mb-1 flex items-center justify-between gap-3">
                  <div
                    class="text-[0.7rem] font-extrabold uppercase tracking-[0.12em] text-slate-600"
                  >
                    Last run summary
                  </div>
                  <div
                    v-if="item.lastRun && item.lastRun !== '-'"
                    class="text-xs font-medium text-slate-500"
                  >
                    {{ item.lastRun }}
                  </div>
                </div>
                <div class="text-sm leading-snug text-slate-800">
                  {{ item.lastRunMessage || 'No run history available yet.' }}
                </div>
              </v-card-text>
            </v-card>
          </v-tooltip>
        </template>

        <template #item.lastRunAt="{ item }">
          <span class="task-time">{{ item.lastRun }}</span>
        </template>

        <template #item.nextRunAt="{ item }">
          <span class="task-time">{{ item.nextRun }}</span>
        </template>

        <template #item.taskType="{ item }">
          <v-chip
            v-if="item.taskType"
            density="comfortable"
            size="small"
            rounded="lg"
            :style="typeChipStyle(item.taskType)"
            class="task-type-chip"
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
              <span v-bind="tooltipProps" class="task-rules-count">
                {{ ruleCountLabel(item) }}
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
                      class="text-h6"
                      style="white-space: normal; word-break: break-word"
                    >
                      Quality rules
                    </div>
                  </v-col>
                  <v-col cols="auto">
                    <v-chip size="small" color="teal-darken-1" variant="tonal">
                      {{ ruleCountLabel(item) }}
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
                    <v-col cols="4">
                      {{ rule.count }}
                    </v-col>
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
            class="task-violation-chip"
          >
            {{ item.monitoringRulesViolated }} rule{{
              item.monitoringRulesViolated === 1 ? '' : 's'
            }}
          </v-chip>
          <span v-else class="text-slate-400">None</span>
        </template>

        <template #item.actions="{ item }">
          <div class="task-actions-inner">
            <v-tooltip location="top" :open-delay="0" :close-delay="0">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn
                    variant="text"
                    size="small"
                    color="black"
                    icon
                    :disabled="pauseButtonDisabled(item)"
                    class="task-pause-btn"
                    aria-label="Pause or resume task"
                    @click.stop="$emit('toggle-paused', item)"
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
              class="detail-action-btn detail-action-btn--compact text-none"
              rounded="lg"
              @click.stop="$emit('run-now', item)"
            >
              Run now
            </v-btn>
            <span
              v-else-if="canEdit && item.userClickedRunNow"
              class="text-xs font-semibold text-slate-500"
            >
              Run requested
            </span>
            <v-btn
              variant="text"
              size="small"
              :style="{ color: accent }"
              :append-icon="mdiChevronRight"
              class="text-none"
              @click.stop="$emit('open-task', item)"
            >
              Details
            </v-btn>
          </div>
        </template>
      </v-data-table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import {
  mdiChevronRight,
  mdiFilterVariant,
  mdiMagnify,
  mdiPause,
  mdiPlay,
  mdiPlus,
} from '@mdi/js'
import type { DataConnection } from '@hydroserver/client'
import { useOrchestrationStore } from '@/store/orchestration'
import TaskStatus from '@/components/Orchestration/shared/TaskStatus.vue'
import HealthPills from '@/components/Orchestration/shared/HealthPills.vue'
import NoScheduleIcon from '@/components/Orchestration/shared/NoScheduleIcon.vue'
import {
  DATA_PRODUCT_TYPE_OPTIONS,
  READ_ONLY_TOOLTIP,
  STATUS_OPTIONS,
  TAB_META,
  getDataProductTypeColors,
  type DataProductTaskType,
  type TaskRow,
} from './orchestrationTabs'

const typeChipStyle = (taskType: DataProductTaskType) => {
  const colors = getDataProductTypeColors(taskType)
  if (!colors) return {}
  return { background: colors.bg, color: colors.text }
}

const taskTypeSelectionStyle = (taskType: unknown) =>
  typeChipStyle(taskType as DataProductTaskType)

const {
  activeTab,
  orchestrationSearch: taskSearch,
  orchestrationStatusFilter: statusFilter,
  orchestrationTaskTypeFilter: taskTypeFilter,
} = storeToRefs(useOrchestrationStore())

const accent = computed(() => TAB_META[activeTab.value].accent)
const accentLight = computed(() => TAB_META[activeTab.value].accentLight)
const defaultSortBy = [{ key: 'name', order: 'asc' }] as const
const tableHeaders = computed(() => {
  const headers = [
    { title: 'Task name', key: 'name' },
  ]

  if (activeTab.value === 'quality') {
    headers.push({ title: 'Run status', key: 'statusSort' })
  } else {
    headers.push(
      { title: 'Status', key: 'statusSort' },
      { title: 'Last run', key: 'lastRunAt' },
      { title: 'Next run', key: 'nextRunAt' }
    )
  }

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

const props = defineProps<{
  canEdit: boolean
  loading: boolean
  hasSelection: boolean
  detailTitle: string
  detailTypeBadge: string
  selectedConnection: DataConnection | null
  visibleTasks: TaskRow[]
  sortedVisibleTasks: TaskRow[]
  emptyHeading: string
  emptyMessage: string
  emptyTasksMessage: string
}>()

defineEmits<{
  (e: 'toggle-paused', row: TaskRow): void
  (e: 'run-now', row: TaskRow): void
  (e: 'open-task', row: TaskRow): void
  (e: 'add-task'): void
  (e: 'add-aggregation'): void
  (e: 'add-expression'): void
  (e: 'add-derivation'): void
  (e: 'add-rating-curve'): void
  (e: 'add-quality'): void
}>()

const removeStatusFilter = (index: number) => {
  const next = [...statusFilter.value]
  next.splice(index, 1)
  statusFilter.value = next
}

const removeTaskTypeFilter = (index: number) => {
  const next = [...taskTypeFilter.value]
  next.splice(index, 1)
  taskTypeFilter.value = next
}

const ruleCountLabel = (item: TaskRow) => {
  const count = item.qualityRuleCount ?? 0
  return `${count} rule${count === 1 ? '' : 's'}`
}

const pauseButtonDisabled = (item: TaskRow) => !props.canEdit || !item.schedule

const pauseTooltipText = (item: TaskRow) => {
  if (!props.canEdit) return READ_ONLY_TOOLTIP
  if (!item.schedule) return 'This task has no schedule configured.'
  return item.schedule.enabled ? 'Pause task' : 'Resume task'
}
</script>

<style scoped>
.detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: white;
  min-width: 0;
}
.detail-header {
  padding: 12px 22px;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  gap: 12px;
  background: white;
  flex-shrink: 0;
}
.detail-title {
  font-size: 17px;
  font-weight: 400;
  color: #1c1b1f;
}
.detail-badge {
  font-size: 10px;
  border-radius: 4px;
  padding: 2px 7px;
  font-weight: 700;
}
.detail-subtitle {
  margin-top: 4px;
}
.detail-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}
.detail-action-btn {
  min-height: 40px;
}
.detail-action-btn--header {
  min-height: 34px;
  padding-inline: 14px;
  font-size: 13px;
  font-weight: 600;
}
.detail-action-btn--primary {
  padding-inline: 20px;
}
.detail-action-btn--compact {
  min-height: 32px;
  padding-inline: 12px;
}
.detail-filterbar {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 10px 22px;
  border-bottom: 1px solid #eef1f5;
  background: white;
}
.detail-search {
  max-width: 260px;
}
.detail-status-filter {
  max-width: 320px;
}
.detail-task-type-filter {
  max-width: 300px;
}
.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px;
}
.detail-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 0;
  color: #475569;
  font-size: 13px;
}
.detail-empty {
  padding: 40px 20px;
  text-align: center;
  color: #475569;
}
.detail-empty h4 {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 6px;
}
.tasks-table {
  font-size: 13px;
}
.tasks-table :deep(thead tr) {
  border-bottom: 2px solid #ebebeb;
}
.tasks-table :deep(th) {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 10.5px;
  color: #49454f;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.tasks-table :deep(tbody tr) {
  border-bottom: 1px solid #f0f0f0;
}
.tasks-table :deep(tbody tr:hover) {
  background: #f5f7fa;
}
.task-name {
  font-weight: 500;
  color: #1c1b1f;
}
.task-time {
  color: #49454f;
  font-size: 12px;
  font-family: 'Roboto Mono', monospace;
  white-space: nowrap;
}
.tasks-table :deep(td) {
  padding: 13px 12px;
}
.task-rules-count {
  color: #475569;
  cursor: default;
  font-size: 13px;
  font-weight: 600;
  max-width: 320px;
  white-space: nowrap;
}
.task-violation-chip {
  font-weight: 700;
}
.quality-run-stack {
  align-items: flex-start;
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  min-width: 11rem;
  padding-block: 0.35rem 0.2rem;
}
.quality-run-stack :deep(.v-chip) {
  margin-bottom: 0.08rem !important;
}
.quality-run-time {
  align-items: baseline;
  display: grid;
  gap: 0.35rem;
  grid-template-columns: 2rem minmax(0, 1fr);
  line-height: 1.15;
}
.quality-run-time .task-time {
  line-height: 1.15;
}
.quality-run-label {
  color: #64748b;
  font-size: 0.68rem;
  font-weight: 700;
  line-height: 1.15;
  text-transform: uppercase;
}
.task-type-chip {
  font-size: 11px;
  font-weight: 600;
}
.task-actions-inner {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}
.task-pause-btn {
  align-self: center;
}
</style>
