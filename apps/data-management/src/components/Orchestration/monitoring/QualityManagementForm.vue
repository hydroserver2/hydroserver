<template>
  <v-card class="d-flex flex-column" style="max-height: 90vh">
    <div class="shrink-0">
      <v-toolbar :style="toolbarStyle" flat>
        <v-card-title>{{
          isEditMode ? 'Edit quality task' : 'Create quality task'
        }}</v-card-title>
        <v-btn
          :icon="mdiInformationOutline"
          variant="text"
          aria-label="Toggle task info"
          @click="showInfo = !showInfo"
        />
      </v-toolbar>
      <v-divider />
      <v-progress-linear
        v-if="loadingExisting"
        indeterminate
        :color="QUALITY_ACCENT"
      />
    </div>

    <v-form
      ref="formRef"
      v-model="valid"
      validate-on="input"
      class="d-flex flex-column grow overflow-hidden"
      @submit.prevent="onSubmit"
    >
      <v-card-text class="overflow-y-auto grow">
        <v-alert
          v-if="showInfo"
          :color="QUALITY_ACCENT"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-5"
        >
          Quality tasks monitor one or more datastreams for range, rate of
          change, persistence, and missing-data conditions. Each rule belongs to
          this task and can notify the recipients below.
        </v-alert>

        <v-text-field
          v-model="taskName"
          label="Task name *"
          :rules="rules.requiredAndMaxLength255"
          :disabled="loadingExisting"
          class="mb-2"
        />

        <v-textarea
          v-model="description"
          label="Description"
          :rules="rules.description"
          :disabled="loadingExisting"
          rows="2"
          auto-grow
          class="mb-2"
        />

        <v-combobox
          v-model="recipientEmails"
          v-model:search="recipientInput"
          :items="[]"
          label="Notification recipients"
          placeholder="Type an email address and press Enter"
          multiple
          clearable
          hide-no-data
          hide-selected
          :disabled="loadingExisting"
          :rules="recipientRules"
          :error-messages="recipientInputError ? [recipientInputError] : []"
          class="mb-2"
          @keydown.enter.prevent="addRecipient"
          @keydown.tab="addRecipient"
          @blur="addRecipient"
        >
          <template #selection="{ item, index }">
            <v-chip
              size="small"
              color="teal-darken-2"
              variant="tonal"
              rounded
              closable
              class="mr-1 mb-1 max-w-full"
              @click:close="removeRecipient(index)"
            >
              <span class="truncate">{{ item.title }}</span>
            </v-chip>
          </template>
        </v-combobox>

        <v-divider class="mb-4" />

        <div class="section-heading mb-3">Schedule</div>
        <v-switch
          v-model="scheduleEnabled"
          :color="QUALITY_ACCENT"
          density="compact"
          hide-details
          :disabled="loadingExisting"
          label="Run this task on a schedule"
          class="mb-2"
        />

        <div v-if="scheduleEnabled" class="schedule-grid mb-4">
          <v-btn-toggle
            v-model="scheduleMode"
            mandatory
            divided
            density="compact"
            :disabled="loadingExisting"
            class="schedule-mode"
          >
            <v-btn value="interval" class="text-none">Interval</v-btn>
            <v-btn value="crontab" class="text-none">Crontab</v-btn>
          </v-btn-toggle>

          <template v-if="scheduleMode === 'interval'">
            <v-text-field
              v-model.number="scheduleInterval"
              label="Every *"
              type="number"
              min="1"
              density="compact"
              :rules="[...rules.required, positiveInteger]"
              :disabled="loadingExisting"
            />
            <v-select
              v-model="scheduleIntervalPeriod"
              :items="scheduleUnitOptions"
              item-title="title"
              item-value="value"
              label="Unit *"
              density="compact"
              :rules="rules.required"
              :disabled="loadingExisting"
            />
          </template>

          <v-text-field
            v-else
            v-model="scheduleCrontab"
            label="Crontab expression *"
            placeholder="0 9 * * *"
            density="compact"
            :rules="rules.required"
            :disabled="loadingExisting"
            class="schedule-crontab"
          />

          <v-text-field
            v-model="scheduleStartInput"
            label="Start"
            type="datetime-local"
            density="compact"
            :disabled="loadingExisting"
            class="schedule-start"
          />
        </div>

        <v-divider class="mb-4" />

        <div class="d-flex align-center mb-3">
          <div class="section-heading">Quality rules</div>
          <v-chip
            v-if="ruleRows.length === 0"
            size="x-small"
            color="warning"
            variant="tonal"
            class="ml-2"
          >
            at least 1 required
          </v-chip>
          <v-spacer />
          <v-btn
            variant="outlined"
            size="small"
            :prepend-icon="mdiPlus"
            :color="QUALITY_ACCENT"
            :disabled="loadingExisting"
            class="text-none"
            @click="addRule"
          >
            Add rule
          </v-btn>
        </div>

        <v-alert
          v-if="ruleErrors.length"
          type="error"
          variant="tonal"
          density="compact"
          class="mb-3"
        >
          <div v-for="error in ruleErrors" :key="error">{{ error }}</div>
        </v-alert>

        <div v-if="ruleRows.length === 0" class="empty-rules mb-4">
          Add a quality rule to define what this task checks.
        </div>

        <div v-for="(row, index) in ruleRows" :key="row.key" class="rule-card">
          <div class="rule-card__header">
            <div>
              <div class="rule-card__title">Rule {{ index + 1 }}</div>
              <div v-if="row.lastCheckedAt" class="rule-card__subtitle">
                Last checked {{ formatTime(row.lastCheckedAt) }}
              </div>
            </div>
            <v-btn
              icon
              variant="text"
              size="small"
              color="error"
              :disabled="loadingExisting"
              aria-label="Remove rule"
              @click="removeRule(index)"
            >
              <v-icon>{{ mdiTrashCanOutline }}</v-icon>
            </v-btn>
          </div>

          <DatastreamCardSelector
            v-model="row.datastreamId"
            :datastreams="siteDatastreams"
            label="Datastream *"
            :loading="loadingDatastreams"
            :disabled="!selectedThingId || loadingExisting"
            :rules="rules.required"
            density="compact"
            class="mb-2"
          />

          <v-select
            v-model="row.ruleType"
            :items="ruleTypeOptions"
            item-title="title"
            item-value="value"
            label="Rule type *"
            density="compact"
            :rules="rules.required"
            :disabled="loadingExisting"
            class="mb-2"
            @update:model-value="normalizeRuleForType(row)"
          />

          <div v-if="row.ruleType === 'range'" class="rule-fields">
            <v-text-field
              v-model.number="row.minValue"
              label="Minimum value"
              type="number"
              density="compact"
              clearable
              :disabled="loadingExisting"
              @click:clear="row.minValue = null"
            />
            <v-text-field
              v-model.number="row.maxValue"
              label="Maximum value"
              type="number"
              density="compact"
              clearable
              :disabled="loadingExisting"
              @click:clear="row.maxValue = null"
            />
          </div>

          <div v-else class="rule-fields">
            <v-text-field
              v-if="row.ruleType === 'rate_of_change'"
              v-model.number="row.maxValue"
              label="Maximum change *"
              type="number"
              density="compact"
              :rules="rules.requiredNumber"
              :disabled="loadingExisting"
              class="rule-fields__full"
            />
            <div class="window-interval-fields">
              <v-text-field
                v-model.number="row.windowInterval"
                label="Window interval *"
                type="number"
                min="1"
                density="compact"
                :rules="[...rules.required, positiveInteger]"
                :disabled="loadingExisting"
              />
              <v-select
                v-model="row.windowIntervalUnits"
                :items="windowUnitOptions"
                item-title="title"
                item-value="value"
                label="Window interval unit *"
                density="compact"
                :rules="rules.required"
                :disabled="loadingExisting"
              />
            </div>
          </div>
        </div>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel :disabled="saving" @click="$emit('close')">
          Cancel
        </v-btn-cancel>
        <v-btn
          v-if="isEditMode"
          color="error"
          variant="text"
          :loading="deleting"
          :disabled="saving"
          @click="onDelete"
        >
          Delete task
        </v-btn>
        <v-btn
          type="submit"
          variant="flat"
          rounded="lg"
          class="text-none"
          :style="submitStyle"
          :loading="saving"
          :disabled="deleting"
        >
          {{ isEditMode ? 'Save changes' : 'Create quality task' }}
        </v-btn>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { VForm } from 'vuetify/components'
import { mdiInformationOutline, mdiPlus, mdiTrashCanOutline } from '@mdi/js'
import { storeToRefs } from 'pinia'
import hs, {
  type Datastream,
  type IntervalPeriod,
  type MonitoringRule,
  type MonitoringRulePayload,
  type MonitoringRuleType,
  type MonitoringRuleWindowUnit,
  type MonitoringTask,
  type TaskSchedule,
} from '@hydroserver/client'
import { rules } from '@/utils/rules'
import { Snackbar } from '@/utils/notifications'
import { formatTime } from '@/utils/time'
import { datastreamsForThing } from '@/utils/orchestration/datastreams'
import {
  QUALITY_ACCENT,
  QUALITY_ACCENT_LIGHT,
} from '../workbench/orchestrationTabs'
import DatastreamCardSelector from '../shared/DatastreamCardSelector.vue'
import { useWorkspaceStore } from '@/store/workspaces'

const props = defineProps<{
  initialThingId?: string | null
  editTaskId?: string | null
}>()

const emit = defineEmits<{
  (e: 'created', task: MonitoringTask): void
  (e: 'updated', task: MonitoringTask): void
  (e: 'deleted'): void
  (e: 'close'): void
}>()

type RuleRow = {
  key: number
  id: string | null
  datastreamId: string | null
  ruleType: MonitoringRuleType
  minValue: number | null
  maxValue: number | null
  windowInterval: number | null
  windowIntervalUnits: MonitoringRuleWindowUnit | null
  lastCheckedAt: string | null
}

let rowKey = 0

const makeRuleRow = (init: Partial<RuleRow> = {}): RuleRow => ({
  key: ++rowKey,
  id: null,
  datastreamId: null,
  ruleType: 'range',
  minValue: null,
  maxValue: null,
  windowInterval: null,
  windowIntervalUnits: null,
  lastCheckedAt: null,
  ...init,
})

const isEditMode = computed(() => !!props.editTaskId)
const selectedThingId = computed(() => props.initialThingId ?? null)
const { selectedWorkspace } = storeToRefs(useWorkspaceStore())

const formRef = ref<VForm>()
const valid = ref<boolean | null>(null)
const showInfo = ref(false)
const loadingDatastreams = ref(false)
const loadingExisting = ref(false)
const saving = ref(false)
const deleting = ref(false)
const datastreams = ref<Datastream[]>([])
const originalRulesById = ref<Record<string, RuleRow>>({})

const taskName = ref('')
const description = ref('')
const recipients = ref<string[]>([])
const recipientInput = ref('')
const recipientInputError = ref('')
const ruleRows = ref<RuleRow[]>([makeRuleRow()])
const ruleErrors = ref<string[]>([])

const scheduleEnabled = ref(false)
const scheduleMode = ref<'interval' | 'crontab'>('interval')
const scheduleInterval = ref<number | null>(1)
const scheduleIntervalPeriod = ref<IntervalPeriod>('days')
const scheduleCrontab = ref('')
const scheduleStartTime = ref<string | null>(new Date().toISOString())

const toolbarStyle = computed(() => ({
  background: QUALITY_ACCENT_LIGHT,
  color: QUALITY_ACCENT,
}))
const submitStyle = computed(() => ({
  background: QUALITY_ACCENT,
  color: 'white',
}))

const ruleTypeOptions: { title: string; value: MonitoringRuleType }[] = [
  { title: 'Range', value: 'range' },
  { title: 'Rate of change', value: 'rate_of_change' },
  { title: 'Persistence', value: 'persistence' },
  { title: 'Missing data', value: 'missing_data' },
]

const windowUnitOptions: { title: string; value: MonitoringRuleWindowUnit }[] =
  [
    { title: 'Minutes', value: 'minutes' },
    { title: 'Hours', value: 'hours' },
    { title: 'Days', value: 'days' },
  ]

const scheduleUnitOptions = windowUnitOptions

const siteDatastreams = computed(() =>
  datastreamsForThing(datastreams.value, selectedThingId.value)
)

type Rule = (v: any) => true | string

const positiveInteger: Rule = (value) =>
  (Number.isInteger(Number(value)) && Number(value) >= 1) ||
  'Must be a positive whole number.'

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const normalizeEmails = (values: readonly unknown[]) => {
  const normalized: string[] = []
  const seen = new Set<string>()
  for (const value of values) {
    const email = toEmailString(value)
    if (!email) continue
    const key = email.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    normalized.push(email)
  }
  return normalized
}

const toEmailString = (value: unknown) => {
  if (typeof value === 'string') return value.trim()
  if (value && typeof value === 'object' && 'title' in value) {
    return `${(value as { title?: string }).title ?? ''}`.trim()
  }
  return `${value ?? ''}`.trim()
}

const recipientEmails = computed<string[]>({
  get: () => recipients.value,
  set: (value) => {
    recipients.value = normalizeEmails(value)
  },
})

const recipientRules = [
  (value: string[] = []) =>
    value.every((email) => emailPattern.test(email)) ||
    'All notification recipient emails must be valid.',
]

function addRecipient() {
  const email = recipientInput.value.trim().replace(/,+$/, '')
  if (!email) {
    recipientInputError.value = ''
    recipientInput.value = ''
    return true
  }
  if (!emailPattern.test(email)) {
    recipientInputError.value = 'Email must be valid.'
    return false
  }
  recipientEmails.value = [...recipientEmails.value, email]
  recipientInput.value = ''
  recipientInputError.value = ''
  return true
}

function removeRecipient(index: number) {
  recipients.value = recipients.value.filter((_, i) => i !== index)
}

function addRule() {
  ruleRows.value.push(makeRuleRow())
}

function removeRule(index: number) {
  ruleRows.value.splice(index, 1)
}

function normalizeRuleForType(row: RuleRow) {
  if (row.ruleType === 'range') {
    row.windowInterval = null
    row.windowIntervalUnits = null
    return
  }
  row.minValue = null
  if (row.ruleType !== 'rate_of_change') row.maxValue = null
  if (!row.windowIntervalUnits) row.windowIntervalUnits = 'hours'
}

function ensureIsoUtc(value: string | null = ''): string | null {
  return value && !/([Zz]|[+-]\d{2}:\d{2})$/.test(value) ? `${value}Z` : value
}

function isoToInput(iso: string | null = ''): string {
  if (!iso) return ''
  const normalized = ensureIsoUtc(iso) ?? ''
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return ''
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}

function inputToIso(value: string): string {
  const date = new Date(value)
  return date.toISOString()
}

const scheduleStartInput = computed({
  get: () => isoToInput(scheduleStartTime.value),
  set: (value: string) => {
    scheduleStartTime.value = value ? inputToIso(value) : null
  },
})

function schedulePayload(): TaskSchedule | null {
  if (!scheduleEnabled.value) return null
  if (scheduleMode.value === 'crontab') {
    return {
      enabled: true,
      startTime: scheduleStartTime.value,
      nextRunAt: null,
      crontab: scheduleCrontab.value.trim(),
      interval: null,
      intervalPeriod: null,
    }
  }
  return {
    enabled: true,
    startTime: scheduleStartTime.value,
    nextRunAt: null,
    crontab: null,
    interval: scheduleInterval.value,
    intervalPeriod: scheduleIntervalPeriod.value,
  }
}

function hydrateSchedule(schedule: TaskSchedule | null | undefined) {
  if (!schedule) {
    scheduleEnabled.value = false
    scheduleMode.value = 'interval'
    scheduleInterval.value = 1
    scheduleIntervalPeriod.value = 'days'
    scheduleCrontab.value = ''
    scheduleStartTime.value = new Date().toISOString()
    return
  }
  scheduleEnabled.value = true
  scheduleMode.value = schedule.crontab ? 'crontab' : 'interval'
  scheduleInterval.value = schedule.interval ?? 1
  scheduleIntervalPeriod.value = schedule.intervalPeriod ?? 'days'
  scheduleCrontab.value = schedule.crontab ?? ''
  scheduleStartTime.value = schedule.startTime ?? new Date().toISOString()
}

async function loadDatastreams() {
  if (!selectedWorkspace.value?.id) {
    datastreams.value = []
    return
  }

  loadingDatastreams.value = true
  try {
    const items = await hs.datastreams.listAllItems({
      workspace_id: [selectedWorkspace.value.id],
      order_by: ['name'],
      expand_related: true,
    } as any)
    datastreams.value = items as Datastream[]
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load datastreams.')
  } finally {
    loadingDatastreams.value = false
  }
}

function ruleToRow(rule: MonitoringRule): RuleRow {
  return makeRuleRow({
    id: rule.id,
    datastreamId: (rule.datastream as any)?.id ?? null,
    ruleType: rule.ruleType,
    minValue: rule.minValue ?? null,
    maxValue: rule.maxValue ?? null,
    windowInterval: rule.windowInterval ?? null,
    windowIntervalUnits: rule.windowIntervalUnits ?? null,
    lastCheckedAt: rule.lastCheckedAt ?? null,
  })
}

async function loadExistingTask() {
  if (!props.editTaskId) return
  loadingExisting.value = true
  try {
    const [taskRes, rulesRes] = await Promise.all([
      hs.monitoringTasks.get(props.editTaskId),
      hs.monitoringTasks.listRules(props.editTaskId, {
        order_by: ['datastreamId', 'ruleType'],
      } as any),
    ])

    if (!taskRes.ok || !taskRes.data) {
      Snackbar.error(taskRes.message || 'Unable to load quality task.')
      return
    }

    taskName.value = taskRes.data.name ?? ''
    description.value = taskRes.data.description ?? ''
    recipients.value = [...(taskRes.data.recipients ?? [])]
    hydrateSchedule(taskRes.data.schedule)

    const rows = ((rulesRes.ok ? rulesRes.data : []) as MonitoringRule[]).map(
      ruleToRow
    )
    ruleRows.value = rows.length ? rows : []
    originalRulesById.value = Object.fromEntries(
      rows.filter((row) => row.id).map((row) => [row.id!, { ...row }])
    )
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load quality task.')
  } finally {
    loadingExisting.value = false
  }
}

function validateRuleRows() {
  const errors: string[] = []
  if (!ruleRows.value.length) {
    errors.push('Add at least one quality rule.')
  }

  ruleRows.value.forEach((row, index) => {
    const label = `Rule ${index + 1}`
    if (!row.datastreamId) errors.push(`${label}: select a datastream.`)

    if (row.ruleType === 'range') {
      const hasMin = row.minValue !== null && row.minValue !== undefined
      const hasMax = row.maxValue !== null && row.maxValue !== undefined
      if (!hasMin && !hasMax) {
        errors.push(`${label}: enter a minimum value, maximum value, or both.`)
      }
      if (hasMin && hasMax && Number(row.minValue) > Number(row.maxValue)) {
        errors.push(`${label}: minimum value must be less than maximum value.`)
      }
      return
    }

    if (row.ruleType === 'rate_of_change' && row.maxValue == null) {
      errors.push(`${label}: enter a maximum change.`)
    }
    if (!row.windowInterval || Number(row.windowInterval) < 1) {
      errors.push(`${label}: enter a positive window interval.`)
    }
    if (!row.windowIntervalUnits) errors.push(`${label}: select a window unit.`)
  })

  ruleErrors.value = errors
  return errors.length === 0
}

function rowPayload(row: RuleRow): MonitoringRulePayload {
  const payload: MonitoringRulePayload = {
    datastreamId: row.datastreamId!,
    ruleType: row.ruleType,
    minValue: null,
    maxValue: null,
    windowInterval: null,
    windowIntervalUnits: null,
  }

  if (row.ruleType === 'range') {
    payload.minValue = row.minValue ?? null
    payload.maxValue = row.maxValue ?? null
  } else {
    payload.windowInterval = row.windowInterval
    payload.windowIntervalUnits = row.windowIntervalUnits
    if (row.ruleType === 'rate_of_change') payload.maxValue = row.maxValue
  }

  return payload
}

async function syncRules(taskId: string) {
  const currentExistingIds = new Set(
    ruleRows.value.map((row) => row.id).filter(Boolean) as string[]
  )
  for (const id of Object.keys(originalRulesById.value)) {
    if (!currentExistingIds.has(id)) {
      const res = await hs.monitoringTasks.deleteRule(taskId, id)
      if (!res.ok)
        throw new Error(res.message || 'Unable to delete quality rule.')
    }
  }

  for (const row of ruleRows.value) {
    const payload = rowPayload(row)
    const original = row.id ? originalRulesById.value[row.id] : null
    const immutableChanged =
      original &&
      (original.datastreamId !== row.datastreamId ||
        original.ruleType !== row.ruleType)

    if (!row.id || immutableChanged) {
      if (row.id) {
        const deleteRes = await hs.monitoringTasks.deleteRule(taskId, row.id)
        if (!deleteRes.ok) {
          throw new Error(
            deleteRes.message || 'Unable to replace quality rule.'
          )
        }
      }
      const createRes = await hs.monitoringTasks.createRule(taskId, payload)
      if (!createRes.ok) {
        throw new Error(createRes.message || 'Unable to create quality rule.')
      }
      continue
    }

    const updateRes = await hs.monitoringTasks.updateRule(taskId, row.id, {
      minValue: payload.minValue,
      maxValue: payload.maxValue,
      windowInterval: payload.windowInterval,
      windowIntervalUnits: payload.windowIntervalUnits,
    })
    if (!updateRes.ok) {
      throw new Error(updateRes.message || 'Unable to update quality rule.')
    }
  }
}

async function onSubmit() {
  await formRef.value?.validate()
  if (!addRecipient()) return
  if (!valid.value) return
  if (!selectedThingId.value && !isEditMode.value) {
    Snackbar.error('Select a site before creating a quality task.')
    return
  }
  if (!validateRuleRows()) return

  saving.value = true
  try {
    if (isEditMode.value) await onUpdate()
    else await onCreate()
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to save quality task.')
  } finally {
    saving.value = false
  }
}

async function onCreate() {
  const taskRes = await hs.monitoringTasks.create({
    id: '',
    name: taskName.value.trim(),
    thingId: selectedThingId.value!,
    description: description.value.trim() || null,
    recipients: recipients.value,
    schedule: schedulePayload(),
  })

  if (!taskRes.ok || !taskRes.data?.id) {
    Snackbar.error(taskRes.message || 'Unable to create quality task.')
    return
  }

  await syncRules(taskRes.data.id)
  Snackbar.success('Quality task created.')
  emit('created', taskRes.data)
  emit('close')
}

async function onUpdate() {
  const taskId = props.editTaskId!
  const taskRes = await hs.monitoringTasks.update({
    id: taskId,
    name: taskName.value.trim(),
    description: description.value.trim() || null,
    recipients: recipients.value,
    schedule: schedulePayload(),
  })

  if (!taskRes.ok || !taskRes.data) {
    Snackbar.error(taskRes.message || 'Unable to update quality task.')
    return
  }

  await syncRules(taskId)
  Snackbar.success('Quality task updated.')
  emit('updated', taskRes.data)
  emit('close')
}

async function onDelete() {
  if (!props.editTaskId) return
  deleting.value = true
  try {
    const res = await hs.monitoringTasks.delete(props.editTaskId)
    if (!res.ok) {
      Snackbar.error(res.message || 'Unable to delete quality task.')
      return
    }
    Snackbar.success('Quality task deleted.')
    emit('deleted')
    emit('close')
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to delete quality task.')
  } finally {
    deleting.value = false
  }
}

watch(recipientInput, () => {
  if (recipientInputError.value) recipientInputError.value = ''
})

watch(
  () => props.initialThingId,
  () => {
    if (isEditMode.value) return
    ruleRows.value = [makeRuleRow()]
  }
)

watch(scheduleEnabled, (enabled) => {
  if (enabled && !scheduleStartTime.value) {
    scheduleStartTime.value = new Date().toISOString()
  }
})

onMounted(async () => {
  await loadDatastreams()
  if (isEditMode.value) await loadExistingTask()
})
</script>

<style scoped>
.section-heading {
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
}

.schedule-grid {
  display: grid;
  grid-template-columns: minmax(160px, auto) minmax(120px, 0.4fr) minmax(
      150px,
      0.6fr
    );
  gap: 12px;
  align-items: start;
}

.schedule-mode,
.schedule-crontab {
  grid-column: span 1;
}

.schedule-start {
  grid-column: 1 / -1;
}

.empty-rules {
  border: 1px dashed rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  color: rgba(var(--v-theme-on-surface), 0.62);
  padding: 18px;
  text-align: center;
}

.rule-card {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  margin-bottom: 12px;
  padding: 14px;
}

.rule-card__header {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.rule-card__title {
  font-size: 0.95rem;
  font-weight: 800;
}

.rule-card__subtitle {
  color: rgba(var(--v-theme-on-surface), 0.62);
  font-size: 0.78rem;
  margin-top: 2px;
}

.rule-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.rule-fields > :only-child {
  grid-column: 1 / -1;
}

.rule-fields__full,
.window-interval-fields {
  grid-column: 1 / -1;
}

.window-interval-fields {
  display: grid;
  grid-template-columns: minmax(120px, 0.4fr) minmax(160px, 0.6fr);
  gap: 10px;
}

@media (max-width: 760px) {
  .schedule-grid,
  .rule-fields {
    grid-template-columns: minmax(0, 1fr);
  }

  .window-interval-fields {
    grid-template-columns: minmax(0, 1fr);
  }

  .schedule-start {
    grid-column: auto;
  }
}
</style>
