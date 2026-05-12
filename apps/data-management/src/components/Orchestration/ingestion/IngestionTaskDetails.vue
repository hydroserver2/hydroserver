<template>
  <div v-if="task" class="flex flex-col flex-1 min-h-0 h-full bg-white overflow-hidden">
    <header class="pt-[14px] border-b border-[#e8e8e8] bg-white shrink-0">
      <button class="task-details-back" type="button" @click="close">
        <v-icon :icon="mdiArrowLeft" size="16" />
        <span>{{ backLabel }}</span>
      </button>

      <div class="flex items-start gap-3 pb-3">
        <div class="flex items-center gap-[10px] flex-wrap min-w-0">
          <h2 class="task-details-title">{{ task.name }}</h2>
          <TaskStatus :status="statusName" :paused="!task.schedule?.enabled" />
          <span v-if="scheduleText" class="schedule-pill">{{ scheduleText }}</span>
        </div>

        <div class="ml-auto flex gap-2 shrink-0 flex-wrap">
          <button
            type="button"
            class="header-btn header-btn--neutral"
            :disabled="!!pauseDisabledReason"
            @click.stop="togglePaused"
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

          <v-dialog v-model="editTaskDialogOpen" width="80rem">
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
            <IngestionTaskForm
              :old-task="task"
              :data-connection="task.dataConnection"
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
                <v-icon :icon="mdiTrashCanOutline" size="16" />
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
            <v-icon :icon="mdiPlay" size="16" />
            <span>{{ runNowRequested ? 'Run requested' : 'Run now' }}</span>
          </button>
        </div>
      </div>
    </header>

    <div class="flex">
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
import NoScheduleIcon from '@/components/Orchestration/shared/NoScheduleIcon.vue'
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
header {
  padding-left: 22px;
  padding-right: 22px;
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
h2.task-details-title {
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
.header-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
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
.task-details-tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  color: #49454f;
  padding: 8px 14px;
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
