<template>
  <StickyForm>
    <template #header>
      <div class="task-form-header">
        <h2 class="hs-subheading">
          {{ isEdit ? 'Edit task' : 'Add task' }}
        </h2>
        <div v-if="headerContextLabel" class="task-form-header__context">
          <span class="task-form-header__dot" />
          <span class="hs-text-sm">{{ headerContextLabel }}</span>
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
        <TaskFormLayout>
          <TaskFormSection>
            <v-text-field
              v-model="task.name"
              label="Task name"
              class="required-label"
              placeholder="e.g. North Fork telemetry import"
              :rules="rules.requiredAndMaxLength255"
            />
          </TaskFormSection>

          <v-divider />

          <ScheduleFields v-model="task.schedule" :color="INGESTION_ACCENT" />

          <template v-if="perTaskPlaceholders.length">
            <v-divider />

            <TaskFormSection title="Template variables">
              <p class="form-note hs-text-sm">
                Fill in values for URL placeholders defined in this data
                connection.
              </p>

              <div class="template-variables">
                <v-text-field
                  v-for="variable in perTaskPlaceholders"
                  :key="variable.name"
                  v-model="task.taskVariables[variable.name]"
                  :label="variable.name"
                  class="required-label"
                  :placeholder="templateVariablePlaceholder(variable.name)"
                  :rules="rules.requiredAndMaxLength255"
                />
              </div>
            </TaskFormSection>
          </template>

          <v-divider />

          <TaskFormSection title="Data mapping">
            <p class="form-note hs-text-sm">
              Map each source field (CSV column or JSON key) to a HydroServer
              datastream.
            </p>

            <v-alert
              v-if="noMappingsError"
              type="error"
              variant="tonal"
              density="compact"
            >
              At least one source target mapping is required.
            </v-alert>

            <div class="mapping-list">
              <div class="mapping-row mapping-row--headers">
                <label class="hs-title required-label">Source field</label>
                <div />
                <label class="hs-title required-label">Target datastream</label>
                <div />
              </div>

              <div
                v-for="(mapping, index) in formMappings"
                :key="index"
                class="mapping-row"
              >
                <v-text-field
                  v-model="mapping.sourceIdentifier"
                  placeholder="CSV column or JSON key"
                  :rules="rules.requiredAndMaxLength150"
                />

                <div class="mapping-row__arrow">
                  <v-icon :icon="mdiArrowRight" size="22" />
                </div>

                <DatastreamCardSelector
                  v-model="mapping.targetDatastreamId"
                  :datastreams="workspaceDatastreams"
                  :monitoring-sites="workspaceMonitoringSites"
                  :workspace-id="selectedWorkspaceId"
                  :draft-datastreams="draftDatastreams"
                  enforce-unique-selections
                  label="Target datastream"
                  placeholder="Select target datastream"
                  :clearable="false"
                  :rules="rules.required"
                  density="compact"
                  @select="onTargetSelected(index, $event)"
                />

                <v-btn-icon
                  :icon="mdiTrashCanOutline"
                  size="small"
                  aria-label="Delete mapping"
                  @click.stop="removeMapping(index)"
                />
              </div>

              <div>
                <v-btn
                  variant="outlined"
                  size="small"
                  type="button"
                  :color="INGESTION_ACCENT"
                  :prepend-icon="mdiPlus"
                  @click="addMapping"
                >
                  Add mapping
                </v-btn>
              </div>
            </div>
          </TaskFormSection>
        </TaskFormLayout>
      </div>
    </v-form>

    <template #actions>
      <v-spacer />
      <v-btn-cancel @click="closeForm">Cancel</v-btn-cancel>
      <v-btn-dialog-action
        :loading="submitLoading"
        :color="INGESTION_ACCENT"
        type="submit"
        @click="onSubmit"
      >
        Save task
      </v-btn-dialog-action>
    </template>
  </StickyForm>
</template>

<script setup lang="ts">
import { VForm } from 'vuetify/components'
import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import hs, {
  DataConnection,
  DatastreamExtended,
  EtlMappingPostBody,
  PlaceholderVariable,
  Task,
  TaskExpanded,
  TaskSchedule,
} from '@hydroserver/client'
import StickyForm from '@/components/Forms/StickyForm.vue'
import DatastreamCardSelector from '@/components/Orchestration/shared/DatastreamCardSelector.vue'
import ScheduleFields from '@/components/Orchestration/shared/ScheduleFields.vue'
import TaskFormLayout from '@/components/Orchestration/shared/TaskFormLayout.vue'
import TaskFormSection from '@/components/Orchestration/shared/TaskFormSection.vue'
import { Snackbar } from '@/utils/notifications'
import { rules } from '@/utils/rules'
import { ensureIsoUtc } from '@/utils/time'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'
import { INGESTION_ACCENT } from '../workbench/orchestrationTabs'
import { mdiArrowRight, mdiPlus, mdiTrashCanOutline } from '@mdi/js'

type FormMapping = { sourceIdentifier: string; targetDatastreamId: string }

const props = defineProps<{
  oldTask?: TaskExpanded
  dataConnection: DataConnection
}>()

const emit = defineEmits(['created', 'updated', 'close'])

const isEdit = !!props.oldTask
const valid = ref<boolean | null>(null)
const myForm = ref<VForm>()
const submitLoading = ref(false)
const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
const selectedWorkspaceId = computed(() => selectedWorkspace.value?.id ?? null)
const perTaskPlaceholders = props.dataConnection.placeholderVariables.filter(
  (variable): variable is PlaceholderVariable => variable.type === 'per_task'
)
const headerContextLabel = props.dataConnection.name || null

const orchestrationStore = useOrchestrationStore()
const {
  linkedDatastreamIds,
  draftDatastreams,
  workspaceDatastreams,
  workspaceMonitoringSites,
} = storeToRefs(orchestrationStore)
const { ensureWorkspaceDatastreams, ensureWorkspaceMonitoringSites } =
  orchestrationStore

const noMappingsError = ref(false)

function defaultSchedule(): TaskSchedule {
  return {
    enabled: true,
    startTime: new Date().toISOString(),
    nextRunAt: null,
    crontab: null,
    interval: 1,
    intervalPeriod: 'days',
  }
}

function cloneSchedule(schedule: TaskSchedule | null): TaskSchedule | null {
  return schedule ? { ...schedule } : null
}

function editableMappingFrom(mapping: any): FormMapping {
  const id = mapping.targetDatastreamId
    ? String(mapping.targetDatastreamId)
    : mapping.targetDatastream?.id
      ? String(mapping.targetDatastream.id)
      : ''
  return {
    sourceIdentifier: String(mapping.sourceIdentifier ?? ''),
    targetDatastreamId: id,
  }
}

function hydrateTask(source?: TaskExpanded): Task {
  const base = source
    ? new Task({
        id: source.id,
        name: source.name,
        description: source.description ?? null,
        taskVariables: { ...source.taskVariables },
        dataConnectionId: source.dataConnection.id ?? props.dataConnection.id,
        mappings: source.mappings.map(editableMappingFrom) as any,
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
if (task.value.mappings.length === 0) {
  task.value.mappings.push({
    sourceIdentifier: '',
    targetDatastreamId: '',
  } as any)
}

const formMappings = computed(
  () => task.value.mappings as unknown as FormMapping[]
)
function templateVariablePlaceholder(name: string) {
  return `e.g. ${name.toUpperCase()}`
}

function syncDraftDatastreams() {
  const refIds = new Set(
    formMappings.value.map((m) => m.targetDatastreamId).filter(Boolean)
  )
  const keepIds = new Set(
    [...refIds].filter((id) => !linkedDatastreamIds.value.has(id))
  )
  const byId = new Map<string, DatastreamExtended>()
  for (const ds of draftDatastreams.value) {
    const key = String(ds.id)
    if (keepIds.has(key) && !byId.has(key)) byId.set(key, ds)
  }
  draftDatastreams.value = [...byId.values()]
}

function onTargetSelected(index: number, datastream: DatastreamExtended) {
  if (!formMappings.value[index]) return
  // Keep the picked record around so it stays visible in the selector's list
  // even before the task is saved.
  draftDatastreams.value = [datastream, ...draftDatastreams.value]
  syncDraftDatastreams()
}

function removeMapping(mi: number) {
  task.value.mappings.splice(mi, 1)
  syncDraftDatastreams()
}

function addMapping() {
  task.value.mappings.push({
    sourceIdentifier: '',
    targetDatastreamId: '',
  } as any)
  noMappingsError.value = false
}

function closeForm() {
  draftDatastreams.value = []
  emit('close')
}

// Each row's fields validate themselves through the form; only "no rows at
// all" has no field to hang an error on.
function validateMappings() {
  noMappingsError.value = formMappings.value.length === 0
  return !noMappingsError.value
}

function taskToPayload(): Task {
  return new Task({
    id: task.value.id,
    name: task.value.name,
    description: task.value.description,
    taskVariables: task.value.taskVariables,
    dataConnectionId: props.dataConnection.id,
    schedule: task.value.schedule,
    mappings: formMappings.value.map((m): EtlMappingPostBody => ({
      sourceIdentifier: m.sourceIdentifier,
      targetDatastreamId: m.targetDatastreamId,
    })),
  })
}

async function onSubmit() {
  const mappingsValid = validateMappings()
  await myForm.value?.validate()
  if (!valid.value || !mappingsValid) return
  submitLoading.value = true
  try {
    const payload = taskToPayload()
    const res = isEdit
      ? await hs.tasks.update(payload)
      : await hs.tasks.create(payload)
    if (!res.ok) {
      Snackbar.error(res.message)
      console.error(res)
      return
    }
    emit(isEdit ? 'updated' : 'created', res.data)
    closeForm()
  } catch (error: unknown) {
    Snackbar.error(
      error instanceof Error ? error.message : 'Unable to save task.'
    )
    console.error(error)
  } finally {
    submitLoading.value = false
  }
}

watch(
  selectedWorkspaceId,
  async (workspaceId) => {
    if (!workspaceId) return
    try {
      await Promise.all([
        ensureWorkspaceDatastreams(workspaceId),
        ensureWorkspaceMonitoringSites(workspaceId),
      ])
    } catch (error) {
      console.error(
        'Error fetching workspace datastreams and monitoringSites',
        error
      )
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.task-form-header {
  padding: var(--hs-space-16) var(--hs-space-24) var(--hs-space-12);
}

.task-form-header__context {
  display: flex;
  gap: var(--hs-space-8);
  align-items: center;
  margin-top: var(--hs-space-4);
  color: var(--hs-text-secondary);
}

.task-form-header__dot {
  width: 10px;
  height: 10px;
  background: v-bind(INGESTION_ACCENT);
  /* A dot is a shape, not a step on the radius scale. */
  border-radius: 50%;
}

.task-form-shell {
  padding: var(--hs-space-16) var(--hs-space-24);
}

.form-note {
  margin: 0;
  color: var(--hs-text-secondary);
}

.template-variables {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 420px));
  gap: var(--hs-space-12);
}

.mapping-list {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-12);
}

.mapping-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--hs-space-32) minmax(0, 2fr) auto;
  gap: var(--hs-space-8);
  align-items: center;
}

.mapping-row--headers {
  color: var(--hs-text-secondary);
}

.mapping-row__arrow {
  display: flex;
  justify-content: center;
  color: var(--hs-text-muted);
}

:deep(.sticky-form-card) {
  border-radius: var(--hs-radius-lg) !important;
}

:deep(.sticky-header .v-divider),
:deep(.sticky-actions .v-divider) {
  border-color: var(--hs-border) !important;
  opacity: 1;
}

:deep(.sticky-actions .v-card-actions) {
  gap: var(--hs-space-8);
  padding: var(--hs-space-8) var(--hs-space-24);
}

:deep(.schedule-start-input .v-field__input) {
  align-items: center;
  padding-right: var(--hs-space-8);
}

:deep(.schedule-start-input input[type='datetime-local']) {
  min-width: 0;
  padding-right: var(--hs-space-8);
  line-height: 1;
}

:deep(
  .schedule-start-input
    input[type='datetime-local']::-webkit-calendar-picker-indicator
) {
  width: 16px;
  height: 16px;
  margin: 0 var(--hs-space-4) 0 var(--hs-space-2);
  padding: 0;
  opacity: 0.82;
  transform: translateY(-1px);
}

@media (max-width: 640px) {
  .task-form-header {
    padding-inline: var(--hs-space-16);
  }

  .task-form-shell {
    padding: var(--hs-space-12) var(--hs-space-16);
  }

  .mapping-row {
    grid-template-columns: minmax(0, 1fr);
  }

  .mapping-row--headers {
    display: none;
  }

  .mapping-row__arrow {
    justify-content: flex-start;
  }
}
</style>
