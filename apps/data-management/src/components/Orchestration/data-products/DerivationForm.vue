<template>
  <v-card class="d-flex flex-column" style="max-height: 90vh">
    <div class="shrink-0">
      <v-toolbar color="primary" flat>
        <div class="d-flex align-center px-4">
          <v-card-title class="hs-subheading pa-0">{{
            isEditMode ? 'Edit derivation task' : 'Create derivation task'
          }}</v-card-title>
          <v-btn
            icon
            class="ml-n1"
            variant="text"
            aria-label="Toggle task info"
            @click="showInfo = !showInfo"
          >
            <v-icon :icon="mdiInformationOutline" size="17" />
          </v-btn>
        </div>
      </v-toolbar>
      <v-divider />
      <v-progress-linear v-if="loadingExisting" indeterminate color="primary" />
    </div>

    <v-form
      ref="formRef"
      v-model="valid"
      validate-on="input"
      class="d-flex flex-column grow overflow-hidden"
      @submit.prevent="onSubmit"
    >
      <v-card-text class="overflow-y-auto grow">
        <TaskFormLayout>
          <v-alert
            v-if="showInfo"
            color="primary"
            type="info"
            variant="tonal"
            density="compact"
          >
            Apply a mathematical formula to one or more input datastreams to
            produce a new output datastream. With more than one input, they're
            matched by exact timestamp; if inputs stop lining up, the run stops
            there until they're back in sync.
          </v-alert>

          <TaskFormSection>
            <v-text-field
              v-model="taskName"
              label="Task name"
              class="required-label"
              :rules="rules.requiredAndMaxLength255"
              :disabled="loadingExisting"
            />
          </TaskFormSection>

          <v-divider />

          <ScheduleFields v-model="schedule" :disabled="loadingExisting" />

          <v-divider />

          <TaskFormSection>
            <div v-for="(inp, i) in inputs" :key="inp.key" class="input-row">
              <DatastreamCardSelector
                v-model="inp.datastreamId"
                :datastreams="datastreams"
                :workspace-id="selectedWorkspaceId"
                :label="`Input datastream ${i + 1}`"
                :hint="i === 0 ? INPUT_SCOPE_NOTE : null"
                :scope-note="INPUT_SCOPE_NOTE"
                :loading="loadingDatastreams"
                :disabled="loadingExisting"
                :rules="rules.required"
                density="compact"
              />
              <v-text-field
                v-model="inp.variableName"
                label="Variable"
                class="required-label"
                :rules="[
                  ...rules.required,
                  validIdentifier,
                  noReservedName,
                  uniqueVarName(i),
                ]"
                :disabled="loadingExisting"
              />
              <v-btn-icon
                :icon="mdiClose"
                size="small"
                :aria-label="`Remove input datastream ${i + 1}`"
                :disabled="inputs.length <= 1 || loadingExisting"
                @click="removeInput(i)"
              />
            </div>

            <div>
              <v-btn
                variant="outlined"
                size="small"
                :prepend-icon="mdiPlus"
                :disabled="loadingExisting"
                @click="addInput"
              >
                Add input
              </v-btn>
            </div>

            <DatastreamCardSelector
              v-model="outputDatastreamId"
              :datastreams="datastreams"
              :workspace-id="selectedWorkspaceId"
              :monitoring-site-id="selectedMonitoringSiteId"
              label="Output datastream"
              :hint="outputScopeNote"
              :scope-note="outputScopeNote"
              :disabled="!selectedMonitoringSiteId || loadingExisting"
              :loading="loadingDatastreams"
              :rules="rules.required"
            />
          </TaskFormSection>

          <v-divider />

          <TaskFormSection title="Formula">
            <div class="token-legend">
              <div class="token-legend__row">
                <span class="token-legend__label hs-text-sm">Variables:</span>
                <v-chip
                  v-for="inp in namedInputs"
                  :key="inp.variableName"
                  size="x-small"
                  color="primary"
                  variant="tonal"
                  class="hs-font-data"
                >
                  {{ inp.variableName }}
                </v-chip>
                <span
                  v-if="!namedInputs.length"
                  class="token-legend__empty hs-text-sm"
                >
                  (define variable names above)
                </span>
              </div>
              <div class="token-legend__row">
                <span class="token-legend__label hs-text-sm">Functions:</span>
                <v-chip
                  v-for="fn in ALLOWED_FUNCTIONS"
                  :key="fn"
                  size="x-small"
                  variant="outlined"
                  color="default"
                  class="hs-font-data"
                >
                  {{ fn }}
                </v-chip>
              </div>
            </div>

            <v-text-field
              v-model="formula"
              label="Output ="
              class="required-label hs-font-data"
              :placeholder="formulaPlaceholder"
              :rules="[
                ...rules.required,
                formulaUsesVariable,
                formulaAllowedTokens,
                formulaBalancedParens,
              ]"
              :disabled="loadingExisting"
            />
          </TaskFormSection>

          <v-divider />

          <TaskFormSection title="Error handling">
            <div class="toggle-row">
              <v-checkbox
                v-model="stopOnNoData"
                color="primary"
                hide-details
                :disabled="loadingExisting"
              >
                <template #label>
                  <span class="hs-text-sm">Stop on no-data value</span>
                </template>
              </v-checkbox>
              <v-tooltip location="end" max-width="280">
                <template #activator="{ props: tp }">
                  <v-icon v-bind="tp" size="16" class="toggle-row__info">
                    {{ mdiInformationOutline }}
                  </v-icon>
                </template>
                If an input is set to a no-data value, stop the run there
                instead of writing the output's no-data value and continuing.
              </v-tooltip>
            </div>

            <div class="toggle-row">
              <v-checkbox
                v-model="stopOnError"
                color="primary"
                hide-details
                :disabled="loadingExisting"
              >
                <template #label>
                  <span class="hs-text-sm">Stop on calculation error</span>
                </template>
              </v-checkbox>
              <v-tooltip location="end" max-width="280">
                <template #activator="{ props: tp }">
                  <v-icon v-bind="tp" size="16" class="toggle-row__info">
                    {{ mdiInformationOutline }}
                  </v-icon>
                </template>
                If the formula produces a non-finite result (e.g. divide by
                zero), stop the run there instead of writing the output's
                no-data value and continuing.
              </v-tooltip>
            </div>
          </TaskFormSection>
        </TaskFormLayout>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel :disabled="saving" @click="$emit('close')"
          >Cancel</v-btn-cancel
        >
        <v-btn-dialog-action
          type="submit"
          :loading="saving"
          :disabled="deleting"
        >
          {{ isEditMode ? 'Save changes' : 'Create derivation task' }}
        </v-btn-dialog-action>
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
  type DataProductTaskExpanded,
  type TaskSchedule,
} from '@hydroserver/client'
import { rules } from '@/utils/rules'
import { Snackbar } from '@/utils/notifications'
import DatastreamCardSelector from '../shared/DatastreamCardSelector.vue'
import ScheduleFields from '../shared/ScheduleFields.vue'
import TaskFormLayout from '../shared/TaskFormLayout.vue'
import TaskFormSection from '../shared/TaskFormSection.vue'
import {
  INPUT_SCOPE_NOTE,
  useDatastreamScopeNotes,
} from '@/composables/orchestration/useDatastreamScopeNotes'
import { useWorkspaceStore } from '@/store/workspaces'
import { useOrchestrationStore } from '@/store/orchestration'

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
  initialMonitoringSiteId?: string | null
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
const inputs = ref<InputRow[]>([makeRow('x')])
const formula = ref('')
const stopOnNoData = ref(true)
const stopOnError = ref(true)

const selectedMonitoringSiteId = computed(
  () => props.initialMonitoringSiteId ?? null
)

const { outputScopeNote } = useDatastreamScopeNotes(
  datastreams,
  selectedMonitoringSiteId
)

const namedInputs = computed(() =>
  inputs.value.filter((inp) => inp.variableName.trim())
)

const formulaPlaceholder = computed(() => {
  const vars = namedInputs.value.map((inp) => inp.variableName)
  if (vars.length >= 2) return `e.g. (${vars[0]} + ${vars[1]}) / 2`
  if (vars.length === 1) return `e.g. (${vars[0]} - 32) * 5/9`
  return 'e.g. (x - 32) * 5/9'
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
  if (inputs.value.length <= 1) return
  inputs.value.splice(index, 1)
}

// --- Validation rules ---

type Rule = (v: any) => true | string

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

  const definedVars = new Set(
    inputs.value.map((inp) => inp.variableName.trim()).filter(Boolean)
  )

  let i = 0
  while (i < s.length) {
    const ch = s[i]
    if (ch === ' ') {
      i++
      continue
    }
    // Identifier: a defined input variable or an allowed function name.
    if (/[a-zA-Z_]/.test(ch)) {
      let j = i
      while (j < s.length && /[a-zA-Z0-9_]/.test(s[j])) j++
      const name = s.slice(i, j)
      if (!definedVars.has(name) && !ALLOWED_FUNCTIONS.includes(name)) {
        return `Unknown name '${name}'. Use a defined variable or an allowed function.`
      }
      i = j
      continue
    }
    if (/\d/.test(ch)) {
      i++
      while (i < s.length && /\d/.test(s[i])) i++
      if (s[i] === '.') {
        i++
        while (i < s.length && /\d/.test(s[i])) i++
      }
      continue
    }
    if (ch === '(' || ch === ')' || ch === ',') {
      i++
      continue
    }
    if (ch === '*' && s[i + 1] === '*') {
      i += 2
      continue
    }
    if (ch === '+' || ch === '-' || ch === '*' || ch === '/') {
      i++
      continue
    }
    return 'Only numbers, defined variables, allowed functions, and + - * / ** ( ) , are allowed.'
  }
  return true
}

const formulaBalancedParens: Rule = (v) => {
  const s = String(v ?? '')
  if (!s.trim()) return true
  let depth = 0
  for (let i = 0; i < s.length; i++) {
    const ch = s[i]
    if (ch === '(') depth++
    else if (ch === ')') {
      depth--
      if (depth < 0) return `Unmatched ')' at position ${i + 1}.`
    }
  }
  return depth === 0
    ? true
    : `Missing ${depth} closing ')'${depth > 1 ? 's' : ''}.`
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
  const taskRes = await hs.dataProductTasks.get(props.editTaskId, {
    expand_related: true,
  })
  if (!taskRes.ok) {
    Snackbar.error(taskRes.message || 'Unable to load existing task.')
    loadingExisting.value = false
    return
  }

  const task = taskRes.data as unknown as DataProductTaskExpanded

  if (task?.name) {
    taskName.value = task.name
    schedule.value = task.schedule ?? null
  }

  if (task?.derivationTransformations?.length) {
    const t = task.derivationTransformations[0]
    existingTransformationId.value = t.id
    outputDatastreamId.value = (t.outputDatastream as any)?.id ?? null
    formula.value = t.formula
    stopOnNoData.value = t.stopOnNoData ?? true
    stopOnError.value = t.stopOnError ?? true

    if (t.inputDatastreams?.length) {
      inputs.value = t.inputDatastreams.map((inp: any) => ({
        key: ++_keyCounter,
        datastreamId: inp.datastream?.id ?? null,
        variableName: inp.variableName ?? '',
      }))
    }
  }

  loadingExisting.value = false
}

// --- Submit ---

async function onSubmit() {
  await formRef.value?.validate()
  if (!valid.value) return
  if (!outputDatastreamId.value) return
  if (inputs.value.some((inp) => !inp.datastreamId)) return

  const inputDatastreams = inputs.value.map((inp) => ({
    datastreamId: inp.datastreamId!,
    variableName: inp.variableName.trim(),
  }))

  saving.value = true
  try {
    if (isEditMode.value) {
      await onUpdate(inputDatastreams)
    } else {
      await onCreate(inputDatastreams)
    }
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to save derivation task.')
  } finally {
    saving.value = false
  }
}

async function onCreate(
  inputDatastreams: { datastreamId: string; variableName: string }[]
) {
  const monitoringSiteId = selectedMonitoringSiteId.value
  if (!monitoringSiteId) {
    Snackbar.error('Select a site before creating a derivation task.')
    return
  }

  const taskRes = await hs.dataProductTasks.create({
    id: '',
    name: taskName.value.trim(),
    monitoringSiteId,
    description: null,
    schedule: schedule.value,
  })

  if (!taskRes.ok || !taskRes.data?.id) {
    Snackbar.error(taskRes.message || 'Unable to create derivation task.')
    return
  }

  const transformRes = await hs.dataProductTasks.createDerivationTransformation(
    taskRes.data.id,
    {
      outputDatastreamId: outputDatastreamId.value!,
      inputDatastreams,
      formula: formula.value.trim(),
      stopOnNoData: stopOnNoData.value,
      stopOnError: stopOnError.value,
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
  inputDatastreams: { datastreamId: string; variableName: string }[]
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
      await hs.dataProductTasks.updateDerivationTransformation(
        taskId,
        existingTransformationId.value,
        {
          outputDatastreamId: outputDatastreamId.value!,
          inputDatastreams,
          formula: formula.value.trim(),
          stopOnNoData: stopOnNoData.value,
          stopOnError: stopOnError.value,
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
  () => props.initialMonitoringSiteId,
  () => {
    if (!isEditMode.value) {
      outputDatastreamId.value = null
    }
  }
)

onMounted(async () => {
  await Promise.all([
    loadDatastreams(),
    // Names the site in the scope notes even when it has no datastreams yet.
    useOrchestrationStore().ensureWorkspaceMonitoringSites(
      selectedWorkspaceId.value
    ),
  ])
  if (isEditMode.value) await loadExistingTask()
})
</script>

<style scoped>
.input-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140px auto;
  gap: var(--hs-space-8);
  /* The first row's selector carries a scope note above its button, so bottom
     alignment is what keeps the three controls on one line. */
  align-items: end;
}

.token-legend {
  display: flex;
  flex-direction: column;
  gap: var(--hs-space-6);
}

.token-legend__row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hs-space-4);
  align-items: center;
}

.token-legend__label {
  margin-right: var(--hs-space-4);
  color: var(--hs-text-secondary);
}

.token-legend__empty {
  color: var(--hs-text-muted);
}

.toggle-row {
  display: flex;
  gap: var(--hs-space-4);
  align-items: center;
}

.toggle-row__info {
  color: var(--hs-text-secondary);
}

@media (max-width: 700px) {
  .input-row {
    grid-template-columns: minmax(0, 1fr);
    align-items: stretch;
  }
}
</style>
