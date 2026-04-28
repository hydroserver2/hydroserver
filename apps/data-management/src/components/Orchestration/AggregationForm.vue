<template>
  <v-card>
    <v-toolbar :style="DATA_PRODUCT_TOOLBAR_STYLE" flat>
      <v-card-title>{{ isEditMode ? 'Edit aggregation task' : 'Create aggregation task' }}</v-card-title>
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

    <v-form
      ref="formRef"
      v-model="valid"
      validate-on="input"
      @submit.prevent="onSubmit"
    >
      <v-card-text>
        <v-alert
          v-if="showInfo"
          :color="DATA_PRODUCT_ACCENT"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-5"
        >
          Aggregate observations from an input datastream into fixed-length
          time buckets and write the results to an output datastream.
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
          :loading="loadingDatastreams"
          :disabled="!selectedThingId || loadingExisting"
          :rules="rules.required"
          class="mb-2"
        />

        <DatastreamCardSelector
          v-model="outputDatastreamId"
          :datastreams="siteDatastreams"
          label="Output datastream *"
          :disabled="!selectedThingId || loadingExisting"
          :loading="loadingDatastreams"
          :rules="rules.required"
          class="mb-2"
        />

        <v-divider class="mb-4" />

        <div class="text-caption text-medium-emphasis mb-3 font-weight-bold text-uppercase">
          Aggregation settings
        </div>

        <v-select
          v-model="aggregationMethod"
          :items="aggregationMethodOptions"
          item-title="title"
          item-value="value"
          label="Aggregation method *"
          :rules="rules.required"
          :disabled="loadingExisting"
          class="mb-2"
        />

        <div class="d-flex gap-3 mb-2">
          <v-text-field
            v-model.number="outputInterval"
            label="Output interval *"
            type="number"
            min="1"
            :rules="[...rules.required, positiveInteger]"
            :disabled="loadingExisting"
            class="shrink"
            style="max-width: 160px"
          />
          <v-select
            v-model="outputIntervalUnits"
            :items="intervalUnitOptions"
            item-title="title"
            item-value="value"
            label="Unit *"
            :rules="rules.required"
            :disabled="loadingExisting"
            class="grow"
          />
        </div>

        <v-text-field
          v-model.number="minValues"
          label="Minimum values per bucket"
          type="number"
          min="1"
          hint="Buckets with fewer than this many values will be skipped."
          persistent-hint
          :rules="minValues !== null && minValues !== undefined ? [positiveInteger] : []"
          :disabled="loadingExisting"
          clearable
          class="mb-2"
          @click:clear="minValues = null"
        />

      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel :disabled="saving" @click="$emit('close')">Cancel</v-btn-cancel>
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
          {{ isEditMode ? 'Save changes' : 'Create aggregation task' }}
        </v-btn>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { VForm } from 'vuetify/components'
import { mdiInformationOutline } from '@mdi/js'
import hs, {
  type Datastream,
  type DataProductTask,
  type AggregationMethod,
  type IntervalUnit,
} from '@hydroserver/client'
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
const showInfo = ref(false)
const loadingDatastreams = ref(false)
const loadingExisting = ref(false)
const saving = ref(false)
const deleting = ref(false)
const datastreams = ref<Datastream[]>([])

const existingTransformationId = ref<string | null>(null)

const taskName = ref('')
const inputDatastreamId = ref<string | null>(null)
const outputDatastreamId = ref<string | null>(null)
const aggregationMethod = ref<AggregationMethod>('mean')
const outputInterval = ref<number | null>(1)
const outputIntervalUnits = ref<IntervalUnit>('hours')
const minValues = ref<number | null>(null)

const selectedThingId = computed(() => props.initialThingId ?? null)

const aggregationMethodOptions = [
  { title: 'Mean', value: 'mean' },
  { title: 'Sum', value: 'sum' },
  { title: 'Min', value: 'min' },
  { title: 'Max', value: 'max' },
  { title: 'First', value: 'first' },
  { title: 'Last', value: 'last' },
]

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

type Rule = (v: any) => true | string

const positiveInteger: Rule = (v) => {
  const n = Number(v)
  return (Number.isInteger(n) && n >= 1) || 'Must be a positive whole number.'
}


async function loadDatastreams() {
  loadingDatastreams.value = true
  try {
    const items = await hs.datastreams.listAllItems({
      workspace_id: [props.workspaceId],
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
      hs.dataProductTasks.listAggregationTransformations(props.editTaskId),
    ])

    if (taskRes.ok && taskRes.data?.name) {
      taskName.value = taskRes.data.name
    }

    if (transformRes.ok && transformRes.data?.length) {
      const t = transformRes.data[0]
      existingTransformationId.value = t.id
      inputDatastreamId.value = (t.inputDatastream as any)?.id ?? null
      outputDatastreamId.value = (t.outputDatastream as any)?.id ?? null
      aggregationMethod.value = t.aggregationMethod
      outputInterval.value = t.outputInterval
      outputIntervalUnits.value = t.outputIntervalUnits
      minValues.value = t.minValues ?? null
    }
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load existing task.')
  } finally {
    loadingExisting.value = false
  }
}

async function onSubmit() {
  await formRef.value?.validate()
  if (!valid.value) return
  if (!inputDatastreamId.value || !outputDatastreamId.value) return
  if (!outputInterval.value) return

  saving.value = true
  try {
    if (isEditMode.value) {
      await onUpdate()
    } else {
      await onCreate()
    }
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to save aggregation task.')
  } finally {
    saving.value = false
  }
}

async function onCreate() {
  const thingId = selectedThingId.value
  if (!thingId) {
    Snackbar.error('Select a site before creating an aggregation task.')
    return
  }

  const taskRes = await hs.dataProductTasks.create({
    id: '',
    name: taskName.value.trim(),
    thingId,
    description: null,
    schedule: null,
  })

  if (!taskRes.ok || !taskRes.data?.id) {
    Snackbar.error(taskRes.message || 'Unable to create aggregation task.')
    return
  }

  const transformRes = await hs.dataProductTasks.createAggregationTransformation(
    taskRes.data.id,
    {
      inputDatastreamId: inputDatastreamId.value!,
      outputDatastreamId: outputDatastreamId.value!,
      aggregationMethod: aggregationMethod.value,
      outputInterval: outputInterval.value!,
      outputIntervalUnits: outputIntervalUnits.value,
      minValues: minValues.value ?? null,
    }
  )

  if (!transformRes.ok) {
    Snackbar.error(transformRes.message || 'Unable to create aggregation transformation.')
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
    const transformRes = await hs.dataProductTasks.updateAggregationTransformation(
      taskId,
      existingTransformationId.value,
      {
        inputDatastreamId: inputDatastreamId.value!,
        outputDatastreamId: outputDatastreamId.value!,
        aggregationMethod: aggregationMethod.value,
        outputInterval: outputInterval.value!,
        outputIntervalUnits: outputIntervalUnits.value,
        minValues: minValues.value ?? null,
      }
    )

    if (!transformRes.ok) {
      Snackbar.error(transformRes.message || 'Unable to update aggregation transformation.')
      return
    }
  }

  Snackbar.success('Aggregation task updated.')
  emit('updated', taskRes.data!)
  emit('close')
}

async function onDelete() {
  if (!props.editTaskId) return
  deleting.value = true
  try {
    const res = await hs.dataProductTasks.delete(props.editTaskId)
    if (!res.ok) {
      Snackbar.error(res.message || 'Unable to delete aggregation task.')
      return
    }
    Snackbar.success('Aggregation task deleted.')
    emit('deleted')
    emit('close')
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to delete aggregation task.')
  } finally {
    deleting.value = false
  }
}

watch(
  () => props.initialThingId,
  () => {
    if (!isEditMode.value) {
      inputDatastreamId.value = null
      outputDatastreamId.value = null
    }
  }
)


onMounted(async () => {
  await loadDatastreams()
  if (isEditMode.value) await loadExistingTask()
})
</script>
