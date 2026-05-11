<template>
  <v-card class="d-flex flex-column" style="max-height: 90vh">
    <div class="shrink-0">
      <v-toolbar :style="DATA_PRODUCT_TOOLBAR_STYLE" flat>
        <v-card-title>{{
          isEditMode ? 'Edit derivation task' : 'Create derivation task'
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
        :color="DATA_PRODUCT_ACCENT"
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
          :color="DATA_PRODUCT_ACCENT"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-5"
        >
          Combine two or more input datastreams using a mathematical formula to
          produce a new derived output datastream. Inputs are aligned to a
          regular time grid before the formula is applied.
        </v-alert>

        <v-text-field
          v-model="taskName"
          label="Task name *"
          :rules="rules.requiredAndMaxLength255"
          :disabled="loadingExisting"
          class="mb-2"
        />

        <ScheduleFields
          v-model="schedule"
          :disabled="loadingExisting"
          :color="DATA_PRODUCT_ACCENT"
        />

        <v-divider class="mb-4" />

        <DatastreamCardSelector
          v-model="outputDatastreamId"
          :datastreams="siteDatastreams"
          label="Output datastream *"
          :disabled="isEditMode || !selectedThingId || loadingExisting"
          :loading="loadingDatastreams"
          :rules="rules.required"
          class="mb-2"
        />

        <v-divider class="mb-4" />

        <!-- Input datastreams -->
        <div class="d-flex align-center mb-3">
          <div
            class="text-caption text-medium-emphasis font-weight-bold text-uppercase"
          >
            Input datastreams
          </div>
          <v-chip
            v-if="inputs.length < 2"
            size="x-small"
            color="warning"
            variant="tonal"
            class="ml-2"
          >
            at least 2 required
          </v-chip>
        </div>

        <div class="inputs-list mb-2">
          <div v-for="(inp, i) in inputs" :key="inp.key" class="input-row mb-2">
            <DatastreamCardSelector
              v-model="inp.datastreamId"
              :datastreams="datastreams"
              :label="`Input datastream ${i + 1} *`"
              :loading="loadingDatastreams"
              :disabled="loadingExisting"
              :rules="rules.required"
              density="compact"
              class="input-ds"
            />
            <v-text-field
              v-model="inp.variableName"
              :label="`Variable *`"
              :rules="[
                ...rules.required,
                validIdentifier,
                noReservedName,
                uniqueVarName(i),
              ]"
              :disabled="loadingExisting"
              density="compact"
              class="input-var"
            />
            <v-btn
              icon
              variant="text"
              size="small"
              color="error"
              :disabled="inputs.length <= 2 || loadingExisting"
              @click="removeInput(i)"
            >
              <v-icon>{{ mdiClose }}</v-icon>
            </v-btn>
          </div>
        </div>

        <v-btn
          variant="outlined"
          :color="DATA_PRODUCT_ACCENT"
          size="small"
          :prepend-icon="mdiPlus"
          :disabled="loadingExisting"
          class="mb-4 text-none"
          @click="addInput"
        >
          Add input
        </v-btn>

        <v-divider class="mb-4" />

        <!-- Formula -->
        <div
          class="text-caption text-medium-emphasis font-weight-bold text-uppercase mb-2"
        >
          Formula
        </div>

        <div class="mb-3">
          <div class="d-flex flex-wrap align-center gap-1 mb-1">
            <span class="text-caption text-medium-emphasis mr-1"
              >Variables:</span
            >
            <v-chip
              v-for="inp in namedInputs"
              :key="inp.variableName"
              size="x-small"
              :color="DATA_PRODUCT_ACCENT"
              variant="tonal"
              class="font-weight-mono"
            >
              {{ inp.variableName }}
            </v-chip>
            <span v-if="!namedInputs.length" class="text-caption text-disabled">
              (define variable names above)
            </span>
          </div>
          <div class="d-flex flex-wrap align-center gap-1">
            <span class="text-caption text-medium-emphasis mr-1"
              >Functions:</span
            >
            <v-chip
              v-for="fn in ALLOWED_FUNCTIONS"
              :key="fn"
              size="x-small"
              variant="outlined"
              color="grey-darken-1"
              class="font-weight-mono"
            >
              {{ fn }}
            </v-chip>
          </div>
        </div>

        <v-text-field
          v-model="formula"
          label="Output = *"
          :placeholder="formulaPlaceholder"
          :rules="[
            ...rules.required,
            formulaUsesVariable,
            formulaAllowedTokens,
          ]"
          :disabled="loadingExisting"
          class="mb-2 formula-field"
          font-family="monospace"
        />

        <v-divider class="mb-4" />

        <!-- Output interval -->
        <div
          class="text-caption text-medium-emphasis font-weight-bold text-uppercase mb-3"
        >
          Output interval
        </div>

        <div class="d-flex gap-3 mb-2">
          <v-text-field
            v-model.number="outputInterval"
            label="Every *"
            type="number"
            min="1"
            :rules="[...rules.required, positiveInteger]"
            :disabled="loadingExisting"
            density="compact"
            class="shrink"
            style="max-width: 120px"
          />
          <v-select
            v-model="outputIntervalUnits"
            :items="intervalUnitOptions"
            item-title="title"
            item-value="value"
            label="Unit *"
            :rules="rules.required"
            :disabled="loadingExisting"
            density="compact"
            class="grow"
          />
        </div>

        <!-- Max gap -->
        <div class="d-flex align-center mb-3">
          <div
            class="text-caption text-medium-emphasis font-weight-bold text-uppercase"
          >
            Max interpolation gap
          </div>
          <v-tooltip location="end" max-width="280">
            <template #activator="{ props: tp }">
              <v-icon v-bind="tp" size="16" color="grey-darken-1" class="ml-1">
                {{ mdiInformationOutline }}
              </v-icon>
            </template>
            Gaps longer than this in any input will not be interpolated. Helps
            prevent unrealistic values across extended outages.
          </v-tooltip>
          <v-spacer />
          <v-switch
            v-model="configureMaxGap"
            :color="DATA_PRODUCT_ACCENT"
            density="compact"
            hide-details
            :disabled="loadingExisting"
            label="Configure"
          />
        </div>

        <div v-if="configureMaxGap" class="d-flex gap-3 mb-2">
          <v-text-field
            v-model.number="maxGapInterval"
            label="Max gap *"
            type="number"
            min="1"
            :rules="[...rules.required, positiveInteger]"
            :disabled="loadingExisting"
            density="compact"
            class="shrink"
            style="max-width: 120px"
          />
          <v-select
            v-model="maxGapIntervalUnits"
            :items="intervalUnitOptions"
            item-title="title"
            item-value="value"
            label="Unit *"
            :rules="rules.required"
            :disabled="loadingExisting"
            density="compact"
            class="grow"
          />
        </div>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel :disabled="saving" @click="$emit('close')"
          >Cancel</v-btn-cancel
        >
        <v-btn-primary
          type="submit"
          :color="DATA_PRODUCT_ACCENT"
          :loading="saving"
          :disabled="deleting"
        >
          {{ isEditMode ? 'Save changes' : 'Create derivation task' }}
        </v-btn-primary>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { VForm } from 'vuetify/components'
import { mdiClose, mdiPlus, mdiInformationOutline } from '@mdi/js'
import { storeToRefs } from 'pinia'
import hs, {
  type Datastream,
  type DataProductTask,
  type IntervalUnit,
  type TaskSchedule,
} from '@hydroserver/client'
import { rules } from '@/utils/rules'
import { Snackbar } from '@/utils/notifications'
import { datastreamsForThing } from '@/utils/orchestration/datastreams'
import {
  DATA_PRODUCT_ACCENT,
  DATA_PRODUCT_TOOLBAR_STYLE,
} from '@/utils/orchestration/dataProductTheme'
import DatastreamCardSelector from '../shared/DatastreamCardSelector.vue'
import ScheduleFields from '../shared/ScheduleFields.vue'
import { useWorkspaceStore } from '@/store/workspaces'

const ALLOWED_FUNCTIONS = [
  'abs',
  'min',
  'max',
  'sqrt',
  'log',
  'log10',
  'log2',
  'exp',
  'sin',
  'cos',
  'tan',
  'asin',
  'acos',
  'atan',
  'floor',
  'ceil',
]

const RESERVED_NAMES = new Set(ALLOWED_FUNCTIONS)

const VAR_LETTERS = 'abcdefghijklmnopqrstuvwxyz'.split('')

const props = defineProps<{
  initialThingId?: string | null
  editTaskId?: string | null
}>()

const emit = defineEmits<{
  (e: 'created', task: DataProductTask): void
  (e: 'updated', task: DataProductTask): void
  (e: 'deleted'): void
  (e: 'close'): void
}>()

type InputRow = {
  key: number
  datastreamId: string | null
  variableName: string
}

let _keyCounter = 0
const makeRow = (letter?: string): InputRow => ({
  key: ++_keyCounter,
  datastreamId: null,
  variableName: letter ?? '',
})

const isEditMode = computed(() => !!props.editTaskId)
const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
const selectedWorkspaceId = computed(() => selectedWorkspace.value?.id ?? null)

const formRef = ref<VForm>()
const valid = ref<boolean | null>(null)
const showInfo = ref(false)
const loadingDatastreams = ref(false)
const loadingExisting = ref(false)
const saving = ref(false)
const deleting = ref(false)
const datastreams = ref<Datastream[]>([])

const existingTransformationId = ref<string | null>(null)

const taskName = ref('')
const schedule = ref<TaskSchedule | null>(null)
const outputDatastreamId = ref<string | null>(null)
const inputs = ref<InputRow[]>([makeRow('a'), makeRow('b')])
const formula = ref('')
const outputInterval = ref<number | null>(1)
const outputIntervalUnits = ref<IntervalUnit>('hours')
const configureMaxGap = ref(false)
const maxGapInterval = ref<number | null>(null)
const maxGapIntervalUnits = ref<IntervalUnit | null>(null)

const selectedThingId = computed(() => props.initialThingId ?? null)

const namedInputs = computed(() =>
  inputs.value.filter((inp) => inp.variableName.trim())
)

const formulaPlaceholder = computed(() => {
  const vars = namedInputs.value.map((inp) => inp.variableName)
  if (vars.length >= 2) return `e.g. (${vars[0]} + ${vars[1]}) / 2`
  return 'e.g. (a + b) / 2'
})

const intervalUnitOptions = [
  { title: 'Minutes', value: 'minutes' },
  { title: 'Hours', value: 'hours' },
  { title: 'Days', value: 'days' },
  { title: 'Weeks', value: 'weeks' },
  { title: 'Months', value: 'months' },
]

const siteDatastreams = computed(() => {
  const thingId = selectedThingId.value
  return datastreamsForThing(datastreams.value, thingId)
})

function nextVarName(): string {
  const used = new Set(inputs.value.map((r) => r.variableName))
  for (const letter of VAR_LETTERS) {
    if (!used.has(letter) && !RESERVED_NAMES.has(letter)) return letter
  }
  for (let n = 1; ; n++) {
    const candidate = `x${n}`
    if (!used.has(candidate)) return candidate
  }
}

function addInput() {
  inputs.value.push(makeRow(nextVarName()))
}

function removeInput(index: number) {
  if (inputs.value.length <= 2) return
  inputs.value.splice(index, 1)
}

// --- Validation rules ---

type Rule = (v: any) => true | string

const positiveInteger: Rule = (v) =>
  (Number.isInteger(Number(v)) && Number(v) >= 1) ||
  'Must be a positive whole number.'

const validIdentifier: Rule = (v) =>
  /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(String(v ?? '')) ||
  'Must start with a letter or underscore, then letters, digits, or underscores.'

const noReservedName: Rule = (v) =>
  !RESERVED_NAMES.has(String(v ?? '')) ||
  `'${v}' is a reserved function name. Use a different variable name.`

const uniqueVarName =
  (index: number): Rule =>
  (v) => {
    const name = String(v ?? '').trim()
    if (!name) return true
    const dup = inputs.value.some(
      (inp, i) => i !== index && inp.variableName.trim() === name
    )
    return !dup || 'Variable names must be unique.'
  }

const formulaUsesVariable: Rule = (v) => {
  const f = String(v ?? '').trim()
  if (!f) return true
  const definedVars = inputs.value
    .map((inp) => inp.variableName.trim())
    .filter(Boolean)
  const usedAny = definedVars.some((name) => {
    const re = new RegExp(`\\b${name}\\b`)
    return re.test(f)
  })
  return (
    usedAny ||
    'Formula must reference at least one of the defined variable names.'
  )
}

const formulaAllowedTokens: Rule = (v) => {
  const s = String(v ?? '').trim()
  if (!s) return true
  let remaining = s
  remaining = remaining.replace(/\b[a-zA-Z_][a-zA-Z0-9_]*\b/g, '')
  remaining = remaining.replace(/\d+(\.\d+)?/g, '')
  remaining = remaining.replace(/[\s+\-*/().,%]/g, '')
  if (remaining.length > 0) {
    return `Unexpected character(s) in formula: ${remaining[0]}`
  }
  return true
}

// --- Data loading ---

async function loadDatastreams() {
  const workspaceId = selectedWorkspaceId.value
  if (!workspaceId) {
    datastreams.value = []
    return
  }

  loadingDatastreams.value = true
  try {
    const items = await hs.datastreams.listAllItems({
      workspace_id: [workspaceId],
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

async function loadExistingTask() {
  if (!props.editTaskId) return
  loadingExisting.value = true
  try {
    const [taskRes, transformRes] = await Promise.all([
      hs.dataProductTasks.get(props.editTaskId),
      hs.dataProductTasks.listCompositeExpressionTransformations(
        props.editTaskId
      ),
    ])

    if (taskRes.ok && taskRes.data?.name) {
      taskName.value = taskRes.data.name
      schedule.value = taskRes.data.schedule ?? null
    }

    if (transformRes.ok && transformRes.data?.length) {
      const t = transformRes.data[0]
      existingTransformationId.value = t.id
      outputDatastreamId.value = (t.outputDatastream as any)?.id ?? null
      formula.value = t.formula
      outputInterval.value = t.outputInterval
      outputIntervalUnits.value = t.outputIntervalUnits

      if (t.maxGapInterval && t.maxGapIntervalUnits) {
        configureMaxGap.value = true
        maxGapInterval.value = t.maxGapInterval
        maxGapIntervalUnits.value = t.maxGapIntervalUnits
      }

      if (t.inputDatastreams?.length) {
        inputs.value = t.inputDatastreams.map((inp: any) => ({
          key: ++_keyCounter,
          datastreamId: inp.datastream?.id ?? null,
          variableName: inp.variableName ?? '',
        }))
      }
    }
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load existing task.')
  } finally {
    loadingExisting.value = false
  }
}

// --- Submit ---

async function onSubmit() {
  await formRef.value?.validate()
  if (!valid.value) return
  if (!outputDatastreamId.value) return
  if (!outputInterval.value) return
  if (inputs.value.length < 2) {
    Snackbar.error('Add at least 2 input datastreams.')
    return
  }
  if (inputs.value.some((inp) => !inp.datastreamId)) return

  const inputDatastreams = inputs.value.map((inp) => ({
    datastreamId: inp.datastreamId!,
    variableName: inp.variableName.trim(),
  }))

  const gapPayload =
    configureMaxGap.value && maxGapInterval.value && maxGapIntervalUnits.value
      ? {
          maxGapInterval: maxGapInterval.value,
          maxGapIntervalUnits: maxGapIntervalUnits.value,
        }
      : { maxGapInterval: null, maxGapIntervalUnits: null }

  saving.value = true
  try {
    if (isEditMode.value) {
      await onUpdate(inputDatastreams, gapPayload)
    } else {
      await onCreate(inputDatastreams, gapPayload)
    }
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to save derivation task.')
  } finally {
    saving.value = false
  }
}

async function onCreate(
  inputDatastreams: { datastreamId: string; variableName: string }[],
  gapPayload: {
    maxGapInterval: number | null
    maxGapIntervalUnits: IntervalUnit | null
  }
) {
  const thingId = selectedThingId.value
  if (!thingId) {
    Snackbar.error('Select a site before creating a derivation task.')
    return
  }

  const taskRes = await hs.dataProductTasks.create({
    id: '',
    name: taskName.value.trim(),
    thingId,
    description: null,
    schedule: schedule.value,
  })

  if (!taskRes.ok || !taskRes.data?.id) {
    Snackbar.error(taskRes.message || 'Unable to create derivation task.')
    return
  }

  const transformRes =
    await hs.dataProductTasks.createCompositeExpressionTransformation(
      taskRes.data.id,
      {
        outputDatastreamId: outputDatastreamId.value!,
        inputDatastreams,
        formula: formula.value.trim(),
        outputInterval: outputInterval.value!,
        outputIntervalUnits: outputIntervalUnits.value,
        ...gapPayload,
      }
    )

  if (!transformRes.ok) {
    Snackbar.error(
      transformRes.message || 'Unable to create derivation transformation.'
    )
    return
  }

  emit('created', taskRes.data)
  emit('close')
}

async function onUpdate(
  inputDatastreams: { datastreamId: string; variableName: string }[],
  gapPayload: {
    maxGapInterval: number | null
    maxGapIntervalUnits: IntervalUnit | null
  }
) {
  const taskId = props.editTaskId!

  const taskRes = await hs.dataProductTasks.update({
    id: taskId,
    name: taskName.value.trim(),
    schedule: schedule.value,
  })

  if (!taskRes.ok) {
    Snackbar.error(taskRes.message || 'Unable to update task name.')
    return
  }

  if (existingTransformationId.value) {
    const transformRes =
      await hs.dataProductTasks.updateCompositeExpressionTransformation(
        taskId,
        existingTransformationId.value,
        {
          inputDatastreams,
          formula: formula.value.trim(),
          outputInterval: outputInterval.value!,
          outputIntervalUnits: outputIntervalUnits.value,
          ...gapPayload,
        }
      )

    if (!transformRes.ok) {
      Snackbar.error(
        transformRes.message || 'Unable to update derivation transformation.'
      )
      return
    }
  }

  Snackbar.success('Derivation task updated.')
  emit('updated', taskRes.data!)
  emit('close')
}

async function onDelete() {
  if (!props.editTaskId) return
  deleting.value = true
  try {
    const res = await hs.dataProductTasks.delete(props.editTaskId)
    if (!res.ok) {
      Snackbar.error(res.message || 'Unable to delete derivation task.')
      return
    }
    Snackbar.success('Derivation task deleted.')
    emit('deleted')
    emit('close')
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to delete derivation task.')
  } finally {
    deleting.value = false
  }
}

watch(
  () => props.initialThingId,
  () => {
    if (!isEditMode.value) {
      outputDatastreamId.value = null
    }
  }
)

watch(configureMaxGap, (val) => {
  if (!val) {
    maxGapInterval.value = null
    maxGapIntervalUnits.value = null
  }
})

onMounted(async () => {
  await loadDatastreams()
  if (isEditMode.value) await loadExistingTask()
})
</script>

<style scoped>
.input-row {
  display: grid;
  grid-template-columns: 1fr 140px 36px;
  gap: 8px;
  align-items: start;
}
.font-weight-mono {
  font-family: monospace;
}
</style>
