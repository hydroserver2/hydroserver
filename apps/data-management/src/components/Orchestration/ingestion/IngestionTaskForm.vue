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

        <div class="flex flex-col gap-3">
          <div class="flex items-baseline gap-2">
            <h3
              class="text-[0.72rem] font-extrabold uppercase tracking-[0.08em] text-[#4f4b59]"
            >
              Schedule
            </h3>
            <span class="text-[0.78rem] leading-[1.3] text-[#5f5a67]">
              {{ timezoneLabel }}
            </span>
          </div>

          <div
            class="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-3"
          >
            <div
              class="min-h-[92px] cursor-pointer rounded-lg border border-[#d0c9d8] bg-white px-3 py-3 outline-none transition-[border-color,background-color,box-shadow] duration-[160ms] ease-in-out hover:border-[#1565c0] focus-visible:border-[#1565c0]"
              :class="{
                '!border-2 !border-[#1565c0] !bg-[#edf3ff] shadow-[inset_0_0_0_1px_rgba(21,101,192,0.05)] [&_.v-field]:bg-white [&_.v-field__overlay]:bg-transparent [&_.v-field__outline]:[--v-field-border-opacity:1]':
                  scheduleMode === 'interval',
              }"
              tabindex="0"
              role="button"
              @click="selectScheduleMode('interval')"
              @keydown.enter.prevent="selectScheduleMode('interval')"
              @keydown.space.prevent="selectScheduleMode('interval')"
            >
              <div class="flex items-start gap-2">
                <span
                  class="mt-px size-4 shrink-0 rounded-full border-2"
                  :class="
                    scheduleMode === 'interval'
                      ? 'border-[#1565c0] shadow-[inset_0_0_0_3px_#1565c0] bg-white'
                      : 'border-[#7e7886]'
                  "
                />
                <div
                  class="text-[0.86rem] font-bold leading-[1.2] text-[#1565c0]"
                  :class="{ 'text-[#1f1d24]': scheduleMode !== 'interval' }"
                >
                  Repeating interval
                </div>
              </div>

              <div
                v-if="scheduleMode === 'interval'"
                class="mt-3 flex flex-wrap items-center gap-2 pl-6 max-[900px]:pl-0"
              >
                <span class="text-[0.82rem] font-medium text-[#1f1d24]"
                  >Every</span
                >
                <v-text-field
                  v-model.number="task.schedule!.interval"
                  class="max-w-20"
                  type="number"
                  min="1"
                  hide-details
                  variant="outlined"
                  rounded="lg"
                  :rules="[(v) => !!v || 'Interval is required']"
                />
                <v-select
                  v-model="task.schedule!.intervalPeriod"
                  class="max-w-[112px]"
                  :items="intervalUnitOptions"
                  item-title="title"
                  item-value="value"
                  hide-details
                  variant="outlined"
                  density="compact"
                  rounded="lg"
                  :rules="[(v) => !!v || 'Units are required']"
                />
              </div>
            </div>

            <div
              class="min-h-[92px] cursor-pointer rounded-lg border border-[#d0c9d8] bg-white px-3 py-3 outline-none transition-[border-color,background-color,box-shadow] duration-[160ms] ease-in-out hover:border-[#1565c0] focus-visible:border-[#1565c0]"
              :class="{
                '!border-2 !border-[#1565c0] !bg-[#edf3ff] shadow-[inset_0_0_0_1px_rgba(21,101,192,0.05)] [&_.v-field]:bg-white [&_.v-field__overlay]:bg-transparent [&_.v-field__outline]:[--v-field-border-opacity:1]':
                  scheduleMode === 'crontab',
              }"
              tabindex="0"
              role="button"
              @click="selectScheduleMode('crontab')"
              @keydown.enter.prevent="selectScheduleMode('crontab')"
              @keydown.space.prevent="selectScheduleMode('crontab')"
            >
              <div class="flex items-start gap-2">
                <span
                  class="mt-px size-4 shrink-0 rounded-full border-2"
                  :class="
                    scheduleMode === 'crontab'
                      ? 'border-[#1565c0] shadow-[inset_0_0_0_3px_#1565c0] bg-white'
                      : 'border-[#7e7886]'
                  "
                />
                <div>
                  <div
                    class="text-[0.86rem] font-bold leading-[1.2] text-[#1f1d24]"
                    :class="{ 'text-[#1565c0]': scheduleMode === 'crontab' }"
                  >
                    Crontab expression
                  </div>
                  <div
                    class="mt-0.5 text-[0.76rem] leading-[1.25] text-[#5f5a67]"
                  >
                    Advanced cron syntax
                  </div>
                </div>
              </div>

              <div
                v-if="scheduleMode === 'crontab'"
                class="mt-3 flex flex-wrap items-center gap-2 pl-6 max-[900px]:pl-0"
              >
                <v-text-field
                  v-model="task.schedule!.crontab"
                  class="w-full max-[640px]:max-w-full"
                  placeholder="0 9 * * *"
                  hide-details
                  variant="outlined"
                  rounded="lg"
                  density="compact"
                  :rules="[(v) => !!v || 'Crontab expression is required']"
                />
              </div>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <label
              class="text-[0.82rem] font-medium text-[#1f1d24]"
              for="task-start-time"
            >
              Start
            </label>
            <v-text-field
              id="task-start-time"
              v-model="startInput"
              class="schedule-start-input max-w-[250px] max-[640px]:w-full max-[640px]:max-w-full"
              type="datetime-local"
              hide-details
              variant="outlined"
              rounded="lg"
              density="compact"
            />
          </div>
        </div>

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

            <template v-for="(m, mi) in task.mappings as any[]" :key="mi">
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
                    v-if="!ensureSinglePath(m).targetIdentifier"
                    variant="outlined"
                    rounded="lg"
                    type="button"
                    class="h-auto min-h-10 w-full justify-start border-2 border-dashed border-[#1565c0] bg-[#f6f9ff] px-3 py-1.5 text-left text-[0.84rem] text-[#1565c0] normal-case [&_.v-btn__content]:w-full [&_.v-btn__content]:min-w-0 [&_.v-btn__content]:justify-start [&_.v-btn__content]:overflow-visible [&_.v-btn__content]:text-left"
                    :class="{
                      'border-[#d32f2f] text-[#d32f2f]': hasTargetError(mi, 0),
                    }"
                    @click="openTargetSelector(mi, 0)"
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
                    class="h-auto min-h-[62px] w-full justify-start border-2 border-solid border-[#1565c0] bg-white px-3 py-1.5 text-left text-[0.84rem] text-[#1c1b1f] normal-case [&_.v-btn__content]:w-full [&_.v-btn__content]:min-w-0 [&_.v-btn__content]:justify-start [&_.v-btn__content]:overflow-visible [&_.v-btn__content]:text-left"
                    @click="openTargetSelector(mi, 0)"
                  >
                    <span class="block max-w-full leading-[1.25] py-[2px]">
                      <span
                        class="block whitespace-normal font-semibold text-[#1c1b1f] [overflow-wrap:anywhere]"
                      >
                        {{
                          datastreamNameById(
                            ensureSinglePath(m).targetIdentifier
                          )
                        }}
                      </span>
                      <span
                        v-if="
                          datastreamThingNameById(
                            ensureSinglePath(m).targetIdentifier
                          )
                        "
                        class="block whitespace-normal text-[0.78rem] text-[rgba(0,0,0,0.66)] [overflow-wrap:anywhere]"
                      >
                        {{
                          datastreamThingNameById(
                            ensureSinglePath(m).targetIdentifier
                          )
                        }}
                      </span>
                      <span
                        class="block whitespace-normal text-[0.72rem] text-[rgba(0,0,0,0.55)] [overflow-wrap:anywhere]"
                      >
                        {{ String(ensureSinglePath(m).targetIdentifier) }}
                      </span>
                    </span>
                  </v-btn>

                  <div
                    v-if="hasTargetError(mi, 0)"
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
                    <v-icon :icon="mdiTrashCanOutline" size="22" />
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
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn-primary :loading="submitLoading" type="button" @click="onSubmit">
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
  Mapping,
  PlaceholderVariable,
  Task,
  TaskExpanded,
  TaskMapping,
  TaskSchedule,
} from '@hydroserver/client'
import StickyForm from '@/components/Forms/StickyForm.vue'
import DatastreamSelectorCard from '@/components/Datastream/DatastreamSelectorCard.vue'
import { Snackbar } from '@/utils/notifications'
import { rules } from '@/utils/rules'
import { useOrchestrationStore } from '@/store/orchestration'
import {
  mdiArrowRight,
  mdiPlus,
  mdiPlusCircleOutline,
  mdiTrashCanOutline,
} from '@mdi/js'

const props = defineProps<{
  oldTask?: TaskExpanded
  dataConnection: DataConnection
  workspaceId: string
}>()

const emit = defineEmits(['created', 'updated', 'close'])

const isEdit = !!props.oldTask
const valid = ref<boolean | null>(null)
const myForm = ref<VForm>()
const submitLoading = ref(false)
const workspaceId = props.workspaceId
const perTaskPlaceholders = props.dataConnection.placeholderVariables.filter(
  (variable): variable is PlaceholderVariable => variable.type === 'per_task'
)
const headerContextLabel = props.dataConnection.name || null
const timezoneLabel = Intl.DateTimeFormat().resolvedOptions().timeZone
const intervalUnitOptions = [
  { value: 'minutes', title: 'Minutes' },
  { value: 'hours', title: 'Hours' },
  { value: 'days', title: 'Days' },
] as const

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
const activePathIndex = ref<number | null>(null)

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
ensureTaskMappings()

const scheduleMode = ref<'interval' | 'crontab'>(
  task.value.schedule?.crontab ? 'crontab' : 'interval'
)

const resolvedWorkspaceId = computed(() => {
  return (
    workspaceId ||
    (task.value as any)?.workspaceId ||
    (task.value as any)?.workspace?.id ||
    null
  )
})

const startInput = computed({
  get: () => isoToInput(task.value.schedule?.startTime ?? ''),
  set: (v: string) => {
    ensureSchedule()
    task.value.schedule!.startTime = v ? inputToIso(v) : null
  },
})

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function stringifyIdentifier(value: unknown): string {
  return value === undefined || value === null ? '' : String(value)
}

function templateVariablePlaceholder(name: string) {
  return `e.g. ${name.toUpperCase()}`
}

function ensureSchedule() {
  if (!task.value.schedule) task.value.schedule = defaultSchedule()
}

function selectScheduleMode(mode: 'interval' | 'crontab') {
  ensureSchedule()
  scheduleMode.value = mode
  if (mode === 'interval') task.value.schedule!.crontab = null
}

function isoToInput(iso: string | null = ''): string {
  if (!iso) return ''
  const normalized = ensureIsoUtc(iso) ?? ''
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return ''
  const tzOffsetMs = d.getTimezoneOffset() * 60_000
  const local = new Date(d.getTime() - tzOffsetMs)
  return local.toISOString().slice(0, 16)
}

function inputToIso(str = ''): string {
  if (!str) return ''
  const parsed = new Date(str)
  return parsed.toISOString()
}

function createEmptyMapping(): Mapping {
  return {
    sourceIdentifier: '',
    paths: [
      {
        targetIdentifier: '',
        dataTransformations: [],
      },
    ],
  } as Mapping
}

function ensureSinglePath(mapping: Mapping) {
  const targetDatastreamId = (mapping as any).targetDatastream?.id
  if (!Array.isArray(mapping.paths) || mapping.paths.length === 0) {
    mapping.paths = [
      {
        targetIdentifier: targetDatastreamId ? String(targetDatastreamId) : '',
        dataTransformations: [],
      },
    ]
  }
  if (mapping.paths.length > 1) mapping.paths = [mapping.paths[0]]
  if (!mapping.paths[0].targetIdentifier && targetDatastreamId) {
    mapping.paths[0].targetIdentifier = String(targetDatastreamId)
  }
  if (!Array.isArray(mapping.paths[0].dataTransformations)) {
    mapping.paths[0].dataTransformations = []
  }
  return mapping.paths[0]
}

function ensureTaskMappings(addInitial = true) {
  if (!Array.isArray(task.value.mappings)) {
    ;(task.value as any).mappings = []
  }

  task.value.mappings.forEach((mapping: any) => {
    ensureSinglePath(mapping)
  })

  if (addInitial && task.value.mappings.length === 0) {
    task.value.mappings.push(createEmptyMapping())
  }
}

function hasTargetError(mi: number, pi: number) {
  return showErrors.value && missingTargetKeys.value.has(`${mi}:${pi}`)
}

function datastreamById(id: string | number | undefined | null): any {
  if (id === undefined || id === null || `${id}` === '') return null
  const key = String(id)
  return (
    workspaceDatastreams.value.find((d) => String(d.id) === key) ||
    linkedDatastreams.value.find((d) => String(d.id) === key) ||
    draftDatastreams.value.find((d) => String(d.id) === key) ||
    task.value.mappings
      ?.map((mapping: any) => mapping?.targetDatastream)
      .find((d: any) => d && String(d.id) === key) ||
    null
  )
}

function datastreamNameById(id: string | number | undefined | null) {
  return datastreamById(id)?.name || ''
}

function datastreamThingNameById(id: string | number | undefined | null) {
  const ds = datastreamById(id)
  if (!ds) return ''
  if (ds.thing?.name) return ds.thing.name
  const thingId = ds.thingId ?? ds.thing_id ?? ds.thing?.id
  if (!thingId) return ''
  return (
    workspaceThings.value.find((thing) => String(thing.id) === String(thingId))
      ?.name || ''
  )
}

function openTargetSelector(mi: number, pi: number) {
  activeMappingIndex.value = mi
  activePathIndex.value = pi
  datastreamSelectorOpen.value = true
}

function referencedTargetIds(): Set<string> {
  const ids = new Set<string>()
  for (const mapping of task.value.mappings as any[]) {
    const paths = Array.isArray(mapping.paths) ? mapping.paths : []
    for (const path of paths) {
      const id = path.targetIdentifier
      if (id !== undefined && id !== null && String(id) !== '') {
        ids.add(String(id))
      }
    }
  }
  return ids
}

function syncDraftDatastreams() {
  const refIds = referencedTargetIds()
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
  const pi = activePathIndex.value
  if (mi == null || pi == null) return

  const mapping = task.value.mappings[mi] as any
  const path = mapping?.paths?.[pi]
  if (!path) return

  path.targetIdentifier = event.id
  draftDatastreams.value = [event, ...draftDatastreams.value]
  syncDraftDatastreams()

  const key = `${mi}:${pi}`
  if (missingTargetKeys.value.has(key)) {
    const next = new Set(missingTargetKeys.value)
    next.delete(key)
    missingTargetKeys.value = next
  }

  activeMappingIndex.value = null
  activePathIndex.value = null
  datastreamSelectorOpen.value = false
}

function removeMapping(mi: number) {
  const mappings = task.value.mappings
  if (!Array.isArray(mappings) || mi < 0 || mi >= mappings.length) return
  mappings.splice(mi, 1)
  syncDraftDatastreams()
}

function addMapping() {
  if (!Array.isArray(task.value.mappings)) {
    ;(task.value as any).mappings = []
  }
  task.value.mappings.push(createEmptyMapping())
  noMappingsError.value = false
}

function validateMappings() {
  ensureTaskMappings(false)
  showErrors.value = true
  noMappingsError.value = task.value.mappings.length === 0

  const nextMissingKeys = new Set<string>()
  task.value.mappings.forEach((mapping: any, mi) => {
    const path = ensureSinglePath(mapping)
    if (!path.targetIdentifier) nextMissingKeys.add(`${mi}:0`)
  })

  missingTargetKeys.value = nextMissingKeys
  return !noMappingsError.value && nextMissingKeys.size === 0
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
  const schedule = task.value.schedule ?? defaultSchedule()
  if (scheduleMode.value === 'interval') schedule.crontab = null

  return new Task({
    id: task.value.id,
    name: task.value.name,
    description: task.value.description,
    taskVariables: task.value.taskVariables,
    dataConnectionId: props.dataConnection.id,
    schedule,
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
  const mappingsValid = validateMappings()
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

watch(
  () => task.value,
  () => ensureTaskMappings(),
  { immediate: true }
)

watch(
  resolvedWorkspaceId,
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
