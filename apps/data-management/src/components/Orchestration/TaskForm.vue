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
        <div v-if="!isDataConnectionScopedCreate" class="task-form-meta-grid">
          <div class="task-form-field">
            <label class="task-form-label" for="task-type">Task type</label>
            <v-select
              id="task-type"
              v-model="(task as any).type"
              :items="taskTypeOptions"
              item-title="title"
              item-value="value"
              placeholder="Select task type"
              variant="outlined"
              rounded="lg"
              density="compact"
              hide-details="auto"
            />
          </div>

          <div v-if="!isAggregationTask" class="task-form-field">
            <label class="task-form-label" for="task-data-connection">
              Data connection <span class="task-form-required">*</span>
            </label>
            <v-select
              id="task-data-connection"
              v-model="task.dataConnectionId"
              :items="workspaceDataConnections"
              item-title="name"
              item-value="id"
              placeholder="Select data connection"
              :rules="rules.requiredAndMaxLength255"
              variant="outlined"
              rounded="lg"
              density="compact"
              hide-details="auto"
            />
          </div>
        </div>

        <div class="task-form-section">
          <div class="task-form-field">
            <label class="task-form-label" for="task-name">
              Task name <span class="task-form-required">*</span>
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

        <v-divider class="task-form-divider" />

        <!-- Aggregation timezone controls are intentionally hidden here.
             Keep this block for reuse in a dedicated aggregation form. -->
        <!--
        <div v-else class="mb-4">
          <p class="font-weight-bold mb-2 required-label">Aggregation timezone</p>
          <v-btn-toggle
            class="mb-3"
            v-model="aggregationTimezoneMode"
            mandatory
            variant="outlined"
            density="compact"
            color="blue"
          >
            <v-btn value="fixedOffset">Fixed offset</v-btn>
            <v-btn value="daylightSavings">Daylight savings aware</v-btn>
          </v-btn-toggle>

          <v-autocomplete
            v-if="aggregationTimezoneMode === 'fixedOffset'"
            v-model="aggregationTimezone"
            :items="FIXED_OFFSET_TIMEZONES"
            item-title="title"
            item-value="value"
            label="Fixed timezone offset"
            :rules="rules.required"
            density="comfortable"
          />

          <v-autocomplete
            v-else
            v-model="aggregationTimezone"
            :items="DST_AWARE_TIMEZONES"
            item-title="title"
            item-value="value"
            label="Daylight savings aware timezone"
            :rules="rules.required"
            density="comfortable"
          />
        </div>
        -->

        <div class="task-form-section">
          <div class="task-form-section-header">
            <h3 class="task-form-section-title">Schedule</h3>
            <span class="task-form-section-subtitle">{{ timezoneLabel }}</span>
          </div>

          <div class="schedule-card-grid">
            <div
              class="schedule-card"
              :class="{ 'schedule-card-active': scheduleMode === 'interval' }"
              tabindex="0"
              role="button"
              @click="scheduleMode = 'interval'"
              @keydown.enter.prevent="scheduleMode = 'interval'"
              @keydown.space.prevent="scheduleMode = 'interval'"
            >
              <div class="schedule-card-top">
                <span
                  class="schedule-card-radio"
                  :class="{
                    'schedule-card-radio-active': scheduleMode === 'interval',
                  }"
                />
                <div>
                  <div class="schedule-card-title">Repeating interval</div>
                </div>
              </div>

              <div
                v-if="scheduleMode === 'interval'"
                class="schedule-card-body"
              >
                <span class="schedule-inline-label">Every</span>
                <v-text-field
                  v-model.number="task.schedule!.interval"
                  class="schedule-interval-input"
                  type="number"
                  min="1"
                  hide-details
                  variant="outlined"
                  density="compact"
                  rounded="lg"
                  :rules="[(v) => !!v || 'Interval is required']"
                />
                <v-select
                  v-model="task.schedule!.intervalPeriod"
                  class="schedule-unit-select"
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
              class="schedule-card"
              :class="{ 'schedule-card-active': scheduleMode === 'crontab' }"
              tabindex="0"
              role="button"
              @click="scheduleMode = 'crontab'"
              @keydown.enter.prevent="scheduleMode = 'crontab'"
              @keydown.space.prevent="scheduleMode = 'crontab'"
            >
              <div class="schedule-card-top">
                <span
                  class="schedule-card-radio"
                  :class="{
                    'schedule-card-radio-active': scheduleMode === 'crontab',
                  }"
                />
                <div>
                  <div class="schedule-card-title">Crontab expression</div>
                  <div class="schedule-card-copy">Advanced cron syntax</div>
                </div>
              </div>

              <div v-if="scheduleMode === 'crontab'" class="schedule-card-body">
                <v-text-field
                  v-model="task.schedule!.crontab"
                  class="schedule-crontab-input schedule-crontab-input-inline"
                  placeholder="0 9 * * *"
                  hide-details
                  variant="outlined"
                  rounded="lg"
                  density="compact"
                />
              </div>
            </div>
          </div>

          <div class="schedule-start-row">
            <label class="schedule-start-label" for="task-start-time"
              >Start</label
            >
            <v-text-field
              id="task-start-time"
              v-model="startInput"
              class="schedule-start-input"
              type="datetime-local"
              hide-details
              variant="outlined"
              rounded="lg"
              density="compact"
            />
          </div>
        </div>

        <v-divider
          v-if="perTaskPlaceholders.length"
          class="task-form-divider"
        />

        <div v-if="perTaskPlaceholders.length" class="task-form-section">
          <div class="task-form-section-header task-form-section-header-stack">
            <h3 class="task-form-section-title">Template variables</h3>
            <p class="task-form-section-copy">
              Fill in values for URL placeholders defined in this data
              connection.
            </p>
          </div>

          <div class="task-form-template-grid">
            <div
              v-for="variable in perTaskPlaceholders"
              :key="variable.name"
              class="task-form-field"
            >
              <label
                class="task-form-label"
                :for="`task-variable-${variable.name}`"
              >
                {{ variable.name }} <span class="task-form-required">*</span>
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

        <v-divider class="task-form-divider" />

        <div class="task-form-section">
          <div class="task-form-section-header task-form-section-header-stack">
            <h3 class="task-form-section-title">Data mapping</h3>
            <p class="task-form-section-copy">
              Map each source field (CSV column or JSON key) to a HydroServer
              datastream.
            </p>
          </div>

          <SwimlanesForm
            v-model:task="task"
            :workspace-id="taskWorkspaceId || null"
            ref="swimlanesRef"
          />
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
</template>

<script setup lang="ts">
import { rules } from '@/utils/rules'
import { VForm } from 'vuetify/components'
import { computed, Ref, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import SwimlanesForm from './SwimlanesForm.vue'
import hs, {
  DataConnection,
  Task,
  TaskExpanded,
  TaskSchedule,
} from '@hydroserver/client'
import { useTaskStore } from '@/store/task'
import { useOrchestrationStore } from '@/store/orchestration'
import StickyForm from '@/components/Forms/StickyForm.vue'
import { useTableLogic } from '@/composables/useTableLogic'
import { useWorkspaceStore } from '@/store/workspaces'
import { Snackbar } from '@/utils/notifications'
import { DST_AWARE_TIMEZONES, FIXED_OFFSET_TIMEZONES } from '@/models/timestamp'

const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
const selectedWorkspaceId = computed(() => selectedWorkspace.value?.id)

const props = defineProps<{
  oldTask?: TaskExpanded
  initialDataConnection?: DataConnection
}>()

const { tasks } = storeToRefs(useTaskStore())
const { workspaceTasks } = storeToRefs(useOrchestrationStore())

const { items: workspaceDataConnections } = useTableLogic(
  async (wsId: string) =>
    await hs.dataConnections.listAllItems({
      workspace_id: [wsId],
      expand_related: true,
      order_by: ['name'],
    } as any),
  hs.dataConnections.delete,
  DataConnection,
  selectedWorkspaceId
)

const emit = defineEmits(['created', 'updated', 'close'])

const isEdit = computed(() => !!props.oldTask || undefined)
const isDataConnectionScopedCreate = computed(
  () => !isEdit.value && !!props.initialDataConnection
)
const valid = ref<boolean | null>(null)
const myForm = ref<VForm>()
const swimlanesRef = ref<any>(null)
const submitLoading = ref(false)
const task = ref<Task>(new Task())
const scheduleMode = ref<'interval' | 'crontab'>('interval')
const aggregationTimezoneMode = ref<'fixedOffset' | 'daylightSavings'>(
  'fixedOffset'
)
const aggregationTimezone = ref<string>('-0700')
const selectedDataConnection = computed<DataConnection | undefined>(() =>
  workspaceDataConnections.value.find(
    (j) => j.id === task.value.dataConnectionId
  )
)
const isAggregationTask = computed(
  () => ((task.value as any)?.type ?? 'ETL') === 'Aggregation'
)
const taskWorkspaceId = computed(() => {
  return (
    (task.value as any).workspaceId ||
    (task.value as any)?.workspace?.id ||
    (props.oldTask?.dataConnection as any)?.workspace?.id ||
    selectedWorkspace.value?.id ||
    ''
  )
})
const perTaskPlaceholders = computed<any[]>(() => {
  if (isAggregationTask.value) return []
  const placeholders =
    (selectedDataConnection.value as any)?.placeholderVariables || []
  return placeholders.filter((v: any) => v?.type === 'per_task')
})
const taskTypeOptions = [
  { title: 'ETL', value: 'ETL' },
  { title: 'Aggregation', value: 'Aggregation' },
]

const intervalUnitOptions = [
  { value: 'minutes', title: 'Minutes' },
  { value: 'hours', title: 'Hours' },
  { value: 'days', title: 'Days' },
] as const

const timezoneLabel = computed(
  () => Intl.DateTimeFormat().resolvedOptions().timeZone
)
const headerContextLabel = computed(() => {
  if (isAggregationTask.value) return null
  return (
    selectedDataConnection.value?.name ||
    props.initialDataConnection?.name ||
    (props.oldTask?.dataConnection as any)?.name ||
    null
  )
})

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

function ensureAggregationTransformation(path: any) {
  if (!Array.isArray(path.dataTransformations)) path.dataTransformations = []
  const existing = path.dataTransformations.find(
    (t: any) => t?.type === 'aggregation'
  )
  const transform = existing || {
    type: 'aggregation',
    aggregationStatistic: 'simple_mean',
    timezoneMode: aggregationTimezoneMode.value,
    timezone: aggregationTimezone.value,
  }
  transform.aggregationStatistic ||= 'simple_mean'
  transform.timezoneMode = aggregationTimezoneMode.value
  transform.timezone = aggregationTimezone.value
  path.dataTransformations = [transform]
}

function hydrateAggregationTimezoneFromMappings() {
  const first = (
    task.value.mappings as any
  )?.[0]?.paths?.[0]?.dataTransformations?.find(
    (t: any) => t?.type === 'aggregation'
  ) as any
  if (!first) {
    aggregationTimezoneMode.value = 'fixedOffset'
    aggregationTimezone.value = '-0700'
    return
  }
  aggregationTimezoneMode.value =
    first.timezoneMode === 'daylightSavings' ? 'daylightSavings' : 'fixedOffset'
  aggregationTimezone.value =
    typeof first.timezone === 'string' && first.timezone
      ? first.timezone
      : aggregationTimezoneMode.value === 'daylightSavings'
      ? 'America/Denver'
      : '-0700'
}

function syncAggregationConfigToMappings() {
  if (!isAggregationTask.value) return

  if (!task.value.mappings?.length) {
    task.value.mappings = [
      {
        sourceIdentifier: '',
        paths: [{ targetIdentifier: '', dataTransformations: [] }],
      } as any,
    ]
  }

  task.value.mappings.forEach((mapping: any) => {
    if (!Array.isArray(mapping.paths) || mapping.paths.length === 0) {
      mapping.paths = [{ targetIdentifier: '', dataTransformations: [] }]
    }
    if (mapping.paths.length > 1) mapping.paths = [mapping.paths[0]]
    ensureAggregationTransformation(mapping.paths[0])
  })
}

const startInput = computed({
  get: () => isoToInput(task.value.schedule?.startTime ?? ''),
  set: (v: string) => {
    if (!task.value.schedule) task.value.schedule = defaultSchedule()
    task.value.schedule.startTime = v ? inputToIso(v) : null
  },
})

function templateVariablePlaceholder(name: string) {
  return `e.g. ${name.toUpperCase()}`
}

function hydrateTask(source?: TaskExpanded) {
  const base = source
    ? new Task(JSON.parse(JSON.stringify(source)))
    : new Task()

  if (!source && props.initialDataConnection) {
    ;(base as any).type = 'ETL'
    base.dataConnectionId = String(props.initialDataConnection.id)
    ;(base as any).dataConnection = JSON.parse(
      JSON.stringify(props.initialDataConnection)
    )
    const workspaceId =
      (props.initialDataConnection as any)?.workspace?.id ??
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
  if ((base as any).type === 'Aggregation') base.dataConnectionId = null as any
  ;(['startTime', 'nextRunAt'] as const).forEach((k) => {
    if (base.schedule && base.schedule[k])
      base.schedule[k] = ensureIsoUtc(base.schedule[k])
  })

  task.value = base
  hydrateAggregationTimezoneFromMappings()
  syncAggregationConfigToMappings()
  scheduleMode.value = base.schedule?.crontab ? 'crontab' : 'interval'
}

watch(
  () => props.oldTask,
  (newTask) => hydrateTask(newTask),
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

watch(
  () => (task.value as any)?.type,
  (nextType) => {
    if (nextType === 'Aggregation') {
      task.value.dataConnectionId = null as any
      syncAggregationConfigToMappings()
    } else if (!task.value.dataConnectionId) {
      task.value.dataConnectionId = ''
    }
  },
  { immediate: true }
)

watch(
  aggregationTimezoneMode,
  (mode) => {
    if (mode === 'daylightSavings') {
      if (
        !aggregationTimezone.value ||
        !DST_AWARE_TIMEZONES.some(
          (tz) => tz.value === aggregationTimezone.value
        )
      ) {
        aggregationTimezone.value = 'America/Denver'
      }
    } else if (
      !aggregationTimezone.value ||
      !FIXED_OFFSET_TIMEZONES.some(
        (tz) => tz.value === aggregationTimezone.value
      )
    ) {
      aggregationTimezone.value = '-0700'
    }
    syncAggregationConfigToMappings()
  },
  { immediate: true }
)

watch(aggregationTimezone, () => syncAggregationConfigToMappings())

watch(
  () =>
    (task.value.mappings || [])
      .map((m: any) => `${m.sourceIdentifier}:${m.paths?.length || 0}`)
      .join('|'),
  () => syncAggregationConfigToMappings()
)

function upsertTaskList(listRef: { value: Task[] }, saved: Task) {
  const index = listRef.value.findIndex((p) => p.id === saved.id)
  if (index !== -1) listRef.value[index] = saved
  else listRef.value = [...listRef.value, saved]
}

async function onSubmit() {
  const swimlanesValid = await swimlanesRef.value.validate()
  if (!swimlanesValid) return

  await myForm.value?.validate()
  if (!valid.value) return

  submitLoading.value = true
  try {
    ;(task.value as any).workspaceId = taskWorkspaceId.value || ''
    if (isDataConnectionScopedCreate.value) {
      ;(task.value as any).type = 'ETL'
      task.value.dataConnectionId = String(
        props.initialDataConnection?.id ?? ''
      )
    }
    if (!task.value.schedule) task.value.schedule = defaultSchedule()
    if (isAggregationTask.value) {
      task.value.dataConnectionId = null as any
      syncAggregationConfigToMappings()
    }

    const res = isEdit.value
      ? await hs.tasks.update(task.value)
      : await hs.tasks.create(task.value)

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
.task-form-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 8px;
  margin-bottom: 8px;
}
.task-form-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.task-form-divider {
  margin: 8px 0;
}
.task-form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.task-form-label {
  font-size: 0.74rem;
  font-weight: 700;
  color: #1f1d24;
}
.task-form-required {
  color: #d32f2f;
}
.task-form-section-header {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.task-form-section-header-stack {
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
}
.task-form-section-title {
  font-size: 0.67rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 800;
  color: #4f4b59;
}
.task-form-section-subtitle,
.task-form-section-copy {
  color: #5f5a67;
  font-size: 0.72rem;
  line-height: 1.3;
}
.task-form-template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 420px));
  gap: 8px;
}
.schedule-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 6px;
}
.schedule-card {
  border: 2px solid #d0c9d8;
  border-radius: 14px;
  background: #fff;
  padding: 8px 10px;
  transition: border-color 0.16s ease, background-color 0.16s ease,
    box-shadow 0.16s ease;
  outline: none;
}
.schedule-card:hover,
.schedule-card:focus-visible {
  border-color: #1565c0;
}
.schedule-card-active {
  border-color: #1565c0;
  background: #edf3ff;
  box-shadow: inset 0 0 0 1px rgba(21, 101, 192, 0.05);
}
.schedule-card-top {
  display: flex;
  align-items: flex-start;
  gap: 5px;
}
.schedule-card-radio {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid #7e7886;
  flex-shrink: 0;
  margin-top: 1px;
}
.schedule-card-radio-active {
  border-color: #1565c0;
  box-shadow: inset 0 0 0 3px #1565c0;
  background: #fff;
}
.schedule-card-title {
  font-size: 0.79rem;
  font-weight: 700;
  color: #1f1d24;
  line-height: 1.2;
}
.schedule-card-copy {
  margin-top: 1px;
  color: #5f5a67;
  font-size: 0.68rem;
  line-height: 1.25;
}
.schedule-card-body {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 4px;
  padding-left: 28px;
  flex-wrap: wrap;
}
.schedule-inline-label,
.schedule-start-label {
  font-size: 0.74rem;
  font-weight: 500;
  color: #1f1d24;
}
.schedule-interval-input {
  max-width: 62px;
}
.schedule-unit-select {
  max-width: 110px;
}
.schedule-crontab-input {
  max-width: 280px;
}
.schedule-crontab-input-inline {
  width: 100%;
  max-width: 100%;
}
.schedule-start-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.schedule-start-input {
  max-width: 220px;
}
:deep(.task-form-shell .v-field) {
  --v-input-control-height: 38px;
}

.schedule-card-active :deep(.v-field) {
  background: #ffffff;
}

.schedule-card-active :deep(.v-field__overlay) {
  background: transparent;
}

.schedule-card-active :deep(.v-field__outline) {
  --v-field-border-opacity: 1;
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

:deep(.schedule-start-input .v-field__input) {
  align-items: center;
}

:deep(.schedule-start-input input[type='datetime-local']) {
  line-height: 1;
  padding-right: 2px;
}

:deep(
    .schedule-start-input
      input[type='datetime-local']::-webkit-calendar-picker-indicator
  ) {
  margin: 0;
  padding: 0;
  opacity: 0.82;
  transform: translateY(-1px);
}

@media (max-width: 900px) {
  .task-form-header,
  .task-form-shell {
    padding-left: 14px;
    padding-right: 14px;
  }

  .schedule-card-body {
    padding-left: 0;
  }
}

@media (max-width: 640px) {
  .task-form-shell {
    padding-bottom: 14px;
  }

  .schedule-start-input,
  .schedule-crontab-input {
    max-width: 100%;
    width: 100%;
  }

}
</style>
