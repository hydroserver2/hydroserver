<template>
  <FullScreenLoader v-if="loading" />
  <div v-else class="visualize-page">
    <DataVisNavRail />
    <div class="visualize-content">
      <div class="visualize-layout">
        <div
          v-if="showPlot"
          class="plot-section"
          :style="{ flex: `${cardHeight} 1 0%` }"
        >
          <DataVisualizationCard :cardHeight="cardHeight" />
        </div>

        <div
          v-if="showTable"
          class="table-section"
          :style="{ flex: `${tableHeight} 1 0%` }"
        >
          <DataVisDatasetsTable />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import DataVisNavRail from '@/components/VisualizeData/DataVisNavRail.vue'
import DataVisDatasetsTable from '@/components/VisualizeData/DataVisDatasetsTable.vue'
import DataVisualizationCard from '@/components/VisualizeData/DataVisualizationCard.vue'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import hs from '@hydroserver/client'
import { useDataVisStore } from '@/store/dataVisualization'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import { Snackbar } from '@/utils/notifications'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'

const route = useRoute()
const router = useRouter()

const dataVisStore = useDataVisStore()
const { onDateBtnClick, resetState } = dataVisStore
const {
  monitoringSites,
  selectedMonitoringSites,
  plottedDatastreams,
  selectedObservedPropertyNames,
  selectedProcessingLevelNames,
  processingLevels,
  observedProperties,
  datastreams,
  beginDate,
  endDate,
  dataZoomStart,
  dataZoomEnd,
  selectedDateBtnId,
  cardHeight,
  tableHeight,
  showPlot,
  showTable,
  showSummaryStatistics,
  tableHeaders,
  tableSearch,
  xAxisRange,
  yAxisRanges,
} = storeToRefs(dataVisStore)

const fullHeight = 90
const defaultPlotHeight = 45
const defaultTableHeight = 35

const updateLayoutHeights = () => {
  if (showPlot.value && showTable.value) {
    cardHeight.value = defaultPlotHeight
    tableHeight.value = defaultTableHeight
  } else if (showPlot.value) {
    cardHeight.value = fullHeight
    tableHeight.value = 0
  } else if (showTable.value) {
    cardHeight.value = 0
    tableHeight.value = fullHeight
  } else {
    cardHeight.value = defaultPlotHeight
    tableHeight.value = defaultTableHeight
    showPlot.value = true
  }
}

watch([showPlot, showTable], updateLayoutHeights, { immediate: true })

watch(showPlot, (isVisible) => {
  if (!isVisible) showSummaryStatistics.value = false
})

const isValidAxisRange = (
  range: { start: number; end: number } | null
): range is { start: number; end: number } =>
  Boolean(
    range &&
    Number.isFinite(range.start) &&
    Number.isFinite(range.end) &&
    range.start < range.end
  )

const buildStateQuery = (): LocationQueryRaw => {
  const query: LocationQueryRaw = {
    sites: selectedMonitoringSites.value.map((site) => site.id),
    datastreams: plottedDatastreams.value.map((datastream) => datastream.id),
    PLs: selectedProcessingLevelNames.value,
    OPs: selectedObservedPropertyNames.value,
    q: tableSearch.value.trim() || undefined,
  }

  // The default layout is represented by the blank route so the main app-bar
  // navigation always opens a clean `/visualize-data` URL.
  if (!showPlot.value) query.plot = '0'
  if (!showTable.value) query.table = '0'
  if (showSummaryStatistics.value) query.summary = '1'

  if (selectedDateBtnId.value < 0) {
    query.beginDate = beginDate.value.toISOString()
    query.endDate = endDate.value.toISOString()
  } else if (selectedDateBtnId.value !== 0) {
    // 0 is the default so no need to put it in the URL.
    query.selectedDateBtnId = selectedDateBtnId.value.toString()
  }

  if (dataZoomStart.value !== 0)
    query.dataZoomStart = dataZoomStart.value.toString()
  if (dataZoomEnd.value !== 0 && dataZoomEnd.value !== 100)
    query.dataZoomEnd = dataZoomEnd.value.toString()

  if (isValidAxisRange(xAxisRange.value)) {
    query.xStart = xAxisRange.value.start.toString()
    query.xEnd = xAxisRange.value.end.toString()
  }

  if (Object.keys(yAxisRanges.value).length)
    query.yRanges = JSON.stringify(yAxisRanges.value)

  const visibleColumns = tableHeaders.value
    .filter((header) => header.visible && header.key !== 'plot')
    .map((header) => header.key)
  const allColumns = tableHeaders.value
    .filter((header) => header.key !== 'plot')
    .map((header) => header.key)

  if (visibleColumns.length && visibleColumns.length !== allColumns.length) {
    query.columns = visibleColumns.join(',')
  }

  return query
}

const parseUrlAndSetState = () => {
  const parseBoolean = (
    value:
      | import('vue-router').LocationQueryValue
      | import('vue-router').LocationQueryValue[]
      | undefined
  ) => {
    if (value === undefined || value === null) return null
    const raw = Array.isArray(value)
      ? (value.find((item): item is string => typeof item === 'string') ?? null)
      : value
    if (!raw) return null
    const normalized = raw.toLowerCase()
    return normalized === '1' || normalized === 'true' || normalized === 'yes'
  }

  const searchParam = route.query.q
  const searchRaw = Array.isArray(searchParam) ? searchParam[0] : searchParam
  tableSearch.value = typeof searchRaw === 'string' ? searchRaw : ''

  const selectedDateBtnIdParam = (route.query.selectedDateBtnId as string) || ''
  if (selectedDateBtnIdParam !== '') {
    const btnId = +selectedDateBtnIdParam
    onDateBtnClick(btnId)
  } else {
    const beginDateParam = (route.query.beginDate as string) || ''
    const endDateParam = (route.query.endDate as string) || ''
    if (beginDateParam || endDateParam) {
      selectedDateBtnId.value = -1
      if (beginDateParam) beginDate.value = new Date(beginDateParam)
      if (endDateParam) endDate.value = new Date(endDateParam)
    }
  }

  // Datastream IDs
  const datastreamIds = route.query.datastreams
  const datastreamIdsArray = Array.isArray(datastreamIds)
    ? datastreamIds
    : datastreamIds
      ? [datastreamIds]
      : []

  const datastreamIdsStrings = datastreamIdsArray.filter(
    (id): id is string => typeof id === 'string'
  )

  if (datastreamIdsStrings.length) {
    const limitedIds = datastreamIdsStrings.slice(0, 5)
    if (datastreamIdsStrings.length > 5) {
      Snackbar.info('Only the first 5 datastreams were loaded from the URL.')
    }
    plottedDatastreams.value = datastreams.value.filter((ds) =>
      limitedIds.includes(ds.id)
    )
  }

  // Site IDs
  const siteIds = route.query.sites
  const siteIdsArray = Array.isArray(siteIds)
    ? siteIds
    : siteIds
      ? [siteIds]
      : []

  const siteIdsStrings = siteIdsArray.filter(
    (id): id is string => typeof id === 'string'
  )

  if (siteIdsStrings.length)
    selectedMonitoringSites.value = monitoringSites.value.filter((t) =>
      siteIdsStrings.includes(t.id)
    )

  // Observed Property Names
  const OPNames = route.query.OPs
  const OPNamesArray = Array.isArray(OPNames)
    ? OPNames
    : OPNames
      ? [OPNames]
      : []

  const OPNamesStrings = OPNamesArray.filter(
    (op): op is string => typeof op === 'string'
  )

  if (OPNamesStrings.length)
    selectedObservedPropertyNames.value = OPNamesStrings

  // Processing Level Names
  const PLNames = route.query.PLs
  const PLNamesArray = Array.isArray(PLNames)
    ? PLNames
    : PLNames
      ? [PLNames]
      : []

  const PLNamesStrings = PLNamesArray.filter(
    (pl): pl is string => typeof pl === 'string'
  )

  if (PLNamesStrings.length) selectedProcessingLevelNames.value = PLNamesStrings

  const start = (route.query.dataZoomStart as string) || ''
  if (start) dataZoomStart.value = +start

  const end = (route.query.dataZoomEnd as string) || ''
  if (end) dataZoomEnd.value = +end

  const xStartParam = route.query.xStart
  const xEndParam = route.query.xEnd
  const xStartRaw = Array.isArray(xStartParam) ? xStartParam[0] : xStartParam
  const xEndRaw = Array.isArray(xEndParam) ? xEndParam[0] : xEndParam
  const xStart = xStartRaw ? Number(xStartRaw) : null
  const xEnd = xEndRaw ? Number(xEndRaw) : null
  if (
    Number.isFinite(xStart) &&
    Number.isFinite(xEnd) &&
    (xStart as number) < (xEnd as number)
  ) {
    xAxisRange.value = { start: xStart as number, end: xEnd as number }
  } else {
    xAxisRange.value = null
  }

  const yRangesParam = route.query.yRanges
  const yRangesRaw = Array.isArray(yRangesParam)
    ? yRangesParam[0]
    : yRangesParam
  if (yRangesRaw) {
    try {
      const parsed = JSON.parse(yRangesRaw)
      if (parsed && typeof parsed === 'object') {
        const normalized: Record<string, [number, number]> = {}
        Object.entries(parsed).forEach(([key, value]) => {
          const normalizedKey = key === 'yaxis1' ? 'yaxis' : key
          if (
            Array.isArray(value) &&
            value.length === 2 &&
            Number.isFinite(Number(value[0])) &&
            Number.isFinite(Number(value[1]))
          ) {
            normalized[normalizedKey] = [Number(value[0]), Number(value[1])]
          }
        })
        yAxisRanges.value = normalized
      } else {
        yAxisRanges.value = {}
      }
    } catch (error) {
      yAxisRanges.value = {}
      console.warn('Unable to parse yRanges from URL', error)
    }
  } else {
    yAxisRanges.value = {}
  }

  const plotParam = parseBoolean(route.query.plot)
  const tableParam = parseBoolean(route.query.table)
  if (plotParam !== null) showPlot.value = plotParam
  if (tableParam !== null) showTable.value = tableParam

  if (!showPlot.value && !showTable.value) {
    showPlot.value = true
  }

  const summaryParam = parseBoolean(route.query.summary)
  if (summaryParam !== null) showSummaryStatistics.value = summaryParam

  const columnsParam = route.query.columns
  if (columnsParam) {
    const raw = Array.isArray(columnsParam)
      ? columnsParam.find((item): item is string => typeof item === 'string')
      : columnsParam
    if (raw) {
      const keys = raw
        .split(',')
        .map((key) => key.trim())
        .filter(Boolean)
      dataVisStore.setTableVisibleColumns(keys)
    }
  }
}

const loading = ref(true)

const syncRouteQuery = () => {
  if (loading.value) return

  const query = buildStateQuery()
  const nextFullPath = router.resolve({
    path: route.path,
    hash: route.hash,
    query,
  }).fullPath
  if (nextFullPath === route.fullPath) return

  void router.replace({ query })
}

// Keep all shareable visualization state in the URL. `replace` avoids adding
// a browser-history entry for every filter, zoom, or layout adjustment.
watch(
  [
    selectedMonitoringSites,
    plottedDatastreams,
    selectedObservedPropertyNames,
    selectedProcessingLevelNames,
    beginDate,
    endDate,
    dataZoomStart,
    dataZoomEnd,
    selectedDateBtnId,
    showPlot,
    showTable,
    showSummaryStatistics,
    tableHeaders,
    tableSearch,
    xAxisRange,
    yAxisRanges,
  ],
  syncRouteQuery,
  { deep: true }
)

onMounted(async () => {
  try {
    const hasBootstrapData =
      monitoringSites.value.length > 0 ||
      datastreams.value.length > 0 ||
      processingLevels.value.length > 0 ||
      observedProperties.value.length > 0

    if (!hasBootstrapData) {
      const res = await hs.datastreams.getVisualizationBootstrap()
      if (res.ok) {
        monitoringSites.value = res.data.monitoringSites
        datastreams.value = res.data.datastreams
        processingLevels.value = res.data.processingLevels
        observedProperties.value = res.data.observedProperties
      }
    }
  } catch (error) {
    Snackbar.error('Unable to fetch data from the API.')
    console.error('Unable to fetch data from the API:', error)
  }

  parseUrlAndSetState()
  loading.value = false
  syncRouteQuery()
})

onUnmounted(() => {
  resetState()
})
</script>

<style scoped>
.visualize-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  gap: var(--hs-space-12);
  --visualize-margin: var(--hs-space-16);
  margin: var(--visualize-margin);
  height: calc(
    100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px) -
      (var(--visualize-margin) * 2)
  );
}

.visualize-page {
  --datavis-rail-width: 64px;
  display: flex;
  height: calc(100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px));
  overflow: hidden;
  background-color: var(--hs-background);
}

.visualize-content {
  flex: 1;
  min-width: 0;
  position: relative;
}

.plot-section,
.table-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.plot-section > *,
.table-section > * {
  flex: 1;
  min-height: 0;
}

@media (max-width: 600px) {
  .visualize-layout {
    --visualize-margin: var(--hs-space-8);
    gap: var(--hs-space-8);
  }
  .visualize-page {
    --datavis-rail-width: 56px;
  }
}
</style>
