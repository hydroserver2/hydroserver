<template>
  <div v-if="task" class="task-details">
    <header class="task-details-header">
      <button class="task-details-back" type="button" @click="close">
        <v-icon :icon="mdiArrowLeft" size="16" />
        <span>{{ backLabel }}</span>
      </button>

      <div class="task-details-header-row">
        <div class="task-details-title-group">
          <h2 class="task-details-title">{{ task.name }}</h2>
          <TaskStatus :status="statusName" :paused="!task.schedule?.enabled" />
          <span v-if="scheduleText" class="schedule-pill">{{
            scheduleText
          }}</span>
        </div>

        <div class="task-details-actions">
          <button
            type="button"
            class="header-btn"
            :disabled="!!pauseDisabledReason"
            @click.stop="togglePaused"
          >
            <v-icon
              :icon="task.schedule?.enabled ? mdiPause : mdiPlay"
              size="14"
            />
            <span>{{ task.schedule?.enabled ? 'Pause' : 'Resume' }}</span>
          </button>

          <v-dialog v-model="editTaskDialogOpen" width="80rem">
            <template #activator="{ props }">
              <button
                v-bind="props"
                type="button"
                class="header-btn"
                :disabled="!canEdit"
              >
                <v-icon :icon="mdiPencil" size="14" />
                <span>Edit</span>
              </button>
            </template>
            <IngestionTaskForm
              :old-task="task"
              :data-connection="task.dataConnection"
              :workspace-id="workspaceId"
              @close="closeEditTaskDialog"
              @updated="onTaskUpdated"
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
                <v-icon :icon="mdiTrashCanOutline" size="14" />
                <span>Delete</span>
              </button>
            </template>
            <DeleteTaskCard :task="task" @close="null" @delete="deleteTask" />
          </v-dialog>

          <button
            type="button"
            class="header-btn header-btn--run"
            :disabled="!!runNowDisabledReason"
            @click="runNow"
          >
            <v-icon :icon="mdiPlay" size="14" />
            <span>{{ runNowRequested ? 'Run requested' : 'Run now' }}</span>
          </button>
        </div>
      </div>
    </header>

    <div class="task-details-tabs">
      <button
        type="button"
        class="task-details-tab"
        :class="{ 'task-details-tab--active': tab === 'runs' }"
        @click="tab = 'runs'"
      >
        Run history
      </button>
      <button
        type="button"
        class="task-details-tab"
        :class="{ 'task-details-tab--active': tab === 'mappings' }"
        @click="tab = 'mappings'"
      >
        Mappings
      </button>
    </div>

    <section class="task-details-body">
      <div class="task-details-panel">
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
        <template v-else>
          <Swimlanes v-if="task.mappings?.length" :task="task" />
          <p v-else class="empty">No mappings configured for this task.</p>
        </template>
      </div>
    </section>
  </div>
  <div v-else class="loading">Loading...</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import TaskStatus from '@/components/Orchestration/shared/TaskStatus.vue'
import IngestionTaskForm from '@/components/Orchestration/ingestion/IngestionTaskForm.vue'
import DeleteTaskCard from '@/components/Orchestration/shared/DeleteTaskCard.vue'
import Swimlanes from '@/components/Orchestration/ingestion/Swimlanes.vue'
import TaskRunHistory from '@/components/Orchestration/shared/TaskRunHistory.vue'
import { useSimpleTaskDetails } from '@/composables/orchestration/useSimpleTaskDetails'
import {
  mdiArrowLeft,
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
const tab = ref('runs')
const editTaskDialogOpen = ref(false)
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
} = useSimpleTaskDetails('etl', props, emit)

function closeEditTaskDialog() {
  editTaskDialogOpen.value = false
}

function onTaskUpdated() {
  closeEditTaskDialog()
  onUpdated()
}
</script>

<style scoped>
.task-details {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  height: 100%;
  background: #ffffff;
  overflow: hidden;
}

.task-details-header {
  padding: 14px 22px 0;
  border-bottom: 1px solid #e8e8e8;
  background: #ffffff;
  flex-shrink: 0;
}

.task-details-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  color: #1565c0;
  padding: 3px 6px;
  border-radius: 6px;
  margin-bottom: 8px;
}

.task-details-back:hover {
  background: rgba(0, 0, 0, 0.05);
}

.task-details-header-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding-bottom: 12px;
}

.task-details-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}

.task-details-title {
  font-size: 18px;
  font-weight: 400;
  color: #1c1b1f;
  margin: 0;
  overflow-wrap: anywhere;
}

.schedule-pill {
  font-size: 11px;
  background: #f5f7fa;
  border-radius: 4px;
  padding: 2px 7px;
  color: #49454f;
}

.task-details-actions {
  margin-left: auto;
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.header-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: 1px solid #cac4d0;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 12px;
  font-family: inherit;
  color: #1c1b1f;
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}

.header-btn:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.05);
}

.header-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.header-btn--run {
  border-color: #2e7d32;
  color: #2e7d32;
  font-weight: 500;
  padding: 6px 14px;
}

.header-btn--run:hover:not(:disabled) {
  background: rgba(46, 125, 50, 0.08);
}

.header-btn--danger {
  color: #b3261e;
}

.header-btn--danger:hover:not(:disabled) {
  background: rgba(179, 38, 30, 0.08);
  border-color: #b3261e;
}

.task-details-tabs {
  display: flex;
  gap: 4px;
}

.task-details-tab {
  background: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  color: #49454f;
  padding: 8px 14px;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 0.12s, border-color 0.12s;
}

.task-details-tab:hover {
  color: #1c1b1f;
}

.task-details-tab--active {
  color: #1565c0;
  border-bottom-color: #1565c0;
}

.task-details-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px;
  background: #f5f7fa;
  min-height: 0;
}

.task-details-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-details-panel :deep(.etl-source-display),
.task-details-panel :deep(.etl-target-display) {
  background: #ffffff;
}

.empty,
.loading {
  padding: 40px 20px;
  text-align: center;
  color: #5f5a67;
}
</style>
