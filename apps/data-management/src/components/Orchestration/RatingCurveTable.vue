<template>
  <div v-if="showHeader" class="rating-curve-manager">
    <div class="d-flex align-center mb-2">
      <h6 class="text-h6 mb-0">Rating Curves</h6>
      <v-chip class="ml-2" size="small" variant="tonal">
        {{ attachmentCountLabel }}
      </v-chip>
      <v-spacer />
      <v-btn
        v-if="showManageButton"
        color="teal-darken-1"
        class="text-none"
        :loading="loading"
        @click="openManageDialog"
      >
        Manage rating curves
      </v-btn>
    </div>
  </div>

  <div v-if="inlineReadOnly" class="rating-curve-surface">
    <v-progress-linear v-if="loading" indeterminate color="primary" />
    <div class="rating-curve-body">
      <div
        v-if="!loading && displayAttachments.length === 0"
        class="text-body-2 text-medium-emphasis"
      >
        No rating curves have been added to this site yet.
      </div>

      <div v-else class="rating-curve-list">
        <div
          v-for="attachment in displayAttachments"
          :key="attachment.id"
          class="rating-curve-item"
        >
          <div class="rating-curve-item-preview">
            <div
              v-if="isPreviewLoading(attachment.id)"
              class="text-caption text-medium-emphasis"
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
              class="text-caption text-error"
            >
              Preview unavailable
            </div>
            <div v-else class="text-caption text-medium-emphasis">No points</div>
          </div>

          <div class="rating-curve-item-main">
            <div class="text-subtitle-2">{{ attachment.name }}</div>
            <div
              v-if="attachment.description"
              class="text-caption text-medium-emphasis"
            >
              {{ attachment.description }}
            </div>
          </div>

          <div v-if="downloadOnly" class="rating-curve-item-actions">
            <v-tooltip location="top">
              <template #activator="{ props: tooltipProps }">
                <span v-bind="tooltipProps" class="inline-flex">
                  <v-btn
                    :icon="mdiDownload"
                    variant="text"
                    :loading="isDownloading(attachment.id)"
                    :disabled="!attachment.link || isDownloading(attachment.id)"
                    @click="downloadAttachment(attachment)"
                  />
                </span>
              </template>
              <span>{{ downloadTooltipText }}</span>
            </v-tooltip>
          </div>
        </div>
      </div>
    </div>
  </div>

  <v-dialog v-model="openManage" width="56rem">
    <v-card>
      <v-card-title class="text-h6 bg-teal-darken-1 text-white">
        Manage rating curves
      </v-card-title>
      <v-divider />
      <v-card-text class="pt-4">
        <div class="d-flex align-center mb-3">
          <v-chip size="small" variant="tonal">
            {{ attachmentCountLabel }}
          </v-chip>
          <v-spacer />
          <v-tooltip v-if="canEditThing" location="top" :disabled="canEditThing">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="inline-flex">
                <v-btn
                  variant="outlined"
                  color="teal-darken-1"
                  class="text-none"
                  :disabled="!canEditThing"
                  @click="openCreateDialog"
                >
                  Add rating curve
                </v-btn>
              </span>
            </template>
            <span>{{ readOnlyTooltip }}</span>
          </v-tooltip>
        </div>

        <div class="rating-curve-surface">
          <v-progress-linear v-if="loading" indeterminate color="primary" />
          <div class="rating-curve-body">
            <div
              v-if="!loading && displayAttachments.length === 0"
              class="text-body-2 text-medium-emphasis"
            >
              No rating curves have been added to this site yet.
            </div>

            <div v-else class="rating-curve-list">
              <div
                v-for="attachment in displayAttachments"
                :key="attachment.id"
                class="rating-curve-item"
              >
                <div class="rating-curve-item-preview">
                  <div
                    v-if="isPreviewLoading(attachment.id)"
                    class="text-caption text-medium-emphasis"
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
                    class="text-caption text-error"
                  >
                    Preview unavailable
                  </div>
                  <div v-else class="text-caption text-medium-emphasis">
                    No points
                  </div>
                </div>

                <div class="rating-curve-item-main">
                  <div class="text-subtitle-2">{{ attachment.name }}</div>
                  <div
                    v-if="attachment.description"
                    class="text-caption text-medium-emphasis"
                  >
                    {{ attachment.description }}
                  </div>
                </div>

                <div v-if="canEditThing" class="rating-curve-item-actions">
                  <v-tooltip location="top" :disabled="canEditThing">
                    <template #activator="{ props: tooltipProps }">
                      <span v-bind="tooltipProps" class="inline-flex">
                        <v-btn
                          :icon="mdiPencil"
                          variant="text"
                          :disabled="!canEditThing"
                          @click="openEditDialog(attachment)"
                        />
                      </span>
                    </template>
                    <span>{{ readOnlyTooltip }}</span>
                  </v-tooltip>

                  <v-tooltip location="top" :disabled="canEditThing">
                    <template #activator="{ props: tooltipProps }">
                      <span v-bind="tooltipProps" class="inline-flex">
                        <v-btn
                          :icon="mdiDelete"
                          variant="text"
                          color="delete"
                          :loading="isValidatingDelete(attachment.id)"
                          :disabled="!canEditThing || isValidatingDelete(attachment.id)"
                          @click="handleDeleteClick(attachment)"
                        />
                      </span>
                    </template>
                    <span>{{ readOnlyTooltip }}</span>
                  </v-tooltip>
                </div>

                <div v-else-if="downloadOnly" class="rating-curve-item-actions">
                  <v-tooltip location="top">
                    <template #activator="{ props: tooltipProps }">
                      <span v-bind="tooltipProps" class="inline-flex">
                        <v-btn
                          :icon="mdiDownload"
                          variant="text"
                          :loading="isDownloading(attachment.id)"
                          :disabled="!attachment.link || isDownloading(attachment.id)"
                          @click="downloadAttachment(attachment)"
                        />
                      </span>
                    </template>
                    <span>{{ downloadTooltipText }}</span>
                  </v-tooltip>
                </div>
              </div>
            </div>
          </div>
        </div>
      </v-card-text>
      <v-divider />
      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="openManage = false">Close</v-btn-cancel>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="openCreate" width="42rem">
    <v-card>
      <v-card-title class="text-h6 bg-teal-darken-1 text-white">
        Add rating curve
      </v-card-title>
      <v-divider />
      <v-card-text class="pt-4">
        <input
          ref="createFileInput"
          type="file"
          accept=".csv,text/csv"
          class="d-none"
          @change="onCreateFileSelected"
        />
        <v-btn
          variant="outlined"
          color="teal-darken-1"
          block
          class="mb-2 text-none"
          @click="openCreateFilePicker"
        >
          {{ selectedFile ? 'Change CSV file' : 'Choose CSV file *' }}
        </v-btn>
        <div v-if="selectedFile" class="d-flex align-center mb-3">
          <span class="text-caption text-medium-emphasis">
            Selected:
            <strong>{{ selectedFile.name }}</strong>
            ({{ formatFileSize(selectedFile.size) }})
          </span>
          <v-spacer />
          <v-btn variant="text" size="small" @click="clearCreateFile">
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
          v-model="attachmentName"
          label="Rating curve name *"
          class="mb-3"
        />
        <v-textarea
          v-model="attachmentDescription"
          label="Description"
          rows="2"
        />
      </v-card-text>
      <v-divider />
      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="openCreate = false">Cancel</v-btn-cancel>
        <v-btn-primary
          :loading="saving"
          :disabled="!canCreateAttachment"
          @click="createAttachment"
        >
          Save
        </v-btn-primary>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="openEdit" width="42rem">
    <v-card>
      <v-card-title class="text-h6 bg-teal-darken-1 text-white">
        Update rating curve
      </v-card-title>
      <v-divider />
      <v-card-text class="pt-4">
        <div class="text-body-2 mb-3">
          Selected rating curve: <strong>{{ editAttachment?.name }}</strong>
        </div>

        <v-text-field
          v-model="editAttachmentName"
          label="Rating curve name *"
          class="mb-3"
        />
        <v-textarea
          v-model="editAttachmentDescription"
          label="Description"
          rows="2"
          class="mb-3"
        />

        <input
          ref="editFileInput"
          type="file"
          accept=".csv,text/csv"
          class="d-none"
          @change="onEditFileSelected"
        />
        <v-btn
          variant="outlined"
          color="teal-darken-1"
          block
          class="mb-2 text-none"
          @click="openEditFilePicker"
        >
          {{ selectedEditFile ? 'Change CSV file' : 'Choose replacement CSV file' }}
        </v-btn>
        <div v-if="selectedEditFile" class="d-flex align-center mb-3">
          <span class="text-caption text-medium-emphasis">
            Selected:
            <strong>{{ selectedEditFile.name }}</strong>
            ({{ formatFileSize(selectedEditFile.size) }})
          </span>
          <v-spacer />
          <v-btn variant="text" size="small" @click="clearEditFile">Clear</v-btn>
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
          class="text-caption text-medium-emphasis mb-3"
        >
          Validating rating curve CSV...
        </div>

        <div v-if="editPreviewPath" class="rating-curve-edit-preview">
          <div class="text-caption text-medium-emphasis mb-1">Preview</div>
          <div class="rating-curve-preview-box">
            <svg
              class="rating-curve-preview-svg"
              :viewBox="`0 0 ${PREVIEW_SVG_WIDTH} ${PREVIEW_SVG_HEIGHT}`"
              preserveAspectRatio="none"
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
      </v-card-text>
      <v-divider />
      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="openEdit = false">Cancel</v-btn-cancel>
        <v-btn-primary
          :loading="saving"
          :disabled="!canSaveEditAttachment"
          @click="saveEditAttachment"
        >
          Save
        </v-btn-primary>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="openDelete" width="30rem">
    <v-card>
      <v-card-title class="text-h6 text-error">Delete rating curve</v-card-title>
      <v-divider />
      <v-card-text class="pt-4">
        Delete <strong>{{ activeAttachment?.name }}</strong> from this site?
      </v-card-text>
      <v-divider />
      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="openDelete = false">Cancel</v-btn-cancel>
        <v-btn-primary color="error" :loading="saving" @click="deleteAttachment">
          Delete
        </v-btn-primary>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="openLinkedTasks" width="42rem" max-width="95vw">
    <v-card>
      <v-toolbar flat color="red-darken-4">
        <v-card-title class="text-h5">
          <v-icon :icon="mdiAlert" />
          Cannot delete rating curve
        </v-card-title>
      </v-toolbar>
      <v-divider />
      <v-card-text class="pt-4">
        <div class="text-body-2 mb-3">
          <strong>{{ blockedAttachment?.name }}</strong> is linked to one or more
          tasks. Remove this rating curve from those tasks before deleting it.
        </div>
        <div class="linked-task-buttons">
          <v-btn
            v-for="task in blockedTasks"
            :key="task.id"
            :to="taskDetailsRoute(task)"
            variant="outlined"
            color="primary"
            block
            class="text-none linked-task-btn"
          >
            <span class="linked-task-btn-name">{{ task.name || task.id }}</span>
            <span class="linked-task-btn-id">{{ task.id }}</span>
          </v-btn>
        </div>
      </v-card-text>
      <v-divider />
      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="openLinkedTasks = false">Close</v-btn-cancel>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { mdiAlert, mdiDelete, mdiDownload, mdiPencil } from '@mdi/js'
import hs, {
  type RatingCurvePreviewRow,
  type ThingFileAttachment,
} from '@hydroserver/client'
import { Snackbar } from '@/utils/notifications'
import {
  parseRatingCurveCsvFile,
  toRatingCurveFileValidationMessage,
} from '@/utils/orchestration/ratingCurveFile'
import { getRatingCurveReference } from '@/utils/orchestration/ratingCurve'
import { useRatingCurveStore } from '@/store/ratingCurves'

const props = withDefaults(
  defineProps<{
    thingId?: string
    canEdit?: boolean
    deferPersist?: boolean
    inlineReadOnly?: boolean
    downloadOnly?: boolean
    workspaceId?: string
    showHeader?: boolean
    refreshToken?: number
  }>(),
  {
    canEdit: false,
    deferPersist: false,
    inlineReadOnly: false,
    downloadOnly: false,
    workspaceId: '',
    showHeader: true,
    refreshToken: 0,
  }
)

const emit = defineEmits<{
  (e: 'attachments-changed', attachments: ThingFileAttachment[]): void
}>()

type DisplayRatingCurve = {
  id: string | number
  name: string
  description: string
  link?: string
  pending: boolean
}

const ratingCurveStore = useRatingCurveStore()

const backendAttachments = ref<ThingFileAttachment[]>([])
const backendLoading = ref(false)
const saving = ref(false)

const openManage = ref(false)
const openCreate = ref(false)
const openEdit = ref(false)
const openDelete = ref(false)
const openLinkedTasks = ref(false)

const attachmentFile = ref<File | File[] | null>(null)
const createFileInput = ref<HTMLInputElement | null>(null)
const attachmentName = ref('')
const attachmentDescription = ref('')
const editAttachment = ref<DisplayRatingCurve | null>(null)
const editAttachmentFile = ref<File | File[] | null>(null)
const editFileInput = ref<HTMLInputElement | null>(null)
const editAttachmentName = ref('')
const editAttachmentDescription = ref('')
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
const editPreviewRows = ref<RatingCurvePreviewRow[]>([])

const PREVIEW_SVG_WIDTH = 132
const PREVIEW_SVG_HEIGHT = 38
const previewRowsByAttachmentId = ref<Record<string, RatingCurvePreviewRow[]>>({})
const previewLoadingByAttachmentId = ref<Record<string, boolean>>({})
const previewErrorByAttachmentId = ref<Record<string, string>>({})
const downloadingByAttachmentId = ref<Record<string, boolean>>({})
const deleteValidationByAttachmentId = ref<Record<string, boolean>>({})

const canEditThing = computed(() => props.canEdit)
const inlineReadOnly = computed(() => props.inlineReadOnly && !canEditThing.value)
const showManageButton = computed(() => canEditThing.value && !inlineReadOnly.value)
const readOnlyTooltip =
  'You have read-only access to this site. Ask an editor or owner to make changes.'
const downloadTooltipText = 'Download rating curve'

const loading = computed(() =>
  props.deferPersist ? ratingCurveStore.loading : backendLoading.value
)

const displayAttachments = computed<DisplayRatingCurve[]>(() => {
  if (!props.deferPersist) {
    return backendAttachments.value.map((attachment) => ({
      id: attachment.id,
      name: attachment.name,
      description: attachment.description || '',
      link: attachment.link,
      pending: false,
    }))
  }

  const deletedIds = new Set(
    ratingCurveStore.pendingDeleteIds.map((item) => String(item))
  )
  const metadataUpdatesById = new Map(
    ratingCurveStore.pendingMetadataUpdates.map((item) => [
      String(item.attachmentId),
      item,
    ])
  )

  const existing = ratingCurveStore.existingRatingCurves
    .filter((attachment) => !deletedIds.has(String(attachment.id)))
    .map((attachment) => {
      const pendingMetadata = metadataUpdatesById.get(String(attachment.id))
      return {
        id: attachment.id,
        name: pendingMetadata?.name ?? attachment.name,
        description: pendingMetadata?.description ?? (attachment.description || ''),
        link: attachment.link,
        pending: false,
      }
    })

  const queued = ratingCurveStore.pendingCreates.map((item) => ({
    id: item.tempId,
    name: item.name,
    description: item.description,
    pending: true,
  }))

  return [...existing, ...queued].sort((a, b) => a.name.localeCompare(b.name))
})

const attachmentCountLabel = computed(() => {
  const count = displayAttachments.value.length
  return `${count} rating curve${count === 1 ? '' : 's'}`
})

const selectedFile = computed(() => {
  const value = attachmentFile.value
  if (!value) return null
  return Array.isArray(value) ? value[0] ?? null : value
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
  return Array.isArray(value) ? value[0] ?? null : value
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
  return buildSparklinePath(points, ranges, PREVIEW_SVG_WIDTH, PREVIEW_SVG_HEIGHT)
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
}

function resetEditState() {
  editValidationRunId += 1
  editFileValidationError.value = ''
  editFileValidationPending.value = false
  editAttachmentFile.value = null
  editAttachmentName.value = ''
  editAttachmentDescription.value = ''
  editPreviewRows.value = []
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
  editPreviewRows.value = []
  if (editFileInput.value) {
    editFileInput.value.value = ''
  }
}

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024) return `${sizeBytes} B`
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
}

function emitAttachmentsChanged() {
  emit('attachments-changed', [...backendAttachments.value])
}

async function refreshAttachments() {
  if (props.deferPersist) {
    try {
      await ratingCurveStore.loadExistingRatingCurves(props.thingId)

      const deletedIds = new Set(
        ratingCurveStore.pendingDeleteIds.map((item) => String(item))
      )
      for (const attachment of ratingCurveStore.existingRatingCurves) {
        if (!deletedIds.has(String(attachment.id))) {
          void loadPreviewForAttachment(attachment)
        }
      }

      for (const pending of ratingCurveStore.pendingCreates) {
        previewRowsByAttachmentId.value[pending.tempId] = pending.previewRows
      }

      for (const pending of ratingCurveStore.pendingReplaces) {
        previewRowsByAttachmentId.value[String(pending.attachmentId)] =
          pending.previewRows
      }
    } catch (error: any) {
      Snackbar.error(error?.message || 'Unable to load rating curves.')
    }

    return
  }

  if (!props.thingId) {
    backendAttachments.value = []
    emitAttachmentsChanged()
    return
  }

  backendLoading.value = true
  try {
    const items = await hs.thingFileAttachments.listItems(props.thingId, {
      type: 'rating_curve',
    })
    backendAttachments.value = items.sort((a, b) => a.name.localeCompare(b.name))
    emitAttachmentsChanged()
    for (const attachment of backendAttachments.value) {
      void loadPreviewForAttachment(attachment)
    }
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load rating curves.')
  } finally {
    backendLoading.value = false
  }
}

function openCreateDialog() {
  if (!canEditThing.value) return
  resetCreateState()
  openCreate.value = true
}

function openManageDialog() {
  if (!canEditThing.value) return
  openManage.value = true
}

function openEditDialog(item: DisplayRatingCurve) {
  if (!canEditThing.value) return
  resetEditState()
  editAttachment.value = item
  editAttachmentName.value = item.name
  editAttachmentDescription.value = item.description || ''
  openEdit.value = true
}

function openDeleteDialog(item: DisplayRatingCurve) {
  if (!canEditThing.value) return
  activeAttachment.value = item
  openDelete.value = true
}

async function handleDeleteClick(item: DisplayRatingCurve) {
  if (!canEditThing.value) return
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
  const previewRows: RatingCurvePreviewRow[] = parsed.rows.map((row) => ({
    inputValue: String(row.inputValue),
    outputValue: String(row.outputValue),
  }))

  if (props.deferPersist) {
    const tempId = ratingCurveStore.queueRatingCurveCreate(
      file,
      trimmedName,
      attachmentDescription.value.trim(),
      previewRows
    )
    previewRowsByAttachmentId.value[tempId] = previewRows
    openCreate.value = false
    resetCreateState()
    return
  }

  if (!props.thingId) {
    Snackbar.error('Save the site first before adding rating curves.')
    return
  }

  saving.value = true
  try {
    const res = await hs.thingFileAttachments.upload(props.thingId, file, {
      type: 'rating_curve',
      name: trimmedName,
      description: attachmentDescription.value.trim() || undefined,
    })

    if (!res.ok || !res.data) {
      Snackbar.error(res.message || 'Unable to create rating curve.')
      return
    }

    const created = res.data
    backendAttachments.value = [...backendAttachments.value, created].sort((a, b) =>
      a.name.localeCompare(b.name)
    )
    emitAttachmentsChanged()
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
      ratingCurveStore.removeQueuedRatingCurveCreate(String(activeAttachment.value.id))
      delete previewRowsByAttachmentId.value[String(activeAttachment.value.id)]
    } else {
      ratingCurveStore.queueExistingRatingCurveDelete(activeAttachment.value.id)
      delete previewRowsByAttachmentId.value[String(activeAttachment.value.id)]
      delete previewErrorByAttachmentId.value[String(activeAttachment.value.id)]
      delete previewLoadingByAttachmentId.value[String(activeAttachment.value.id)]
    }

    openDelete.value = false
    return
  }

  if (!props.thingId) {
    Snackbar.error('Save the site first before deleting rating curves.')
    return
  }

  if (await blockDeletionIfLinked(activeAttachment.value)) {
    openDelete.value = false
    return
  }

  saving.value = true
  try {
    const res = await hs.thingFileAttachments.delete(
      props.thingId,
      activeAttachment.value.id
    )

    if (!res.ok) {
      Snackbar.error(res.message || 'Unable to delete rating curve.')
      return
    }

    backendAttachments.value = backendAttachments.value.filter(
      (item) => String(item.id) !== String(activeAttachment.value?.id)
    )
    emitAttachmentsChanged()

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
    name: 'Orchestration',
    query: {
      workspaceId: task.workspaceId,
      taskId: task.id,
    },
  }
}

async function blockDeletionIfLinked(item: DisplayRatingCurve) {
  if (item.pending || !item.link) return false

  const workspaceId = props.workspaceId?.trim()
  if (!workspaceId) {
    Snackbar.error('Unable to validate rating curve usage for this site.')
    return true
  }

  const linkedTasks = await findTasksUsingRatingCurve(item.link, workspaceId)
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
  ratingCurveLink: string,
  workspaceId: string
) {
  try {
    const tasks = (await hs.tasks.listAllItems({
      workspace_id: [workspaceId],
      expand_related: true,
    } as any)) as any[]

    return tasks
      .filter((task) => taskUsesRatingCurve(task, ratingCurveLink))
      .map((task) => ({
        id: String(task.id),
        name: `${task.name ?? ''}`.trim(),
        workspaceId:
          String(task.workspaceId ?? task.workspace?.id ?? workspaceId) || workspaceId,
      }))
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to validate rating curve usage.')
    return null
  }
}

function taskUsesRatingCurve(task: any, ratingCurveLink: string) {
  const mappings = Array.isArray(task?.mappings) ? task.mappings : []
  for (const mapping of mappings) {
    const paths = Array.isArray(mapping?.paths) ? mapping.paths : []
    for (const path of paths) {
      const transformations = Array.isArray(path?.dataTransformations)
        ? path.dataTransformations
        : []
      for (const transformation of transformations) {
        const reference = getRatingCurveReference(transformation)
        if (isSameRatingCurveReference(reference, ratingCurveLink)) return true
      }
    }
  }
  return false
}

function isSameRatingCurveReference(left: string, right: string) {
  const leftRef = parseRatingCurveReference(left)
  const rightRef = parseRatingCurveReference(right)

  if (leftRef.raw && rightRef.raw && leftRef.raw === rightRef.raw) return true
  if (leftRef.pathname && rightRef.pathname && leftRef.pathname === rightRef.pathname) {
    return true
  }
  if (
    leftRef.attachmentId &&
    rightRef.attachmentId &&
    leftRef.attachmentId === rightRef.attachmentId
  ) {
    return true
  }

  return false
}

function parseRatingCurveReference(value: string) {
  const raw = `${value ?? ''}`.trim().replace(/\/+$/, '')
  if (!raw) {
    return {
      raw: '',
      pathname: '',
      attachmentId: '',
    }
  }

  try {
    const parsed = new URL(raw, globalThis.location?.origin ?? undefined)
    const pathname = parsed.pathname.replace(/\/+$/, '')
    return {
      raw,
      pathname,
      attachmentId: extractAttachmentId(pathname),
    }
  } catch {
    return {
      raw,
      pathname: raw.replace(/\/+$/, ''),
      attachmentId: extractAttachmentId(raw),
    }
  }
}

function extractAttachmentId(path: string) {
  const match =
    /\/things\/[^/]+\/file-attachments\/([^/]+)\/download\/?$/i.exec(path)
  if (!match?.[1]) return ''
  try {
    return decodeURIComponent(match[1])
  } catch {
    return match[1]
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
    trimmedName !== item.name || trimmedDescription !== (item.description || '')
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
  if (fileChanged && file) {
    const isValidFile = await validateEditFile(file)
    if (!isValidFile) {
      Snackbar.error(
        editFileValidationError.value || 'Invalid rating curve CSV format.'
      )
      return
    }

    const parsed = await parseRatingCurveCsvFile(file)
    previewRows = parsed.rows.map((row) => ({
      inputValue: String(row.inputValue),
      outputValue: String(row.outputValue),
    }))
  }

  if (props.deferPersist) {
    if (item.pending) {
      const updated = ratingCurveStore.updateQueuedRatingCurveCreate(
        String(item.id),
        {
          ...(fileChanged && file ? { file } : {}),
          ...(previewRows ? { previewRows } : {}),
          name: trimmedName,
          description: trimmedDescription,
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
          trimmedDescription
        )
      }
      if (fileChanged && file && previewRows) {
        ratingCurveStore.queueExistingRatingCurveReplace(item.id, file, previewRows)
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

  if (!props.thingId) {
    Snackbar.error('Save the site first before updating rating curves.')
    return
  }

  saving.value = true
  try {
    let updatedAttachment =
      backendAttachments.value.find(
        (attachment) => String(attachment.id) === String(item.id)
      ) || null

    if (metadataChanged) {
      const metaRes = await hs.thingFileAttachments.update(props.thingId, item.id, {
        name: trimmedName,
        description: trimmedDescription,
      })
      if (!metaRes.ok || !metaRes.data) {
        Snackbar.error(metaRes.message || 'Unable to update rating curve.')
        return
      }
      updatedAttachment = metaRes.data
    }

    if (fileChanged && file) {
      const fileRes = await hs.thingFileAttachments.replaceFile(
        props.thingId,
        item.id,
        file
      )
      if (!fileRes.ok || !fileRes.data) {
        Snackbar.error(fileRes.message || 'Unable to update rating curve file.')
        return
      }
      updatedAttachment = fileRes.data
    }

    backendAttachments.value = backendAttachments.value.map((attachment) =>
      String(attachment.id) === String(item.id)
        ? updatedAttachment || attachment
        : attachment
    )
    emitAttachmentsChanged()
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

async function loadPreviewForAttachment(attachment: ThingFileAttachment) {
  const key = String(attachment.id)
  if (previewLoadingByAttachmentId.value[key]) return
  if (previewRowsByAttachmentId.value[key]?.length) return

  previewLoadingByAttachmentId.value[key] = true
  previewErrorByAttachmentId.value[key] = ''
  try {
    const res = await hs.thingFileAttachments.fetchRatingCurvePreview(
      attachment.link,
      20
    )
    if (!res.ok) {
      previewRowsByAttachmentId.value[key] = []
      previewErrorByAttachmentId.value[key] =
        res.message || 'Unable to load preview.'
      return
    }
    previewRowsByAttachmentId.value[key] = res.data
  } catch {
    previewRowsByAttachmentId.value[key] = []
    previewErrorByAttachmentId.value[key] = 'Unable to load preview.'
  } finally {
    previewLoadingByAttachmentId.value[key] = false
  }
}

function getPreviewRows(attachmentId: string | number): RatingCurvePreviewRow[] {
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
  return buildSparklinePath(points, ranges, PREVIEW_SVG_WIDTH, PREVIEW_SVG_HEIGHT)
}

async function downloadAttachment(item: DisplayRatingCurve) {
  const key = String(item.id)
  if (downloadingByAttachmentId.value[key]) return

  if (!item.link) {
    Snackbar.error('Rating curve download link unavailable.')
    return
  }

  downloadingByAttachmentId.value[key] = true
  try {
    let response: Response
    try {
      response = await fetch(item.link, {
        method: 'GET',
        credentials: 'include',
        headers: {
          Accept: 'text/csv, text/plain, application/octet-stream',
        },
      })
    } catch {
      triggerDownloadLink(item.link, buildDownloadFilename(item.name))
      return
    }

    if (!response.ok) {
      Snackbar.error('Unable to download rating curve.')
      return
    }

    const blob = await response.blob()
    const dispositionFilename = filenameFromContentDisposition(
      response.headers.get('content-disposition')
    )
    triggerDownloadBlob(
      blob,
      dispositionFilename || buildDownloadFilename(item.name)
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

function triggerDownloadLink(downloadUrl: string, filename: string) {
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  link.target = '_blank'
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function buildDownloadFilename(name: string) {
  const sanitized = `${name ?? ''}`
    .trim()
    .replace(/[\\/:*?"<>|]+/g, '_')
  const baseName = sanitized || 'rating_curve'
  return /\.csv$/i.test(baseName) ? baseName : `${baseName}.csv`
}

function filenameFromContentDisposition(value: string | null) {
  if (!value) return ''

  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(value)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1].replace(/["']/g, ''))
    } catch {
      return utf8Match[1].replace(/["']/g, '')
    }
  }

  const basicMatch = /filename="?([^";]+)"?/i.exec(value)
  return basicMatch?.[1] ?? ''
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

function computeCurveRange(points: RatingCurvePoint[]): RatingCurveRange | null {
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
  () => props.thingId,
  () => {
    void refreshAttachments()
  },
  { immediate: true }
)

watch(
  () => props.refreshToken,
  () => {
    void refreshAttachments()
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
    editPreviewRows.value = []
    return
  }

  void validateEditFile(file)
})

watch(openEdit, (isOpen) => {
  if (!isOpen) {
    resetEditState()
  }
})
</script>

<style scoped>
.rating-curve-surface {
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.012);
}

.rating-curve-body {
  padding: 0.75rem;
}

.rating-curve-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  max-height: 18rem;
  overflow: auto;
}

.rating-curve-item {
  display: grid;
  grid-template-columns: 8.5rem minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: center;
  padding: 0.45rem 0.2rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.rating-curve-item:last-child {
  border-bottom: none;
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
  gap: 0.1rem;
}

.rating-curve-preview-box {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  height: 38px;
  width: 132px;
  margin-block: 2px;
}

.rating-curve-preview-svg {
  height: 100%;
  width: 100%;
}

.rating-curve-line {
  stroke: #00796b;
  stroke-width: 2;
}

.rating-curve-edit-preview {
  margin-top: 0.25rem;
}

.linked-task-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.linked-task-btn {
  height: auto;
  justify-content: flex-start;
  text-align: left;
  padding: 0.65rem 0.85rem;
}

.linked-task-btn-name,
.linked-task-btn-id {
  display: block;
  width: 100%;
}

.linked-task-btn-name {
  font-weight: 600;
  color: currentColor;
}

.linked-task-btn-id {
  margin-top: 0.15rem;
  font-size: 0.75rem;
  opacity: 0.9;
  text-transform: none;
}

@media (max-width: 680px) {
  .rating-curve-item {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .rating-curve-item-preview {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
}
</style>
