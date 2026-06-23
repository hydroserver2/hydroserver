<template>
  <div v-if="task" class="detail">
    <header class="bar">
      <button class="back" @click="close">← {{ backLabel }}</button>
      <div class="title">
        <h2>{{ task.name }}</h2>
        <span v-if="scheduleText" class="pill">{{ scheduleText }}</span>
      </div>
      <div class="actions">
        <button
          type="button"
          class="header-btn header-btn--neutral"
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
        <v-dialog width="64rem">
          <template #activator="{ props }">
            <button
              v-bind="props"
              type="button"
              class="header-btn header-btn--neutral"
              :disabled="!canEdit"
            >
              <v-icon :icon="mdiPencil" size="16" />
              <span>Edit</span>
            </button>
          </template>
          <QualityManagementForm
            :initial-thing-id="task.thing.id"
            :edit-task-id="task.id"
            @close="onUpdated"
            @updated="onUpdated"
            @deleted="deleteTask"
          />
        </v-dialog>
        <v-dialog width="34rem">
          <template #activator="{ props }">
            <button
              v-bind="props"
              type="button"
              class="header-btn header-btn--danger"
              :disabled="!canEdit"
            >
              <v-icon :icon="mdiTrashCanOutline" size="16" />
              <span>Delete</span>
            </button>
          </template>
          <DeleteTaskCard :task="task" @delete="deleteTask" />
        </v-dialog>
        <button
          type="button"
          class="header-btn header-btn--run"
          :disabled="!!runNowDisabledReason"
          @click="runNow"
        >
          <v-icon :icon="mdiPlay" size="16" />
          <span>{{ runNowRequested ? 'Run requested' : 'Run now' }}</span>
        </button>
      </div>
    </header>
    <section class="body">
      <TaskRunHistory
        :rows="runRows"
        :show-loading="loadingRuns"
        :has-loaded-full-run-history="true"
        :loading-full-run-history="loadingRuns"
        highlighted-run-id=""
        @fetch-full="fetchRuns"
        @copy="copy"
      />
    </section>
  </div>
  <div v-else class="loading">Loading...</div>
</template>

<script setup lang="ts">
import DeleteTaskCard from '@/components/Orchestration/shared/DeleteTaskCard.vue'
import NoScheduleIcon from '@/components/Orchestration/shared/NoScheduleIcon.vue'
import QualityManagementForm from '@/components/Orchestration/monitoring/QualityManagementForm.vue'
import TaskRunHistory from '@/components/Orchestration/shared/TaskRunHistory.vue'
import { useSimpleTaskDetails } from '@/composables/orchestration/useSimpleTaskDetails'
import {
  mdiPause,
  mdiPencil,
  mdiPlay,
  mdiTrashCanOutline,
} from '@mdi/js'

const props = defineProps<{
  taskId: string
  runId?: string | null
  embedded?: boolean
  initialTask?: any
}>()
const emit = defineEmits(['close', 'deleted', 'updated'])
const {
  task,
  loadingRuns,
  runRows,
  canEdit,
  backLabel,
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
} = useSimpleTaskDetails('monitoring', props, emit)
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
}
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  align-self: start;
  gap: 8px;
}
.header-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  gap: 8px;
  height: 34px;
  min-height: 34px;
  padding: 0 14px;
  background: #ffffff;
  border: 1px solid #cac4d0;
  border-radius: 8px;
  color: #1c1b1f;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.1;
  transition: background-color 0.12s, border-color 0.12s, color 0.12s;
  white-space: nowrap;
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
