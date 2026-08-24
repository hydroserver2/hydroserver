<template>
  <div v-if="task" class="detail">
    <header class="bar">
      <button
        class="task-details-back hs-text-sm font-weight-medium"
        type="button"
        @click="close"
      >
        <v-icon :icon="mdiArrowLeft" size="16" />
        <span>{{ backLabel }}</span>
      </button>
      <div class="title">
        <h2 class="hs-text-md font-weight-regular">{{ task.name }}</h2>
        <span
          class="pill task-type-pill hs-text-2xs font-weight-semibold"
          :style="taskTypePillStyle"
        >
          {{ taskLabel }}
        </span>
        <span v-if="scheduleText" class="pill hs-text-2xs">{{
          scheduleText
        }}</span>
      </div>
      <div class="actions">
        <button
          type="button"
          class="header-btn header-btn--neutral hs-text-sm font-weight-semibold"
          :disabled="!!pauseDisabledReason"
          @click="togglePaused"
        >
          <NoScheduleIcon v-if="!task.schedule" />
          <v-icon
            v-else
            :icon="task.schedule.enabled ? mdiPause : mdiPlay"
            size="16"
          />
          <span>{{
            !task.schedule
              ? 'No schedule'
              : task.schedule.enabled
                ? 'Pause'
                : 'Resume'
          }}</span>
        </button>
        <v-dialog v-model="editDialogOpen" width="60rem">
          <template #activator="{ props }">
            <button
              v-bind="props"
              type="button"
              class="header-btn header-btn--neutral hs-text-sm font-weight-semibold"
              :disabled="!canEdit"
            >
              <v-icon :icon="mdiPencil" size="16" />
              <span>Edit</span>
            </button>
          </template>
          <AggregationForm
            v-if="taskLabel === 'aggregation'"
            :initial-monitoring-site-id="task.monitoringSite.id"
            :edit-task-id="task.id"
            @close="closeEditDialog"
            @updated="onFormUpdated"
            @deleted="deleteTask"
          />
          <DerivationForm
            v-else-if="taskLabel === 'derivation'"
            :initial-monitoring-site-id="task.monitoringSite.id"
            :edit-task-id="task.id"
            @close="closeEditDialog"
            @updated="onFormUpdated"
            @deleted="deleteTask"
          />
          <RatingCurveForm
            v-else
            :initial-monitoring-site-id="task.monitoringSite.id"
            :edit-task-id="task.id"
            @close="closeEditDialog"
            @updated="onFormUpdated"
            @deleted="deleteTask"
          />
        </v-dialog>
        <v-dialog v-model="deleteTaskDialogOpen" width="34rem">
          <template #activator="{ props }">
            <button
              v-bind="props"
              type="button"
              class="header-btn header-btn--danger hs-text-sm font-weight-semibold"
              :disabled="!canDelete"
            >
              <v-icon :icon="mdiTrashCanOutline" size="16" />
              <span>Delete</span>
            </button>
          </template>
          <DeleteTaskCard
            :task="task"
            @close="deleteTaskDialogOpen = false"
            @delete="deleteTask"
          />
        </v-dialog>
        <button
          type="button"
          class="header-btn header-btn--run hs-text-sm font-weight-semibold"
          :disabled="!!runNowDisabledReason"
          @click="runNow"
        >
          <v-icon :icon="mdiPlay" size="16" />
          <span>{{ runNowRequested ? 'Run requested' : 'Run now' }}</span>
        </button>
      </div>
    </header>

    <div class="detail-tabbar">
      <v-tabs v-model="tab" color="primary" density="comfortable" show-arrows>
        <v-tab value="runs" :prepend-icon="mdiHistory">Run history</v-tab>
        <v-tab value="mappings" :prepend-icon="mdiTransitConnectionVariant">
          Mappings
        </v-tab>
      </v-tabs>
    </div>
    <section class="body">
      <div v-if="tab === 'runs'" class="run-history-list">
        <TaskRunHistory
          :rows="runRows"
          :show-loading="loadingRuns"
          :has-loaded-full-run-history="true"
          :loading-full-run-history="loadingRuns"
          highlighted-run-id=""
          @fetch-full="fetchRuns"
          @copy="copy"
        />
      </div>
      <RatingCurveSwimlanes
        v-else-if="taskLabel === 'rating curve'"
        :transformations="task.ratingCurveTransformations ?? []"
        :monitoring-site-id="task.monitoringSite?.id"
      />
      <ProductTaskSwimlanes
        v-else
        :task="task"
        :task-label="taskLabel"
        :monitoring-site-id="task.monitoringSite?.id"
      />
    </section>
  </div>
  <div v-else class="loading">Loading...</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import DeleteTaskCard from '@/components/Orchestration/shared/DeleteTaskCard.vue'
import NoScheduleIcon from '@/components/Orchestration/shared/NoScheduleIcon.vue'
import AggregationForm from '@/components/Orchestration/data-products/AggregationForm.vue'
import DerivationForm from '@/components/Orchestration/data-products/DerivationForm.vue'
import RatingCurveForm from '@/components/Orchestration/data-products/RatingCurveForm.vue'
import ProductTaskSwimlanes from '@/components/Orchestration/data-products/ProductTaskSwimlanes.vue'
import RatingCurveSwimlanes from '@/components/Orchestration/data-products/RatingCurveSwimlanes.vue'
import TaskRunHistory from '@/components/Orchestration/shared/TaskRunHistory.vue'
import { useSimpleTaskDetails } from '@/composables/orchestration/useSimpleTaskDetails'
import {
  getDataProductTypeColors,
  type DataProductTaskType,
} from '@/components/Orchestration/workbench/orchestrationTabs'
import {
  mdiArrowLeft,
  mdiHistory,
  mdiPause,
  mdiPencil,
  mdiPlay,
  mdiTransitConnectionVariant,
  mdiTrashCanOutline,
} from '@mdi/js'

const props = defineProps<{
  taskLabel: 'aggregation' | 'derivation' | 'rating curve'
  taskId: string
  runId?: string | null
  embedded?: boolean
  initialTask?: any
}>()
const emit = defineEmits(['close', 'deleted', 'updated'])
const tab = ref('runs')
const editDialogOpen = ref(false)
const deleteTaskDialogOpen = ref(false)

const taskTypePillStyle = computed(() => {
  const label = toDataProductTaskType(props.taskLabel)
  const colors = getDataProductTypeColors(label)
  if (!colors) return {}
  return { background: colors.bg, color: colors.text }
})

const {
  task,
  loadingRuns,
  runRows,
  canEdit,
  canDelete,
  backLabel,
  statusName,
  scheduleText,
  pauseDisabledReason,
  runNowDisabledReason,
  runNowRequested,
  close,
  copy,
  deleteTask,
  fetchRuns,
  onUpdated,
  runNow,
  togglePaused,
} = useSimpleTaskDetails('dataProduct', props, emit)

function toDataProductTaskType(
  label: typeof props.taskLabel
): DataProductTaskType {
  switch (label) {
    case 'aggregation':
      return 'Aggregation'
    case 'derivation':
      return 'Derivation'
    case 'rating curve':
      return 'Rating curve'
    default:
      return null
  }
}

function closeEditDialog() {
  editDialogOpen.value = false
}

function onFormUpdated() {
  closeEditDialog()
  onUpdated()
}
</script>

<style scoped>
.detail {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
}
.bar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content;
  align-items: start;
  column-gap: 10px;
  row-gap: 0;
  padding: 14px 22px 12px;
  border-bottom: 1px solid #e8e8e8;
}
.task-details-back {
  grid-column: 1 / -1;
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: inherit;
  color: #1565c0;
  padding: 3px 6px;
  border-radius: 6px;
  margin-bottom: 8px;
}
.task-details-back:hover {
  background: rgba(0, 0, 0, 0.05);
}
.title {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
}
h2 {
  margin: 0;
}
.pill {
  background: #f5f7fa;
  border-radius: 4px;
  padding: 2px 7px;
  text-transform: capitalize;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
  align-self: start;
  justify-content: flex-end;
  justify-self: end;
}
.header-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: flex-start;
  flex: 0 0 auto;
  gap: 8px;
  min-height: 34px;
  padding: 0 14px;
  background: #ffffff;
  border: 1px solid #cac4d0;
  border-radius: 8px;
  color: #1c1b1f;
  cursor: pointer;
  font-family: inherit;
  line-height: 1.1;
  transition:
    background-color 0.12s,
    border-color 0.12s,
    color 0.12s;
  white-space: nowrap;
  width: auto;
}
.header-btn :deep(.v-icon) {
  flex: 0 0 auto;
}
.header-btn:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.05);
}
.header-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.header-btn--neutral {
  border-color: #cac4d0;
  color: #1c1b1f;
}
.header-btn--run {
  border-color: #2e7d32;
  color: #2e7d32;
}
.header-btn--run:hover:not(:disabled) {
  background: rgba(46, 125, 50, 0.08);
}
.header-btn--danger {
  border-color: #b3261e;
  color: #b3261e;
}
.header-btn--danger:hover:not(:disabled) {
  background: rgba(179, 38, 30, 0.08);
  border-color: #b3261e;
}
.detail-tabbar {
  padding: 0 var(--hs-space-24);
  border-bottom: 1px solid var(--hs-border);
  background: var(--hs-surface-subtle);
  flex-shrink: 0;
}
.body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 22px;
  background: #f5f7fa;
}
.run-history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.loading {
  padding: 40px 20px;
  text-align: center;
  color: #5f5a67;
}

@media (max-width: 760px) {
  .bar {
    grid-template-columns: 1fr;
  }
  .actions {
    justify-self: start;
    justify-content: flex-start;
  }
}

@media (max-width: 700px) {
  .detail-tabbar {
    padding: 0 var(--hs-space-8);
  }
}
</style>
