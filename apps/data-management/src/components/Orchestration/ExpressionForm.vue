<template>
  <v-card>
    <v-toolbar :style="DATA_PRODUCT_TOOLBAR_STYLE" flat>
      <v-card-title>{{
        isEditMode ? 'Edit expression task' : 'Create expression task'
      }}</v-card-title>
      <v-btn
        :icon="mdiInformationOutline"
        variant="text"
        aria-label="Toggle expression help"
        @click="showHelp = !showHelp"
      />
    </v-toolbar>
    <v-divider />

    <v-form
      ref="formRef"
      v-model="valid"
      validate-on="input"
      @submit.prevent="onSubmit"
    >
      <v-card-text>
        <v-alert
          v-if="showHelp"
          :color="DATA_PRODUCT_ACCENT"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-5"
        >
          Apply an expression to each incoming data point independently. Enter a
          single-line Python expression using
          <code>x</code> for the incoming value.
          <div class="mt-4">
            For example, if you wanted a unit conversion from degrees Fahrenheit
            (deg F) to Celsius (deg C), you'd type in '(x - 32) * 5/9'.
          </div>
          <div class="mt-4">
            <strong>Allowed operators:</strong>
            <span class="d-inline-flex flex-wrap ml-2">
              <v-chip
                v-for="op in ALLOWED_OPS"
                :key="op"
                size="small"
                variant="tonal"
                class="mr-1 mb-1"
              >
                {{ op }}
              </v-chip>
            </span>
          </div>
        </v-alert>

        <v-text-field
          v-model="taskName"
          label="Task name *"
          :rules="rules.requiredAndMaxLength255"
          :disabled="loadingExisting"
          class="mb-2"
        />

        <DatastreamCardSelector
          v-model="inputDatastreamId"
          :datastreams="siteDatastreams"
          label="Input datastream *"
          :loading="loading"
          :disabled="!selectedThingId || loadingExisting"
          :rules="rules.required"
          class="mb-2"
        />

        <DatastreamCardSelector
          v-model="outputDatastreamId"
          :datastreams="siteDatastreams"
          label="Output datastream *"
          :disabled="isEditMode || !selectedThingId || loadingExisting"
          :loading="loading"
          :rules="rules.required"
          class="mb-2"
        />

        <v-text-field
          v-model="formula"
          label="Output = *"
          placeholder="eg. (x - 32) * 5/9"
          :rules="[
            ...rules.required,
            formulaContainsVariable,
            exprAllowedTokens,
            exprBalancedParens,
          ]"
          :disabled="loadingExisting"
        />
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel :disabled="saving" @click="$emit('close')"
          >Cancel</v-btn-cancel
        >
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
          :style="DATA_PRODUCT_SUBMIT_STYLE"
          :loading="saving"
          :disabled="deleting"
        >
          {{ isEditMode ? 'Save changes' : 'Create expression task' }}
        </v-btn>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { VForm } from 'vuetify/components'
import { mdiInformationOutline } from '@mdi/js'
import hs, { type Datastream, type DataProductTask } from '@hydroserver/client'
import { rules } from '@/utils/rules'
import { Snackbar } from '@/utils/notifications'
import { datastreamsForThing } from '@/utils/orchestration/datastreams'
import {
  DATA_PRODUCT_ACCENT,
  DATA_PRODUCT_SUBMIT_STYLE,
  DATA_PRODUCT_TOOLBAR_STYLE,
} from '@/utils/orchestration/dataProductTheme'
import DatastreamCardSelector from './DatastreamCardSelector.vue'

const props = defineProps<{
  workspaceId: string
  initialThingId?: string | null
  editTaskId?: string | null
}>()

const emit = defineEmits<{
  (e: 'created', task: DataProductTask): void
  (e: 'updated', task: DataProductTask): void
  (e: 'deleted'): void
  (e: 'close'): void
}>()

const isEditMode = computed(() => !!props.editTaskId)

const formRef = ref<VForm>()
const valid = ref<boolean | null>(null)
const loading = ref(false)
const loadingExisting = ref(false)
const saving = ref(false)
const deleting = ref(false)
const showHelp = ref(false)
const datastreams = ref<Datastream[]>([])

const taskName = ref('')
const inputDatastreamId = ref<string | null>(null)
const outputDatastreamId = ref<string | null>(null)
const formula = ref('')
const selectedThingId = computed(() => props.initialThingId ?? null)
const existingTransformationId = ref<string | null>(null)
const ALLOWED_OPS = ['+', '-', '*', '/', '**', '(', ')']

const siteDatastreams = computed(() => {
  const thingId = selectedThingId.value
  return datastreamsForThing(datastreams.value, thingId)
})

async function loadOptions() {
  loading.value = true
  try {
    const datastreamItems = await hs.datastreams.listAllItems({
      workspace_id: [props.workspaceId],
      order_by: ['name'],
      expand_related: true,
    } as any)
    datastreams.value = datastreamItems as Datastream[]
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load expression form options.')
  } finally {
    loading.value = false
  }
}

async function loadExistingTask() {
  if (!props.editTaskId) return
  loadingExisting.value = true
  try {
    const [taskRes, transformRes] = await Promise.all([
      hs.dataProductTasks.get(props.editTaskId),
      hs.dataProductTasks.listExpressionTransformations(props.editTaskId),
    ])

    if (taskRes.ok && taskRes.data?.name) {
      taskName.value = taskRes.data.name
    }

    if (transformRes.ok && transformRes.data?.length) {
      const t = transformRes.data[0]
      existingTransformationId.value = t.id
      inputDatastreamId.value = (t.inputDatastream as any)?.id ?? null
      outputDatastreamId.value = (t.outputDatastream as any)?.id ?? null
      formula.value = t.formula ?? ''
    }
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load existing expression task.')
  } finally {
    loadingExisting.value = false
  }
}

async function onSubmit() {
  await formRef.value?.validate()
  if (!selectedThingId.value) {
    Snackbar.error('Select a site before creating an expression task.')
    return
  }
  if (!valid.value) return
  if (!inputDatastreamId.value || !outputDatastreamId.value) return

  saving.value = true
  try {
    if (isEditMode.value) await onUpdate()
    else await onCreate()
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to save expression task.')
  } finally {
    saving.value = false
  }
}

async function onCreate() {
  const taskRes = await hs.dataProductTasks.create({
    id: '',
    name: taskName.value.trim(),
    thingId: selectedThingId.value!,
    description: null,
    schedule: null,
  })

  if (!taskRes.ok || !taskRes.data?.id) {
    Snackbar.error(taskRes.message || 'Unable to create expression task.')
    return
  }

  const transformRes = await hs.dataProductTasks.createExpressionTransformation(
    taskRes.data.id,
    {
      inputDatastreamId: inputDatastreamId.value!,
      outputDatastreamId: outputDatastreamId.value!,
      variableName: 'x',
      formula: formula.value.trim(),
    }
  )

  if (!transformRes.ok) {
    Snackbar.error(
      transformRes.message || 'Unable to create expression transformation.'
    )
    return
  }

  emit('created', taskRes.data)
  emit('close')
}

async function onUpdate() {
  const taskId = props.editTaskId!
  const taskRes = await hs.dataProductTasks.update({
    id: taskId,
    name: taskName.value.trim(),
  })

  if (!taskRes.ok) {
    Snackbar.error(taskRes.message || 'Unable to update task name.')
    return
  }

  if (existingTransformationId.value) {
    const transformRes =
      await hs.dataProductTasks.updateExpressionTransformation(
        taskId,
        existingTransformationId.value,
        {
          inputDatastreamId: inputDatastreamId.value!,
          variableName: 'x',
          formula: formula.value.trim(),
        }
      )

    if (!transformRes.ok) {
      Snackbar.error(
        transformRes.message || 'Unable to update expression transformation.'
      )
      return
    }
  }

  Snackbar.success('Expression task updated.')
  emit('updated', taskRes.data!)
  emit('close')
}

async function onDelete() {
  if (!props.editTaskId) return
  deleting.value = true
  try {
    const res = await hs.dataProductTasks.delete(props.editTaskId)
    if (!res.ok) {
      Snackbar.error(res.message || 'Unable to delete expression task.')
      return
    }
    Snackbar.success('Expression task deleted.')
    emit('deleted')
    emit('close')
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to delete expression task.')
  } finally {
    deleting.value = false
  }
}

watch(selectedThingId, () => {
  if (isEditMode.value) return
  inputDatastreamId.value = null
  outputDatastreamId.value = null
})

onMounted(async () => {
  await loadOptions()
  if (isEditMode.value) await loadExistingTask()
})

type Rule = (v: any) => true | string

const formulaContainsVariable: Rule = (v) => {
  return (
    /\bx\b/.test(String(v ?? '')) ||
    "Expression must contain input variable 'x'."
  )
}

const exprAllowedTokens: Rule = (v) => {
  const s = String(v ?? '').trim()
  if (!s) return true

  let i = 0
  while (i < s.length) {
    const ch = s[i]
    if (ch === ' ') {
      i++
      continue
    }
    if (s[i] === 'x') {
      i++
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
    if (ch === '(' || ch === ')') {
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
    return "Only numbers, spaces, 'x', and + - * / ** ( ) are allowed."
  }
  return true
}

const exprBalancedParens: Rule = (v) => {
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
</script>
