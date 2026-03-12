<template>
  <FullScreenLoader v-if="loading" />
  <div v-else class="visualize-page">
    <DataVisNavRail />
    <div class="visualize-content">
      <DataVisFiltersDrawer @drawer-change="handleDrawerChange" />

      <div class="visualize-layout">
        <div
          v-if="showPlot"
          class="plot-section"
          :style="{ flex: `${cardHeight} 1 0%` }"
        >
          <DataVisualizationCard
            :cardHeight="cardHeight"
            @copy-state="copyStateToClipboard"
          />
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
import DataVisFiltersDrawer from '@/components/VisualizeData/DataVisFiltersDrawer.vue'
import DataVisNavRail from '@/components/VisualizeData/DataVisNavRail.vue'
import DataVisDatasetsTable from '@/components/VisualizeData/DataVisDatasetsTable.vue'
import DataVisualizationCard from '@/components/VisualizeData/DataVisualizationCard.vue'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import hs from '@hydroserver/client'
import { useDataVisStore } from '@/store/dataVisualization'
import { useSidebarStore } from '@/store/useSidebar'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import { Snackbar } from '@/utils/notifications'
import FullScreenLoader from '@/components/base/FullScreenLoader.vue'

const route = useRoute()

const dataVisStore = useDataVisStore()
const { onDateBtnClick, resetState } = dataVisStore
const {
  things,
  selectedThings,
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
  xAxisRange,
  yAxisRanges,
} = storeToRefs(dataVisStore)
const sidebar = useSidebarStore()

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

const handleDrawerChange = () => {
  setTimeout(() => {
    window.dispatchEvent(new Event('resize'))
    window.dispatchEvent(new Event('datavis-layout'))
  }, 250)
}

const generateStateUrl = () => {
  const BASE_URL = `${window.location.origin}/visualize-data/`

  const queryParams = new URLSearchParams()

  selectedThings.value.forEach((t) => queryParams.append('sites', t.id))

  plottedDatastreams.value.forEach((ds) =>
    queryParams.append('datastreams', ds.id)
  )

  selectedProcessingLevelNames.value.forEach((pl) =>
    queryParams.append('PLs', pl)
  )

  selectedObservedPropertyNames.value.forEach((op) =>
    queryParams.append('OPs', op)
  )

  if (selectedDateBtnId.value < 0) {
    queryParams.append('beginDate', beginDate.value.toISOString())
    queryParams.append('endDate', endDate.value.toISOString())
  } else {
    // 0 is the default so no need to put it in the URL
    if (selectedDateBtnId.value !== 0)
      queryParams.append(
        'selectedDateBtnId',
        selectedDateBtnId.value.toString()
      )
  }

  if (dataZoomStart.value !== 0)
    queryParams.append('dataZoomStart', dataZoomStart.value.toString())
  if (dataZoomEnd.value !== 0 && dataZoomEnd.value !== 100)
    queryParams.append('dataZoomEnd', dataZoomEnd.value.toString())

  if (xAxisRange.value) {
    queryParams.append('xStart', xAxisRange.value.start.toString())
    queryParams.append('xEnd', xAxisRange.value.end.toString())
  }

  const yRangeKeys = Object.keys(yAxisRanges.value)
  if (yRangeKeys.length) {
    queryParams.append('yRanges', JSON.stringify(yAxisRanges.value))
  }

  queryParams.append('plot', showPlot.value ? '1' : '0')
  queryParams.append('table', showTable.value ? '1' : '0')
  queryParams.append('summary', showSummaryStatistics.value ? '1' : '0')
  queryParams.append('drawer', sidebar.isOpen ? '1' : '0')

  const visibleColumns = tableHeaders.value
    .filter((header) => header.visible && header.key !== 'plot')
    .map((header) => header.key)
  const allColumns = tableHeaders.value
    .filter((header) => header.key !== 'plot')
    .map((header) => header.key)

  if (visibleColumns.length !== allColumns.length) {
    queryParams.append('columns', visibleColumns.join(','))
  }

  return `${BASE_URL}?${queryParams.toString()}`
}

const copyStateToClipboard = async () => {
  try {
    const stateUrl = generateStateUrl()
    await navigator.clipboard.writeText(stateUrl)
    Snackbar.info('Copied URL to clipboard')
  } catch (err) {
    console.error('Failed to copy URL:', err)
  }
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
      ? value.find((item): item is string => typeof item === 'string') ?? null
      : value
    if (!raw) return null
    const normalized = raw.toLowerCase()
    return normalized === '1' || normalized === 'true' || normalized === 'yes'
  }

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
    selectedThings.value = things.value.filter((t) =>
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
  if (Number.isFinite(xStart) && Number.isFinite(xEnd)) {
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

  const drawerParam = parseBoolean(route.query.drawer)
  if (drawerParam !== null) {
    sidebar.setOpen(drawerParam, true)
  }

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

onMounted(async () => {
  try {
    const [
      thingsResponse,
      datastreamsResponse,
      processingLevelsResponse,
      observedPropertiesResponse,
    ] = await Promise.all([
      hs.things.listAllItems(),
      hs.datastreams.listAllItems(),
      hs.processingLevels.listAllItems(),
      hs.observedProperties.listAllItems(),
    ])

    things.value = thingsResponse
    datastreams.value = datastreamsResponse
    processingLevels.value = processingLevelsResponse
    observedProperties.value = observedPropertiesResponse
  } catch (error) {
    Snackbar.error('Unable to fetch data from the API.')
    console.error('Unable to fetch data from the API:', error)
  }

  parseUrlAndSetState()
  loading.value = false
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
  gap: 12px;
  --visualize-margin: 16px;
  margin: var(--visualize-margin);
  height: calc(
    100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px) -
      (var(--visualize-margin) * 2)
  );
}

.visualize-page {
  --datavis-rail-width: 64px;
  display: flex;
  height: calc(
    100dvh - var(--v-layout-top, 0px) - var(--v-layout-bottom, 0px)
  );
  overflow: hidden;
  background-color: #eef2f6;
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
    --visualize-margin: 8px;
    gap: 8px;
  }
  .visualize-page {
    --datavis-rail-width: 56px;
  }
}
</style>
