<template>
  <v-card>
    <v-toolbar :color="local.type === 'expression' ? 'deep-purple' : 'teal'">
      <v-card-title
        >{{ isEdit ? 'Edit' : 'Add' }} data transformation</v-card-title
      >
    </v-toolbar>
    <v-divider />

    <v-form
      ref="myForm"
      v-model="valid"
      validate-on="input"
      @submit.prevent="onSubmit"
    >
      <v-card-text>
        <v-radio-group v-model="local.type" inline>
          <v-radio label="Expression" value="expression" />
          <v-radio label="Rating curve" value="rating_curve" />
        </v-radio-group>

        <template v-if="local.type === 'expression'">
          <v-alert
            color="deep-purple"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-6"
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
            v-model="local.expression"
            label="Output = *"
            placeholder="eg. (x - 32) * 5/9"
            :rules="[
              ...rules.required,
              exprContainsX,
              exprAllowedTokens,
              exprBalancedParens,
            ]"
            auto-grow
          />
        </template>

        <template v-else>
          <v-alert
            color="teal"
            type="info"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            Select the site first, then choose one of that site's rating curve
            files or add a new rating curve file to the selected site.
          </v-alert>

          <template v-if="canSelectThing">
            <v-autocomplete
              v-model="selectedThingId"
              :items="thingOptions"
              item-title="title"
              item-value="value"
              label="Site *"
              clearable
              :loading="thingsLoading"
              :rules="rules.required"
              class="mb-3"
              @update:model-value="onThingSelected"
            />

            <template v-if="selectedThingId">
              <v-radio-group
                v-model="ratingCurveInputMode"
                inline
                hide-details
                class="mb-3"
              >
                <v-radio
                  label="Select existing rating curve"
                  value="existing"
                />
                <v-radio label="Create new rating curve" value="create" />
              </v-radio-group>

              <template v-if="ratingCurveInputMode === 'existing'">
                <v-select
                  v-model="selectedAttachmentId"
                  :items="attachmentOptions"
                  item-title="title"
                  item-value="value"
                  label="Select rating curve *"
                  clearable
                  :disabled="!selectedThingId"
                  :loading="attachmentsLoading"
                  :rules="rules.required"
                  class="mb-2"
                  @update:model-value="onAttachmentSelected"
                >
                  <template #item="{ props: itemProps, item }">
                    <v-list-item v-bind="itemProps" :title="undefined" :subtitle="undefined">
                      <div class="attachment-option">
                        <div class="attachment-option-preview">
                          <div
                            v-if="isAttachmentPreviewLoading(item.raw.value)"
                            class="text-caption text-medium-emphasis"
                          >
                            Loading...
                          </div>
                          <div
                            v-else-if="getAttachmentPreviewPath(item.raw.value)"
                            class="attachment-option-preview-box"
                          >
                            <svg
                              class="attachment-option-preview-svg"
                              :viewBox="`0 0 ${OPTION_PREVIEW_SVG_WIDTH} ${OPTION_PREVIEW_SVG_HEIGHT}`"
                              preserveAspectRatio="none"
                            >
                              <path
                                class="rating-curve-line"
                                :d="getAttachmentPreviewPath(item.raw.value)"
                                fill="none"
                                vector-effect="non-scaling-stroke"
                                stroke-linejoin="round"
                                stroke-linecap="round"
                              />
                            </svg>
                          </div>
                          <div
                            v-else-if="getAttachmentPreviewError(item.raw.value)"
                            class="text-caption text-error"
                          >
                            Preview unavailable
                          </div>
                          <div v-else class="text-caption text-medium-emphasis">No points</div>
                        </div>
                        <div class="attachment-option-main">
                          <div class="attachment-option-title">{{ item.raw.name }}</div>
                          <div
                            v-if="item.raw.description"
                            class="attachment-option-description"
                          >
                            {{ item.raw.description }}
                          </div>
                        </div>
                      </div>
                    </v-list-item>
                  </template>
                </v-select>

                <div
                  v-if="!attachmentsLoading && !attachmentOptions.length"
                  class="text-caption text-medium-emphasis mb-3"
                >
                  No rating curves found for this site. Switch to "Create new
                  rating curve" to add one.
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
                  color="teal-darken-1"
                  block
                  class="mb-2 text-none"
                  :loading="createSaving"
                  @click="openCreateFilePicker"
                >
                  {{
                    selectedCreateFile ? 'Change CSV file' : 'Choose CSV file *'
                  }}
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
                    :disabled="createSaving"
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
                  v-model="createAttachmentName"
                  label="Rating curve name *"
                  class="mb-3"
                />
                <v-textarea
                  v-model="createAttachmentDescription"
                  label="Description"
                  rows="2"
                  class="mb-3"
                />

                <v-btn
                  color="teal-darken-1"
                  class="text-none"
                  :loading="createSaving"
                  :disabled="!canCreateAttachment"
                  @click="createAttachmentForThing"
                >
                  Create rating curve
                </v-btn>
              </template>

              <v-alert
                v-if="previewError"
                type="warning"
                variant="tonal"
                density="compact"
                class="mb-2"
              >
                {{ previewError }}
              </v-alert>

              <div v-if="selectedAttachment" class="mb-4">
                <div class="d-flex align-center mb-2">
                  <span class="text-subtitle-2">Preview</span>
                </div>

                <div
                  v-if="previewCurvePoints.length"
                  class="rating-curve-preview"
                >
                  <svg
                    class="rating-curve-preview-svg"
                    :viewBox="`0 0 ${PREVIEW_SVG_WIDTH} ${PREVIEW_SVG_HEIGHT}`"
                    preserveAspectRatio="none"
                  >
                    <path
                      v-if="previewSparklinePath"
                      class="rating-curve-line"
                      :d="previewSparklinePath"
                      fill="none"
                      vector-effect="non-scaling-stroke"
                      stroke-linejoin="round"
                      stroke-linecap="round"
                    />
                  </svg>
                </div>
                <div
                  v-if="previewRanges"
                  class="text-caption text-medium-emphasis mt-1"
                >
                  Showing {{ previewCurvePoints.length }} numeric points. x:
                  {{ formatPreviewNumber(previewRanges.xMin) }} to
                  {{ formatPreviewNumber(previewRanges.xMax) }}. y:
                  {{ formatPreviewNumber(previewRanges.yMin) }} to
                  {{ formatPreviewNumber(previewRanges.yMax) }}.
                </div>
                <div v-else class="text-caption text-medium-emphasis">
                  No numeric preview rows available.
                </div>
              </div>
            </template>
          </template>

          <v-alert v-else type="info" variant="tonal" density="compact">
            Select a workspace to choose a Thing and rating curve.
          </v-alert>
        </template>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn-cancel @click="$emit('close')">Cancel</v-btn-cancel>
        <v-btn-primary type="submit">{{
          isEdit ? 'Update' : 'Save'
        }}</v-btn-primary>
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { VForm } from 'vuetify/components'
import hs, {
  RATING_CURVE_ATTACHMENT_TYPE,
  type DataTransformation,
  type Thing,
  type ThingFileAttachment,
  type RatingCurvePreviewRow,
} from '@hydroserver/client'

import { rules } from '@/utils/rules'
import { Snackbar } from '@/utils/notifications'
import {
  getRatingCurveReference,
  setRatingCurveReference,
} from '@/utils/orchestration/ratingCurve'
import {
  parseRatingCurveCsvFile,
  toRatingCurveFileValidationMessage,
} from '@/utils/orchestration/ratingCurveFile'

const props = defineProps<{
  transformation?: DataTransformation
  workspaceId?: string | null
}>()

const emit = defineEmits<{
  (e: 'created', t: DataTransformation): void
  (e: 'updated', t: DataTransformation): void
  (e: 'close'): void
}>()

type ExpressionTransformationDraft = {
  type: 'expression'
  expression: string
}

type RatingCurveTransformationDraft = {
  type: 'rating_curve'
  ratingCurveUrl: string
}

type LocalTransformationDraft =
  | ExpressionTransformationDraft
  | RatingCurveTransformationDraft

const ALLOWED_OPS = ['+', '-', '*', '/', '**', '(', ')']
const isEdit = computed(() => !!props.transformation)
const canSelectThing = computed(() => !!props.workspaceId)

function makeInitial(): LocalTransformationDraft {
  if (props.transformation?.type === 'expression') {
    return {
      type: 'expression',
      expression: props.transformation.expression ?? '',
    }
  }

  if (props.transformation?.type === 'rating_curve') {
    return {
      type: 'rating_curve',
      ratingCurveUrl: getRatingCurveReference(props.transformation),
    }
  }

  return { type: 'expression', expression: '' }
}

const local = ref<LocalTransformationDraft>(makeInitial())
const valid = ref<boolean | null>(null)
const myForm = ref<VForm>()

const things = ref<Thing[]>([])
const thingsLoading = ref(false)
const selectedThingId = ref<string | null>(null)

const attachments = ref<ThingFileAttachment[]>([])
const attachmentsLoading = ref(false)
const selectedAttachmentId = ref<string | number | null>(null)
const ratingCurveInputMode = ref<'existing' | 'create'>('existing')
const createFileInput = ref<HTMLInputElement | null>(null)
const createAttachmentFile = ref<File | null>(null)
const createAttachmentName = ref('')
const createAttachmentDescription = ref('')
const createSaving = ref(false)
const createFileValidationError = ref('')
const createFileValidationPending = ref(false)
let createValidationRunId = 0

const previewRows = ref<RatingCurvePreviewRow[]>([])
const previewError = ref('')
const PREVIEW_SVG_WIDTH = 320
const PREVIEW_SVG_HEIGHT = 120
const OPTION_PREVIEW_SVG_WIDTH = 96
const OPTION_PREVIEW_SVG_HEIGHT = 28
const previewRowsByAttachmentId = ref<Record<string, RatingCurvePreviewRow[]>>(
  {}
)
const previewLoadingByAttachmentId = ref<Record<string, boolean>>({})
const previewErrorByAttachmentId = ref<Record<string, string>>({})

const thingOptions = computed(() =>
  things.value.map((thing) => ({
    title: thing.name,
    value: thing.id,
  }))
)

const attachmentOptions = computed(() =>
  attachments.value.map((attachment) => ({
    title: attachment.description
      ? `${attachment.name} - ${attachment.description}`
      : attachment.name,
    value: attachment.id,
    name: attachment.name,
    description: attachment.description || '',
  }))
)

const selectedAttachment = computed(() =>
  attachments.value.find(
    (attachment) => String(attachment.id) === String(selectedAttachmentId.value)
  )
)
const selectedCreateFile = computed(() => createAttachmentFile.value)
const canCreateAttachment = computed(
  () =>
    !!selectedThingId.value &&
    !!selectedCreateFile.value &&
    !!createAttachmentName.value.trim() &&
    !createSaving.value &&
    !createFileValidationPending.value &&
    !createFileValidationError.value
)

type RatingCurvePoint = { x: number; y: number }
type RatingCurveRange = {
  xMin: number
  xMax: number
  yMin: number
  yMax: number
}

const previewCurvePoints = computed<RatingCurvePoint[]>(() =>
  previewRows.value
    .map((row) => ({
      x: Number(row.inputValue),
      y: Number(row.outputValue),
    }))
    .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
    .sort((a, b) => a.x - b.x)
)

const previewRanges = computed<RatingCurveRange | null>(() => {
  if (!previewCurvePoints.value.length) return null

  let xMin = previewCurvePoints.value[0].x
  let xMax = previewCurvePoints.value[0].x
  let yMin = previewCurvePoints.value[0].y
  let yMax = previewCurvePoints.value[0].y

  for (const point of previewCurvePoints.value) {
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
})

const previewSparklinePath = computed(() =>
  buildSparklinePath(
    previewCurvePoints.value,
    previewRanges.value,
    PREVIEW_SVG_WIDTH,
    PREVIEW_SVG_HEIGHT
  )
)

function extractThingIdFromRatingCurveUrl(reference: string): string | null {
  if (!reference) return null

  try {
    const parsed = new URL(reference, globalThis.location?.origin ?? undefined)
    const pathSegments = parsed.pathname.split('/').filter(Boolean)
    if (pathSegments.length < 5) return null
    if (pathSegments[pathSegments.length - 5] !== 'things') return null
    if (pathSegments[pathSegments.length - 3] !== 'file-attachments')
      return null
    if (pathSegments[pathSegments.length - 1] !== 'download') return null

    return pathSegments[pathSegments.length - 4] ?? null
  } catch {
    return null
  }
}

function clearRatingCurveSelection() {
  ratingCurveInputMode.value = 'existing'
  selectedAttachmentId.value = null
  attachments.value = []
  previewRows.value = []
  previewError.value = ''
  previewRowsByAttachmentId.value = {}
  previewLoadingByAttachmentId.value = {}
  previewErrorByAttachmentId.value = {}
  resetCreateFormState()
  if (local.value.type === 'rating_curve') {
    setRatingCurveReference(local.value, '')
  }
}

function syncSelectedThingWithReference() {
  if (local.value.type !== 'rating_curve') {
    selectedThingId.value = null
    return
  }

  const thingIdFromReference = extractThingIdFromRatingCurveUrl(
    getRatingCurveReference(local.value)
  )

  if (
    thingIdFromReference &&
    things.value.some((thing) => String(thing.id) === thingIdFromReference)
  ) {
    selectedThingId.value = thingIdFromReference
  }
}

function syncSelectedAttachmentWithReference() {
  if (local.value.type !== 'rating_curve') {
    selectedAttachmentId.value = null
    return
  }

  const currentReference = getRatingCurveReference(local.value)
  const selected = attachments.value.find(
    (attachment) => attachment.link === currentReference
  )

  selectedAttachmentId.value = selected?.id ?? null
}

function normalizeRatingCurveAttachments(items: ThingFileAttachment[]) {
  return items
    .filter(
      (attachment) =>
        attachment.fileAttachmentType === RATING_CURVE_ATTACHMENT_TYPE
    )
    .sort((a, b) => a.name.localeCompare(b.name))
}

function resetCreateFormState() {
  createValidationRunId += 1
  createAttachmentFile.value = null
  createAttachmentName.value = ''
  createAttachmentDescription.value = ''
  createFileValidationError.value = ''
  createFileValidationPending.value = false
  if (createFileInput.value) {
    createFileInput.value.value = ''
  }
}

function openCreateFilePicker() {
  createFileInput.value?.click()
}

function onCreateFileSelected(event: Event) {
  const target = event.target as HTMLInputElement | null
  const file = target?.files?.[0] ?? null
  createAttachmentFile.value = file
}

function clearCreateFile() {
  createAttachmentFile.value = null
  if (createFileInput.value) {
    createFileInput.value.value = ''
  }
}

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024) return `${sizeBytes} B`
  if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(1)} KB`
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
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

async function createAttachmentForThing() {
  const thingId = selectedThingId.value
  const file = selectedCreateFile.value
  const trimmedName = createAttachmentName.value.trim()
  if (!thingId || !file || !trimmedName) return

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

  createSaving.value = true
  try {
    const res = await hs.thingFileAttachments.upload(thingId, file, {
      type: RATING_CURVE_ATTACHMENT_TYPE,
      name: trimmedName,
      description: createAttachmentDescription.value.trim() || undefined,
    })

    if (!res.ok || !res.data) {
      Snackbar.error(res.message || 'Unable to create rating curve.')
      return
    }

    attachments.value = normalizeRatingCurveAttachments([
      ...attachments.value,
      res.data,
    ])
    onAttachmentSelected(res.data.id)
    resetCreateFormState()
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to create rating curve.')
  } finally {
    createSaving.value = false
  }
}

async function loadThings() {
  if (!props.workspaceId) {
    things.value = []
    selectedThingId.value = null
    clearRatingCurveSelection()
    return
  }

  thingsLoading.value = true
  try {
    things.value = await hs.things.listAllItems({
      workspace_id: [props.workspaceId],
      order_by: ['name'],
    })

    syncSelectedThingWithReference()

    if (selectedThingId.value) {
      await loadAttachmentsForThing(selectedThingId.value)
    }
  } catch (error: any) {
    Snackbar.error(error?.message || 'Unable to load Things.')
  } finally {
    thingsLoading.value = false
  }
}

async function loadAttachmentsForThing(thingId: string) {
  attachmentsLoading.value = true
  previewRows.value = []
  previewError.value = ''
  previewRowsByAttachmentId.value = {}
  previewLoadingByAttachmentId.value = {}
  previewErrorByAttachmentId.value = {}

  try {
    const items = await hs.thingFileAttachments.listItems(thingId, {
      type: RATING_CURVE_ATTACHMENT_TYPE,
    })
    attachments.value = normalizeRatingCurveAttachments(items)
    for (const attachment of attachments.value) {
      void loadAttachmentPreview(attachment)
    }
    syncSelectedAttachmentWithReference()
  } catch (error: any) {
    attachments.value = []
    selectedAttachmentId.value = null
    Snackbar.error(error?.message || 'Unable to load rating curves.')
  } finally {
    attachmentsLoading.value = false
  }
}

function onThingSelected(thingId: string | null) {
  selectedThingId.value = thingId
  clearRatingCurveSelection()

  if (!thingId || local.value.type !== 'rating_curve') return
  void loadAttachmentsForThing(thingId)
}

function onAttachmentSelected(attachmentId: string | number | null) {
  selectedAttachmentId.value = attachmentId

  if (local.value.type !== 'rating_curve') return
  const attachment = attachments.value.find(
    (item) => String(item.id) === String(attachmentId)
  )

  if (!attachment) {
    setRatingCurveReference(local.value, '')
    previewRows.value = []
    previewError.value = ''
    return
  }

  setRatingCurveReference(local.value, attachment.link)
  void loadPreviewForAttachment(attachment)
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

function formatPreviewNumber(value: number) {
  if (!Number.isFinite(value)) return '-'
  const absValue = Math.abs(value)
  if ((absValue >= 1000 || absValue < 0.01) && absValue !== 0) {
    return value.toExponential(2)
  }
  return value.toFixed(3).replace(/\.?0+$/, '')
}

async function loadPreviewForAttachment(attachment: ThingFileAttachment) {
  previewError.value = ''
  const cacheKey = String(attachment.id)
  const cachedRows = previewRowsByAttachmentId.value[cacheKey]
  if (cachedRows?.length) {
    previewRows.value = cachedRows
    return
  }
  try {
    const res = await hs.thingFileAttachments.fetchRatingCurvePreview(
      attachment.link,
      12
    )
    if (!res.ok) {
      previewRows.value = []
      previewError.value = res.message || 'Unable to load rating curve preview.'
      previewErrorByAttachmentId.value[cacheKey] = previewError.value
      return
    }
    previewRows.value = res.data
    previewRowsByAttachmentId.value[cacheKey] = res.data
    previewErrorByAttachmentId.value[cacheKey] = ''
  } catch (error: any) {
    previewRows.value = []
    previewError.value =
      error?.message || 'Unable to load rating curve preview.'
    previewErrorByAttachmentId.value[cacheKey] = previewError.value
  }
}

async function loadAttachmentPreview(attachment: ThingFileAttachment) {
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

function isAttachmentPreviewLoading(attachmentId: string | number) {
  return !!previewLoadingByAttachmentId.value[String(attachmentId)]
}

function getAttachmentPreviewError(attachmentId: string | number) {
  return previewErrorByAttachmentId.value[String(attachmentId)] ?? ''
}

function getAttachmentPreviewRows(
  attachmentId: string | number
): RatingCurvePreviewRow[] {
  return previewRowsByAttachmentId.value[String(attachmentId)] ?? []
}

function getAttachmentPreviewPath(attachmentId: string | number): string {
  const points = getAttachmentPreviewRows(attachmentId)
    .map((row) => ({
      x: Number(row.inputValue),
      y: Number(row.outputValue),
    }))
    .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
    .sort((a, b) => a.x - b.x)

  let xMin = points[0]?.x
  let xMax = points[0]?.x
  let yMin = points[0]?.y
  let yMax = points[0]?.y

  if (
    xMin === undefined ||
    xMax === undefined ||
    yMin === undefined ||
    yMax === undefined
  ) {
    return ''
  }

  for (const point of points) {
    if (point.x < xMin) xMin = point.x
    if (point.x > xMax) xMax = point.x
    if (point.y < yMin) yMin = point.y
    if (point.y > yMax) yMax = point.y
  }

  if (xMin === xMax) {
    const delta = Math.abs(xMin || 1) * 0.1
    xMin -= delta
    xMax += delta
  }
  if (yMin === yMax) {
    const delta = Math.abs(yMin || 1) * 0.1
    yMin -= delta
    yMax += delta
  }

  return buildSparklinePath(
    points,
    { xMin, xMax, yMin, yMax },
    OPTION_PREVIEW_SVG_WIDTH,
    OPTION_PREVIEW_SVG_HEIGHT
  )
}

async function onSubmit() {
  await myForm.value?.validate()
  if (!valid.value) return

  if (local.value.type === 'rating_curve') {
    if (!selectedThingId.value) {
      Snackbar.error(
        'Select a Thing before saving this rating curve transformation.'
      )
      return
    }

    if (!selectedAttachment.value) {
      Snackbar.error(
        ratingCurveInputMode.value === 'create'
          ? 'Create and select a new rating curve before saving this transformation.'
          : 'Select a rating curve before saving this transformation.'
      )
      return
    }

    setRatingCurveReference(local.value, selectedAttachment.value.link)
    delete (local.value as any).expression
  } else {
    delete (local.value as any).ratingCurveUrl
  }

  isEdit.value
    ? emit('updated', local.value as unknown as DataTransformation)
    : emit('created', local.value as unknown as DataTransformation)

  emit('close')
}

watch(
  () => props.workspaceId,
  () => {
    loadThings()
  }
)

watch(
  () => props.transformation,
  () => {
    local.value = makeInitial()
    ratingCurveInputMode.value = 'existing'
    selectedThingId.value = null
    selectedAttachmentId.value = null
    attachments.value = []
    previewRows.value = []
    previewError.value = ''
    resetCreateFormState()
    loadThings()
  }
)

watch(selectedAttachment, (attachment) => {
  if (!attachment || local.value.type !== 'rating_curve') return
  if (
    getRatingCurveReference(local.value) === attachment.link &&
    previewRows.value.length
  ) {
    return
  }
  void loadPreviewForAttachment(attachment)
})

watch(ratingCurveInputMode, (mode) => {
  if (local.value.type !== 'rating_curve') return
  if (!selectedThingId.value) return
  if (mode !== 'create') return

  onAttachmentSelected(null)
})

watch(selectedCreateFile, (file) => {
  if (!file) {
    createValidationRunId += 1
    createFileValidationError.value = ''
    createFileValidationPending.value = false
    return
  }

  if (!createAttachmentName.value.trim()) {
    createAttachmentName.value = file.name
  }

  void validateCreateFile(file)
})

onMounted(() => {
  loadThings()
})

type Rule = (v: any) => true | string

const exprContainsX: Rule = (v) =>
  /x/.test((v ?? '') as string) || "Expression must contain input variable 'x'"

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
    if (ch === 'x') {
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

    return "Only numbers, spaces, 'x', and + - * / ** ( ) are allowed"
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
      if (depth < 0) return `Unmatched ')' at position ${i + 1}`
    }
  }
  return depth === 0
    ? true
    : `Missing ${depth} closing ')'${depth > 1 ? 's' : ''}`
}
</script>

<style scoped>
.rating-curve-preview {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  height: 120px;
  width: 100%;
  max-width: 360px;
}

.rating-curve-preview-svg {
  height: 100%;
  width: 100%;
}

.rating-curve-line {
  stroke: #00796b;
  stroke-width: 2;
}

.attachment-option {
  align-items: center;
  display: flex;
  gap: 0.625rem;
  width: 100%;
}

.attachment-option-preview {
  align-items: center;
  display: flex;
  justify-content: center;
  min-width: 6.25rem;
}

.attachment-option-preview-box {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  height: 1.75rem;
  width: 6rem;
}

.attachment-option-preview-svg {
  height: 100%;
  width: 100%;
}

.attachment-option-main {
  min-width: 0;
}

.attachment-option-title {
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1.2;
}

.attachment-option-description {
  color: rgba(0, 0, 0, 0.6);
  font-size: 0.75rem;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
