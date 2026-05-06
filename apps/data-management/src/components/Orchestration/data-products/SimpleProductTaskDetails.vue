<template>
  <div v-if="task" class="detail">
    <header class="bar">
      <button class="back" @click="close">← {{ backLabel }}</button>
      <div class="title">
        <h2>{{ task.name }}</h2>
        <TaskStatus :status="statusName" :paused="!task.schedule?.enabled" />
        <span class="pill">{{ taskLabel }}</span>
        <span v-if="scheduleText" class="pill">{{ scheduleText }}</span>
      </div>
      <div class="actions">
        <v-btn
          variant="outlined"
          :disabled="!!pauseDisabledReason"
          @click="togglePaused"
        >
          {{ task.schedule?.enabled ? 'Pause' : 'Resume' }}
        </v-btn>
        <v-dialog width="60rem">
          <template #activator="{ props }">
            <v-btn v-bind="props" variant="outlined" :disabled="!canEdit"
              >Edit</v-btn
            >
          </template>
          <AggregationForm
            v-if="taskLabel === 'aggregation'"
            :workspace-id="workspaceId"
            :initial-thing-id="task.thing.id"
            :edit-task-id="task.id"
            @close="onUpdated"
            @updated="onUpdated"
            @deleted="deleteTask"
          />
          <ExpressionForm
            v-else-if="taskLabel === 'expression'"
            :workspace-id="workspaceId"
            :initial-thing-id="task.thing.id"
            :edit-task-id="task.id"
            @close="onUpdated"
            @updated="onUpdated"
            @deleted="deleteTask"
          />
          <DerivationForm
            v-else-if="taskLabel === 'derivation'"
            :workspace-id="workspaceId"
            :initial-thing-id="task.thing.id"
            :edit-task-id="task.id"
            @close="onUpdated"
            @updated="onUpdated"
            @deleted="deleteTask"
          />
          <RatingCurveForm
            v-else
            :workspace-id="workspaceId"
            :initial-thing-id="task.thing.id"
            :edit-task-id="task.id"
            @close="onUpdated"
            @updated="onUpdated"
            @deleted="deleteTask"
          />
        </v-dialog>
        <v-dialog width="34rem">
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              color="error"
              variant="outlined"
              :disabled="!canEdit"
              >Delete</v-btn
            >
          </template>
          <DeleteTaskCard :task="task" @delete="deleteTask" />
        </v-dialog>
        <v-btn
          color="success"
          variant="outlined"
          :disabled="!!runNowDisabledReason"
          @click="runNow"
        >
          {{ runNowRequested ? 'Run requested' : 'Run now' }}
        </v-btn>
      </div>
    </header>

    <v-tabs v-if="taskLabel === 'rating curve'" v-model="tab" density="compact">
      <v-tab value="runs">Run history</v-tab>
      <v-tab value="mappings">Mappings</v-tab>
    </v-tabs>
    <section class="body">
      <TaskRunHistory
        v-if="tab === 'runs'"
        :rows="runRows"
        :show-loading="loadingRuns"
        :has-loaded-full-run-history="true"
        :loading-full-run-history="loadingRuns"
        highlighted-run-id=""
        @fetch-full="fetchRuns"
        @copy="copy"
        @copy-run-link="() => null"
      />
      <RatingCurveSwimlanes
        v-else
        :transformations="task.ratingCurveTransformations ?? []"
      />
    </section>
  </div>
  <div v-else class="loading">Loading...</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import TaskStatus from '@/components/Orchestration/shared/TaskStatus.vue'
import DeleteTaskCard from '@/components/Orchestration/shared/DeleteTaskCard.vue'
import AggregationForm from '@/components/Orchestration/data-products/AggregationForm.vue'
import ExpressionForm from '@/components/Orchestration/data-products/ExpressionForm.vue'
import DerivationForm from '@/components/Orchestration/data-products/DerivationForm.vue'
import RatingCurveForm from '@/components/Orchestration/data-products/RatingCurveForm.vue'
import RatingCurveSwimlanes from '@/components/Orchestration/data-products/RatingCurveSwimlanes.vue'
import TaskRunHistory from '@/components/Orchestration/shared/TaskRunHistory.vue'
import { useSimpleTaskDetails } from '@/composables/orchestration/useSimpleTaskDetails'

const props = defineProps<{
  taskLabel: 'aggregation' | 'expression' | 'derivation' | 'rating curve'
  taskId: string
  runId?: string | null
  embedded?: boolean
  initialTask?: any
}>()
const emit = defineEmits(['close', 'deleted', 'updated'])
const tab = ref('runs')
const {
  task,
  loadingRuns,
  runRows,
  canEdit,
  backLabel,
  statusName,
  scheduleText,
  pauseDisabledReason,
  runNowDisabledReason,
  runNowRequested,
  workspaceId,
  close,
  copy,
  deleteTask,
  fetchRuns,
  onUpdated,
  runNow,
  togglePaused,
} = useSimpleTaskDetails('dataProduct', props, emit)
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
  grid-template-columns: 1fr auto;
  gap: 10px;
  padding: 14px 22px 12px;
  border-bottom: 1px solid #e8e8e8;
}
.back {
  grid-column: 1 / -1;
  justify-self: start;
  border: 0;
  background: transparent;
  color: #1565c0;
  cursor: pointer;
}
.title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
h2 {
  font-size: 18px;
  font-weight: 400;
  margin: 0;
}
.pill {
  font-size: 11px;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 2px 7px;
  text-transform: capitalize;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 22px;
  background: #f5f7fa;
}
.loading {
  padding: 40px 20px;
  text-align: center;
  color: #5f5a67;
}
</style>
