<template>
  <StickyForm>
    <template #header>
      <p class="ml-6 font-weight-bold">
        {{ isEdit ? 'Edit' : 'Add' }} task configuration
        <span v-if="isEdit" class="opacity-80">· {{ task?.name }}</span>
      </p>
    </template>

    <v-form
      @submit.prevent="onSubmit"
      ref="myForm"
      v-model="valid"
      validate-on="blur"
    >
      <v-card-text v-if="task">
        <p class="font-weight-bold mb-2 required-label">Name your task</p>
        <v-text-field
          v-model="task.name"
          label="Task name"
          :rules="rules.requiredAndMaxLength255"
          density="comfortable"
        />

        <p class="font-weight-bold mb-2 required-label">Task type</p>
        <v-select
          v-model="(task as any).type"
          :items="taskTypeOptions"
          item-title="title"
          item-value="value"
          label="Task type"
          density="comfortable"
        />

        <template v-if="!isAggregationTask">
          <p class="font-weight-bold mb-2 required-label">
            Select data connection
          </p>
          <v-select
            v-model="task.dataConnectionId"
            :items="workspaceDataConnections"
            item-title="name"
            item-value="id"
            label="Data connection"
            :rules="rules.requiredAndMaxLength255"
            density="comfortable"
          />
        </template>

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

        <div v-if="perTaskPlaceholders.length" class="mb-4">
          <p class="font-weight-bold mb-2">Template variables</p>
          <v-row>
            <v-col
              cols="12"
              md="6"
              v-for="variable in perTaskPlaceholders"
              :key="variable.name"
            >
              <v-text-field
                v-model="(task as any).extractorVariables[variable.name]"
                :label="`URL template variable: ${variable.name} *`"
                :rules="rules.requiredAndMaxLength255"
                density="comfortable"
              />
            </v-col>
          </v-row>
        </div>

        <div class="mb-4">
          <p class="font-weight-bold mb-2">Schedule ({{ timezoneLabel }})</p>
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="startInput"
                label="Start time"
                type="datetime-local"
                density="comfortable"
              />
            </v-col>
          </v-row>

          <v-radio-group v-model="scheduleMode" inline>
            <v-radio label="Interval" value="interval" />
            <v-radio label="Crontab" value="crontab" />
          </v-radio-group>

          <v-row v-if="scheduleMode === 'interval'">
            <v-col cols="12" md="6">
              <v-text-field
                v-model.number="task.schedule!.interval"
                label="Interval"
                type="number"
                min="1"
                :rules="[(v) => !!v || 'Interval is required']"
                density="comfortable"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="task.schedule!.intervalPeriod"
                :items="intervalUnitOptions"
                item-title="title"
                item-value="value"
                label="Interval Units"
                :rules="[(v) => !!v || 'Units are required']"
                density="comfortable"
              />
            </v-col>
          </v-row>

          <v-text-field
            v-else
            v-model="task.schedule!.crontab"
            label="Crontab"
            hint="Five-field crontab string"
            persistent-hint
            density="comfortable"
          />
        </div>

        <v-divider class="mb-6" />
        <SwimlanesForm
          v-model:task="task"
          :workspace-id="taskWorkspaceId || null"
          ref="swimlanesRef"
        />
      </v-card-text>
    </v-form>

    <template #actions>
      <v-spacer />
      <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
      <v-btn-primary :loading="submitLoading" type="button" @click="onSubmit">
        Save
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
  OrchestrationSystem,
  PlaceholderVariable,
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
import {
  DST_AWARE_TIMEZONES,
  FIXED_OFFSET_TIMEZONES,
} from '@/models/timestamp'

const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
const selectedWorkspaceId = computed(() => selectedWorkspace.value?.id)

const props = defineProps<{
  oldTask?: TaskExpanded
  orchestrationSystem: OrchestrationSystem
}>()

const { tasks } = storeToRefs(useTaskStore())
const { workspaceTasks } = storeToRefs(useOrchestrationStore())

const { items: workspaceDataConnections } = useTableLogic(
  async (wsId: string) =>
    await hs.dataConnections.listAllItems({
      workspace_id: [wsId],
      expand_related: true,
      order_by: ['name'],
    }),
  hs.dataConnections.delete,
  DataConnection,
  selectedWorkspaceId
)

const emit = defineEmits(['created', 'updated', 'close'])

const isEdit = computed(() => !!props.oldTask || undefined)
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
    task.value.workspaceId ||
    (task.value as any)?.workspace?.id ||
    props.oldTask?.workspace?.id ||
    selectedWorkspace.value?.id ||
    ''
  )
})
const perTaskPlaceholders = computed<PlaceholderVariable[]>(() => {
  if (isAggregationTask.value) return []
  const placeholders =
    (selectedDataConnection.value as any)?.extractor?.settings
      ?.placeholderVariables || []
  return placeholders.filter((v: PlaceholderVariable) => v?.type === 'perTask')
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

function defaultSchedule(): TaskSchedule {
  const now = new Date().toISOString()
  return {
    paused: false,
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
  const first = task.value.mappings?.[0]?.paths?.[0]?.dataTransformations?.find(
    (t: any) => t?.type === 'aggregation'
  ) as any
  if (!first) {
    aggregationTimezoneMode.value = 'fixedOffset'
    aggregationTimezone.value = '-0700'
    return
  }
  aggregationTimezoneMode.value =
    first.timezoneMode === 'daylightSavings'
      ? 'daylightSavings'
      : 'fixedOffset'
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

function hydrateTask(source?: TaskExpanded) {
  const base = source
    ? new Task(JSON.parse(JSON.stringify(source)))
    : new Task()

  ;(base as any).type = (base as any).type || 'ETL'
  if (!base.schedule) base.schedule = defaultSchedule()
  if (!base.mappings) base.mappings = []
  if (!base.workspaceId && (base as any).workspace?.id)
    base.workspaceId = String((base as any).workspace.id)
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
    if (!task.value.extractorVariables)
      task.value.extractorVariables = {} as Record<string, any>
    const next: Record<string, any> = {}
    names.forEach((n) => {
      next[n] =
        (task.value as any).extractorVariables[n] === undefined
          ? ''
          : (task.value as any).extractorVariables[n]
    })
    task.value.extractorVariables = next
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
        !DST_AWARE_TIMEZONES.some((tz) => tz.value === aggregationTimezone.value)
      ) {
        aggregationTimezone.value = 'America/Denver'
      }
    } else if (
      !aggregationTimezone.value ||
      !FIXED_OFFSET_TIMEZONES.some((tz) => tz.value === aggregationTimezone.value)
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

  task.value.workspaceId = taskWorkspaceId.value || ''
  task.value.orchestrationSystemId =
    props.orchestrationSystem?.id || task.value.orchestrationSystemId
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
  } else {
    const saved = res.data
    upsertTaskList(tasks, saved)
    upsertTaskList(workspaceTasks as unknown as Ref<Task[]>, saved)
    hydrateTask(saved)

    emit(isEdit.value ? 'updated' : 'created', saved)
  }

  submitLoading.value = false
  emit('close')
}
</script>

<style scoped>
:deep(.v-expansion-panel-text__wrapper) {
  padding: 0 !important;
}
</style>
