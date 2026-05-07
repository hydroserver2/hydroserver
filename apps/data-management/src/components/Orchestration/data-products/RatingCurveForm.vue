<template>
  <v-card>
    <v-toolbar :style="DATA_PRODUCT_TOOLBAR_STYLE" flat>
      <v-card-title>{{
        isEditMode ? 'Edit rating curve task' : 'Create rating curve task'
      }}</v-card-title>
      <v-btn
        :icon="mdiInformationOutline"
        variant="text"
        aria-label="Toggle task info"
        @click="showInfo = !showInfo"
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
          v-if="showInfo"
          :color="DATA_PRODUCT_ACCENT"
          type="info"
          variant="tonal"
          density="compact"
          class="mb-5"
        >
          Select an existing rating curve or create one from a two-column CSV,
          then write transformed values to an output datastream at the selected
          site.
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

        <v-radio-group
          v-model="ratingCurveInputMode"
          inline
          hide-details
          class="mb-3"
        >
          <v-radio label="Select existing rating curve" value="existing" />
          <v-radio label="Create new rating curve" value="create" />
        </v-radio-group>

        <template v-if="ratingCurveInputMode === 'existing'">
          <v-select
            v-model="selectedRatingCurveId"
            :items="ratingCurveOptions"
            item-title="title"
            item-value="value"
            label="Rating curve *"
            clearable
            :disabled="!selectedThingId"
            :loading="ratingCurvesLoading || loadingExisting"
            :rules="rules.required"
            class="mb-2"
          />
          <div
            v-if="
              selectedThingId &&
              !ratingCurvesLoading &&
              !ratingCurveOptions.length
            "
            class="text-caption text-medium-emphasis mb-3"
          >
            No rating curves found for this site. Switch to "Create new rating
            curve" to add one.
          </div>
        </template>

        <template v-else>
          <input
            ref="createFileInput"
            type="file"
            accept=".csv,text/csv"
            class="d-none"
            @change="onCreateFileSelected"
          />
          <v-btn
            variant="outlined"
            :color="DATA_PRODUCT_ACCENT"
            block
            class="mb-2 text-none"
            @click="openCreateFilePicker"
          >
            {{ selectedCreateFile ? 'Change CSV file' : 'Choose CSV file *' }}
          </v-btn>
          <div v-if="selectedCreateFile" class="d-flex align-center mb-3">
            <span class="text-caption text-medium-emphasis">
              Selected:
              <strong>{{ selectedCreateFile.name }}</strong>
              ({{ formatFileSize(selectedCreateFile.size) }})
            </span>
            <v-spacer />
            <v-btn
              variant="text"
              size="small"
              :disabled="saving"
              @click="clearCreateFile"
            >
              Clear
            </v-btn>
          </div>
          <v-alert
            v-if="createFileValidationError"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-3"
          >
            {{ createFileValidationError }}
          </v-alert>
          <div
            v-else-if="createFileValidationPending"
            class="text-caption text-medium-emphasis mb-3"
          >
            Validating rating curve CSV...
          </div>

          <v-text-field
            v-model="createCurveName"
            label="Rating curve name *"
            :rules="rules.requiredAndMaxLength255"
            class="mb-2"
          />
          <v-textarea
            v-model="createCurveDescription"
            label="Description"
            rows="2"
            class="mb-2"
          />
          <v-select
            v-model="createFittingMethod"
            :items="fittingMethodOptions"
            item-title="title"
            item-value="value"
            label="Fitting method *"
            :rules="rules.required"
          />
        </template>
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
          {{ isEditMode ? 'Save changes' : 'Create rating curve task' }}
        </v-btn>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { VForm } from 'vuetify/components'
import { mdiInformationOutline } from '@mdi/js'
import { storeToRefs } from 'pinia'
import hs, {
  type Datastream,
  type RatingCurve,
  type DataProductTask,
} from '@hydroserver/client'
import { rules } from '@/utils/rules'
import { Snackbar } from '@/utils/notifications'
import {
  parseRatingCurveCsvFile,
  toRatingCurveFileValidationMessage,
} from '@/utils/orchestration/ratingCurveFile'
import { datastreamsForThing } from '@/utils/orchestration/datastreams'
import {
  DATA_PRODUCT_ACCENT,
  DATA_PRODUCT_SUBMIT_STYLE,
  DATA_PRODUCT_TOOLBAR_STYLE,
} from '@/utils/orchestration/dataProductTheme'
import DatastreamCardSelector from '../shared/DatastreamCardSelector.vue'
import { useWorkspaceStore } from '@/store/workspaces'

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

const isEditMode = computed(() => !!props.editTaskId)
const { selectedWorkspace } = storeToRefs(useWorkspaceStore())
const selectedWorkspaceId = computed(() => selectedWorkspace.value?.id ?? null)

const formRef = ref<VForm>()
const valid = ref<boolean | null>(null)
const showInfo = ref(false)
const loading = ref(false)
const loadingExisting = ref(false)
const saving = ref(false)
const deleting = ref(false)
const datastreams = ref<Datastream[]>([])
const ratingCurves = ref<RatingCurve[]>([])
const ratingCurvesLoading = ref(false)

const taskName = ref('')
const inputDatastreamId = ref<string | null>(null)
const outputDatastreamId = ref<string | null>(null)
const selectedRatingCurveId = ref<string | null>(null)
const ratingCurveInputMode = ref<'existing' | 'create'>('existing')
const existingTransformationId = ref<string | null>(null)

const createFileInput = ref<HTMLInputElement | null>(null)
const createCurveFile = ref<File | null>(null)
const createCurveName = ref('')
const createCurveDescription = ref('')
const createFittingMethod = ref<'linear' | 'power_law'>('linear')
const createFileValidationError = ref('')
const createFileValidationPending = ref(false)
const createCurvePoints = ref<[number, number][]>([])
let createValidationRunId = 0

const fittingMethodOptions = [
  { title: 'Linear', value: 'linear' },
  { title: 'Power law', value: 'power_law' },
]
const selectedThingId = computed(() => props.initialThingId ?? null)

const siteDatastreams = computed(() => {
  const thingId = selectedThingId.value
  return datastreamsForThing(datastreams.value, thingId)
})

const ratingCurveOptions = computed(() =>
  ratingCurves.value.map((curve) => ({
    title: curve.description
      ? `${curve.name} - ${curve.description}`
      : curve.name,
    value: curve.id,
  }))
)

const selectedCreateFile = computed(() => createCurveFile.value)

async function loadOptions() {
  const workspaceId = selectedWorkspaceId.value
  if (!workspaceId) {
    datastreams.value = []
    return
  }

  loading.value = true
  try {
    const datastreamItems = await hs.datastreams.listAllItems({
      workspace_id: [workspaceId],
      order_by: ['name'],
      expand_related: true,
    } as any)
    datastreams.value = datastreamItems as Datastream[]
    if (selectedThingId.value) await loadRatingCurves(selectedThingId.value)
  } catch (error: any) {
    Snackbar.error(
      error?.message || 'Unable to load rating curve form options.'
    )
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
      hs.dataProductTasks.listRatingCurveTransformations(props.editTaskId),
    ])

    if (taskRes.ok && taskRes.data?.name) {
      taskName.value = taskRes.data.name
    }

    if (transformRes.ok && transformRes.data?.length) {
      const t = transformRes.data[0]
      existingTransformationId.value = t.id
      inputDatastreamId.value = (t.inputDatastream as any)?.id ?? null
      outputDatastreamId.value = (t.outputDatastream as any)?.id ?? null
      selectedRatingCurveId.value = (t.ratingCurve as any)?.id ?? null
      ratingCurveInputMode.value = 'existing'
    }
  } catch (error: any) {
    Snackbar.error(
      error?.message || 'Unable to load existing rating curve task.'
    )
  } finally {
    loadingExisting.value = false
  }
}

async function loadRatingCurves(thingId: string) {
  ratingCurvesLoading.value = true
  try {
    const items = await hs.ratingCurves.listItemsForThing(thingId, {
      order_by: ['name'],
    })
    ratingCurves.value = [...items].sort((a, b) => a.name.localeCompare(b.name))
  } catch (error: any) {
    ratingCurves.value = []
    Snackbar.error(error?.message || 'Unable to load rating curves.')
  } finally {
    ratingCurvesLoading.value = false
  }
}

function openCreateFilePicker() {
  createFileInput.value?.click()
}

function onCreateFileSelected(event: Event) {
  const target = event.target as HTMLInputElement | null
  createCurveFile.value = target?.files?.[0] ?? null
}

function clearCreateFile() {
  createValidationRunId += 1
  createCurveFile.value = null
  createCurvePoints.value = []
  createFileValidationError.value = ''
  createFileValidationPending.value = false
  if (createFileInput.value) createFileInput.value.value = ''
}

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024) return `${sizeBytes} B`
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
}

async function validateCreateFile(file: File | null): Promise<boolean> {
  const runId = ++createValidationRunId
  createFileValidationError.value = ''
  createCurvePoints.value = []

  if (!file) {
    createFileValidationPending.value = false
    return true
  }

  createFileValidationPending.value = true
  try {
    const parsed = await parseRatingCurveCsvFile(file)
    if (runId !== createValidationRunId) return false
    createCurvePoints.value = parsed.rows.map((row) => [
      Number(row.inputValue),
      Number(row.outputValue),
    ])
    return true
  } catch (error: unknown) {
    if (runId !== createValidationRunId) return false
    createFileValidationError.value = toRatingCurveFileValidationMessage(error)
    return false
  } finally {
    if (runId === createValidationRunId) {
      createFileValidationPending.value = false
    }
  }
}

async function resolveRatingCurveId() {
  if (ratingCurveInputMode.value === 'existing')
    return selectedRatingCurveId.value

  const file = selectedCreateFile.value
  if (!selectedThingId.value || !file || !createCurveName.value.trim()) {
    Snackbar.error('Choose a CSV file and rating curve name.')
    return null
  }
  if (createFileValidationPending.value) {
    Snackbar.error('Please wait for rating curve validation to finish.')
    return null
  }

  const validFile = await validateCreateFile(file)
  if (!validFile) {
    Snackbar.error(
      createFileValidationError.value || 'Invalid rating curve CSV format.'
    )
    return null
  }

  const res = await hs.ratingCurves.create({
    id: '',
    name: createCurveName.value.trim(),
    description: createCurveDescription.value.trim() || null,
    fittingMethod: createFittingMethod.value,
    thingId: selectedThingId.value,
    points: createCurvePoints.value,
  })

  if (!res.ok || !res.data?.id) {
    Snackbar.error(res.message || 'Unable to create rating curve.')
    return null
  }

  ratingCurves.value = [...ratingCurves.value, res.data]
  selectedRatingCurveId.value = res.data.id
  return res.data.id
}

async function onSubmit() {
  await formRef.value?.validate()
  if (!selectedThingId.value) {
    Snackbar.error('Select a site before creating a rating curve task.')
    return
  }
  if (!valid.value) return
  if (!inputDatastreamId.value || !outputDatastreamId.value) return

  saving.value = true
  try {
    if (isEditMode.value) await onUpdate()
    else await onCreate()
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to save rating curve task.')
  } finally {
    saving.value = false
  }
}

async function onCreate() {
  const ratingCurveId = await resolveRatingCurveId()
  if (!ratingCurveId) return

  const taskRes = await hs.dataProductTasks.create({
    id: '',
    name: taskName.value.trim(),
    thingId: selectedThingId.value!,
    description: null,
    schedule: null,
  })

  if (!taskRes.ok || !taskRes.data?.id) {
    Snackbar.error(taskRes.message || 'Unable to create rating curve task.')
    return
  }

  const transformRes =
    await hs.dataProductTasks.createRatingCurveTransformation(taskRes.data.id, {
      inputDatastreamId: inputDatastreamId.value!,
      outputDatastreamId: outputDatastreamId.value!,
      ratingCurveId,
    })

  if (!transformRes.ok) {
    Snackbar.error(
      transformRes.message || 'Unable to create rating curve transformation.'
    )
    return
  }

  emit('created', taskRes.data)
  emit('close')
}

async function onUpdate() {
  const taskId = props.editTaskId!
  const ratingCurveId = await resolveRatingCurveId()
  if (!ratingCurveId) return

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
      await hs.dataProductTasks.updateRatingCurveTransformation(
        taskId,
        existingTransformationId.value,
        {
          inputDatastreamId: inputDatastreamId.value!,
          ratingCurveId,
        }
      )

    if (!transformRes.ok) {
      Snackbar.error(
        transformRes.message || 'Unable to update rating curve transformation.'
      )
      return
    }
  }

  Snackbar.success('Rating curve task updated.')
  emit('updated', taskRes.data!)
  emit('close')
}

async function onDelete() {
  if (!props.editTaskId) return
  deleting.value = true
  try {
    const res = await hs.dataProductTasks.delete(props.editTaskId)
    if (!res.ok) {
      Snackbar.error(res.message || 'Unable to delete rating curve task.')
      return
    }
    Snackbar.success('Rating curve task deleted.')
    emit('deleted')
    emit('close')
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to delete rating curve task.')
  } finally {
    deleting.value = false
  }
}

watch(selectedThingId, (thingId) => {
  if (isEditMode.value) return
  inputDatastreamId.value = null
  outputDatastreamId.value = null
  selectedRatingCurveId.value = null
  ratingCurves.value = []
  if (thingId) void loadRatingCurves(thingId)
})

watch(selectedCreateFile, (file) => {
  if (!file) return
  if (!createCurveName.value.trim()) createCurveName.value = file.name
  void validateCreateFile(file)
})

watch(ratingCurveInputMode, () => {
  selectedRatingCurveId.value = null
})

onMounted(async () => {
  await loadOptions()
  if (isEditMode.value) await loadExistingTask()
})
</script>
