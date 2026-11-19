<template>
  <div class="rating-curves">
    <!-- The tab already shows the count, so the toolbar only holds the action. -->
    <div
      v-if="canEditMonitoringSite && !openCreate"
      class="rating-curves__toolbar"
    >
      <div class="hs-table-actions">
        <v-btn-page-action
          data-testid="add-rating-curve-button"
          @click="openCreateDialog"
        >
          Add rating curve
        </v-btn-page-action>
      </div>
    </div>

    <!-- Outside the list: a ref inside v-for would become an array. -->
    <input
      ref="editFileInput"
      type="file"
      accept=".csv,text/csv"
      class="d-none"
      data-testid="rating-curve-edit-file"
      @change="onEditFileSelected"
    />

    <v-expand-transition>
      <section
        v-if="openCreate"
        class="rating-curve-form"
        aria-labelledby="rating-curve-create-title"
        data-testid="rating-curve-create-form"
      >
        <h3 id="rating-curve-create-title" class="hs-text-md mb-3">
          Add rating curve
        </h3>
        <input
          ref="createFileInput"
          type="file"
          accept=".csv,text/csv"
          class="d-none"
          data-testid="rating-curve-create-file"
          @change="onCreateFileSelected"
        />
        <div class="rating-curve-form__file">
          <v-btn variant="outlined" color="primary" @click="openCreateFilePicker">
            {{ selectedFile ? 'Change CSV file' : 'Choose CSV file *' }}
          </v-btn>
          <span v-if="selectedFile" class="hs-text-2xs text-medium-emphasis">
            <strong>{{ selectedFile.name }}</strong>
            ({{ formatFileSize(selectedFile.size) }})
          </span>
          <v-btn
            v-if="selectedFile"
            variant="text"
            size="small"
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
          class="hs-text-2xs text-medium-emphasis mb-3"
        >
          Validating rating curve CSV...
        </div>

        <div class="rating-curve-form__fields">
          <v-text-field v-model="attachmentName" label="Rating curve name *" />
          <v-select
            v-model="attachmentFittingMethod"
            :items="fittingMethodOptions"
            item-title="title"
            item-value="value"
            label="Fitting method *"
          />
          <v-textarea
            v-model="attachmentDescription"
            label="Description"
            rows="2"
            class="rating-curve-form__wide"
          />
        </div>

        <div class="rating-curve-form__actions">
          <v-btn-cancel @click="openCreate = false">Cancel</v-btn-cancel>
          <v-btn-dialog-action
            :loading="saving"
            :disabled="!canCreateAttachment"
            data-testid="rating-curve-create-save"
            @click="createAttachment"
          >
            Save
          </v-btn-dialog-action>
        </div>
      </section>
    </v-expand-transition>

    <v-progress-linear v-if="loading" indeterminate color="primary" />

    <p
      v-if="!loading && displayAttachments.length === 0"
      class="rating-curves__empty hs-text-sm text-medium-emphasis"
    >
      No rating curves have been added to this site yet.
    </p>

    <ul v-else class="rating-curve-list">
      <li
        v-for="attachment in displayAttachments"
        :key="attachment.id"
        class="rating-curve-entry"
        :data-testid="`rating-curve-${attachment.id}`"
      >
        <!-- Editing swaps the row for its form, in place. -->
        <section
          v-if="openEdit && editAttachment?.id === attachment.id"
          class="rating-curve-form rating-curve-form--edit"
          :aria-label="`Edit ${attachment.name}`"
        >
          <div class="rating-curve-form__fields">
            <v-text-field
              v-model="editAttachmentName"
              label="Rating curve name *"
            />
            <v-select
              v-model="editAttachmentFittingMethod"
              :items="fittingMethodOptions"
              item-title="title"
              item-value="value"
              label="Fitting method *"
            />
            <v-textarea
              v-model="editAttachmentDescription"
              label="Description"
              rows="2"
              class="rating-curve-form__wide"
            />
          </div>

          <div class="rating-curve-form__file">
            <v-btn variant="outlined" color="primary" @click="openEditFilePicker">
              {{
                selectedEditFile ? 'Change CSV file' : 'Replace points from a CSV file'
              }}
            </v-btn>
            <span
              v-if="selectedEditFile"
              class="hs-text-2xs text-medium-emphasis"
            >
              <strong>{{ selectedEditFile.name }}</strong>
              ({{ formatFileSize(selectedEditFile.size) }})
            </span>
            <v-btn
              v-if="selectedEditFile"
              variant="text"
              size="small"
              @click="clearEditFile"
            >
              Clear
            </v-btn>
          </div>

          <v-alert
            v-if="editFileValidationError"
            type="error"
            variant="tonal"
            density="compact"
            class="mb-3"
          >
            {{ editFileValidationError }}
          </v-alert>
          <div
            v-else-if="editFileValidationPending"
            class="hs-text-2xs text-medium-emphasis mb-3"
          >
            Validating rating curve CSV...
          </div>
          <div
            v-else-if="editPreviewLoading"
            class="hs-text-2xs text-medium-emphasis mb-3"
          >
            Loading current preview...
          </div>
          <v-alert
            v-else-if="editPreviewError"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-3"
          >
            {{ editPreviewError }}
          </v-alert>

          <div v-if="editPreviewPath" class="mb-3">
            <div class="hs-text-2xs text-medium-emphasis mb-1">Preview</div>
            <div class="rating-curve-preview-box">
              <svg
                class="rating-curve-preview-svg"
                :viewBox="`0 0 ${PREVIEW_SVG_WIDTH} ${PREVIEW_SVG_HEIGHT}`"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                <path
                  class="rating-curve-line"
                  :d="editPreviewPath"
                  fill="none"
                  vector-effect="non-scaling-stroke"
                  stroke-linejoin="round"
                  stroke-linecap="round"
                />
              </svg>
            </div>
          </div>

          <div class="rating-curve-form__actions">
            <v-btn-cancel @click="openEdit = false">Cancel</v-btn-cancel>
            <v-btn-dialog-action
              :loading="saving"
              :disabled="!canSaveEditAttachment"
              @click="saveEditAttachment"
            >
              Save
            </v-btn-dialog-action>
          </div>
        </section>

        <template v-else>
          <div class="rating-curve-item">
            <div class="rating-curve-item-preview">
              <div
                v-if="isPreviewLoading(attachment.id)"
                class="hs-text-2xs text-medium-emphasis"
              >
                Loading...
              </div>
              <div
                v-else-if="getPreviewPath(attachment.id)"
                class="rating-curve-preview-box"
              >
                <svg
                  class="rating-curve-preview-svg"
                  :viewBox="`0 0 ${PREVIEW_SVG_WIDTH} ${PREVIEW_SVG_HEIGHT}`"
                  preserveAspectRatio="none"
                  aria-hidden="true"
                >
                  <path
                    class="rating-curve-line"
                    :d="getPreviewPath(attachment.id)"
                    fill="none"
                    vector-effect="non-scaling-stroke"
                    stroke-linejoin="round"
                    stroke-linecap="round"
                  />
                </svg>
              </div>
              <div
                v-else-if="getPreviewError(attachment.id)"
                class="hs-text-2xs text-error"
              >
                Preview unavailable
              </div>
              <div v-else class="hs-text-2xs text-medium-emphasis">
                No points
              </div>
            </div>

            <div class="rating-curve-item-main">
              <div class="hs-text-sm font-weight-medium">
                {{ attachment.name }}
              </div>
              <div
                v-if="attachment.description"
                class="hs-text-2xs text-medium-emphasis"
              >
                {{ attachment.description }}
              </div>
            </div>

            <div class="rating-curve-item-actions">
              <v-btn-icon
                :icon="mdiDownload"
                :aria-label="`Download ${attachment.name}`"
                :loading="isDownloading(attachment.id)"
                :disabled="isDownloading(attachment.id)"
                @click="downloadAttachment(attachment)"
              />
              <template v-if="canEditMonitoringSite">
                <v-btn-icon
                  :icon="mdiPencil"
                  :aria-label="`Edit ${attachment.name}`"
                  :data-testid="`edit-rating-curve-${attachment.id}`"
                  @click="openEditDialog(attachment)"
                />
                <v-btn-icon
                  :icon="mdiTrashCanOutline"
                  color="delete"
                  :aria-label="`Delete ${attachment.name}`"
                  :data-testid="`delete-rating-curve-${attachment.id}`"
                  :loading="isValidatingDelete(attachment.id)"
                  :disabled="isValidatingDelete(attachment.id)"
                  @click="handleDeleteClick(attachment)"
                />
              </template>
            </div>
          </div>

          <div
            v-if="openDelete && activeAttachment?.id === attachment.id"
            class="rating-curve-confirm"
            role="alert"
          >
            <span class="hs-text-sm">
              Delete <strong>{{ attachment.name }}</strong> from this site?
            </span>
            <div class="rating-curve-form__actions mt-0">
              <v-btn-cancel @click="openDelete = false">Cancel</v-btn-cancel>
              <v-btn-destructive
                :loading="saving"
                data-testid="confirm-delete-rating-curve"
                @click="deleteAttachment"
              >
                Delete
              </v-btn-destructive>
            </div>
          </div>

          <v-alert
            v-if="openLinkedTasks && blockedAttachment?.id === attachment.id"
            type="error"
            variant="tonal"
            density="compact"
            closable
            class="mt-2"
            @click:close="openLinkedTasks = false"
          >
            <strong>{{ attachment.name }}</strong> is used by these tasks.
            Remove it from them before deleting it.
            <ul class="rating-curve-linked-tasks">
              <li v-for="task in blockedTasks" :key="task.id">
                <router-link :to="taskDetailsRoute(task)">
                  {{ task.name || task.id }}
                </router-link>
              </li>
            </ul>
          </v-alert>
        </template>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { mdiTrashCanOutline, mdiDownload, mdiPencil } from '@mdi/js'
import hs, {
  type RatingCurve,
  type RatingCurveFittingMethod,
  type RatingCurvePoint as RatingCurveTuple,
  type RatingCurvePreviewRow,
} from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import {
  parseRatingCurveCsvFile,
  toRatingCurveFileValidationMessage,
} from '@/utils/orchestration/ratingCurveFile'
import { useRatingCurveStore } from '@/store/ratingCurves'

const props = withDefaults(
  defineProps<{
    monitoringSiteId?: string
    canEdit?: boolean
    deferPersist?: boolean
    workspaceId?: string
    refreshToken?: number
  }>(),
  {
    canEdit: false,
    deferPersist: false,
    workspaceId: '',
    refreshToken: 0,
  }
)

const emit = defineEmits<{
  (e: 'rating-curves-changed', ratingCurves: RatingCurve[]): void
}>()

type DisplayRatingCurve = {
  id: string
  name: string
  description: string
  fittingMethod: RatingCurveFittingMethod
  points: RatingCurveTuple[]
  pending: boolean
}

const ratingCurveStore = useRatingCurveStore()

const backendRatingCurves = ref<RatingCurve[]>([])
const backendLoading = ref(false)
const saving = ref(false)

// These flags show each step inline on the page: the create form above the
// list, the edit form in place of its row, and delete confirmation or the
// "used by tasks" notice under its row.
const openCreate = ref(false)
const openEdit = ref(false)
const openDelete = ref(false)
const openLinkedTasks = ref(false)

const attachmentFile = ref<File | File[] | null>(null)
const createFileInput = ref<HTMLInputElement | null>(null)
const attachmentName = ref('')
const attachmentDescription = ref('')
const attachmentFittingMethod = ref<RatingCurveFittingMethod>('linear')
const editAttachment = ref<DisplayRatingCurve | null>(null)
const editAttachmentFile = ref<File | File[] | null>(null)
const editFileInput = ref<HTMLInputElement | null>(null)
const editAttachmentName = ref('')
const editAttachmentDescription = ref('')
const editAttachmentFittingMethod = ref<RatingCurveFittingMethod>('linear')
const activeAttachment = ref<DisplayRatingCurve | null>(null)
const blockedAttachment = ref<DisplayRatingCurve | null>(null)
const blockedTasks = ref<
  Array<{ id: string; name: string; workspaceId: string }>
>([])

const createFileValidationError = ref('')
const createFileValidationPending = ref(false)
let createValidationRunId = 0
const editFileValidationError = ref('')
const editFileValidationPending = ref(false)
let editValidationRunId = 0
let editPreviewRunId = 0
const editPreviewRows = ref<RatingCurvePreviewRow[]>([])
const editPreviewLoading = ref(false)
const editPreviewError = ref('')

const PREVIEW_SVG_WIDTH = 132
const PREVIEW_SVG_HEIGHT = 38
const previewRowsByAttachmentId = ref<Record<string, RatingCurvePreviewRow[]>>(
  {}
)
const previewLoadingByAttachmentId = ref<Record<string, boolean>>({})
const previewErrorByAttachmentId = ref<Record<string, string>>({})
const downloadingByAttachmentId = ref<Record<string, boolean>>({})
const deleteValidationByAttachmentId = ref<Record<string, boolean>>({})

const fittingMethodOptions = [
  { title: 'Linear', value: 'linear' },
  { title: 'Power law', value: 'power_law' },
]

const canEditMonitoringSite = computed(() => props.canEdit)

const loading = computed(() =>
  props.deferPersist ? ratingCurveStore.loading : backendLoading.value
)

const displayAttachments = computed<DisplayRatingCurve[]>(() => {
  if (!props.deferPersist) {
    return backendRatingCurves.value.map((curve) => ({
      id: curve.id,
      name: curve.name,
      description: curve.description || '',
      fittingMethod: curve.fittingMethod,
      points: curve.points ?? [],
      pending: false,
    }))
  }

  const deletedIds = new Set(
    ratingCurveStore.pendingDeleteIds.map((item) => String(item))
  )
  const metadataUpdatesById = new Map(
    ratingCurveStore.pendingMetadataUpdates.map((item) => [
      String(item.ratingCurveId),
      item,
    ])
  )

  const existing = ratingCurveStore.existingRatingCurves
    .filter((attachment) => !deletedIds.has(String(attachment.id)))
    .map((attachment) => {
      const pendingMetadata = metadataUpdatesById.get(String(attachment.id))
      const pendingReplace = ratingCurveStore.pendingReplaces.find(
        (replace) => String(replace.ratingCurveId) === String(attachment.id)
      )
      return {
        id: attachment.id,
        name: pendingMetadata?.name ?? attachment.name,
        description:
          pendingMetadata?.description ?? (attachment.description || ''),
        fittingMethod:
          pendingMetadata?.fittingMethod ?? attachment.fittingMethod,
        points: pendingReplace?.points ?? attachment.points ?? [],
        pending: false,
      }
    })

  const queued = ratingCurveStore.pendingCreates.map((item) => ({
    id: item.tempId,
    name: item.name,
    description: item.description,
    fittingMethod: item.fittingMethod,
    points: item.points,
    pending: true,
  }))

  return [...existing, ...queued].sort((a, b) => a.name.localeCompare(b.name))
})

const selectedFile = computed(() => {
  const value = attachmentFile.value
  if (!value) return null
  return Array.isArray(value) ? (value[0] ?? null) : value
})

const canCreateAttachment = computed(
  () =>
    !!selectedFile.value &&
    !!attachmentName.value.trim() &&
    !createFileValidationPending.value &&
    !createFileValidationError.value
)
const selectedEditFile = computed(() => {
  const value = editAttachmentFile.value
  if (!value) return null
  return Array.isArray(value) ? (value[0] ?? null) : value
})
const canSaveEditAttachment = computed(
  () =>
    !!editAttachment.value &&
    !!editAttachmentName.value.trim() &&
    !editFileValidationPending.value &&
    !editFileValidationError.value &&
    hasEditChanges.value
)
const hasEditMetadataChanges = computed(() => {
  const item = editAttachment.value
  if (!item) return false
  return (
    editAttachmentName.value.trim() !== item.name ||
    editAttachmentDescription.value.trim() !== (item.description || '')
  )
})
const hasEditFileChange = computed(() => !!selectedEditFile.value)
const hasEditChanges = computed(
  () => hasEditMetadataChanges.value || hasEditFileChange.value
)
const editPreviewPath = computed(() => {
  const points = toCurvePoints(editPreviewRows.value)
  const ranges = computeCurveRange(points)
  return buildSparklinePath(
    points,
    ranges,
    PREVIEW_SVG_WIDTH,
    PREVIEW_SVG_HEIGHT
  )
})

type RatingCurvePoint = { x: number; y: number }
type RatingCurveRange = {
  xMin: number
  xMax: number
  yMin: number
  yMax: number
}

function resetCreateState() {
  createValidationRunId += 1
  createFileValidationError.value = ''
  createFileValidationPending.value = false
  attachmentFile.value = null
  if (createFileInput.value) {
    createFileInput.value.value = ''
  }
  attachmentName.value = ''
  attachmentDescription.value = ''
  attachmentFittingMethod.value = 'linear'
}

function resetEditState() {
  editValidationRunId += 1
  editPreviewRunId += 1
  editFileValidationError.value = ''
  editFileValidationPending.value = false
  editAttachmentFile.value = null
  editAttachmentName.value = ''
  editAttachmentDescription.value = ''
  editAttachmentFittingMethod.value = 'linear'
  editPreviewRows.value = []
  editPreviewLoading.value = false
  editPreviewError.value = ''
  if (editFileInput.value) {
    editFileInput.value.value = ''
  }
  editAttachment.value = null
}

function openCreateFilePicker() {
  createFileInput.value?.click()
}

function openEditFilePicker() {
  editFileInput.value?.click()
}

function onCreateFileSelected(event: Event) {
  const target = event.target as HTMLInputElement | null
  const file = target?.files?.[0] ?? null
  attachmentFile.value = file
}

function onEditFileSelected(event: Event) {
  const target = event.target as HTMLInputElement | null
  const file = target?.files?.[0] ?? null
  editAttachmentFile.value = file
}

function clearCreateFile() {
  attachmentFile.value = null
  if (createFileInput.value) {
    createFileInput.value.value = ''
  }
}

function clearEditFile() {
  editAttachmentFile.value = null
  if (editFileInput.value) {
    editFileInput.value.value = ''
  }
}

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024) return `${sizeBytes} B`
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
}

function emitRatingCurvesChanged() {
  emit('rating-curves-changed', [...backendRatingCurves.value])
}

async function refreshRatingCurves() {
  if (props.deferPersist) {
    try {
      await ratingCurveStore.loadExistingRatingCurves(props.monitoringSiteId)

      const deletedIds = new Set(
        ratingCurveStore.pendingDeleteIds.map((item) => String(item))
      )
      for (const curve of ratingCurveStore.existingRatingCurves) {
        if (!deletedIds.has(String(curve.id))) {
          previewRowsByAttachmentId.value[String(curve.id)] =
            pointsToPreviewRows(curve.points ?? [])
        }
      }

      for (const pending of ratingCurveStore.pendingCreates) {
        previewRowsByAttachmentId.value[pending.tempId] = pending.previewRows
      }

      for (const pending of ratingCurveStore.pendingReplaces) {
        previewRowsByAttachmentId.value[String(pending.ratingCurveId)] =
          pending.previewRows
      }
    } catch (error: any) {
      Snackbar.error(error?.message || 'Unable to load rating curves.')
    }

    return
  }

  if (!props.monitoringSiteId) {
    backendRatingCurves.value = []
    emitRatingCurvesChanged()
    return
  }

  backendLoading.value = true
  try {
    const items = await hs.ratingCurves.listItemsForMonitoringSite(props.monitoringSiteId, {
      sortby: ['name'],
    })
    backendRatingCurves.value = items.sort((a, b) =>
      a.name.localeCompare(b.name)
    )
    emitRatingCurvesChanged()
    for (const curve of backendRatingCurves.value) {
      previewRowsByAttachmentId.value[String(curve.id)] = pointsToPreviewRows(
        curve.points ?? []
      )
    }
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load rating curves.')
  } finally {
    backendLoading.value = false
  }
}

function openCreateDialog() {
  if (!canEditMonitoringSite.value) return
  resetCreateState()
  openCreate.value = true
}

function openEditDialog(item: DisplayRatingCurve) {
  if (!canEditMonitoringSite.value) return
  resetEditState()
  editAttachment.value = item
  editAttachmentName.value = item.name
  editAttachmentDescription.value = item.description || ''
  editAttachmentFittingMethod.value = item.fittingMethod
  openEdit.value = true
  void hydrateEditPreview(item)
}

function openDeleteDialog(item: DisplayRatingCurve) {
  if (!canEditMonitoringSite.value) return
  activeAttachment.value = item
  openDelete.value = true
}

async function handleDeleteClick(item: DisplayRatingCurve) {
  if (!canEditMonitoringSite.value) return
  if (!props.deferPersist) {
    if (await blockDeletionIfLinkedWithSpinner(item)) return
    openDeleteDialog(item)
    return
  }

  if (item.pending) {
    ratingCurveStore.removeQueuedRatingCurveCreate(String(item.id))
    delete previewRowsByAttachmentId.value[String(item.id)]
  } else {
    if (await blockDeletionIfLinkedWithSpinner(item)) return
    ratingCurveStore.queueExistingRatingCurveDelete(item.id)
    delete previewRowsByAttachmentId.value[String(item.id)]
    delete previewErrorByAttachmentId.value[String(item.id)]
    delete previewLoadingByAttachmentId.value[String(item.id)]
  }
}

async function createAttachment() {
  const file = selectedFile.value
  const trimmedName = attachmentName.value.trim()
  if (!file || !trimmedName) return

  if (createFileValidationPending.value) {
    Snackbar.error('Please wait for rating curve validation to finish.')
    return
  }

  const isValidFile = await validateCreateFile(file)
  if (!isValidFile) {
    Snackbar.error(
      createFileValidationError.value || 'Invalid rating curve CSV format.'
    )
    return
  }

  const parsed = await parseRatingCurveCsvFile(file)
  const points = parsed.rows.map(
    (row) =>
      [Number(row.inputValue), Number(row.outputValue)] as RatingCurveTuple
  )
  const previewRows = pointsToPreviewRows(points)

  if (props.deferPersist) {
    const tempId = ratingCurveStore.queueRatingCurveCreate(
      trimmedName,
      attachmentDescription.value.trim(),
      attachmentFittingMethod.value,
      points,
      previewRows
    )
    previewRowsByAttachmentId.value[tempId] = previewRows
    openCreate.value = false
    resetCreateState()
    return
  }

  if (!props.monitoringSiteId) {
    Snackbar.error('Save the site first before adding rating curves.')
    return
  }

  saving.value = true
  try {
    const res = await hs.ratingCurves.create({
      id: '',
      name: trimmedName,
      description: attachmentDescription.value.trim() || null,
      fittingMethod: attachmentFittingMethod.value,
      monitoringSiteId: props.monitoringSiteId,
      points,
    })

    if (!res.ok || !res.data) {
      Snackbar.error(res.message || 'Unable to create rating curve.')
      return
    }

    const created = res.data
    backendRatingCurves.value = [...backendRatingCurves.value, created].sort(
      (a, b) => a.name.localeCompare(b.name)
    )
    emitRatingCurvesChanged()
    previewRowsByAttachmentId.value[String(created.id)] = previewRows

    openCreate.value = false
    resetCreateState()
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to create rating curve.')
  } finally {
    saving.value = false
  }
}

async function deleteAttachment() {
  if (!activeAttachment.value) return

  if (props.deferPersist) {
    if (activeAttachment.value.pending) {
      ratingCurveStore.removeQueuedRatingCurveCreate(
        String(activeAttachment.value.id)
      )
      delete previewRowsByAttachmentId.value[String(activeAttachment.value.id)]
    } else {
      ratingCurveStore.queueExistingRatingCurveDelete(activeAttachment.value.id)
      delete previewRowsByAttachmentId.value[String(activeAttachment.value.id)]
      delete previewErrorByAttachmentId.value[String(activeAttachment.value.id)]
      delete previewLoadingByAttachmentId.value[
        String(activeAttachment.value.id)
      ]
    }

    openDelete.value = false
    return
  }

  if (!props.monitoringSiteId) {
    Snackbar.error('Save the site first before deleting rating curves.')
    return
  }

  if (await blockDeletionIfLinked(activeAttachment.value)) {
    openDelete.value = false
    return
  }

  saving.value = true
  try {
    const res = await hs.ratingCurves.delete(activeAttachment.value.id)

    if (!res.ok) {
      Snackbar.error(res.message || 'Unable to delete rating curve.')
      return
    }

    backendRatingCurves.value = backendRatingCurves.value.filter(
      (item) => String(item.id) !== String(activeAttachment.value?.id)
    )
    emitRatingCurvesChanged()

    delete previewRowsByAttachmentId.value[String(activeAttachment.value.id)]
    delete previewErrorByAttachmentId.value[String(activeAttachment.value.id)]
    delete previewLoadingByAttachmentId.value[String(activeAttachment.value.id)]

    openDelete.value = false
    Snackbar.success('Rating curve deleted.')
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to delete rating curve.')
  } finally {
    saving.value = false
  }
}

function taskDetailsRoute(task: { id: string; workspaceId: string }) {
  return {
    name: 'OrchestrationRatingCurveDetails',
    params: { view: 'aggregation' },
    query: {
      workspace_id: task.workspaceId,
      task_id: task.id,
    },
  }
}

async function blockDeletionIfLinked(item: DisplayRatingCurve) {
  if (item.pending) return false

  const workspaceId = props.workspaceId?.trim()
  if (!workspaceId) {
    Snackbar.error('Unable to validate rating curve usage for this site.')
    return true
  }

  const linkedTasks = await findTasksUsingRatingCurve(item.id, workspaceId)
  if (linkedTasks === null) return true
  if (!linkedTasks.length) return false

  blockedAttachment.value = item
  blockedTasks.value = linkedTasks
  openLinkedTasks.value = true
  return true
}

async function blockDeletionIfLinkedWithSpinner(item: DisplayRatingCurve) {
  const key = String(item.id)
  if (deleteValidationByAttachmentId.value[key]) return true

  deleteValidationByAttachmentId.value[key] = true
  try {
    return await blockDeletionIfLinked(item)
  } finally {
    delete deleteValidationByAttachmentId.value[key]
  }
}

async function findTasksUsingRatingCurve(
  ratingCurveId: string,
  workspaceId: string
) {
  try {
    const tasks = (await hs.dataProductTasks.listAllItems({
      workspaceId: [workspaceId],
      ratingCurveId: [ratingCurveId],
    } as any)) as any[]

    return tasks.map((task) => ({
      id: String(task.id),
      name: `${task.name ?? ''}`.trim(),
      workspaceId: String(task.workspaceId ?? workspaceId) || workspaceId,
    }))
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to validate rating curve usage.')
    return null
  }
}

async function saveEditAttachment() {
  const item = editAttachment.value
  if (!item) return

  const file = selectedEditFile.value
  const trimmedName = editAttachmentName.value.trim()
  const trimmedDescription = editAttachmentDescription.value.trim()
  if (!trimmedName) return

  const metadataChanged =
    trimmedName !== item.name ||
    trimmedDescription !== (item.description || '') ||
    editAttachmentFittingMethod.value !== item.fittingMethod
  const fileChanged = !!file

  if (!metadataChanged && !fileChanged) {
    openEdit.value = false
    resetEditState()
    return
  }

  if (fileChanged && editFileValidationPending.value) {
    Snackbar.error('Please wait for rating curve validation to finish.')
    return
  }

  let previewRows: RatingCurvePreviewRow[] | null = null
  let points: RatingCurveTuple[] | null = null
  if (fileChanged && file) {
    const isValidFile = await validateEditFile(file)
    if (!isValidFile) {
      Snackbar.error(
        editFileValidationError.value || 'Invalid rating curve CSV format.'
      )
      return
    }

    const parsed = await parseRatingCurveCsvFile(file)
    points = parsed.rows.map(
      (row) =>
        [Number(row.inputValue), Number(row.outputValue)] as RatingCurveTuple
    )
    previewRows = pointsToPreviewRows(points)
  }

  if (props.deferPersist) {
    if (item.pending) {
      const updated = ratingCurveStore.updateQueuedRatingCurveCreate(
        String(item.id),
        {
          ...(points ? { points } : {}),
          ...(previewRows ? { previewRows } : {}),
          name: trimmedName,
          description: trimmedDescription,
          fittingMethod: editAttachmentFittingMethod.value,
        }
      )
      if (!updated) {
        Snackbar.error('Unable to update pending rating curve.')
        return
      }
    } else {
      if (metadataChanged) {
        ratingCurveStore.queueExistingRatingCurveMetadataUpdate(
          item.id,
          trimmedName,
          trimmedDescription,
          editAttachmentFittingMethod.value
        )
      }
      if (fileChanged && points && previewRows) {
        ratingCurveStore.queueExistingRatingCurveReplace(
          item.id,
          points,
          previewRows
        )
      }
    }

    if (previewRows) {
      previewRowsByAttachmentId.value[String(item.id)] = previewRows
      delete previewErrorByAttachmentId.value[String(item.id)]
      delete previewLoadingByAttachmentId.value[String(item.id)]
    }
    openEdit.value = false
    resetEditState()
    return
  }

  if (!props.monitoringSiteId) {
    Snackbar.error('Save the site first before updating rating curves.')
    return
  }

  saving.value = true
  try {
    const currentCurve =
      backendRatingCurves.value.find(
        (curve) => String(curve.id) === String(item.id)
      ) || null
    if (!currentCurve) {
      Snackbar.error('Unable to find rating curve.')
      return
    }

    const res = await hs.ratingCurves.update({
      id: currentCurve.id,
      name: trimmedName,
      description: trimmedDescription,
      fittingMethod: editAttachmentFittingMethod.value,
      points: points ?? currentCurve.points ?? [],
    })
    if (!res.ok || !res.data) {
      Snackbar.error(res.message || 'Unable to update rating curve.')
      return
    }

    backendRatingCurves.value = backendRatingCurves.value.map((curve) =>
      String(curve.id) === String(item.id) ? res.data || curve : curve
    )
    emitRatingCurvesChanged()
    if (previewRows) {
      previewRowsByAttachmentId.value[String(item.id)] = previewRows
      delete previewErrorByAttachmentId.value[String(item.id)]
      delete previewLoadingByAttachmentId.value[String(item.id)]
    }
    openEdit.value = false
    resetEditState()
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to update rating curve.')
  } finally {
    saving.value = false
  }
}

async function hydrateEditPreview(item: DisplayRatingCurve) {
  const runId = ++editPreviewRunId
  const key = String(item.id)
  editPreviewLoading.value = false
  editPreviewError.value = ''

  const cachedRows = previewRowsByAttachmentId.value[key]
  if (cachedRows?.length) {
    if (runId !== editPreviewRunId) return
    editPreviewRows.value = [...cachedRows]
    return
  }

  previewRowsByAttachmentId.value[key] = pointsToPreviewRows(item.points)
  if (runId !== editPreviewRunId) return
  editPreviewRows.value = [...previewRowsByAttachmentId.value[key]]
}

function getPreviewRows(
  attachmentId: string | number
): RatingCurvePreviewRow[] {
  return previewRowsByAttachmentId.value[String(attachmentId)] ?? []
}

function isPreviewLoading(attachmentId: string | number) {
  return !!previewLoadingByAttachmentId.value[String(attachmentId)]
}

function getPreviewError(attachmentId: string | number) {
  return previewErrorByAttachmentId.value[String(attachmentId)] ?? ''
}

function isDownloading(attachmentId: string | number) {
  return !!downloadingByAttachmentId.value[String(attachmentId)]
}

function isValidatingDelete(attachmentId: string | number) {
  return !!deleteValidationByAttachmentId.value[String(attachmentId)]
}

function getPreviewPath(attachmentId: string | number): string {
  const points = toCurvePoints(getPreviewRows(attachmentId))
  const ranges = computeCurveRange(points)
  return buildSparklinePath(
    points,
    ranges,
    PREVIEW_SVG_WIDTH,
    PREVIEW_SVG_HEIGHT
  )
}

async function downloadAttachment(item: DisplayRatingCurve) {
  const key = String(item.id)
  if (downloadingByAttachmentId.value[key]) return

  downloadingByAttachmentId.value[key] = true
  try {
    const csv = [
      'inputValue,outputValue',
      ...item.points.map(([inputValue, outputValue]) =>
        [inputValue, outputValue].join(',')
      ),
    ].join('\n')
    triggerDownloadBlob(
      new Blob([csv], { type: 'text/csv;charset=utf-8' }),
      buildDownloadFilename(item.name)
    )
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to download rating curve.')
  } finally {
    downloadingByAttachmentId.value[key] = false
  }
}

function triggerDownloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function buildDownloadFilename(name: string) {
  const sanitized = `${name ?? ''}`.trim().replace(/[\\/:*?"<>|]+/g, '_')
  const baseName = sanitized || 'rating_curve'
  return /\.csv$/i.test(baseName) ? baseName : `${baseName}.csv`
}

function pointsToPreviewRows(
  points: RatingCurveTuple[]
): RatingCurvePreviewRow[] {
  return points.map(([inputValue, outputValue]) => ({
    inputValue: String(inputValue),
    outputValue: String(outputValue),
  }))
}

function toCurvePoints(rows: RatingCurvePreviewRow[]): RatingCurvePoint[] {
  return rows
    .map((row) => ({
      x: Number(row.inputValue),
      y: Number(row.outputValue),
    }))
    .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
    .sort((a, b) => a.x - b.x)
}

function computeCurveRange(
  points: RatingCurvePoint[]
): RatingCurveRange | null {
  if (!points.length) return null

  let xMin = points[0].x
  let xMax = points[0].x
  let yMin = points[0].y
  let yMax = points[0].y

  for (const point of points) {
    if (point.x < xMin) xMin = point.x
    if (point.x > xMax) xMax = point.x
    if (point.y < yMin) yMin = point.y
    if (point.y > yMax) yMax = point.y
  }

  if (xMin === xMax) {
    const xDelta = Math.abs(xMin || 1) * 0.1
    xMin -= xDelta
    xMax += xDelta
  }

  if (yMin === yMax) {
    const yDelta = Math.abs(yMin || 1) * 0.1
    yMin -= yDelta
    yMax += yDelta
  }

  return { xMin, xMax, yMin, yMax }
}

function buildSparklinePath(
  points: RatingCurvePoint[],
  ranges: RatingCurveRange | null,
  width: number,
  height: number
) {
  if (!points.length || !ranges) return ''

  const scaleX = (x: number) =>
    ((x - ranges.xMin) / (ranges.xMax - ranges.xMin)) * width
  const scaleY = (y: number) =>
    (1 - (y - ranges.yMin) / (ranges.yMax - ranges.yMin)) * height

  if (points.length === 1) {
    const y = scaleY(points[0].y).toFixed(2)
    return `M0 ${y} L${width} ${y}`
  }

  return points
    .map((point, index) => {
      const x = scaleX(point.x).toFixed(2)
      const y = scaleY(point.y).toFixed(2)
      return `${index === 0 ? 'M' : 'L'}${x} ${y}`
    })
    .join(' ')
}

async function validateCreateFile(file: File | null): Promise<boolean> {
  const runId = ++createValidationRunId
  createFileValidationError.value = ''

  if (!file) {
    createFileValidationPending.value = false
    return true
  }

  createFileValidationPending.value = true
  try {
    await parseRatingCurveCsvFile(file)
    if (runId !== createValidationRunId) return false
    createFileValidationError.value = ''
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

async function validateEditFile(file: File | null): Promise<boolean> {
  const runId = ++editValidationRunId
  editFileValidationError.value = ''

  if (!file) {
    editFileValidationPending.value = false
    return true
  }

  editFileValidationPending.value = true
  try {
    const parsed = await parseRatingCurveCsvFile(file)
    if (runId !== editValidationRunId) return false
    editPreviewRows.value = parsed.rows.map((row) => ({
      inputValue: String(row.inputValue),
      outputValue: String(row.outputValue),
    }))
    editFileValidationError.value = ''
    return true
  } catch (error: unknown) {
    if (runId !== editValidationRunId) return false
    editPreviewRows.value = []
    editFileValidationError.value = toRatingCurveFileValidationMessage(error)
    return false
  } finally {
    if (runId === editValidationRunId) {
      editFileValidationPending.value = false
    }
  }
}

watch(
  () => props.monitoringSiteId,
  () => {
    void refreshRatingCurves()
  },
  { immediate: true }
)

watch(
  () => props.refreshToken,
  () => {
    void refreshRatingCurves()
  }
)

watch(selectedFile, (file) => {
  if (!file) {
    createValidationRunId += 1
    createFileValidationError.value = ''
    createFileValidationPending.value = false
    return
  }

  if (!attachmentName.value.trim()) {
    attachmentName.value = file.name
  }

  void validateCreateFile(file)
})

watch(selectedEditFile, (file) => {
  if (!file) {
    editValidationRunId += 1
    editFileValidationError.value = ''
    editFileValidationPending.value = false
    const item = editAttachment.value
    if (!item) {
      editPreviewRows.value = []
      editPreviewLoading.value = false
      editPreviewError.value = ''
      return
    }

    void hydrateEditPreview(item)
    return
  }

  editPreviewRunId += 1
  editPreviewLoading.value = false
  editPreviewError.value = ''
  void validateEditFile(file)
})

watch(openEdit, (isOpen) => {
  if (!isOpen) {
    resetEditState()
  }
})
</script>

<style scoped>
.rating-curves__toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--hs-space-12);
}

.rating-curves__empty {
  margin: 0;
  padding: var(--hs-space-16) 0;
  text-align: center;
}

/* Inline create/edit form: a quiet panel, not another bordered card. */
.rating-curve-form {
  margin-bottom: var(--hs-space-12);
  padding: var(--hs-space-16);
  background: var(--hs-surface-muted);
  border-radius: var(--hs-radius-md);
}

.rating-curve-form--edit {
  margin-bottom: 0;
}

.rating-curve-form__file {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--hs-space-8);
  margin-bottom: var(--hs-space-12);
}

.rating-curve-form__fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 var(--hs-space-12);
}

.rating-curve-form__wide {
  grid-column: 1 / -1;
}

.rating-curve-form__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--hs-space-8);
  margin-top: var(--hs-space-4);
}

.rating-curve-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.rating-curve-entry {
  padding: var(--hs-space-8) 0;
  border-bottom: 1px solid var(--hs-border);
}

.rating-curve-entry:last-child {
  border-bottom: none;
}

.rating-curve-item {
  display: grid;
  grid-template-columns: 8.5rem minmax(0, 1fr) auto;
  gap: var(--hs-space-12);
  align-items: center;
}

.rating-curve-item-main {
  min-width: 0;
}

.rating-curve-item-preview {
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rating-curve-item-actions {
  display: flex;
  align-items: center;
  gap: var(--hs-space-2);
}

.rating-curve-confirm {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--hs-space-8);
  margin-top: var(--hs-space-8);
  padding: var(--hs-space-8) var(--hs-space-12);
  background: var(--hs-danger-bg);
  border-radius: var(--hs-radius-md);
}

.rating-curve-linked-tasks {
  margin: var(--hs-space-4) 0 0;
  padding-left: var(--hs-space-20);
}

.rating-curve-preview-box {
  border: 1px solid var(--hs-border);
  border-radius: var(--hs-radius-sm);
  height: 38px;
  width: 132px;
  margin-block: var(--hs-space-2);
}

.rating-curve-preview-svg {
  height: 100%;
  width: 100%;
}

.rating-curve-line {
  stroke: var(--hs-primary);
  stroke-width: 2;
}

@media (max-width: 680px) {
  .rating-curve-item {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .rating-curve-item-preview {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }

  .rating-curve-form__fields {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
