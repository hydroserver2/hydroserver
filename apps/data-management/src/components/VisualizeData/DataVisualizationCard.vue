<template>
  <v-card class="elevation-2 plot-card" :loading="updating">
    <template v-slot:loader="{ isActive }">
      <v-progress-linear color="primary" :active="isActive" indeterminate />
    </template>

    <div v-if="showNoDataWarning" class="plot-warning">
      <v-alert type="warning" density="comfortable" variant="tonal">
        No data available for the selected date range. Please select a
        different date range to re-plot.
      </v-alert>
    </div>

    <keep-alive>
      <v-card-text
        v-if="canPlot"
        :style="{ height: '100%' }"
        class="plot-shell"
      >
        <div class="plot-body">
          <div class="plot-rail">
            <v-tooltip bottom :openDelay="0">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="mdiChartLine"
                  class="plot-rail-btn"
                  :class="{ 'plot-rail-btn--active': viewMode === 'plot' }"
                  variant="text"
                  size="small"
                  block
                  rounded="0"
                  @click="viewMode = 'plot'"
                />
              </template>
              Plot
            </v-tooltip>
            <v-tooltip bottom :openDelay="0">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  :icon="mdiSigma"
                  class="plot-rail-btn"
                  :class="{ 'plot-rail-btn--active': viewMode === 'summary' }"
                  variant="text"
                  size="small"
                  block
                  rounded="0"
                  @click="viewMode = 'summary'"
                />
              </template>
              Summary statistics
            </v-tooltip>
          </div>
          <div class="plot-panel">
            <v-window v-model="viewMode" class="plot-window" :touch="false">
              <v-window-item value="plot" class="plot-window-item">
                <div class="plot-plot-area">
                  <div v-if="showLargeSeriesDisclaimer" class="plot-disclaimer">
                    <v-tooltip
                      location="bottom"
                      :open-delay="0"
                      content-class="pa-0 ma-0 bg-transparent"
                    >
                      <template v-slot:activator="{ props }">
                        <div class="plot-disclaimer-text" v-bind="props">
                          *Large data mode
                        </div>
                      </template>
                      <v-card
                        elevation="2"
                        rounded="lg"
                        class="plot-disclaimer-card"
                      >
                        <v-card-title class="px-4 py-2 text-subtitle-1">
                          Large data mode
                        </v-card-title>
                        <v-divider />
                        <v-card-text class="px-4 py-2 text-body-2">
                          Tooltips and markers are disabled to keep the plot
                          responsive. This happens when visible points exceed
                          {{ largeSeriesVisibleThreshold }} or total points
                          exceed {{ largeSeriesTotalThreshold }}.
                        </v-card-text>
                      </v-card>
                    </v-tooltip>
                  </div>
                  <div ref="plotContainer" class="plotly-chart" />
                </div>
                <div class="plot-toolbar">
                  <DataVisTimeFilters @copy-state="handleCopyState" />
                </div>
              </v-window-item>
              <v-window-item value="summary" class="plot-window-item">
                <SummaryStatisticsTable />
              </v-window-item>
            </v-window>
          </div>
        </div>
      </v-card-text>
    </keep-alive>

    <div v-if="showInstructions && viewMode === 'plot'" class="plot-empty">
      <v-card-text>
        <div class="plot-empty__title">Visualize data</div>
        <v-timeline align="start" density="compact">
          <v-timeline-item size="x-small" dot-color="primary">
            <div>
              <strong> Filter: </strong>
            </div>
            <div>
              Filter the datastream table items with the filter drawer on the
              left and the search bar on the top of the datastreams table.
            </div>
          </v-timeline-item>
          <v-timeline-item size="x-small" dot-color="secondary">
            <div>
              <strong> Adjust the time range: </strong>
            </div>
            <div>
              Adjust the time range to cover the desired period you wish to
              observe.
            </div>
          </v-timeline-item>
          <v-timeline-item size="x-small" dot-color="blue-grey">
            <div>
              <strong> Select up to 5 datastreams: </strong>
            </div>
            <div>
              The plot allows up to 5 datastreams to be shown at once. If two
              datastreams share the same observed property and unit, they'll
              share a y-axis.
            </div>
          </v-timeline-item>
        </v-timeline>
      </v-card-text>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import SummaryStatisticsTable from './SummaryStatisticsTable.vue'
import DataVisTimeFilters from './DataVisTimeFilters.vue'
import { useDataVisStore } from '@/store/dataVisualization'
import { ref, watch, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import { debounce } from 'lodash-es'
import { getXRangeBounds } from '@/utils/plotting/plotly'
import { mdiChartLine, mdiSigma } from '@mdi/js'

const emit = defineEmits(['copy-state'])

const props = defineProps({
  cardHeight: { type: Number, required: true },
})

const { onDateBtnClick } = useDataVisStore()
const {
  showSummaryStatistics,
  dataZoomStart,
  dataZoomEnd,
  graphSeriesArray,
  plotlyOptions,
  loadingStates,
  plottedDatastreams,
  beginDate,
  endDate,
  xAxisRange,
  yAxisRanges,
} = storeToRefs(useDataVisStore())

const plotContainer = ref<HTMLDivElement | null>(null)
const plotlyRef = ref<(HTMLDivElement & { [key: string]: any }) | null>(null)
const handlersAttached = ref(false)
let plotlyApi: any | null = null

const ensurePlotly = async () => {
  if (plotlyApi) return plotlyApi
  const PlotlyModule = await import('plotly.js-dist')
  plotlyApi = (PlotlyModule as any).default ?? PlotlyModule
  return plotlyApi
}

const parseNumericAxisValue = (value: unknown) => {
  const parsed = typeof value === 'string' ? Number(value) : value
  return typeof parsed === 'number' && Number.isFinite(parsed) ? parsed : null
}

const parseDateAxisValue = (value: unknown) => {
  if (value === null || value === undefined) return null
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Date.parse(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

const LARGE_SERIES_VISIBLE_THRESHOLD = 50_000
const LARGE_SERIES_TOTAL_THRESHOLD = 150_000
const DEFAULT_HOVER_TEMPLATE = '<b>%{y}</b><extra></extra>'
const currentHoverInfo = ref<'y' | 'skip'>('y')
const isLargeSeriesMode = ref(false)
const defaultTraceModes = ref<string[]>([])
const defaultMarkerSizes = ref<number[]>([])
const defaultHoverMode = ref<'x' | false>('x')
const lastStyledTraceCount = ref(0)
const showLargeSeriesDisclaimer = computed(() => isLargeSeriesMode.value)
const largeSeriesVisibleThreshold = computed(() =>
  LARGE_SERIES_VISIBLE_THRESHOLD.toLocaleString()
)
const largeSeriesTotalThreshold = computed(() =>
  LARGE_SERIES_TOTAL_THRESHOLD.toLocaleString()
)

const toNumeric = (value: unknown) => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Date.parse(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

const findFirstGreaterOrEqual = (arr: ArrayLike<unknown>, value: number) => {
  let low = 0
  let high = arr.length
  while (low < high) {
    const mid = Math.floor((low + high) / 2)
    const midValue = toNumeric(arr[mid])
    if (midValue === null || midValue < value) {
      low = mid + 1
    } else {
      high = mid
    }
  }
  return low
}

const asArrayLike = (value: unknown): ArrayLike<unknown> | null => {
  if (Array.isArray(value)) return value
  if (ArrayBuffer.isView(value)) return value as unknown as ArrayLike<unknown>
  return null
}

const getVisiblePointCount = (rangeStart: number, rangeEnd: number) => {
  if (!plotlyRef.value) return 0
  let visiblePoints = 0
  const traces = plotlyRef.value.data || []
  traces.forEach((trace: any) => {
    const xArray = asArrayLike(trace?.x)
    if (!xArray) return
    const startIdx = findFirstGreaterOrEqual(xArray, rangeStart)
    const endIdx = findFirstGreaterOrEqual(xArray, rangeEnd)
    visiblePoints += Math.max(0, endIdx - startIdx)
  })
  return visiblePoints
}

const getTotalPointCount = () => {
  if (!plotlyRef.value) return 0
  let totalPoints = 0
  const traces = plotlyRef.value.data || []
  traces.forEach((trace: any) => {
    const xArray = asArrayLike(trace?.x)
    if (!xArray) return
    totalPoints += xArray.length
  })
  return totalPoints
}

const syncDefaultTraceStyles = () => {
  const traces = plotlyOptions.value?.traces ?? []
  defaultTraceModes.value = traces.map(
    (trace: any) => trace?.mode ?? 'lines+markers'
  )
  defaultMarkerSizes.value = traces.map((trace: any) => {
    const size = trace?.marker?.size
    return typeof size === 'number' ? size : 6
  })
  const hoverMode = plotlyOptions.value?.layout?.hovermode
  defaultHoverMode.value = hoverMode === false ? false : 'x'
}

const normalizeTraceArray = <T>(values: T[], length: number, fallback: T) => {
  if (values.length === length) return values
  const next = new Array(length).fill(fallback) as T[]
  for (let i = 0; i < Math.min(values.length, length); i += 1) {
    next[i] = values[i]
  }
  return next
}

const applyLargeSeriesMode = async (visiblePoints: number) => {
  if (!plotlyRef.value || !plotlyApi) return
  const totalPoints = getTotalPointCount()
  const forceLargeMode = totalPoints > LARGE_SERIES_TOTAL_THRESHOLD
  const shouldEnable =
    visiblePoints > LARGE_SERIES_VISIBLE_THRESHOLD || forceLargeMode

  const traceCount = plotlyRef.value.data?.length ?? 0
  if (!traceCount) return
  const needsEnforcement =
    shouldEnable &&
    plotlyRef.value.data?.some((trace: any) => {
      if (trace?.mode !== 'lines') return true
      const size = trace?.marker?.size
      return typeof size === 'number' ? size !== 0 : false
    })
  const nextModes = shouldEnable
    ? new Array(traceCount).fill('lines')
    : normalizeTraceArray(defaultTraceModes.value, traceCount, 'lines+markers')
  const nextMarkerSizes = shouldEnable
    ? new Array(traceCount).fill(0)
    : normalizeTraceArray(defaultMarkerSizes.value, traceCount, 6)
  const nextHoverInfo: 'y' | 'skip' = shouldEnable ? 'skip' : 'y'
  const nextHoverMode = forceLargeMode ? false : defaultHoverMode.value
  const traceCountChanged = traceCount !== lastStyledTraceCount.value

  if (
    traceCountChanged ||
    needsEnforcement ||
    shouldEnable !== isLargeSeriesMode.value ||
    nextHoverInfo !== currentHoverInfo.value
  ) {
    const nextTemplate = nextHoverInfo === 'skip' ? '' : DEFAULT_HOVER_TEMPLATE
    await plotlyApi.restyle(plotlyRef.value, {
      mode: nextModes,
      'marker.size': nextMarkerSizes,
      hoverinfo: nextHoverInfo,
      hovertemplate: nextTemplate,
    })
    isLargeSeriesMode.value = shouldEnable
    currentHoverInfo.value = nextHoverInfo
    lastStyledTraceCount.value = traceCount
  }

  if (
    plotlyRef.value &&
    plotlyApi &&
    plotlyRef.value.layout?.hovermode !== nextHoverMode
  ) {
    await plotlyApi.relayout(plotlyRef.value, { hovermode: nextHoverMode })
  }
}

const applyLargeSeriesModeForCurrentRange = () => {
  if (!plotlyRef.value) return
  const layout = plotlyRef.value._fullLayout || plotlyRef.value.layout
  const range = layout?.xaxis?.range
  if (Array.isArray(range) && range.length === 2) {
    const start = parseDateAxisValue(range[0])
    const end = parseDateAxisValue(range[1])
    if (start === null || end === null) return
    const visiblePoints = getVisiblePointCount(start, end)
    applyLargeSeriesMode(visiblePoints)
    return
  }
  const bounds =
    plotlyOptions.value?.xRange || getXRangeBounds(graphSeriesArray.value)
  if (bounds) {
    const visiblePoints = getVisiblePointCount(bounds.min, bounds.max)
    applyLargeSeriesMode(visiblePoints)
    return
  }
  const totalPoints = getTotalPointCount()
  if (totalPoints) {
    applyLargeSeriesMode(totalPoints)
  }
}

const captureAxisRangesFromPlotly = () => {
  if (!plotlyRef.value) return
  const layout = plotlyRef.value._fullLayout || plotlyRef.value.layout
  if (!layout) return

  const xRange = layout.xaxis?.range
  if (Array.isArray(xRange) && xRange.length === 2) {
    const start = parseDateAxisValue(xRange[0])
    const end = parseDateAxisValue(xRange[1])
    if (start !== null && end !== null) {
      xAxisRange.value = { start, end }
    }
  }

  const nextYRanges: Record<string, [number, number]> = {}
  const axisKeys = new Set<string>()
  const axisList = layout._axisList as any[] | undefined
  if (Array.isArray(axisList) && axisList.length) {
    axisList.forEach((axis) => {
      const axisName = axis?._name
      if (typeof axisName === 'string' && axisName.startsWith('yaxis')) {
        axisKeys.add(axisName)
      }
    })
  }

  if (!axisKeys.size) {
    Object.getOwnPropertyNames(layout).forEach((key) => {
      if (/^yaxis\\d*$/.test(key)) axisKeys.add(key)
    })
  }

  if (!axisKeys.size) {
    for (let index = 1; index <= 8; index += 1) {
      const key = index === 1 ? 'yaxis' : `yaxis${index}`
      if (layout[key]) axisKeys.add(key)
    }
  }

  axisKeys.forEach((axisKey) => {
    const axis = layout[axisKey]
    if (!axis || axis.autorange === true) return
    const range = axis.range
    if (!Array.isArray(range) || range.length !== 2) return
    const start = parseNumericAxisValue(range[0])
    const end = parseNumericAxisValue(range[1])
    if (start !== null && end !== null) {
      const normalizedKey = axisKey === 'yaxis1' ? 'yaxis' : axisKey
      nextYRanges[normalizedKey] = [start, end]
    }
  })

  if (Object.keys(nextYRanges).length) {
    yAxisRanges.value = nextYRanges
  } else if (yAxisRanges.value && Object.keys(yAxisRanges.value).length) {
    yAxisRanges.value = {}
  }
}

const handleCopyState = () => {
  captureAxisRangesFromPlotly()
  emit('copy-state')
}

const updating = computed(() =>
  Array.from(loadingStates.value.values()).some((isLoading) => isLoading)
)

const isDataAvailable = computed(() =>
  graphSeriesArray.value.some((series) => series.data && series.data.length > 0)
)
const hasSelectedDatastreams = computed(() => plottedDatastreams.value.length > 0)

const hasLoadedSelectedSeries = computed(() => {
  if (!plottedDatastreams.value.length) return false
  const selectedIds = new Set(plottedDatastreams.value.map((ds) => ds.id))
  const loadedIds = new Set(graphSeriesArray.value.map((series) => series.id))
  if (selectedIds.size !== loadedIds.size) return false
  for (const id of selectedIds) {
    if (!loadedIds.has(id)) return false
  }
  return true
})

const canPlot = computed(() =>
  Boolean(plotlyOptions.value && hasSelectedDatastreams.value)
)
const showInstructions = computed(() => !hasSelectedDatastreams.value)
const showNoDataWarning = computed(
  () =>
    hasSelectedDatastreams.value &&
    !updating.value &&
    hasLoadedSelectedSeries.value &&
    !isDataAvailable.value
)
const viewMode = computed<'plot' | 'summary'>({
  get: () => (showSummaryStatistics.value ? 'summary' : 'plot'),
  set: (value) => {
    showSummaryStatistics.value = value === 'summary'
  },
})

const showPlot = computed(() => canPlot.value && viewMode.value === 'plot')

const clampPercent = (value: number) => Math.min(100, Math.max(0, value))
const RANGE_MATCH_TOLERANCE_MS = 5 * 60 * 1000
const PRESET_MATCH_TOLERANCE_MS = 36 * 60 * 60 * 1000

const isWithinTolerance = (value: number, target: number, tolerance: number) =>
  Math.abs(value - target) <= tolerance

const getMostRecentEndTime = () =>
  plottedDatastreams.value.reduce((latest, ds) => {
    if (!ds.phenomenonEndTime) return latest
    const dsEndDate = new Date(ds.phenomenonEndTime)
    return dsEndDate > latest ? dsEndDate : latest
  }, new Date(0))

const getOldestBeginTime = () =>
  plottedDatastreams.value.reduce((oldest, ds) => {
    if (!ds.phenomenonBeginTime) return oldest
    const dsBeginDate = new Date(ds.phenomenonBeginTime)
    return dsBeginDate < oldest ? dsBeginDate : oldest
  }, endDate.value)

const getPhenomenonRange = () => {
  let min = Infinity
  let max = -Infinity

  plottedDatastreams.value.forEach((ds) => {
    if (ds.phenomenonBeginTime) {
      const begin = new Date(ds.phenomenonBeginTime).getTime()
      if (Number.isFinite(begin)) min = Math.min(min, begin)
    }
    if (ds.phenomenonEndTime) {
      const end = new Date(ds.phenomenonEndTime).getTime()
      if (Number.isFinite(end)) max = Math.max(max, end)
    }
  })

  if (!Number.isFinite(min) || !Number.isFinite(max)) return null
  return { min, max }
}

const matchPresetRange = (rangeStart: number, rangeEnd: number) => {
  if (!plottedDatastreams.value.length) return null

  const mostRecentEnd = getMostRecentEndTime().getTime()
  if (!Number.isFinite(mostRecentEnd)) return null
  if (!isWithinTolerance(rangeEnd, mostRecentEnd, PRESET_MATCH_TOLERANCE_MS))
    return null

  const end = new Date(mostRecentEnd)
  const candidates = [
    {
      id: 0,
      begin: new Date(end.getFullYear(), end.getMonth() - 1, end.getDate()),
    },
    {
      id: 1,
      begin: new Date(end.getFullYear(), end.getMonth() - 6, end.getDate()),
    },
    {
      id: 2,
      begin: new Date(end.getFullYear(), 0, 1),
    },
    {
      id: 3,
      begin: new Date(end.getFullYear() - 1, end.getMonth(), end.getDate()),
    },
    {
      id: 4,
      begin: getOldestBeginTime(),
    },
  ]

  const match = candidates.find((candidate) =>
    isWithinTolerance(
      rangeStart,
      candidate.begin.getTime(),
      PRESET_MATCH_TOLERANCE_MS
    )
  )
  return match ? match.id : null
}

const handleRelayout = async (eventData: any) => {
  if (!plotlyRef.value) return

  if (!eventData) return

  const eventKeys = Object.keys(eventData)
  const isResizeEvent =
    eventData.autosize === true ||
    eventData.width !== undefined ||
    eventData.height !== undefined
  const nextYRanges: Record<string, [number, number]> = {
    ...yAxisRanges.value,
  }
  const pendingYRanges: Record<string, { start?: number; end?: number }> = {}
  let yRangesUpdated = false

  const normalizeAxisKey = (key: string) => (key === 'yaxis1' ? 'yaxis' : key)

  eventKeys.forEach((key) => {
    const autorangeMatch = key.match(/^(yaxis\\d*)\\.autorange$/)
    if (autorangeMatch && eventData[key] === true) {
      if (!isResizeEvent) {
        delete nextYRanges[normalizeAxisKey(autorangeMatch[1])]
        yRangesUpdated = true
      }
      return
    }

    const rangeArrayMatch = key.match(/^(yaxis\\d*)\\.range$/)
    if (rangeArrayMatch && Array.isArray(eventData[key])) {
      const [start, end] = eventData[key]
      const parsedStart = parseNumericAxisValue(start)
      const parsedEnd = parseNumericAxisValue(end)
      if (parsedStart !== null && parsedEnd !== null) {
        nextYRanges[normalizeAxisKey(rangeArrayMatch[1])] = [
          parsedStart,
          parsedEnd,
        ]
        yRangesUpdated = true
      }
      return
    }

    const rangeMatch = key.match(/^(yaxis\\d*)\\.range\\[(0|1)\\]$/)
    if (!rangeMatch) return
    const axisKey = normalizeAxisKey(rangeMatch[1])
    const index = Number(rangeMatch[2])
    const parsedValue = parseNumericAxisValue(eventData[key])
    if (parsedValue === null) return
    pendingYRanges[axisKey] = pendingYRanges[axisKey] || {}
    if (index === 0) pendingYRanges[axisKey].start = parsedValue
    if (index === 1) pendingYRanges[axisKey].end = parsedValue
  })

  Object.entries(pendingYRanges).forEach(([axisKey, range]) => {
    if (
      range.start !== undefined &&
      range.end !== undefined &&
      Number.isFinite(range.start) &&
      Number.isFinite(range.end)
    ) {
      nextYRanges[axisKey] = [range.start, range.end]
      yRangesUpdated = true
    }
  })

  if (yRangesUpdated) {
    yAxisRanges.value = nextYRanges
  }

  if (eventData['xaxis.autorange'] === true && !isResizeEvent) {
    xAxisRange.value = null
    dataZoomStart.value = 0
    dataZoomEnd.value = 100
    return
  }

  let eventRangeStart = eventData['xaxis.range[0]']
  let eventRangeEnd = eventData['xaxis.range[1]']
  const eventRange = eventData['xaxis.range']
  if (
    (eventRangeStart === undefined || eventRangeEnd === undefined) &&
    Array.isArray(eventRange)
  ) {
    ;[eventRangeStart, eventRangeEnd] = eventRange
  }
  if (eventRangeStart === undefined || eventRangeEnd === undefined) return

  const rangeStart =
    typeof eventRangeStart === 'string'
      ? Date.parse(eventRangeStart)
      : eventRangeStart
  const rangeEnd =
    typeof eventRangeEnd === 'string'
      ? Date.parse(eventRangeEnd)
      : eventRangeEnd
  if (!Number.isFinite(rangeStart) || !Number.isFinite(rangeEnd)) return

  const bounds =
    plotlyOptions.value?.xRange || getXRangeBounds(graphSeriesArray.value)
  if (!bounds) return

  const span = bounds.max - bounds.min
  if (span <= 0) return

  dataZoomStart.value = Math.round(
    clampPercent(((rangeStart - bounds.min) / span) * 100)
  )
  dataZoomEnd.value = Math.round(
    clampPercent(((rangeEnd - bounds.min) / span) * 100)
  )
  xAxisRange.value = { start: rangeStart, end: rangeEnd }

  const visiblePoints = getVisiblePointCount(rangeStart, rangeEnd)
  await applyLargeSeriesMode(visiblePoints)

  const currentStart = beginDate.value?.getTime()
  const currentEnd = endDate.value?.getTime()
  const rangeMatchesCurrent =
    currentStart !== undefined &&
    currentEnd !== undefined &&
    isWithinTolerance(rangeStart, currentStart, RANGE_MATCH_TOLERANCE_MS) &&
    isWithinTolerance(rangeEnd, currentEnd, RANGE_MATCH_TOLERANCE_MS)

  if (!rangeMatchesCurrent) {
    const phenomenonRange = getPhenomenonRange()
    const rangeMatchesDataBounds =
      isWithinTolerance(rangeStart, bounds.min, RANGE_MATCH_TOLERANCE_MS) &&
      isWithinTolerance(rangeEnd, bounds.max, RANGE_MATCH_TOLERANCE_MS)
    const needsFullRange =
      phenomenonRange &&
      (bounds.min > phenomenonRange.min + RANGE_MATCH_TOLERANCE_MS ||
        bounds.max < phenomenonRange.max - RANGE_MATCH_TOLERANCE_MS)
    const matchedPresetId =
      rangeMatchesDataBounds && needsFullRange
        ? 4
        : matchPresetRange(rangeStart, rangeEnd)
    if (matchedPresetId !== null) {
      onDateBtnClick(matchedPresetId)
    }
  }
}

const debouncedRelayout = debounce(handleRelayout, 250)

const attachHandlers = () => {
  if (!plotlyRef.value || handlersAttached.value) return
  plotlyRef.value.on('plotly_redraw', debouncedRelayout)
  plotlyRef.value.on('plotly_relayout', debouncedRelayout)
  plotlyRef.value.on('plotly_afterplot', applyLargeSeriesModeForCurrentRange)
  handlersAttached.value = true
}

const renderPlot = async () => {
  if (!plotlyOptions.value || !plotContainer.value) return

  const Plotly = await ensurePlotly()
  const { traces, layout, config } = plotlyOptions.value
  if (!plotlyRef.value) {
    plotlyRef.value = await Plotly.newPlot(
      plotContainer.value,
      traces,
      layout,
      config
    )
    attachHandlers()
  } else {
    await Plotly.react(plotlyRef.value, traces, layout, config)
  }

  applyLargeSeriesModeForCurrentRange()
  queueResize()
}

const cleanupPlot = () => {
  if (plotlyRef.value) {
    if (plotlyApi) {
      plotlyApi.purge(plotlyRef.value)
    }
    plotlyRef.value = null
    handlersAttached.value = false
  }
}

const queueResize = () => {
  if (!plotlyRef.value || !plotlyApi) return
  requestAnimationFrame(() => {
    if (plotlyRef.value) plotlyApi.Plots.resize(plotlyRef.value)
  })
  setTimeout(() => {
    if (plotlyRef.value) plotlyApi.Plots.resize(plotlyRef.value)
  }, 200)
}

const handleLayoutResize = () => {
  if (plotlyRef.value) {
    queueResize()
  }
}

watch([() => props.cardHeight], ([newHeight], [oldHeight]) => {
  if (Math.abs(newHeight - oldHeight) < 0.2) return
  nextTick(() => {
    queueResize()
  })
})

watch(
  () => canPlot.value,
  (shouldRender) => {
    if (!shouldRender) {
      cleanupPlot()
      return
    }
    nextTick(() => {
      renderPlot()
    })
  },
  { immediate: true }
)

watch(
  () => plotlyOptions.value,
  () => {
    syncDefaultTraceStyles()
    if (showPlot.value) {
      nextTick(() => {
        renderPlot()
      })
    }
  }
)

watch(
  () => showPlot.value,
  (isVisible) => {
    if (isVisible) {
      nextTick(() => {
        renderPlot()
        queueResize()
      })
    }
  }
)

onBeforeUnmount(() => {
  window.removeEventListener('datavis-layout', handleLayoutResize)
  window.removeEventListener('resize', handleLayoutResize)
  cleanupPlot()
})

onMounted(() => {
  window.addEventListener('datavis-layout', handleLayoutResize)
  window.addEventListener('resize', handleLayoutResize)
  setTimeout(() => {
    queueResize()
  }, 200)
})
</script>

<style scoped>
.plot-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.plot-card :deep(.v-card-text) {
  padding: 0;
  flex: 1;
  min-height: 0;
}

.plot-warning {
  padding: 0;
}

.plot-warning :deep(.v-alert) {
  margin: 0;
  border-radius: 0;
}

.plot-empty {
  min-height: 100%;
}

.plot-empty :deep(.v-card-text) {
  margin-top: 12px;
  margin-left: 12px;
}

.plot-empty__title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 8px 8px 12px;
}

.plotly-chart {
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
}

.plot-plot-area {
  position: relative;
  flex: 1;
  min-height: 0;
}

.plot-disclaimer {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 5;
  pointer-events: auto;
}

.plot-disclaimer-text {
  display: inline-flex;
  align-items: center;
  font-size: 0.75rem;
  font-weight: 500;
  color: #6b7280;
  background: rgba(255, 255, 255, 0.85);
  border-radius: 4px;
  padding: 2px 6px;
  text-decoration: underline dotted;
  text-underline-offset: 3px;
  cursor: default;
}

.plot-disclaimer-card {
  max-width: 320px;
  min-width: 240px;
}

.plot-toolbar {
  padding: 0;
}

.plot-shell {
  display: flex;
  flex-direction: column;
  gap: 0;
  flex: 1;
  min-height: 0;
  height: 100%;
}

.plot-shell :deep(.js-plotly-plot .plotly) {
  .drag.cursor-ns-resize,
  .drag.cursor-n-resize,
  .drag.cursor-s-resize,
  .drag.cursor-w-resize,
  .drag.cursor-ew-resize,
  .drag.cursor-e-resize {
    fill: #f8f8f8 !important;
    stroke: #f8f8f8 !important;
    stroke-width: 1px !important;
  }

  .drag.cursor-sw-resize,
  .drag.cursor-nw-resize,
  .drag.cursor-ne-resize,
  .drag.cursor-se-resize {
    fill: #f2f2f2 !important;
    stroke: #f2f2f2 !important;
    stroke-width: 1px !important;
  }
}

.plot-body {
  display: flex;
  min-height: 0;
  flex: 1;
  align-items: stretch;
  height: 100%;
}

.plot-rail {
  width: 44px;
  background-color: #f2f2f2;
  border-right: 1px solid #e0e0e0;
  border-radius: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0;
  padding: 0;
  min-height: 100%;
}

.plot-rail-btn {
  border-radius: 0;
  min-width: 100%;
  min-height: 44px;
}

.plot-rail-btn--active {
  background-color: rgba(33, 150, 243, 0.12);
  color: #1e88e5;
  position: relative;
}

.plot-rail-btn--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background-color: #1e88e5;
}

.plot-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.plot-window {
  flex: 1;
  min-height: 0;
  height: 100%;
}

.plot-window :deep(.v-window__container) {
  height: 100%;
}

.plot-window-item {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

@media (max-width: 600px) {
  .plot-body {
    flex-direction: column;
  }

  .plot-rail {
    width: 100%;
    height: 36px;
    min-height: 0;
    flex: 0 0 36px;
    flex-direction: row;
    border-right: 0;
    border-bottom: 1px solid #e0e0e0;
  }

  .plot-rail-btn {
    min-height: 36px;
    min-width: 36px;
    flex: 1;
  }

  .plot-rail-btn--active::before {
    left: 0;
    right: 0;
    top: auto;
    bottom: 0;
    width: auto;
    height: 3px;
  }
}
</style>
