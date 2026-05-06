<template>
  <div v-if="task" class="detail">
    <header class="bar">
      <button class="back" @click="close">← {{ backLabel }}</button>
      <div class="title">
        <h2>{{ task.name }}</h2>
        <TaskStatus :status="statusName" :paused="!task.schedule?.enabled" />
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
        <v-dialog width="64rem">
          <template #activator="{ props }">
            <v-btn v-bind="props" variant="outlined" :disabled="!canEdit"
              >Edit</v-btn
            >
          </template>
          <QualityManagementForm
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
    <section class="body">
      <TaskRunHistory
        :rows="runRows"
        :show-loading="loadingRuns"
        :has-loaded-full-run-history="true"
        :loading-full-run-history="loadingRuns"
        highlighted-run-id=""
        @fetch-full="fetchRuns"
        @copy="copy"
        @copy-run-link="() => null"
      />
    </section>
  </div>
  <div v-else class="loading">Loading...</div>
</template>

<script setup lang="ts">
import TaskStatus from '@/components/Orchestration/TaskStatus.vue'
import DeleteTaskCard from '@/components/Orchestration/DeleteTaskCard.vue'
import QualityManagementForm from '@/components/Orchestration/QualityManagementForm.vue'
import TaskRunHistory from '@/components/Orchestration/TaskRunHistory.vue'
import { useSimpleTaskDetails } from '@/composables/orchestration/useSimpleTaskDetails'

const props = defineProps<{
  taskId: string
  runId?: string | null
  embedded?: boolean
}>()
const emit = defineEmits(['close', 'deleted', 'updated'])
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
