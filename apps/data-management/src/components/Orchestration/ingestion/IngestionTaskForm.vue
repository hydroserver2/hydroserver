<template>
  <StickyForm>
    <template #header>
      <div class="px-6 pt-4 pb-3 max-[640px]:px-4">
        <h2 class="text-[1.15rem] leading-tight font-medium text-[#1c1b1f]">
          {{ isEdit ? 'Edit task' : 'Add task' }}
        </h2>
        <div
          v-if="headerContextLabel"
          class="mt-1 flex items-center gap-2 text-[0.82rem] font-medium text-[#4f4b59]"
        >
          <span class="size-2.5 rounded-full bg-[#1565c0]" />
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
      <div
        v-if="task"
        class="task-form-shell mx-6 my-4 max-[640px]:mx-4 max-[640px]:my-3 [&_.v-messages]:min-h-3 [&_.v-messages]:text-[0.66rem]"
      >
        <div class="flex flex-col gap-2">
          <div class="flex flex-col gap-2">
            <label
              class="text-[0.82rem] font-bold text-[#1f1d24]"
              for="task-name"
            >
              Task name <span class="text-[#d32f2f]">*</span>
            </label>
            <v-text-field
              id="task-name"
              v-model="task.name"
              placeholder="e.g. North Fork telemetry import"
              :rules="rules.requiredAndMaxLength255"
              variant="outlined"
              rounded="lg"
              density="compact"
              hide-details="auto"
            />
          </div>
        </div>

        <v-divider class="my-4" />

        <ScheduleFields v-model="task.schedule" color="#1565c0" />

        <v-divider v-if="perTaskPlaceholders.length" class="my-4" />

        <div v-if="perTaskPlaceholders.length" class="flex flex-col gap-3">
          <div class="flex flex-col gap-1">
            <h3
              class="text-[0.72rem] font-extrabold uppercase tracking-[0.08em] text-[#4f4b59]"
            >
              Template variables
            </h3>
            <p class="text-[0.8rem] leading-[1.35] text-[#5f5a67]">
              Fill in values for URL placeholders defined in this data
              connection.
            </p>
          </div>

          <div
            class="grid grid-cols-[repeat(auto-fit,minmax(260px,420px))] gap-2"
          >
            <div
              v-for="variable in perTaskPlaceholders"
              :key="variable.name"
              class="flex flex-col gap-1"
            >
              <label
                class="text-[0.82rem] font-bold text-[#1f1d24]"
                :for="`task-variable-${variable.name}`"
              >
                {{ variable.name }} <span class="text-[#d32f2f]">*</span>
              </label>
              <v-text-field
                :id="`task-variable-${variable.name}`"
                v-model="task.taskVariables[variable.name]"
                :placeholder="templateVariablePlaceholder(variable.name)"
                :rules="rules.requiredAndMaxLength255"
                variant="outlined"
                rounded="lg"
                density="compact"
                hide-details="auto"
              />
            </div>
          </div>
        </div>

        <v-divider class="my-4" />

        <div class="flex flex-col gap-3">
          <div class="flex flex-col gap-1">
            <h3
              class="text-[0.72rem] font-extrabold uppercase tracking-[0.08em] text-[#4f4b59]"
            >
              Data mapping
            </h3>
            <p class="text-[0.8rem] leading-[1.35] text-[#5f5a67]">
              Map each source field (CSV column or JSON key) to a HydroServer
              datastream.
            </p>
          </div>

          <v-alert
            v-if="showErrors && noMappingsError"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-3"
          >
            At least one source target mapping is required.
          </v-alert>

          <div class="flex flex-col gap-2">
            <div
              class="grid grid-cols-[minmax(0,1fr)_42px_minmax(0,2fr)_44px] gap-2 max-[640px]:hidden"
            >
              <div
                class="text-[0.72rem] font-extrabold uppercase tracking-[0.04em] text-[#4f4b59]"
              >
                Source field
              </div>
              <div />
              <div
                class="text-[0.72rem] font-extrabold uppercase tracking-[0.04em] text-[#4f4b59]"
              >
                Target datastream
              </div>
              <div />
            </div>

            <template v-for="(m, mi) in formMappings" :key="mi">
              <div
                class="grid grid-cols-[minmax(0,1fr)_42px_minmax(0,2fr)_44px] items-center gap-2 max-[640px]:grid-cols-1 max-[640px]:gap-2"
              >
                <div class="min-w-0 self-center [&_.v-field__input]:text-left">
                  <v-text-field
                    v-model="m.sourceIdentifier"
                    placeholder="CSV column or JSON key"
                    density="compact"
                    variant="outlined"
                    rounded="lg"
                    hide-details="auto"
                    :rules="rules.requiredAndMaxLength150"
                  />
                </div>

                <div
                  class="flex items-center justify-center text-[#c0b8c9] min-h-[40px] max-[640px]:justify-start max-[640px]:min-h-0"
                >
                  <v-icon :icon="mdiArrowRight" size="22" />
                </div>

                <div class="min-w-0 self-center">
                  <v-btn
                    v-if="!m.targetDatastreamId"
                    variant="outlined"
                    rounded="lg"
                    type="button"
                    class="h-auto min-h-10 w-full justify-start border-2 border-dashed border-[#1565c0] bg-[#f6f9ff] px-3 py-1.5 text-left text-[0.84rem] text-[#1565c0] normal-case [&_.v-btn__content]:w-full [&_.v-btn__content]:min-w-0 [&_.v-btn__content]:justify-start [&_.v-btn__content]:overflow-visible [&_.v-btn__content]:text-left"
                    :class="{
                      'border-[#d32f2f] text-[#d32f2f]': hasTargetError(mi),
                    }"
                    @click="openTargetSelector(mi)"
                  >
                    <span class="inline-flex items-center gap-1.5 font-bold">
                      <v-icon :icon="mdiPlusCircleOutline" size="18" />
                      <span>Select target datastream</span>
                    </span>
                  </v-btn>

                  <v-btn
                    v-else
                    variant="outlined"
                    rounded="lg"
                    type="button"
                    class="h-auto min-h-[48px] w-full justify-start border-2 border-solid border-[#1565c0] bg-white px-3 py-1.5 text-left text-[0.84rem] text-[#1c1b1f] normal-case [&_.v-btn__content]:w-full [&_.v-btn__content]:min-w-0 [&_.v-btn__content]:justify-start [&_.v-btn__content]:overflow-visible [&_.v-btn__content]:text-left"
                    @click="openTargetSelector(mi)"
                  >
                    <span class="block max-w-full leading-[1.25] py-[2px]">
                      <span
                        class="block whitespace-normal font-semibold text-[#1c1b1f] [overflow-wrap:anywhere]"
                      >
                        {{ datastreamNameById(m.targetDatastreamId) }}
                      </span>
                      <span
                        class="block whitespace-normal text-[0.72rem] text-[rgba(0,0,0,0.55)] [overflow-wrap:anywhere]"
                      >
                        {{ m.targetDatastreamId }}
                      </span>
                    </span>
                  </v-btn>

                  <div
                    v-if="hasTargetError(mi)"
                    class="text-error text-caption mt-1"
                  >
                    Target is required
                  </div>
                </div>

                <div
                  class="flex items-center justify-center min-h-[40px] max-[640px]:justify-start max-[640px]:min-h-0"
                >
                  <v-btn
                    icon
                    variant="text"
                    color="grey-lighten-1"
                    type="button"
                    title="Delete mapping"
                    @click.stop="removeMapping(mi)"
                  >
                    <v-icon
                      :icon="mdiTrashCanOutline"
                      color="red-darken-3"
                      size="22"
                    />
                  </v-btn>
                </div>
              </div>
            </template>

            <div class="mt-px">
              <v-btn
                variant="outlined"
                rounded="lg"
                type="button"
                class="min-h-9 w-fit border-2 border-dashed border-[#d0c9d8] px-3 text-[0.84rem] text-[#1565c0] normal-case"
                :prepend-icon="mdiPlus"
                @click="addMapping"
              >
                Add mapping
              </v-btn>
            </div>
          </div>
        </div>
      </div>
    </v-form>

    <template #actions>
      <v-spacer />
      <v-btn-cancel @click="closeForm">Cancel</v-btn-cancel>
      <v-btn-primary
        :loading="submitLoading"
        :color="INGESTION_ACCENT"
        type="submit"
        @click="onSubmit"
      >
        Save task
      </v-btn-primary>
    </template>
  </StickyForm>

  <v-dialog v-model="datastreamSelectorOpen" width="75rem">
    <DatastreamSelectorCard
      card-title="Select a target datastream"
      @selected-datastream="onTargetSelected"
      @close="datastreamSelectorOpen = false"
      enforce-unique-selections
      :draft-datastreams="draftDatastreams"
    />
  </v-dialog>
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
import DatastreamSelectorCard from '@/components/Datastream/DatastreamSelectorCard.vue'
import ScheduleFields from '@/components/Orchestration/shared/ScheduleFields.vue'
import { Snackbar } from '@/utils/notifications'
import { rules } from '@/utils/rules'
import { ensureIsoUtc } from '@/utils/time'
import { useOrchestrationStore } from '@/store/orchestration'
import { useWorkspaceStore } from '@/store/workspaces'
import { INGESTION_ACCENT } from '../workbench/orchestrationTabs'
import {
  mdiArrowRight,
  mdiPlus,
  mdiPlusCircleOutline,
  mdiTrashCanOutline,
} from '@mdi/js'

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
  linkedDatastreams,
  draftDatastreams,
  workspaceDatastreams,
  workspaceThings,
} = storeToRefs(orchestrationStore)
const { ensureWorkspaceDatastreams, ensureWorkspaceThings } = orchestrationStore

const showErrors = ref(false)
const missingTargetKeys = ref<Set<string>>(new Set())
const noMappingsError = ref(false)
const datastreamSelectorOpen = ref(false)
const activeMappingIndex = ref<number | null>(null)

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
        dataConnectionId: source.dataConnection.id || props.dataConnection.id,
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

function hasTargetError(mi: number) {
  return showErrors.value && missingTargetKeys.value.has(`${mi}`)
}

function datastreamById(id: string | undefined | null): any {
  if (!id) return null
  return (
    workspaceDatastreams.value.find((d) => String(d.id) === id) ||
    linkedDatastreams.value.find((d) => String(d.id) === id) ||
    draftDatastreams.value.find((d) => String(d.id) === id) ||
    null
  )
}

function datastreamNameById(id: string | undefined | null) {
  return datastreamById(id)?.name || ''
}

function openTargetSelector(mi: number) {
  activeMappingIndex.value = mi
  datastreamSelectorOpen.value = true
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

function onTargetSelected(event: DatastreamExtended) {
  const mi = activeMappingIndex.value
  if (mi == null) return
  const m = formMappings.value[mi]
  if (!m) return
  m.targetDatastreamId = String(event.id)
  draftDatastreams.value = [event, ...draftDatastreams.value]
  syncDraftDatastreams()
  if (missingTargetKeys.value.has(`${mi}`)) {
    const next = new Set(missingTargetKeys.value)
    next.delete(`${mi}`)
    missingTargetKeys.value = next
  }
  activeMappingIndex.value = null
  datastreamSelectorOpen.value = false
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

function validateMappings() {
  showErrors.value = true
  noMappingsError.value = formMappings.value.length === 0
  const nextMissingKeys = new Set<string>()
  formMappings.value.forEach((m, mi) => {
    if (!m.targetDatastreamId) nextMissingKeys.add(`${mi}`)
  })
  missingTargetKeys.value = nextMissingKeys
  return !noMappingsError.value && nextMissingKeys.size === 0
}

function taskToPayload(): Task {
  return new Task({
    id: task.value.id,
    name: task.value.name,
    description: task.value.description,
    taskVariables: task.value.taskVariables,
    dataConnectionId: props.dataConnection.id,
    schedule: task.value.schedule,
    mappings: formMappings.value.map(
      (m): EtlMappingPostBody => ({
        sourceIdentifier: m.sourceIdentifier,
        targetDatastreamId: m.targetDatastreamId,
      })
    ),
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
    task.value = hydrateTask(res.data)
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
        ensureWorkspaceThings(workspaceId),
      ])
    } catch (error) {
      console.error('Error fetching workspace datastreams and things', error)
    }
  },
  { immediate: true }
)
</script>

<style scoped>
:deep(.sticky-form-card) {
  border-radius: 12px !important;
}
:deep(.sticky-header .v-divider),
:deep(.sticky-actions .v-divider) {
  border-color: #e7e2eb !important;
  opacity: 1;
}
:deep(.v-expansion-panel-text__wrapper) {
  padding: 0 !important;
}
:deep(.sticky-actions .v-card-actions) {
  padding: 8px 24px;
  gap: 8px;
}
:deep(.schedule-start-input .v-field__input) {
  align-items: center;
  padding-right: 8px;
}
:deep(.schedule-start-input input[type='datetime-local']) {
  line-height: 1;
  min-width: 0;
  padding-right: 8px;
}
:deep(
    .schedule-start-input
      input[type='datetime-local']::-webkit-calendar-picker-indicator
  ) {
  height: 16px;
  margin: 0 4px 0 2px;
  padding: 0;
  width: 16px;
  opacity: 0.82;
  transform: translateY(-1px);
}
</style>
