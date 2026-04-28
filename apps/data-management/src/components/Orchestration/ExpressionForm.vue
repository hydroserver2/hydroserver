<template>
  <v-card>
    <v-toolbar color="deep-purple" flat>
      <v-card-title>Create expression task</v-card-title>
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
          color="deep-purple"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-5"
        >
          Apply an expression to each incoming data point independently. Enter
          a single-line Python expression using
          <code>x</code> for the incoming value.
          <div class="mt-4">
            For example, if you wanted a unit conversion from degrees
            Fahrenheit (deg F) to Celsius (deg C), you'd type in '(x - 32) *
            5/9'.
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
          class="mb-2"
        />

        <v-autocomplete
          v-model="inputDatastreamId"
          :items="datastreamOptions"
          item-title="title"
          item-value="value"
          label="Input datastream *"
          clearable
          :loading="loading"
          :rules="rules.required"
          class="mb-2"
        />

        <v-autocomplete
          v-model="outputDatastreamId"
          :items="outputDatastreamOptions"
          item-title="title"
          item-value="value"
          label="Output datastream *"
          clearable
          :disabled="!selectedThingId"
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
        />
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
        <v-btn-primary type="submit" :loading="saving">
          Create expression task
        </v-btn-primary>
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

const props = defineProps<{
  workspaceId: string
  initialThingId?: string | null
}>()

const emit = defineEmits<{
  (e: 'created', task: DataProductTask): void
  (e: 'close'): void
}>()

const formRef = ref<VForm>()
const valid = ref<boolean | null>(null)
const loading = ref(false)
const saving = ref(false)
const showHelp = ref(false)
const datastreams = ref<Datastream[]>([])

const taskName = ref('')
const inputDatastreamId = ref<string | null>(null)
const outputDatastreamId = ref<string | null>(null)
const formula = ref('')
const selectedThingId = computed(() => props.initialThingId ?? null)
const ALLOWED_OPS = ['+', '-', '*', '/', '**', '(', ')']

const datastreamOptions = computed(() =>
  datastreams.value.map((datastream) => ({
    title: datastream.name,
    value: datastream.id,
  }))
)

const outputDatastreamOptions = computed(() =>
  datastreams.value
    .filter((datastream) => datastream.thingId === selectedThingId.value)
    .map((datastream) => ({
      title: datastream.name,
      value: datastream.id,
    }))
)

async function loadOptions() {
  loading.value = true
  try {
    const datastreamItems = await hs.datastreams.listAllItems({
      workspace_id: [props.workspaceId],
      order_by: ['name'],
    } as any)
    datastreams.value = datastreamItems as Datastream[]
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load expression form options.')
  } finally {
    loading.value = false
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
    const taskRes = await hs.dataProductTasks.create({
      id: '',
      name: taskName.value.trim(),
      thingId: selectedThingId.value,
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
        inputDatastreamId: inputDatastreamId.value,
        outputDatastreamId: outputDatastreamId.value,
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
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to create expression task.')
  } finally {
    saving.value = false
  }
}

watch(selectedThingId, () => {
  outputDatastreamId.value = null
})

onMounted(loadOptions)

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

