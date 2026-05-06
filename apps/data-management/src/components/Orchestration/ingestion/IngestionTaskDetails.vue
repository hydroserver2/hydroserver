<template>
  <div v-if="task" class="flex flex-col flex-1 min-h-0 h-full bg-white overflow-hidden">
    <header class="px-[22px] pt-[14px] border-b border-[#e8e8e8] bg-white shrink-0">
      <button
        class="inline-flex items-center gap-1.5 bg-transparent border-none cursor-pointer font-[inherit] text-xs font-medium text-[#1565c0] px-1.5 py-[3px] rounded-md mb-2 hover:bg-black/5"
        type="button"
        @click="close"
      >
        <v-icon :icon="mdiArrowLeft" size="16" />
        <span>{{ backLabel }}</span>
      </button>

      <div class="flex items-start gap-3 pb-3">
        <div class="flex items-center gap-[10px] flex-wrap min-w-0">
          <h2 class="text-[18px] font-normal text-[#1c1b1f] m-0 [overflow-wrap:anywhere]">
            {{ task.name }}
          </h2>
          <TaskStatus :status="statusName" :paused="!task.schedule?.enabled" />
          <span
            v-if="scheduleText"
            class="text-[11px] bg-[#f5f7fa] rounded-[4px] px-[7px] py-[2px] text-[#49454f]"
          >
            {{ scheduleText }}
          </span>
        </div>

        <div class="ml-auto flex gap-1.5 shrink-0 flex-wrap">
          <button
            type="button"
            class="header-btn inline-flex items-center gap-[5px] bg-transparent border border-[#cac4d0] rounded-lg px-3 py-1.5 text-xs font-[inherit] text-[#1c1b1f] cursor-pointer transition-[background,color,border-color] duration-[120ms] disabled:opacity-55 disabled:cursor-not-allowed"
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
                class="header-btn inline-flex items-center gap-[5px] bg-transparent border border-[#cac4d0] rounded-lg px-3 py-1.5 text-xs font-[inherit] text-[#1c1b1f] cursor-pointer transition-[background,color,border-color] duration-[120ms] disabled:opacity-55 disabled:cursor-not-allowed"
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
                class="header-btn header-btn--danger inline-flex items-center gap-[5px] bg-transparent border border-[#cac4d0] rounded-lg px-3 py-1.5 text-xs font-[inherit] text-[#b3261e] cursor-pointer transition-[background,color,border-color] duration-[120ms] disabled:opacity-55 disabled:cursor-not-allowed"
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
            class="header-btn header-btn--run inline-flex items-center gap-[5px] bg-transparent border border-[#2e7d32] rounded-lg px-3.5 py-1.5 text-xs font-medium font-[inherit] text-[#2e7d32] cursor-pointer transition-[background,color,border-color] duration-[120ms] disabled:opacity-55 disabled:cursor-not-allowed"
            :disabled="!!runNowDisabledReason"
            @click="runNow"
          >
            <v-icon :icon="mdiPlay" size="14" />
            <span>{{ runNowRequested ? 'Run requested' : 'Run now' }}</span>
          </button>
        </div>
      </div>
    </header>

    <div class="flex gap-1">
      <button
        type="button"
        class="task-details-tab bg-transparent border-0 cursor-pointer font-[inherit] text-[13px] font-medium text-[#49454f] px-3.5 py-2 border-b-2 border-b-transparent -mb-px transition-[color,border-color] duration-[120ms]"
        :class="{ 'text-[#1565c0] !border-b-[#1565c0]': tab === 'runs' }"
        @click="tab = 'runs'"
      >
        Run history
      </button>
      <button
        type="button"
        class="task-details-tab bg-transparent border-0 cursor-pointer font-[inherit] text-[13px] font-medium text-[#49454f] px-3.5 py-2 border-b-2 border-b-transparent -mb-px transition-[color,border-color] duration-[120ms]"
        :class="{ 'text-[#1565c0] !border-b-[#1565c0]': tab === 'mappings' }"
        @click="tab = 'mappings'"
      >
        Mappings
      </button>
    </div>

    <section class="flex-1 overflow-y-auto px-[22px] py-4 bg-[#f5f7fa] min-h-0">
      <div class="task-details-panel flex flex-col gap-2">
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
          <p
            v-else
            class="py-[40px] px-[20px] text-center text-[#5f5a67]"
          >
            No mappings configured for this task.
          </p>
        </template>
      </div>
    </section>
  </div>
  <div
    v-else
    class="py-[40px] px-[20px] text-center text-[#5f5a67]"
  >
    Loading...
  </div>
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
.header-btn:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.05);
}
.header-btn--run:hover:not(:disabled) {
  background: rgba(46, 125, 50, 0.08);
}
.header-btn--danger:hover:not(:disabled) {
  background: rgba(179, 38, 30, 0.08);
  border-color: #b3261e;
}
.task-details-tab:hover {
  color: #1c1b1f;
}
.task-details-panel :deep(.etl-source-display),
.task-details-panel :deep(.etl-target-display) {
  background: #ffffff;
}
</style>
