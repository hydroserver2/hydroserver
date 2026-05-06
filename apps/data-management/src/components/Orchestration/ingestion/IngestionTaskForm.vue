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

        <IngestionTaskSchedule v-model:task="task" />

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
          :workspace-id="workspaceId"
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
import { ref } from 'vue'
import hs, {
  DataConnection,
  EtlMappingPostBody,
  Mapping,
  PlaceholderVariable,
  Task,
  TaskExpanded,
  TaskMapping,
  TaskSchedule,
} from '@hydroserver/client'
import StickyForm from '@/components/Forms/StickyForm.vue'
import IngestionTaskBasics from './IngestionTaskBasics.vue'
import IngestionTaskMappings from './IngestionTaskMappings.vue'
import IngestionTaskSchedule from './IngestionTaskSchedule.vue'
import IngestionTaskVariables from './IngestionTaskVariables.vue'
import { Snackbar } from '@/utils/notifications'

const props = defineProps<{
  oldTask?: TaskExpanded
  dataConnection: DataConnection
  workspaceId: string
}>()

const emit = defineEmits(['created', 'updated', 'close'])

const isEdit = !!props.oldTask
const valid = ref<boolean | null>(null)
const myForm = ref<VForm>()
const mappingsRef = ref<InstanceType<typeof IngestionTaskMappings>>()
const submitLoading = ref(false)
const workspaceId = props.workspaceId
const perTaskPlaceholders = props.dataConnection.placeholderVariables.filter(
  (variable): variable is PlaceholderVariable => variable.type === 'per_task'
)
const headerContextLabel = props.dataConnection.name || null

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

function cloneSchedule(schedule: TaskSchedule | null): TaskSchedule {
  return schedule ? { ...schedule } : defaultSchedule()
}

function hydrateTask(source?: TaskExpanded): Task {
  const base = source
    ? new Task({
        id: source.id,
        name: source.name,
        description: source.description ?? null,
        taskVariables: { ...source.taskVariables },
        dataConnectionId: source.dataConnection.id || props.dataConnection.id,
        mappings: source.mappings.map(editableMappingFrom),
        schedule: cloneSchedule(source.schedule),
      })
    : new Task({
        dataConnectionId: props.dataConnection.id,
        schedule: defaultSchedule(),
        mappings: [],
      })

  ;(['startTime', 'nextRunAt'] as const).forEach((k) => {
    if (base.schedule && base.schedule[k])
      base.schedule[k] = ensureIsoUtc(base.schedule[k])
  })

  return base
}

function initializeTaskVariables(base: Task) {
  if (!perTaskPlaceholders.length) return

  const current = base.taskVariables ?? {}
  base.taskVariables = Object.fromEntries(
    perTaskPlaceholders.map((placeholder) => [
      placeholder.name,
      current[placeholder.name] === undefined ? '' : current[placeholder.name],
    ])
  )
}

const task = ref<Task>(hydrateTask(props.oldTask))
initializeTaskVariables(task.value)

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function stringifyIdentifier(value: unknown): string {
  return value === undefined || value === null ? '' : String(value)
}

function editableMappingFrom(mapping: TaskMapping): Mapping {
  const sourceIdentifier = stringifyIdentifier(mapping.sourceIdentifier)

  if ('paths' in mapping) {
    return {
      sourceIdentifier,
      paths:
        mapping.paths.length > 0
          ? mapping.paths.map((path) => ({
              targetIdentifier: path.targetIdentifier,
              dataTransformations: [...path.dataTransformations],
            }))
          : [{ targetIdentifier: '', dataTransformations: [] }],
    }
  }

  return {
    sourceIdentifier,
    paths: [
      {
        targetIdentifier: targetDatastreamId(mapping),
        dataTransformations: [],
      },
    ],
  }
}

function targetDatastreamId(mapping: unknown): string {
  if (!isRecord(mapping)) return ''

  const paths = mapping.paths
  if (Array.isArray(paths)) {
    const firstPath = paths[0]
    if (isRecord(firstPath) && firstPath.targetIdentifier) {
      return String(firstPath.targetIdentifier)
    }
  }

  if (mapping.targetDatastreamId) return String(mapping.targetDatastreamId)

  const targetDatastream = mapping.targetDatastream
  if (isRecord(targetDatastream) && targetDatastream.id) {
    return String(targetDatastream.id)
  }

  return ''
}

function taskToPayload(): Task {
  return new Task({
    id: task.value.id,
    name: task.value.name,
    description: task.value.description,
    taskVariables: task.value.taskVariables,
    dataConnectionId: props.dataConnection.id,
    schedule: task.value.schedule ?? defaultSchedule(),
    mappings: task.value.mappings.map(
      (mapping): EtlMappingPostBody => ({
        sourceIdentifier: isRecord(mapping)
          ? stringifyIdentifier(mapping.sourceIdentifier)
          : '',
        targetDatastreamId: targetDatastreamId(mapping),
      })
    ),
  })
}

async function onSubmit() {
  const mappingsValid = mappingsRef.value?.validate() ?? false
  await myForm.value?.validate()
  if (!valid.value || !mappingsValid) return

  submitLoading.value = true
  try {
    task.value.dataConnectionId = props.dataConnection.id
    if (!task.value.schedule) task.value.schedule = defaultSchedule()

    const payload = taskToPayload()

    const res = isEdit
      ? await hs.tasks.update(payload)
      : await hs.tasks.create(payload)

    if (!res.ok) {
      Snackbar.error(res.message)
      console.error(res)
      return
    }

    const saved = res.data
    task.value = hydrateTask(saved)

    emit(isEdit ? 'updated' : 'created', saved)
    emit('close')
  } catch (error: unknown) {
    Snackbar.error(
      error instanceof Error ? error.message : 'Unable to save task.'
    )
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
