<template>
  <v-progress-linear v-if="loading" color="secondary" indeterminate />
  <div v-else-if="!loading && canShowSparkline">
    <div class="w-[300px] max-w-full max-[600px]:w-full">
      <div class="mb-1 text-body-3 font-weight-light opacity-70">
        Sparkline is showing most recent {{ validObservations.length }}
        values
      </div>
      <div
        class="h-[100px] w-full cursor-pointer"
        :style="sparklineContainerStyle"
        @click="handleEmit"
      >
        <svg
          v-if="sparklinePaths.line.length"
          class="h-full w-full"
          :viewBox="`0 0 ${SPARKLINE_WIDTH} ${SPARKLINE_HEIGHT}`"
          preserveAspectRatio="none"
        >
          <path
            v-for="(d, index) in sparklinePaths.area"
            :key="`area-${index}`"
            :d="d"
            :fill="sparklineColors.fill"
            stroke="none"
          />
          <path
            v-for="(d, index) in sparklinePaths.line"
            :key="`line-${index}`"
            :d="d"
            :stroke="sparklineColors.line"
            stroke-width="1"
            fill="none"
            vector-effect="non-scaling-stroke"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
        </svg>
      </div>
    </div>
  </div>
  <div v-else>No observations</div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount, watch } from 'vue'
import { PropType } from 'vue'
import { Datastream, TimeSpacingUnit } from '@hydroserver/client'
import {
  preProcessData,
  subtractHours,
  ObservationArray,
} from '@/utils/observationsUtils'
import { useObservationStore } from '@/store/observations'

const { fetchObservationsInRange } = useObservationStore()

const props = defineProps({
  datastream: {
    type: Object as PropType<Datastream>,
    required: true,
  },
  unitName: String,
})

type LatestValuePayload = { text: string; showUnit: boolean; isBad: boolean }

const emit = defineEmits<{
  (e: 'openChart'): void
  (e: 'latest-value', value: LatestValuePayload): void
}>()
const handleEmit = () => {
  emit('openChart')
}

const sparklineObservations = ref<ObservationArray>([])
const loading = ref(true)

const SPARKLINE_WIDTH = 300
const SPARKLINE_HEIGHT = 100

type SparklinePoint = { x: number; y: number }
type SparklineSegment = SparklinePoint[]

const processedObs = computed(() =>
  preProcessData(sparklineObservations.value, props.datastream)
)

const getNumericValue = (value: unknown) => {
  const numericValue = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(numericValue) ? numericValue : null
}

const validObservations = computed(() =>
  processedObs.value.filter((point) => getNumericValue(point.value) !== null)
)

const sparklineSegments = computed<SparklineSegment[]>(() => {
  const segments: SparklineSegment[] = []
  let current: SparklineSegment = []

  processedObs.value.forEach((point) => {
    const numericValue = getNumericValue(point.value)
    if (numericValue === null) {
      if (current.length) {
        segments.push(current)
        current = []
      }
      return
    }

    current.push({
      x: point.date.getTime(),
      y: numericValue,
    })
  })

  if (current.length) {
    segments.push(current)
  }

  return segments
})

const buildSparklinePaths = (
  segments: SparklineSegment[]
): { line: string[]; area: string[] } => {
  const points = segments.flat()
  if (!points.length) {
    return { line: [], area: [] }
  }

  let xMin = points[0].x
  let xMax = points[0].x
  let yMinData = points[0].y
  let yMaxData = points[0].y

  points.forEach((point) => {
    if (point.x < xMin) xMin = point.x
    if (point.x > xMax) xMax = point.x
    if (point.y < yMinData) yMinData = point.y
    if (point.y > yMaxData) yMaxData = point.y
  })

  if (xMin === xMax) {
    xMin -= 1
    xMax += 1
  }

  let yMin = yMinData
  let yMax = yMaxData
  if (yMin === yMax) {
    yMin -= 1
    yMax += 1
  }

  const scaleX = (value: number) =>
    ((value - xMin) / (xMax - xMin)) * SPARKLINE_WIDTH
  const scaleY = (value: number) =>
    SPARKLINE_HEIGHT - ((value - yMin) / (yMax - yMin)) * SPARKLINE_HEIGHT
  const clamp = (value: number, min: number, max: number) =>
    Math.min(Math.max(value, min), max)
  const zeroY = scaleY(clamp(0, yMin, yMax))

  const linePaths: string[] = []
  const areaPaths: string[] = []

  segments.forEach((segment) => {
    if (!segment.length) return
    const line = segment
      .map((point, index) => {
        const x = scaleX(point.x)
        const y = scaleY(point.y)
        return `${index === 0 ? 'M' : 'L'}${x} ${y}`
      })
      .join(' ')

    linePaths.push(line)

    if (segment.length < 2) return

    const firstX = scaleX(segment[0].x)
    const lastX = scaleX(segment[segment.length - 1].x)
    const area = line + ` L${lastX} ${zeroY}` + ` L${firstX} ${zeroY}` + ' Z'
    areaPaths.push(area)
  })

  return { line: linePaths, area: areaPaths }
}

const sparklinePaths = computed(() =>
  buildSparklinePaths(sparklineSegments.value)
)

const normalizeNoDataValue = (value: unknown) => {
  if (value === null || value === undefined) return null
  if (typeof value === 'number') return value
  if (typeof value === 'string' && value.trim() !== '') {
    const numeric = Number(value)
    return Number.isFinite(numeric) ? numeric : value
  }
  return value
}

const isNoDataValue = (value: unknown) => {
  const noDataValue = normalizeNoDataValue(props.datastream.noDataValue)
  if (noDataValue === null || noDataValue === undefined) return false
  if (typeof noDataValue === 'number') {
    const numericValue = getNumericValue(value)
    return numericValue !== null && numericValue === noDataValue
  }
  return String(value) === String(noDataValue)
}

const latestRawObservationValue = computed<unknown>(() => {
  const arr = sparklineObservations.value
  for (let i = arr.length - 1; i >= 0; i -= 1) {
    const rawValue = arr[i]?.[1] as unknown
    if (rawValue !== undefined) {
      return rawValue
    }
  }
  return null
})

const mostRecentDataValue = computed<LatestValuePayload>(() => {
  if (!sparklineObservations.value.length) {
    return { text: 'No observations', showUnit: false, isBad: false }
  }
  const rawValue = latestRawObservationValue.value
  if (rawValue === undefined) {
    return { text: 'No observations', showUnit: false, isBad: false }
  }
  if (rawValue === null) {
    return { text: 'null', showUnit: false, isBad: true }
  }
  if (typeof rawValue === 'string') {
    const trimmed = rawValue.trim()
    if (trimmed === '') {
      return { text: 'empty', showUnit: false, isBad: true }
    }
    if (trimmed.toLowerCase() === 'nan') {
      return { text: 'NaN', showUnit: false, isBad: true }
    }
  }
  if (typeof rawValue === 'number' && Number.isNaN(rawValue)) {
    return { text: 'NaN', showUnit: false, isBad: true }
  }
  if (isNoDataValue(rawValue)) {
    const noDataValue = props.datastream.noDataValue
    return {
      text:
        noDataValue === null || noDataValue === undefined
          ? 'No data'
          : String(noDataValue),
      showUnit: false,
      isBad: true,
    }
  }
  const numericValue = getNumericValue(rawValue)
  if (numericValue !== null) {
    return { text: formatNumber(numericValue), showUnit: true, isBad: false }
  }
  return { text: 'No observations', showUnit: false, isBad: false }
})

const sparklineColors = computed(() =>
  isStale(props.datastream.phenomenonEndTime)
    ? { line: '#9E9E9E', fill: '#EEEEEE', border: '#BDBDBD' }
    : { line: '#4CAF50', fill: '#E8F5E9', border: '#BDBDBD' }
)

const sparklineContainerStyle = computed(() => ({
  height: '100px',
  width: '100%',
  border: `2px solid ${sparklineColors.value.border}`,
  borderRadius: '4px',
  overflow: 'hidden',
}))

const hasValidSparklineData = computed(() => validObservations.value.length > 0)
const canShowSparkline = computed(
  () =>
    Boolean(props.datastream.phenomenonEndTime) &&
    sparklineObservations.value.length > 0 &&
    hasValidSparklineData.value
)

function isStale(timestamp: string | null | undefined) {
  if (!timestamp) return true
  let endTime = new Date(timestamp)
  let seventyTwoHoursAgo = new Date(Date.now() - 72 * 60 * 60 * 1000)
  return endTime < seventyTwoHoursAgo
}

const convertToMilliseconds = (
  amount: number,
  unit: TimeSpacingUnit
): number => {
  switch (unit) {
    case 'seconds':
      return amount * 1000
    case 'minutes':
      return amount * 60 * 1000
    case 'hours':
      return amount * 60 * 60 * 1000
    case 'days':
      return amount * 24 * 60 * 60 * 1000
  }
}

const fetchSparklineObservations = async (ds: Datastream) => {
  const {
    phenomenonEndTime: endTime,
    intendedTimeSpacing,
    intendedTimeSpacingUnit,
  } = ds

  if (!endTime) return null

  let beginTime: string
  if (intendedTimeSpacing && intendedTimeSpacingUnit) {
    const spacingMs = convertToMilliseconds(
      intendedTimeSpacing,
      intendedTimeSpacingUnit
    )

    const timeIntervalCount =
      spacingMs >= 86_400_000
        ? 30 // daily data should display 30 values
        : spacingMs >= 3_600_000
        ? 50 // hourly data should display 50 values
        : 200 // sub-hourly data should display 200 values

    const observationCount = timeIntervalCount - 1
    const totalDurationMs = spacingMs * observationCount
    beginTime = new Date(
      new Date(endTime).getTime() - totalDurationMs
    ).toISOString()
  } else {
    beginTime = subtractHours(endTime, 72)
  }

  return fetchObservationsInRange(ds, beginTime, endTime).catch((error) => {
    console.error('Failed to fetch observations:', error)
    return null
  })
}

const formatNumber = (value: string | number): string => {
  const numericValue = typeof value === 'number' ? value : Number(value)
  if (Number.isFinite(numericValue)) {
    const formatter = new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })
    return formatter.format(numericValue)
  }

  return ''
}

onMounted(async () => {
  sparklineObservations.value =
    (await fetchSparklineObservations(props.datastream)) || []
  loading.value = false
})

watch(
  mostRecentDataValue,
  (value) => {
    emit('latest-value', value)
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  // No cleanup required for SVG-based sparklines.
})
</script>
