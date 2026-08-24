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

    <template
      v-if="activeTab === 'aggregation' || activeTab === 'quality'"
      #actions
    >
      <div class="detail-actions">
        <template v-if="activeTab === 'aggregation'">
          <v-tooltip location="top" :disabled="canCreate">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn
                  variant="outlined"
                  class="detail-action-btn detail-action-btn--header hs-text-sm font-weight-semibold text-none"
                  :disabled="!canCreate"
                  rounded="lg"
                  @click="emit('add-aggregation')"
                >
                  + Aggregation
                </v-btn>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
          <v-tooltip location="top" :disabled="canCreate">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn
                  variant="outlined"
                  class="detail-action-btn detail-action-btn--header hs-text-sm font-weight-semibold text-none"
                  :disabled="!canCreate"
                  rounded="lg"
                  @click="emit('add-derivation')"
                >
                  + Derivation
                </v-btn>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
          <v-tooltip location="top" :disabled="canCreateRatingCurve">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn
                  variant="outlined"
                  class="detail-action-btn detail-action-btn--header hs-text-sm font-weight-semibold text-none"
                  :disabled="!canCreateRatingCurve"
                  rounded="lg"
                  @click="emit('add-rating-curve')"
                >
                  + Rating curve
                </v-btn>
              </span>
            </template>
            <span>{{ READ_ONLY_TOOLTIP }}</span>
          </v-tooltip>
        </template>
        <v-tooltip v-else location="top" :disabled="canCreate">
          <template #activator="{ props: tooltipProps }">
            <span v-bind="tooltipProps" class="inline-flex">
              <v-btn
                variant="flat"
                :prepend-icon="mdiPlus"
                :style="{ background: accent, color: 'white' }"
                :disabled="!canCreate"
                class="detail-action-btn detail-action-btn--primary text-none"
                rounded="lg"
                @click="emit('add-quality')"
              >
                Add quality task
              </v-btn>
            </span>
          </template>
          <span>{{ READ_ONLY_TOOLTIP }}</span>
        </v-tooltip>
      </div>
    </template>

    <template #accessory>
      <WorkspaceSelector />
    </template>

    <template
      v-if="
        hasSelection && (visibleTasks.length > 0 || activeTab === 'ingestion')
      "
      #toolbar
    >
      <div class="hs-table-tools detail-filterbar">
        <HsSearchInput v-model="taskSearch" placeholder="Search tasks…" />
        <v-autocomplete
          v-if="activeTab !== 'ingestion'"
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
              <v-icon
                :icon="taskStatusIcon(item.value)"
                size="14"
                class="mr-1"
                :style="{ color: taskStatusColor(item.value) }"
              />
              <span>{{ item.title }}</span>
            </v-chip>
          </template>
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps">
              <template #prepend>
                <v-icon
                  :icon="taskStatusIcon(item.value)"
                  size="18"
                  :style="{ color: taskStatusColor(item.value) }"
                />
              </template>
            </v-list-item>
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
              class="mr-1 task-type-chip hs-text-2xs font-weight-semibold"
              :style="taskTypeSelectionStyle(item)"
              @click:close="removeTaskTypeFilter(index)"
            >
              <span>{{ item }}</span>
            </v-chip>
          </template>
        </v-autocomplete>
        <div
          v-if="activeTab === 'ingestion' && selectedConnection"
          class="hs-table-actions"
        >
          <v-tooltip location="top" :disabled="canCreate">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn-secondary
                  variant="flat"
                  :prepend-icon="mdiPlus"
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
      :can-edit="canEdit"
      :accent="accent"
      @toggle-paused="emit('toggle-paused', $event)"
      @run-now="emit('run-now', $event)"
      @open-task="emit('open-task', $event)"
    />
  </HsDetailPanel>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { mdiFilterVariant, mdiPlus } from '@mdi/js'
import type { DataConnection } from '@hydroserver/client'
import HsDetailPanel from '@/components/base/HsDetailPanel.vue'
import HsEmptyState from '@/components/base/HsEmptyState.vue'
import HsSearchInput from '@/components/base/HsSearchInput.vue'
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
import {
  taskStatusColor,
  taskStatusIcon,
  taskTypeChipStyle,
} from './taskPresentation'

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

const taskTypeSelectionStyle = (taskType: unknown) =>
  taskTypeChipStyle(taskType as DataProductTaskType)

const removeStatusFilter = (index: number) => {
  const next = [...statusFilter.value]
  next.splice(index, 1)
  statusFilter.value = next
}

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

const removeTaskTypeFilter = (index: number) => {
  const next = [...taskTypeFilter.value]
  next.splice(index, 1)
  taskTypeFilter.value = next
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

.detail-actions {
  display: flex;
  flex-shrink: 0;
  gap: var(--hs-space-8);
  align-items: center;
}

.detail-action-btn {
  min-height: 40px;
}

.detail-action-btn--header {
  min-height: 34px;
  padding-inline: var(--hs-space-12);
  color: rgb(var(--v-theme-primary));
  border-color: rgb(var(--v-theme-primary));
}

.detail-action-btn--primary {
  padding-inline: var(--hs-space-20);
}

.detail-filterbar {
  padding: 0 var(--hs-space-24);
  margin: var(--hs-space-24) 0 var(--hs-space-10);
}

.detail-status-filter {
  max-width: 320px;
}

.detail-task-type-filter {
  max-width: 300px;
}

.detail-loading {
  display: flex;
  gap: var(--hs-space-12);
  align-items: center;
  padding: var(--hs-space-24) 0;
  color: var(--hs-text-secondary);
}
</style>
