<template>
  <StickyForm>
    <template #header>
      <div class="task-form-header">
        <h2 class="task-form-title">{{ isEdit ? 'Edit task' : 'Add task' }}</h2>
        <div v-if="headerContextLabel" class="task-form-context">
          <span class="task-form-context-dot" />
          <span>{{ headerContextLabel }}</span>
        </div>
      </div>
    </template>

    <v-form
      @submit.prevent="onSubmit"
      ref="myForm"
      v-model="valid"
      validate-on="blur"
    >
      <div v-if="task" class="task-form-shell">
        <IngestionTaskBasics v-model:task="task" />

        <v-divider class="task-form-divider" />

        <IngestionTaskSchedule
          v-model:task="task"
          v-model:schedule-mode="scheduleMode"
          :timezone-label="timezoneLabel"
        />

        <v-divider
          v-if="perTaskPlaceholders.length"
          class="task-form-divider"
        />

        <IngestionTaskVariables
          v-if="perTaskPlaceholders.length"
          v-model:task="task"
          :placeholders="perTaskPlaceholders"
        />

        <v-divider class="task-form-divider" />

        <IngestionTaskMappings
          ref="mappingsRef"
          v-model:task="task"
          :workspace-id="taskWorkspaceId || null"
        />
      </div>
    </v-form>

    <template #actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn-primary :loading="submitLoading" type="button" @click="onSubmit">
        Save task
      </v-btn-primary>
    </template>
  </StickyForm>
</template>

<script setup lang="ts">
import { VForm } from 'vuetify/components'
import { computed, Ref, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import hs, {
  DataConnection,
  Task,
  TaskExpanded,
  TaskSchedule,
} from '@hydroserver/client'
import { useTaskStore } from '@/store/task'
import { useOrchestrationStore } from '@/store/orchestration'
import StickyForm from '@/components/Forms/StickyForm.vue'
import IngestionTaskBasics from './IngestionTaskBasics.vue'
import IngestionTaskMappings from './IngestionTaskMappings.vue'
import IngestionTaskSchedule from './IngestionTaskSchedule.vue'
import IngestionTaskVariables from './IngestionTaskVariables.vue'
import { useWorkspaceStore } from '@/store/workspaces'
import { Snackbar } from '@/utils/notifications'

const { selectedWorkspace } = storeToRefs(useWorkspaceStore())

const props = defineProps<{
  oldTask?: TaskExpanded
  dataConnectionId: string
}>()

const { tasks } = storeToRefs(useTaskStore())
const { workspaceTasks } = storeToRefs(useOrchestrationStore())

const emit = defineEmits(['created', 'updated', 'close'])

const isEdit = computed(() => !!props.oldTask || undefined)
const valid = ref<boolean | null>(null)
const myForm = ref<VForm>()
const mappingsRef = ref<InstanceType<typeof IngestionTaskMappings>>()
const submitLoading = ref(false)
const dataConnection = ref<DataConnection | null>(null)
const task = ref<Task>(new Task())
const scheduleMode = ref<'interval' | 'crontab'>('interval')

const taskWorkspaceId = computed(() => {
  return (
    (task.value as any).workspaceId ||
    (task.value as any)?.workspace?.id ||
    (dataConnection.value as any)?.workspace?.id ||
    (props.oldTask?.dataConnection as any)?.workspace?.id ||
    selectedWorkspace.value?.id ||
    ''
  )
})
const perTaskPlaceholders = computed<any[]>(() => {
  const placeholders = (dataConnection.value as any)?.placeholderVariables || []
  return placeholders.filter((v: any) => v?.type === 'per_task')
})

const timezoneLabel = computed(
  () => Intl.DateTimeFormat().resolvedOptions().timeZone
)
const headerContextLabel = computed(() => {
  return (
    dataConnection.value?.name ||
    (props.oldTask?.dataConnection as any)?.name ||
    null
  )
})

async function loadDataConnection(dataConnectionId?: string | null) {
  if (!dataConnectionId) {
    dataConnection.value = null
    return
  }

  try {
    const oldTaskDataConnection = props.oldTask?.dataConnection as
      | DataConnection
      | undefined
    if (
      oldTaskDataConnection &&
      String((oldTaskDataConnection as any).id) === dataConnectionId
    ) {
      dataConnection.value = oldTaskDataConnection
      return
    }

    const item = await hs.dataConnections.getItem(dataConnectionId, {
      expand_related: true,
    })
    dataConnection.value = item
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load data connection.')
    console.error(error)
  }
}

function defaultSchedule(): TaskSchedule {
  const now = new Date().toISOString()
  return {
    enabled: true,
    startTime: now,
    nextRunAt: null,
    crontab: null,
    interval: 1,
    intervalPeriod: 'days',
  }
}

function ensureIsoUtc(s: string | null = ''): string | null {
  return s && !/([Zz]|[+-]\d{2}:\d{2})$/.test(s) ? s + 'Z' : s
}

function hydrateTask(source?: TaskExpanded) {
  const base = source
    ? new Task(JSON.parse(JSON.stringify(source)))
    : new Task()

  if (!source) {
    ;(base as any).type = 'ETL'
    base.dataConnectionId = String(props.dataConnectionId)
    if (dataConnection.value) {
      ;(base as any).dataConnection = JSON.parse(
        JSON.stringify(dataConnection.value)
      )
    }
    const workspaceId =
      (dataConnection.value as any)?.workspace?.id ??
      selectedWorkspace.value?.id
    if (workspaceId) {
      ;(base as any).workspaceId = String(workspaceId)
    }
  }

  ;(base as any).type = (base as any).type || 'ETL'
  if (!base.schedule) base.schedule = defaultSchedule()
  if (!base.mappings) base.mappings = []
  if (!(base as any).workspaceId && (base as any).workspace?.id)
    (base as any).workspaceId = String((base as any).workspace.id)
  if (!base.dataConnectionId && (base as any).dataConnection?.id)
    base.dataConnectionId = String((base as any).dataConnection.id)
  ;(['startTime', 'nextRunAt'] as const).forEach((k) => {
    if (base.schedule && base.schedule[k])
      base.schedule[k] = ensureIsoUtc(base.schedule[k])
  })

  task.value = base
  scheduleMode.value = base.schedule?.crontab ? 'crontab' : 'interval'
}

function taskToPayload() {
  const flatMappings = (task.value.mappings as any[]).map((mapping: any) => ({
    sourceIdentifier: mapping.sourceIdentifier,
    targetDatastreamId: String(
      mapping.paths?.[0]?.targetIdentifier ??
        mapping.targetDatastreamId ??
        mapping.targetDatastream?.id ??
        ''
    ),
  }))

  return { ...task.value, mappings: flatMappings } as any
}

watch(
  () => props.oldTask,
  (newTask) => hydrateTask(newTask),
  { immediate: true }
)

watch(
  () => props.dataConnectionId,
  async (dataConnectionId) => {
    await loadDataConnection(dataConnectionId)
    hydrateTask(props.oldTask)
  },
  { immediate: true }
)

watch(
  () => perTaskPlaceholders.value.map((p) => p.name).join('|'),
  () => {
    const names = perTaskPlaceholders.value.map((p) => p.name)
    if (!names.length) return
    if (!(task.value as any).taskVariables)
      (task.value as any).taskVariables = {}
    const next: Record<string, any> = {}
    names.forEach((n) => {
      next[n] =
        (task.value as any).taskVariables[n] === undefined
          ? ''
          : (task.value as any).taskVariables[n]
    })
    ;(task.value as any).taskVariables = next
  },
  { immediate: true }
)

function upsertTaskList(listRef: { value: Task[] }, saved: Task) {
  const index = listRef.value.findIndex((p) => p.id === saved.id)
  if (index !== -1) listRef.value[index] = saved
  else listRef.value = [...listRef.value, saved]
}

async function onSubmit() {
  const mappingsValid = mappingsRef.value?.validate() ?? false
  await myForm.value?.validate()
  if (!valid.value || !mappingsValid) return

  submitLoading.value = true
  try {
    ;(task.value as any).workspaceId = taskWorkspaceId.value || ''
    ;(task.value as any).type = 'ETL'
    task.value.dataConnectionId = String(props.dataConnectionId)
    if (!task.value.schedule) task.value.schedule = defaultSchedule()

    const payload = taskToPayload()

    const res = isEdit.value
      ? await hs.tasks.update(payload)
      : await hs.tasks.create(payload)

    if (!res.ok) {
      Snackbar.error(res.message)
      console.error(res)
      return
    }

    const saved = res.data
    upsertTaskList(tasks, saved)
    upsertTaskList(workspaceTasks as unknown as Ref<Task[]>, saved)
    hydrateTask(saved)

    emit(isEdit.value ? 'updated' : 'created', saved)
    emit('close')
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to save task.')
    console.error(error)
  } finally {
    submitLoading.value = false
  }
}
</script>

<style scoped>
:deep(.v-expansion-panel-text__wrapper) {
  padding: 0 !important;
}

.task-form-header {
  padding: 10px 18px 8px;
}
.task-form-title {
  font-size: 1rem;
  line-height: 1.2;
  font-weight: 500;
  color: #1c1b1f;
}
.task-form-context {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 3px;
  color: #4f4b59;
  font-size: 0.74rem;
  font-weight: 500;
}
.task-form-context-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #1565c0;
}
.task-form-shell {
  padding: 10px 14px 12px;
}
.task-form-divider {
  margin: 8px 0;
}
:deep(.task-form-shell .v-field) {
  --v-input-control-height: 38px;
}

:deep(.task-form-shell .v-field__input) {
  min-height: 38px;
  padding-top: 0;
  padding-bottom: 0;
  font-size: 0.86rem;
}

:deep(.task-form-shell .v-label) {
  font-size: 0.76rem;
}

:deep(.task-form-shell .v-messages) {
  min-height: 12px;
  font-size: 0.66rem;
}

@media (max-width: 900px) {
  .task-form-header,
  .task-form-shell {
    padding-left: 14px;
    padding-right: 14px;
  }
}

@media (max-width: 640px) {
  .task-form-shell {
    padding-bottom: 14px;
  }
}
</style>
