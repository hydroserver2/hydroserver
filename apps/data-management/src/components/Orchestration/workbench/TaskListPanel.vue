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
        @update:model-value="$emit('update:taskSearch', $event ?? '')"
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
        @update:model-value="$emit('update:statusFilter', $event ?? [])"
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
        <p>Clear search or status filters to see all tasks.</p>
      </div>

      <table v-else class="tasks-table">
        <thead>
          <tr>
            <th v-for="col in sortableColumns" :key="col.key">
              <button
                type="button"
                class="th-sort"
                @click="$emit('toggle-sort', col.key)"
              >
                {{ col.label }}
                <v-icon :icon="sortIcon(col.key)" size="14" />
              </button>
            </th>
            <th v-if="activeTab === 'aggregation'">Type</th>
            <th v-if="activeTab === 'quality'">Rules</th>
            <th v-if="activeTab === 'quality'">Violations</th>
            <th class="text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in sortedVisibleTasks" :key="row.id">
            <td class="task-name">{{ row.name || '—' }}</td>
            <td>
              <v-tooltip
                location="bottom"
                :open-delay="0"
                :close-delay="80"
                content-class="pa-0 ma-0 bg-transparent"
                max-width="520"
              >
                <template #activator="{ props: tooltipProps }">
                  <span v-bind="tooltipProps" class="inline-flex">
                    <TaskStatus :status="row.statusSort" :paused="false" />
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
                        v-if="row.lastRun && row.lastRun !== '-'"
                        class="text-xs font-medium text-slate-500"
                      >
                        {{ row.lastRun }}
                      </div>
                    </div>
                    <div class="text-sm leading-snug text-slate-800">
                      {{
                        row.lastRunMessage || 'No run history available yet.'
                      }}
                    </div>
                  </v-card-text>
                </v-card>
              </v-tooltip>
            </td>
            <td class="task-time">{{ row.lastRun }}</td>
            <td class="task-time">{{ row.nextRun }}</td>
            <td v-if="activeTab === 'aggregation'" class="task-type">
              <v-chip
                v-if="row.taskType"
                density="comfortable"
                size="small"
                rounded="lg"
                :style="typeChipStyle(row.taskType)"
                class="task-type-chip"
              >
                {{ row.taskType }}
              </v-chip>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td v-if="activeTab === 'quality'" class="task-rules">
              {{ row.qualityRuleSummary || 'No rules' }}
            </td>
            <td v-if="activeTab === 'quality'" class="task-violations">
              <v-chip
                v-if="(row.monitoringRulesViolated ?? 0) > 0"
                color="red-darken-3"
                variant="tonal"
                size="small"
                rounded="lg"
                class="task-violation-chip"
              >
                {{ row.monitoringRulesViolated }} rule{{
                  row.monitoringRulesViolated === 1 ? '' : 's'
                }}
              </v-chip>
              <span v-else class="text-slate-400">None</span>
            </td>
            <td class="task-actions">
              <div class="task-actions-inner">
                <v-tooltip location="top" :open-delay="0" :close-delay="0">
                  <template #activator="{ props: tooltipProps }">
                    <span v-bind="tooltipProps" class="inline-flex">
                      <v-btn
                        variant="text"
                        size="small"
                        color="black"
                        :icon="row.schedule?.enabled ? mdiPause : mdiPlay"
                        :disabled="!canEdit"
                        class="task-pause-btn"
                        aria-label="Pause or resume task"
                        @click.stop="$emit('toggle-paused', row)"
                      />
                    </span>
                  </template>
                  <span>{{
                    !canEdit
                      ? READ_ONLY_TOOLTIP
                      : row.schedule?.enabled
                      ? 'Pause task'
                      : 'Resume task'
                  }}</span>
                </v-tooltip>
                <v-btn
                  v-if="canEdit && !row.userClickedRunNow"
                  variant="outlined"
                  color="green-darken-3"
                  :prepend-icon="mdiPlay"
                  class="detail-action-btn detail-action-btn--compact text-none"
                  rounded="lg"
                  @click.stop="$emit('run-now', row)"
                >
                  Run now
                </v-btn>
                <span
                  v-else-if="canEdit && row.userClickedRunNow"
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
                  @click.stop="$emit('open-task', row)"
                >
                  Details
                </v-btn>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import {
  mdiArrowDown,
  mdiArrowUp,
  mdiArrowUpDown,
  mdiChevronRight,
  mdiFilterVariant,
  mdiMagnify,
  mdiPause,
  mdiPlay,
  mdiPlus,
} from '@mdi/js'
import type { DataConnection } from '@hydroserver/client'
import TaskStatus from '@/components/Orchestration/shared/TaskStatus.vue'
import HealthPills from '@/components/Orchestration/shared/HealthPills.vue'
import {
  DATA_PRODUCT_TYPE_COLORS,
  READ_ONLY_TOOLTIP,
  STATUS_OPTIONS,
  type DataProductTaskType,
  type SortDir,
  type SortKey,
  type TabId,
  type TaskRow,
} from './orchestrationTabs'

const typeChipStyle = (taskType: DataProductTaskType) => {
  if (!taskType) return {}
  const c = DATA_PRODUCT_TYPE_COLORS[taskType]
  return { background: c.bg, color: c.text }
}

const props = defineProps<{
  activeTab: TabId
  accent: string
  accentLight: string
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
  taskSearch: string
  statusFilter: string[]
  sortKey: SortKey
  sortDir: SortDir
}>()

const emit = defineEmits<{
  (e: 'update:taskSearch', value: string): void
  (e: 'update:statusFilter', value: string[]): void
  (e: 'toggle-sort', key: SortKey): void
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

const sortableColumns: { key: SortKey; label: string }[] = [
  { key: 'name', label: 'Task name' },
  { key: 'status', label: 'Status' },
  { key: 'lastRunAt', label: 'Last run' },
  { key: 'nextRunAt', label: 'Next run' },
]

const sortIcon = (key: SortKey) => {
  if (props.sortKey !== key) return mdiArrowUpDown
  return props.sortDir === 'asc' ? mdiArrowUp : mdiArrowDown
}

const removeStatusFilter = (index: number) => {
  const next = [...props.statusFilter]
  next.splice(index, 1)
  emit('update:statusFilter', next)
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
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.tasks-table thead tr {
  border-bottom: 2px solid #ebebeb;
}
.tasks-table th {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 10.5px;
  color: #49454f;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.tasks-table th.text-right {
  text-align: right;
}
.tasks-table tbody tr {
  border-bottom: 1px solid #f0f0f0;
}
.tasks-table tbody tr:hover {
  background: #f5f7fa;
}
.th-sort {
  background: none;
  border: none;
  cursor: pointer;
  font: inherit;
  color: inherit;
  text-transform: inherit;
  letter-spacing: inherit;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 4px;
  border-radius: 4px;
}
.th-sort:hover {
  background: rgba(0, 0, 0, 0.05);
}
.task-name {
  padding: 13px 12px;
  font-weight: 500;
  color: #1c1b1f;
}
.task-time {
  padding: 13px 12px;
  color: #49454f;
  font-size: 12px;
  font-family: 'Roboto Mono', monospace;
  white-space: nowrap;
}
.tasks-table td {
  padding: 13px 12px;
}
.task-type {
  padding: 13px 12px;
  white-space: nowrap;
}
.task-rules {
  color: #475569;
  font-size: 13px;
  max-width: 320px;
}
.task-violations {
  white-space: nowrap;
}
.task-violation-chip {
  font-weight: 700;
}
.task-type-chip {
  font-size: 11px;
  font-weight: 600;
}
.task-actions {
  text-align: right;
  white-space: nowrap;
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
