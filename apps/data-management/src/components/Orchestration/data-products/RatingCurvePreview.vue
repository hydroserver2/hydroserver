<template>
  <div class="rating-curve-preview-panel">
    <div class="rating-curve-preview-header mb-3">
      <div class="rating-curve-preview-title">
        <div class="text-subtitle-2 text-truncate">
          {{ ratingCurve.name }}
        </div>
        <div
          v-if="ratingCurve.description"
          class="text-caption text-medium-emphasis"
        >
          {{ ratingCurve.description }}
        </div>
      </div>
      <div class="rating-curve-preview-chips">
        <v-chip size="small" variant="tonal" color="teal-darken-1">
          {{ fittingMethodLabel }}
        </v-chip>
        <v-chip size="small" variant="tonal">
          {{ ratingCurvePoints.length }}
          point{{ ratingCurvePoints.length === 1 ? '' : 's' }}
        </v-chip>
      </div>
    </div>

    <div v-if="previewCurvePoints.length" class="rating-curve-preview">
      <svg
        class="rating-curve-preview-svg"
        :viewBox="`0 0 ${PREVIEW_SVG_WIDTH} ${PREVIEW_SVG_HEIGHT}`"
        preserveAspectRatio="none"
      >
        <path
          v-if="sparklinePath"
          class="rating-curve-line"
          :d="sparklinePath"
          fill="none"
          vector-effect="non-scaling-stroke"
          stroke-linejoin="round"
          stroke-linecap="round"
        />
      </svg>
    </div>

    <div v-if="previewRanges" class="text-caption text-medium-emphasis mt-2">
      x: {{ formatPreviewNumber(previewRanges.xMin) }} to
      {{ formatPreviewNumber(previewRanges.xMax) }}. y:
      {{ formatPreviewNumber(previewRanges.yMin) }} to
      {{ formatPreviewNumber(previewRanges.yMax) }}.
    </div>
    <div v-else class="text-caption text-medium-emphasis">
      No numeric points available for preview.
    </div>

    <v-table
      v-if="visiblePreviewRows.length"
      density="compact"
      class="rating-curve-preview-table mt-3"
    >
      <thead>
        <tr>
          <th>Input</th>
          <th>Output</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(point, index) in visiblePreviewRows"
          :key="`${point.x}-${point.y}-${index}`"
        >
          <td>{{ formatPreviewNumber(point.x) }}</td>
          <td>{{ formatPreviewNumber(point.y) }}</td>
        </tr>
      </tbody>
    </v-table>

    <div
      v-if="visiblePreviewRows.length"
      class="rating-curve-preview-footer mt-1"
    >
      <span class="text-caption text-medium-emphasis">
        {{ tableSummary }}
      </span>
      <v-btn
        v-if="hasMoreRows"
        variant="text"
        size="small"
        color="teal-darken-1"
        class="text-none"
        @click="showMoreRows"
      >
        See more
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { RatingCurve } from '@hydroserver/client'

const props = withDefaults(
  defineProps<{
    ratingCurve: RatingCurve
    initialRowLimit?: number
    rowIncrement?: number
  }>(),
  {
    initialRowLimit: 6,
    rowIncrement: 25,
  }
)

const PREVIEW_SVG_WIDTH = 360
const PREVIEW_SVG_HEIGHT = 120

type PreviewPoint = { x: number; y: number }

type PreviewRange = {
  xMin: number
  xMax: number
  yMin: number
  yMax: number
}

const visibleRowLimit = ref(props.initialRowLimit)

const fittingMethodOptions = [
  { title: 'Linear', value: 'linear' },
  { title: 'Power law', value: 'power_law' },
]

const ratingCurvePoints = computed(() => props.ratingCurve.points ?? [])

const previewCurvePoints = computed<PreviewPoint[]>(() =>
  ratingCurvePoints.value
    .map(([inputValue, outputValue]) => ({
      x: Number(inputValue),
      y: Number(outputValue),
    }))
    .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
    .sort((a, b) => a.x - b.x)
)

const visiblePreviewRows = computed(() =>
  previewCurvePoints.value.slice(0, visibleRowLimit.value)
)

const hasMoreRows = computed(
  () => visiblePreviewRows.value.length < previewCurvePoints.value.length
)

const previewRanges = computed<PreviewRange | null>(() =>
  computePreviewRange(previewCurvePoints.value)
)

const sparklinePath = computed(() =>
  buildSparklinePath(
    previewCurvePoints.value,
    previewRanges.value,
    PREVIEW_SVG_WIDTH,
    PREVIEW_SVG_HEIGHT
  )
)

const fittingMethodLabel = computed(
  () =>
    fittingMethodOptions.find(
      (item) => item.value === props.ratingCurve.fittingMethod
    )?.title ?? ''
)

const tableSummary = computed(() => {
  const visibleCount = visiblePreviewRows.value.length
  const totalCount = previewCurvePoints.value.length
  if (visibleCount < totalCount) {
    return `Showing first ${visibleCount} of ${totalCount} datapoints.`
  }
  return `Showing all ${totalCount} datapoints.`
})

function showMoreRows() {
  visibleRowLimit.value = Math.min(
    previewCurvePoints.value.length,
    visibleRowLimit.value + props.rowIncrement
  )
}

function formatPreviewNumber(value: number) {
  if (!Number.isFinite(value)) return '-'
  const absValue = Math.abs(value)
  if ((absValue >= 1000 || absValue < 0.01) && absValue !== 0) {
    return value.toExponential(2)
  }
  return value.toFixed(3).replace(/\.?0+$/, '')
}

function computePreviewRange(points: PreviewPoint[]): PreviewRange | null {
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
  points: PreviewPoint[],
  ranges: PreviewRange | null,
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

watch(
  () => props.ratingCurve.id,
  () => {
    visibleRowLimit.value = props.initialRowLimit
  }
)

watch(
  () => props.initialRowLimit,
  (limit) => {
    visibleRowLimit.value = limit
  }
)
</script>

<style scoped>
.rating-curve-preview-panel {
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  padding: 0.75rem;
}

.rating-curve-preview-header {
  align-items: flex-start;
  display: flex;
  gap: 0.75rem;
}

.rating-curve-preview-title {
  min-width: 0;
}

.rating-curve-preview-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  justify-content: flex-end;
  margin-left: auto;
}

.rating-curve-preview {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  height: 120px;
  width: 100%;
}

.rating-curve-preview-svg {
  height: 100%;
  width: 100%;
}

.rating-curve-line {
  stroke: #00796b;
  stroke-width: 2;
}

.rating-curve-preview-table {
  max-width: 24rem;
}

.rating-curve-preview-table th,
.rating-curve-preview-table td {
  white-space: nowrap;
}

.rating-curve-preview-footer {
  align-items: center;
  display: flex;
  gap: 0.5rem;
  justify-content: space-between;
  max-width: 24rem;
}
</style>
