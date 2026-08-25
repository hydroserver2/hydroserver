<template>
  <HsDetailPanel>
    <template #header>
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="detail-title hs-text-md font-weight-regular">
            {{ detailTitle }}
          </h2>
          <span
            v-if="detailTypeBadge"
            class="detail-badge hs-label"
            :style="{ color: accent, background: accentLight }"
          >
            {{ detailTypeBadge }}
          </span>
        </div>
        <div class="detail-subtitle">
          <HealthPills
            :tasks="visibleTasks"
            interactive
            :active-statuses="statusFilter"
            @toggle-status="toggleStatusFilter"
          />
        </div>
      </div>
    </template>

    <template #accessory>
      <WorkspaceSelector />
    </template>

    <template v-if="hasSelection" #toolbar>
      <div class="hs-table-tools detail-filterbar">
        <HsQuerySearchInput
          v-model="taskSearch"
          placeholder="Search tasks…"
          :qualifiers="searchQualifiers"
        />
        <div class="hs-table-actions">
          <v-tooltip
            v-if="activeTab === 'ingestion' && selectedConnection"
            location="top"
            :disabled="canCreate"
          >
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn-secondary
                  variant="flat"
                  :disabled="!canCreate"
                  data-testid="add-ingestion-task"
                  @click="emit('add-task')"
                >
                  Add task
                </v-btn-secondary>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>

          <template v-if="activeTab === 'aggregation'">
            <v-tooltip location="top" :disabled="canCreate">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn-secondary
                    variant="flat"
                    :disabled="!canCreate"
                    data-testid="add-aggregation-task"
                    @click="emit('add-aggregation')"
                  >
                    Add aggregation
                  </v-btn-secondary>
                </span>
              </template>
              <span>{{ READ_ONLY_TOOLTIP }}</span>
            </v-tooltip>
            <v-tooltip location="top" :disabled="canCreate">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn-secondary
                    variant="flat"
                    :disabled="!canCreate"
                    data-testid="add-derivation-task"
                    @click="emit('add-derivation')"
                  >
                    Add derivation
                  </v-btn-secondary>
                </span>
              </template>
              <span>{{ READ_ONLY_TOOLTIP }}</span>
            </v-tooltip>
            <v-tooltip location="top" :disabled="canCreateRatingCurve">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn-secondary
                    variant="flat"
                    :disabled="!canCreateRatingCurve"
                    data-testid="add-rating-curve-task"
                    @click="emit('add-rating-curve')"
                  >
                    Add rating curve
                  </v-btn-secondary>
                </span>
              </template>
              <span>{{ READ_ONLY_TOOLTIP }}</span>
            </v-tooltip>
          </template>

          <v-tooltip
            v-if="activeTab === 'quality'"
            location="top"
            :disabled="canCreate"
          >
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn-secondary
                  variant="flat"
                  :disabled="!canCreate"
                  data-testid="add-quality-task"
                  @click="emit('add-quality')"
                >
                  Add quality task
                </v-btn-secondary>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
        </div>
      </div>
    </template>

    <div v-if="loading" class="detail-loading hs-text-sm">
      <v-progress-circular
        indeterminate
        size="22"
        width="2"
        color="blue-grey-darken-1"
      />
      <span>Loading…</span>
    </div>

    <HsEmptyState v-else-if="!hasSelection" compact :title="emptyHeading">
      <small>{{ emptyMessage }}</small>
    </HsEmptyState>

    <HsEmptyState
      v-else-if="visibleTasks.length === 0"
      compact
      title="No tasks"
    >
      <small>{{ emptyTasksMessage }}</small>
    </HsEmptyState>

    <HsEmptyState
      v-else-if="sortedVisibleTasks.length === 0"
      compact
      title="No tasks match your filter"
    >
      <small
        >Clear search, status, or task type filters to see all tasks.</small
      >
    </HsEmptyState>

    <IngestionTaskTable
      v-else-if="activeTab === 'ingestion'"
      :tasks="sortedVisibleTasks"
      :status-filter="statusFilter"
      :can-edit="canEdit"
      :accent="accent"
      @toggle-status="toggleStatusFilter"
      @clear-status="clearStatusFilter"
      @toggle-paused="emit('toggle-paused', $event)"
      @run-now="emit('run-now', $event)"
      @open-task="emit('open-task', $event)"
    />

    <OrchestrationTaskTable
      v-else
      :tasks="sortedVisibleTasks"
      :status-filter="statusFilter"
      :task-type-filter="taskTypeFilter"
      :can-edit="canEdit"
      :accent="accent"
      @toggle-status="toggleStatusFilter"
      @clear-status="clearStatusFilter"
      @toggle-task-type="toggleTaskTypeFilter"
      @clear-task-type="clearTaskTypeFilter"
      @toggle-paused="emit('toggle-paused', $event)"
      @run-now="emit('run-now', $event)"
      @open-task="emit('open-task', $event)"
    />
  </HsDetailPanel>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import type { DataConnection } from '@hydroserver/client'
import {
  HsDetailPanel,
  HsEmptyState,
  HsQuerySearchInput,
} from '@hydroserver/design-system/vue'
import HealthPills from '@/components/Orchestration/shared/HealthPills.vue'
import WorkspaceSelector from '@/components/Workspace/WorkspaceSelector.vue'
import { useOrchestrationStore } from '@/store/orchestration'
import IngestionTaskTable from './IngestionTaskTable.vue'
import OrchestrationTaskTable from './OrchestrationTaskTable.vue'
import {
  DATA_PRODUCT_TYPE_OPTIONS,
  READ_ONLY_TOOLTIP,
  STATUS_OPTIONS,
  TAB_META,
  type DataProductTaskType,
  type TaskRow,
} from './orchestrationTabs'

defineProps<{
  canCreate: boolean
  canCreateRatingCurve: boolean
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

const emit = defineEmits<{
  'toggle-paused': [row: TaskRow]
  'run-now': [row: TaskRow]
  'open-task': [row: TaskRow]
  'add-task': []
  'add-aggregation': []
  'add-derivation': []
  'add-rating-curve': []
  'add-quality': []
}>()

const {
  activeTab,
  orchestrationSearch: taskSearch,
  orchestrationStatusFilter: statusFilter,
  orchestrationTaskTypeFilter: taskTypeFilter,
} = storeToRefs(useOrchestrationStore())

const accent = computed(() =>
  activeTab.value === 'ingestion'
    ? 'rgb(var(--v-theme-primary))'
    : TAB_META[activeTab.value].accent
)
const accentLight = computed(() => TAB_META[activeTab.value].accentLight)

const searchQualifiers = computed(() => [
  {
    key: 'status',
    label: 'Status',
    values: STATUS_OPTIONS.map(({ value }) => value),
  },
  ...(activeTab.value === 'aggregation'
    ? [
        {
          key: 'type',
          label: 'Task type',
          values: DATA_PRODUCT_TYPE_OPTIONS,
        },
      ]
    : []),
  { key: 'name', label: 'Task name', values: [] },
])

const qualifierValues = (query: string, key: string) => {
  const values: string[] = []
  const pattern = new RegExp(`${key}:(?:"([^"]*)"|(\\S+))`, 'gi')
  let match: RegExpExecArray | null
  while ((match = pattern.exec(query))) {
    const value = (match[1] ?? match[2] ?? '').toLocaleLowerCase()
    if (value) values.push(value)
  }
  return values
}

watch(
  taskSearch,
  (query) => {
    const selectedStatuses = qualifierValues(query, 'status')
    statusFilter.value = STATUS_OPTIONS.filter(({ value }) =>
      selectedStatuses.includes(value.toLocaleLowerCase())
    ).map(({ value }) => value)

    const selectedTaskTypes = qualifierValues(query, 'type')
    taskTypeFilter.value = DATA_PRODUCT_TYPE_OPTIONS.filter((taskType) =>
      selectedTaskTypes.includes(taskType.toLocaleLowerCase())
    )
  },
  { immediate: true }
)

const toggleStatusFilter = (status: string) => {
  const next = new Set(statusFilter.value)
  next.has(status) ? next.delete(status) : next.add(status)
  statusFilter.value = Array.from(next)

  const searchWithoutStatuses = taskSearch.value
    .replace(/(?:^|\s)status:(?:"[^"]*"|\S+)/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  const statusQuery = Array.from(next)
    .map((value) => `status:${/\s/.test(value) ? `"${value}"` : value}`)
    .join(' ')
  taskSearch.value = [statusQuery, searchWithoutStatuses]
    .filter(Boolean)
    .join(' ')
}

const clearStatusFilter = () => {
  statusFilter.value.slice().forEach(toggleStatusFilter)
}

const toggleTaskTypeFilter = (taskType: string) => {
  const typedTaskType = taskType as NonNullable<DataProductTaskType>
  const next = new Set(taskTypeFilter.value)
  next.has(typedTaskType) ? next.delete(typedTaskType) : next.add(typedTaskType)
  taskTypeFilter.value = Array.from(next)

  const searchWithoutTaskTypes = taskSearch.value
    .replace(/(?:^|\s)type:(?:"[^"]*"|\S+)/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  const typeQuery = Array.from(next)
    .map((value) => `type:${/\s/.test(value) ? `"${value}"` : value}`)
    .join(' ')
  taskSearch.value = [typeQuery, searchWithoutTaskTypes]
    .filter(Boolean)
    .join(' ')
}

const clearTaskTypeFilter = () => {
  taskTypeFilter.value.slice().forEach(toggleTaskTypeFilter)
}
</script>

<style scoped>
.detail-title {
  color: var(--hs-text-primary);
}

.detail-badge {
  padding: var(--hs-space-2) var(--hs-space-6);
  border-radius: var(--hs-radius-sm);
}

.detail-subtitle {
  margin-top: var(--hs-space-4);
}

.detail-filterbar {
  padding: 0 var(--hs-space-24);
  margin: var(--hs-space-24) 0 var(--hs-space-10);
}

.detail-filterbar .hs-table-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.detail-loading {
  display: flex;
  gap: var(--hs-space-12);
  align-items: center;
  padding: var(--hs-space-24) 0;
  color: var(--hs-text-secondary);
}
</style>
