import {
  Datastream,
  ObservedProperty,
  ProcessingLevel,
  MonitoringSite,
  GraphSeries,
  Workspace,
} from '@hydroserver/client'
import {
  SummaryStatistics,
  calculateSummaryStatistics,
} from '@/utils/plotting/summaryStatisticUtils'
import { defineStore } from 'pinia'
import { computed, reactive, ref, watch } from 'vue'
import { PlotlyColors } from '@/utils/materialColors'
import { createPlotlyOption, PlotlyOptions } from '@/utils/plotting/plotly'
import { useObservationStore } from '@/store/observations'

export const useDataVisStore = defineStore('dataVisualization', () => {
  const { fetchGraphSeries, fetchGraphSeriesData } = useObservationStore()

  const monitoringSites = ref<MonitoringSite[]>([])
  const datastreams = ref<Datastream[]>([])
  const observedProperties = ref<ObservedProperty[]>([])
  const processingLevels = ref<ProcessingLevel[]>([])

  const selectedMonitoringSites = ref<MonitoringSite[]>([])
  const plottedDatastreams = ref<Datastream[]>([])
  const selectedWorkspaces = ref<Workspace[]>([])
  const selectedObservedPropertyNames = ref<string[]>([])
  const selectedProcessingLevelNames = ref<string[]>([])

  const showSummaryStatistics = ref(false)
  const tableSearch = ref('')
  const summaryStatisticsArray = ref<SummaryStatistics[]>([])

  const graphSeriesArray = ref<GraphSeries[]>([])
  const plotlyOptions = ref<PlotlyOptions | undefined>()
  const loadingStates = ref(new Map<string, boolean>()) // State to track loading status of individual datasets
  const prevIds = ref<string[]>([])
  const requestCounters = ref<Record<string, number>>({})
  const refreshCounter = ref(0)
  const activeRefreshKey = ref('')

  const cardHeight = ref(40)
  const tableHeight = ref(30)
  const showPlot = ref(true)
  const showTable = ref(true)
  const datastreamDetailLevel = ref(1)
  const tableHeaders = reactive([
    { title: 'Plot', key: 'plot', visible: true },
    {
      title: 'Number Observations',
      key: 'valueCount',
      visible: false,
    },
    {
      title: 'Date Last Updated',
      key: 'phenomenonEndTime',
      visible: false,
    },
  ])

  const endDate = ref<Date>(new Date())
  const oneMonth = 30 * 24 * 60 * 60 * 1000
  const beginDate = ref<Date>(new Date(endDate.value.getTime() - oneMonth))
  const selectedDateBtnId = ref(0)
  const dataZoomStart = ref(0)
  const dataZoomEnd = ref(100)
  const xAxisRange = ref<{ start: number; end: number } | null>(null)
  const yAxisRanges = ref<Record<string, [number, number]>>({})
  const monitoringSiteById = computed(
    () =>
      new Map(
        monitoringSites.value.map((monitoringSite) => [
          monitoringSite.id,
          monitoringSite,
        ])
      )
  )
  const observedPropertyById = computed(
    () =>
      new Map(
        observedProperties.value.map((observedProperty) => [
          observedProperty.id,
          observedProperty,
        ])
      )
  )
  const processingLevelById = computed(
    () =>
      new Map(
        processingLevels.value.map((processingLevel) => [
          processingLevel.id,
          processingLevel,
        ])
      )
  )
  const selectedMonitoringSiteIds = computed(
    () =>
      new Set(
        selectedMonitoringSites.value.map((monitoringSite) => monitoringSite.id)
      )
  )
  const selectedWorkspaceIds = computed(
    () => new Set(selectedWorkspaces.value.map((workspace) => workspace.id))
  )
  const selectedObservedPropertyNameSet = computed(
    () => new Set(selectedObservedPropertyNames.value)
  )
  const selectedProcessingLevelNameSet = computed(
    () => new Set(selectedProcessingLevelNames.value)
  )

  function resetState() {
    selectedMonitoringSites.value = []
    plottedDatastreams.value = []
    selectedWorkspaces.value = []
    selectedObservedPropertyNames.value = []
    selectedProcessingLevelNames.value = []
    showSummaryStatistics.value = false
    tableSearch.value = ''
    summaryStatisticsArray.value = []
    endDate.value = new Date()
    beginDate.value = new Date(new Date().getTime() - oneMonth)
    selectedDateBtnId.value = 0
    dataZoomStart.value = 0
    dataZoomEnd.value = 100
    showPlot.value = true
    showTable.value = true
    datastreamDetailLevel.value = 1
    tableHeaders.forEach((header) => {
      header.visible = header.key === 'plot'
    })
    xAxisRange.value = null
    yAxisRanges.value = {}
  }

  function matchesSelectedObservedProperty(datastream: Datastream) {
    if (selectedObservedPropertyNameSet.value.size === 0) return true

    const OPName = observedPropertyById.value.get(
      datastream.observedPropertyId
    )?.name
    return (
      OPName !== undefined && selectedObservedPropertyNameSet.value.has(OPName)
    )
  }

  function matchesSelectedProcessingLevel(datastream: Datastream) {
    if (selectedProcessingLevelNameSet.value.size === 0) return true

    const PLName = processingLevelById.value.get(
      datastream.processingLevelId
    )?.name
    return (
      PLName !== undefined && selectedProcessingLevelNameSet.value.has(PLName)
    )
  }

  function matchesSelectedMonitoringSite(datastream: Datastream) {
    return (
      selectedMonitoringSiteIds.value.size === 0 ||
      selectedMonitoringSiteIds.value.has(datastream.monitoringSiteId)
    )
  }

  function matchesSelectedWorkspace(datastream: Datastream) {
    if (selectedWorkspaceIds.value.size === 0) return true

    const monitoringSiteWorkspaceId = monitoringSiteById.value.get(
      datastream.monitoringSiteId
    )?.workspaceId

    if (!monitoringSiteWorkspaceId) return false

    return selectedWorkspaceIds.value.has(monitoringSiteWorkspaceId)
  }

  const filteredDatastreams = computed(() => {
    return datastreams.value.filter(
      (datastream) =>
        matchesSelectedMonitoringSite(datastream) &&
        matchesSelectedWorkspace(datastream) &&
        matchesSelectedObservedProperty(datastream) &&
        matchesSelectedProcessingLevel(datastream)
    )
  })

  const getOldestBeginTime = () => {
    const earliest = plottedDatastreams.value.reduce((oldest, ds) => {
      if (!ds.phenomenonBeginTime) return oldest
      const dsBeginDate = new Date(ds.phenomenonBeginTime)
      return dsBeginDate < oldest ? dsBeginDate : oldest
    }, endDate.value)

    return earliest
  }

  const dateOptions = ref([
    {
      id: 0,
      label: '1m',
      calculateBeginDate: () => {
        const now = endDate.value
        return new Date(now.getFullYear(), now.getMonth() - 1, now.getDate())
      },
    },
    {
      id: 1,
      label: '6m',
      calculateBeginDate: () => {
        const now = endDate.value
        return new Date(now.getFullYear(), now.getMonth() - 6, now.getDate())
      },
    },
    {
      id: 2,
      label: 'YTD',
      calculateBeginDate: () => {
        const now = endDate.value
        return new Date(now.getFullYear(), 0, 1)
      },
    },
    {
      id: 3,
      label: '1y',
      calculateBeginDate: () => {
        const now = endDate.value
        return new Date(now.getFullYear() - 1, now.getMonth(), now.getDate())
      },
    },
    {
      id: 4,
      label: 'all',
      calculateBeginDate: () => {
        return getOldestBeginTime()
      },
    },
  ])

  const getMostRecentEndTime = () =>
    plottedDatastreams.value.reduce((latest, ds) => {
      const dsEndDate = new Date(ds.phenomenonEndTime!)
      return dsEndDate > latest ? dsEndDate : latest
    }, new Date(0))

  interface SetDateRangeParams {
    begin?: Date
    end?: Date
    update?: boolean
    custom?: boolean
  }

  const setDateRange = async ({
    begin,
    end,
    update = true,
    custom = true,
  }: SetDateRangeParams) => {
    dataZoomStart.value = 0
    dataZoomEnd.value = 100
    xAxisRange.value = null
    yAxisRanges.value = {}
    if (begin) beginDate.value = begin
    if (end) endDate.value = end
    if (custom) selectedDateBtnId.value = -1

    if (
      update &&
      beginDate.value &&
      endDate.value &&
      plottedDatastreams.value.length
    ) {
      await refreshGraphSeriesArray(plottedDatastreams.value)
    }
  }

  const onDateBtnClick = (selectedId: number) => {
    const selectedOption = dateOptions.value.find(
      (option) => option.id === selectedId
    )
    if (selectedOption) {
      const newEndDate = getMostRecentEndTime()
      const newBeginDate = selectedOption.calculateBeginDate()

      selectedDateBtnId.value = selectedId
      setDateRange({
        begin: newBeginDate,
        end: newEndDate,
        custom: false,
      })
    }
  }

  function updateVisualization() {
    graphSeriesArray.value.forEach((series, index) => {
      series.lineColor = PlotlyColors[index % PlotlyColors.length]
    })
    summaryStatisticsArray.value = calculateSummaryStatistics(
      graphSeriesArray.value
    )
    const uirevision = graphSeriesArray.value
      .map((series) => series.id)
      .sort()
      .join('|')
    plotlyOptions.value = createPlotlyOption(graphSeriesArray.value, {
      dataZoomStart: dataZoomStart.value,
      dataZoomEnd: dataZoomEnd.value,
      xAxisRange: xAxisRange.value,
      yAxisRanges: yAxisRanges.value,
      addSummaryButton: false,
      activeRangeSelector:
        selectedDateBtnId.value >= 0 ? selectedDateBtnId.value : -1,
      showRangeSelector: false,
      uirevision,
    })
    prevIds.value = graphSeriesArray.value.map((series) => series.id)
  }

  const updateOrFetchGraphSeries = async (
    datastream: Datastream,
    start: string,
    end: string,
    refreshId: number,
    refreshKey: string
  ): Promise<boolean> => {
    const requestId = (requestCounters.value[datastream.id] ?? 0) + 1
    requestCounters.value[datastream.id] = requestId
    loadingStates.value.set(datastream.id, true)

    const isLatest = () => requestCounters.value[datastream.id] === requestId
    const isCurrentRefresh = () =>
      refreshCounter.value === refreshId &&
      activeRefreshKey.value === refreshKey
    const isStillSelected = () =>
      plottedDatastreams.value.some((ds) => ds.id === datastream.id)

    try {
      const seriesIndex = graphSeriesArray.value.findIndex(
        (series) => series.id === datastream.id
      )

      if (seriesIndex >= 0) {
        // Update the existing graph series with new data
        const data = await fetchGraphSeriesData(datastream, start, end)
        if (!data || !isLatest() || !isCurrentRefresh() || !isStillSelected()) {
          return false
        }
        const currentIndex = graphSeriesArray.value.findIndex(
          (series) => series.id === datastream.id
        )
        if (currentIndex >= 0) graphSeriesArray.value[currentIndex].data = data
      } else {
        // Add new graph series
        const newSeries = await fetchGraphSeries(datastream, start, end)
        if (
          !newSeries ||
          !isLatest() ||
          !isCurrentRefresh() ||
          !isStillSelected()
        ) {
          return false
        }
        const alreadyPresent = graphSeriesArray.value.some(
          (series) => series.id === datastream.id
        )
        if (!alreadyPresent) graphSeriesArray.value.push(newSeries)
      }

      return isLatest() && isCurrentRefresh() && isStillSelected()
    } catch (error) {
      console.error(
        `Failed to fetch or update dataset for ${datastream.id}:`,
        error
      )
      return false
    } finally {
      if (isLatest()) {
        loadingStates.value.set(datastream.id, false)
      }
    }
  }

  /** Refreshes the graphSeriesArray based on the current selection of datastreams */
  const refreshGraphSeriesArray = async (datastreams: Datastream[]) => {
    const begin = beginDate.value.toISOString()
    const end = endDate.value.toISOString()
    const ids = datastreams
      .map((ds) => ds.id)
      .sort()
      .join('|')
    const refreshId = refreshCounter.value + 1
    const refreshKey = `${begin}|${end}|${ids}`
    refreshCounter.value = refreshId
    activeRefreshKey.value = refreshKey

    // Remove graphSeries that are no longer selected
    const currentIds = new Set(datastreams.map((ds) => ds.id))
    graphSeriesArray.value = graphSeriesArray.value.filter((s) =>
      currentIds.has(s.id)
    )

    await Promise.all(
      datastreams.map((ds) =>
        updateOrFetchGraphSeries(ds, begin, end, refreshId, refreshKey)
      )
    )

    if (
      refreshCounter.value !== refreshId ||
      activeRefreshKey.value !== refreshKey
    ) {
      return
    }

    const orderById = new Map(datastreams.map((ds, index) => [ds.id, index]))
    graphSeriesArray.value.sort(
      (a, b) => (orderById.get(a.id) ?? 0) - (orderById.get(b.id) ?? 0)
    )
    updateVisualization()
  }

  // If currently selected datastreams are no longer in filteredDatastreams, deselect them
  watch(
    () => filteredDatastreams.value,
    (newDatastreams) => {
      plottedDatastreams.value = plottedDatastreams.value.filter((ds) =>
        newDatastreams.some((datastream) => datastream.id === ds.id)
      )
    },
    { deep: true }
  )

  const clearState = () => {
    graphSeriesArray.value = []
    prevIds.value = []
    showSummaryStatistics.value = false
    plotlyOptions.value = undefined
    xAxisRange.value = null
    yAxisRanges.value = {}
  }

  const setAxisRanges = (
    xRange: { start: number; end: number } | null,
    ranges?: Record<string, [number, number]>
  ) => {
    xAxisRange.value = xRange
    if (ranges) yAxisRanges.value = ranges
  }

  const setYAxisRanges = (ranges: Record<string, [number, number]>) => {
    yAxisRanges.value = ranges
  }

  const setTableVisibleColumns = (keys: string[]) => {
    const keySet = new Set(keys)
    tableHeaders.forEach((header) => {
      if (header.key === 'plot') {
        header.visible = true
        return
      }
      header.visible = keySet.has(header.key)
    })
  }

  // Update the time range to the most recent phenomenon end time
  let prevDatastreamIds = ''
  watch(
    () => plottedDatastreams.value,
    (newDs) => {
      const newDatastreamIds = JSON.stringify(newDs.map((ds) => ds.id).sort())

      if (!newDs.length || !beginDate.value || !endDate.value) {
        clearState()
      } else if (newDatastreamIds !== prevDatastreamIds) {
        const oldEnd = endDate.value
        const oldBegin = beginDate.value

        endDate.value = getMostRecentEndTime()

        const selectedOption = dateOptions.value.find(
          (option) => option.id === selectedDateBtnId.value
        )

        if (selectedOption) {
          beginDate.value = selectedOption.calculateBeginDate()
        } else {
          const timeDifference = oldEnd.getTime() - oldBegin.getTime()
          beginDate.value = new Date(endDate.value.getTime() - timeDifference)
        }

        void refreshGraphSeriesArray(newDs)
      }
      prevDatastreamIds = newDatastreamIds
    },
    { deep: true, immediate: true }
  )

  return {
    monitoringSites,
    datastreams,
    processingLevels,
    observedProperties,
    monitoringSiteById,
    observedPropertyById,
    processingLevelById,
    selectedMonitoringSites,
    selectedWorkspaces,
    selectedObservedPropertyNames,
    selectedProcessingLevelNames,
    filteredDatastreams,
    plottedDatastreams,
    beginDate,
    endDate,
    dataZoomStart,
    dataZoomEnd,
    xAxisRange,
    yAxisRanges,
    dateOptions,
    graphSeriesArray,
    plotlyOptions,
    prevIds,
    loadingStates,
    selectedDateBtnId,
    showSummaryStatistics,
    tableSearch,
    summaryStatisticsArray,
    cardHeight,
    tableHeight,
    showPlot,
    showTable,
    datastreamDetailLevel,
    tableHeaders,
    matchesSelectedObservedProperty,
    matchesSelectedProcessingLevel,
    matchesSelectedMonitoringSite,
    matchesSelectedWorkspace,
    setDateRange,
    onDateBtnClick,
    setAxisRanges,
    setYAxisRanges,
    setTableVisibleColumns,
    resetState,
  }
})
