import { defineStore, storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import { usePlotlyStore } from './plotly'
import { useObservationStore } from './observations'
import { Snackbar } from '@uwrl/qc-utils'
import { handleNewPlot } from '@/utils/plotting/plotly'
import {
  Datastream,
  type DatastreamExtended,
  ObservedProperty,
  ProcessingLevel,
  Thing,
} from '@hydroserver/client'

export const useDataVisStore = defineStore('dataVisualization', () => {
  const {
    // resetChartZoom,
    updateOptions,
    clearChartState,
    fetchGraphSeries,
  } = usePlotlyStore()
  const { fetchObservationsInRange } = useObservationStore()

  const { graphSeriesArray } = storeToRefs(usePlotlyStore())

  // To only fetch these once per page
  const things = ref<Thing[]>([])
  const datastreams = ref<(Datastream & DatastreamExtended)[]>([])
  const observedProperties = ref<ObservedProperty[]>([])
  const processingLevels = ref<ProcessingLevel[]>([])

  // Filters
  const selectedThings = ref<Thing[]>([])
  const selectedObservedPropertyNames = ref<string[]>([])
  const selectedProcessingLevelNames = ref<string[]>([])

  // Datasets
  /** The datastream selected to go through the quality control process */
  const qcDatastream = ref<Datastream | null>(null)
  const plottedDatastreams = ref<Datastream[]>([])

  // Qualifiers
  const qualifierSet = ref<Set<string>>(new Set())
  const selectedQualifier = ref('')

  const selectedData = ref<number[] | null>(null)

  /** Track the loading status of each datastream to be plotted.
   * Set to true when we get a response from the API. Keyed by datastream id. */
  const loadingStates = ref(new Map<string, boolean>())

  // Time range
  const endDate = ref<Date>(new Date())
  const oneWeek = 7 * 24 * 60 * 60 * 1000
  const beginDate = ref<Date>(new Date(endDate.value.getTime() - oneWeek))
  const selectedDateBtnId = ref(0)

  function resetState() {
    selectedThings.value = []
    plottedDatastreams.value = []
    selectedObservedPropertyNames.value = []
    selectedProcessingLevelNames.value = []
    endDate.value = new Date()
    beginDate.value = new Date(new Date().getTime() - oneWeek)
    selectedDateBtnId.value = 0
    // resetChartZoom()
  }

  function toggleDatastream(datastream: Datastream) {
    const index = plottedDatastreams.value.findIndex(
      (item) => item.id === datastream.id
    )
    if (index === -1) {
      plottedDatastreams.value.push(datastream)
      if (!qcDatastream.value) {
        qcDatastream.value = datastream
      }
    } else {
      plottedDatastreams.value.splice(index, 1)
      if (qcDatastream.value?.id == datastream.id) {
        qcDatastream.value =
          plottedDatastreams.value[Math.max(index - 1, 0)] || null
      }
    }
  }

  // Note: datastreams are loaded with `expand_related: true`, so these carry
  // nested `thing`/`observedProperty`/`processingLevel` objects rather than
  // the flat `*Id` fields on the bare Datastream type.
  function matchesSelectedObservedProperty(
    datastream: Datastream & DatastreamExtended
  ) {
    if (selectedObservedPropertyNames.value.length === 0) return true
    const name = datastream.observedProperty?.name
    return !!name && selectedObservedPropertyNames.value.includes(name)
  }

  function matchesSelectedProcessingLevel(
    datastream: Datastream & DatastreamExtended
  ) {
    if (selectedProcessingLevelNames.value.length === 0) return true
    const def = datastream.processingLevel?.definition
    return !!def && selectedProcessingLevelNames.value.includes(def)
  }

  function matchesSelectedThing(datastream: Datastream & DatastreamExtended) {
    if (selectedThings.value.length === 0) return true
    const thingId = datastream.thing?.id
    return (
      !!thingId && selectedThings.value.some((thing) => thing.id === thingId)
    )
  }

  const filteredDatastreams = computed(() => {
    return datastreams.value?.filter(
      (datastream) =>
        matchesSelectedThing(datastream) &&
        matchesSelectedObservedProperty(datastream) &&
        matchesSelectedProcessingLevel(datastream)
    )
  })

  const getEarliestBeginTime = () =>
    plottedDatastreams.value.reduce((earliest, ds) => {
      if (!ds.phenomenonBeginTime) return earliest
      const dsBegin = new Date(ds.phenomenonBeginTime)
      return !earliest || dsBegin < earliest ? dsBegin : earliest
    }, null as Date | null)

  const dateOptions = ref([
    {
      id: 0,
      icon: 'mdi-calendar-week',
      label: '1w',
      title: 'Last week',
      calculateBeginDate: () => {
        const now = endDate.value
        return new Date(now.getFullYear(), now.getMonth(), now.getDate() - 7)
      },
    },
    {
      id: 1,
      icon: 'mdi-calendar-month',
      label: '1m',
      title: 'Last month',
      calculateBeginDate: () => {
        const now = endDate.value
        return new Date(now.getFullYear(), now.getMonth() - 1, now.getDate())
      },
    },
    {
      id: 2,
      icon: 'mdi-calendar-range',
      label: '6m',
      title: 'Last 6 months',
      calculateBeginDate: () => {
        const now = endDate.value
        return new Date(now.getFullYear(), now.getMonth() - 6, now.getDate())
      },
    },
    {
      id: 3,
      icon: 'mdi-calendar-today',
      label: 'YTD',
      title: 'Year to date',
      calculateBeginDate: () => {
        const now = endDate.value
        return new Date(now.getFullYear(), 0, 1)
      },
    },
    {
      id: 4,
      icon: 'mdi-calendar',
      label: '1y',
      title: 'Last year',
      calculateBeginDate: () => {
        const now = endDate.value
        return new Date(now.getFullYear() - 1, now.getMonth(), now.getDate())
      },
    },
    {
      id: 5,
      icon: 'mdi-infinity',
      label: 'All',
      title: 'Full history',
      calculateBeginDate: () => {
        const earliest = getEarliestBeginTime()
        if (earliest) return earliest
        // Fallback: 10 years back if no plotted series / missing metadata.
        const now = endDate.value
        return new Date(now.getFullYear() - 10, now.getMonth(), now.getDate())
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
    // resetChartZoom()
    if (begin) beginDate.value = begin
    if (end) endDate.value = end
    if (custom) selectedDateBtnId.value = -1

    if (
      update &&
      beginDate.value &&
      endDate.value &&
      plottedDatastreams.value.length
    ) {
      const { redraw } = usePlotlyStore()
      await refreshGraphSeriesArray()
      redraw()
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

  const updateOrFetchGraphSeries = async (
    datastream: Datastream,
    start: Date,
    end: Date
  ) => {
    try {
      const seriesIndex = graphSeriesArray.value.findIndex(
        (series) => series.id === datastream.id
      )

      if (seriesIndex >= 0) {
        // Update the existing graph series with new data
        const obsRecord = await fetchObservationsInRange(
          datastream,
          start,
          end
        ).catch((error) => {
          Snackbar.error('Failed to fetch observations')
          console.error('Failed to fetch observations:', error)
          return null
        })
        if (obsRecord && graphSeriesArray.value[seriesIndex]) {
          graphSeriesArray.value[seriesIndex].data = obsRecord
        }
      } else {
        // Add new graph series
        const newSeries = await fetchGraphSeries(datastream, start, end)
        graphSeriesArray.value.push(newSeries)
      }
    } catch (error) {
      console.error(
        `Failed to fetch or update dataset for ${datastream.id}:`,
        error
      )
    } finally {
      loadingStates.value.set(datastream.id, false)
    }
  }

  /** Refreshes the graphSeriesArray based on the current selection of datastreams */
  const refreshGraphSeriesArray = async () => {
    // Remove graphSeries that are no longer selected
    const currentIds = new Set(plottedDatastreams.value.map((ds) => ds.id))
    graphSeriesArray.value = graphSeriesArray.value.filter((s) =>
      currentIds.has(s.id)
    )

    const updateOrFetchPromises = plottedDatastreams.value.map(async (ds) => {
      loadingStates.value.set(ds.id, true)
      return updateOrFetchGraphSeries(ds, beginDate.value, endDate.value)
    })

    return Promise.all(updateOrFetchPromises)
  }

  // TODO: avoid using watchers!

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

  // Set the time range to the qcDatastream's endTime if there is one, otherwise
  // update the time range to the most recent phenomenon endTime
  let prevDatastreamIds = ''
  let prevSelectedDatastreamId = ''

  watch(
    () => plottedDatastreams.value,
    async (newDs) => {
      const newDatastreamIds = JSON.stringify(newDs.map((ds) => ds.id).sort())

      if (!newDs.length || !beginDate.value || !endDate.value) {
        clearChartState()
      } else if (
        newDatastreamIds !== prevDatastreamIds ||
        prevSelectedDatastreamId !== qcDatastream.value?.id
      ) {
        const oldEnd = endDate.value
        const oldBegin = beginDate.value

        endDate.value = qcDatastream.value
          ? new Date(qcDatastream.value.phenomenonEndTime!)
          : getMostRecentEndTime()

        const selectedOption = dateOptions.value.find(
          (option) => option.id === selectedDateBtnId.value
        )

        // Keep the previous time window size, now with different start and end times
        if (selectedOption) {
          beginDate.value = selectedOption.calculateBeginDate()
        } else {
          const timeDifference = oldEnd.getTime() - oldBegin.getTime()
          beginDate.value = new Date(endDate.value.getTime() - timeDifference)
        }

        if (newDatastreamIds !== prevDatastreamIds) {
          await refreshGraphSeriesArray()
          // Call above will make data available and show plot before updateOptions
          updateOptions()

          const { plotlyRef } = storeToRefs(usePlotlyStore())
          if (plotlyRef.value) {
            handleNewPlot()
          }
        }
      }
      prevDatastreamIds = newDatastreamIds
      prevSelectedDatastreamId = qcDatastream.value?.id || ''
    },
    { deep: true, immediate: true }
  )

  // TODO: Revisit this. Does it make sense to convert qualifierValue to a string in preprocessing
  // just to split it into an array of strings here? Maybe just save it as an array of strings instead
  function updateQualifiers() {
    const series = graphSeriesArray.value.find(
      (s) => s.id === qcDatastream.value?.id
    )

    qualifierSet.value = new Set([])
    if (series) {
      // TODO
      // for (const dataPoint of series.data) {
      //   if (typeof dataPoint.qualifierValue === 'string') {
      //     // Split the qualifierValue string into individual qualifiers and add them to the set
      //     dataPoint.qualifierValue
      //       .split(',')
      //       .forEach((qualifier) => qualifierSet.value.add(qualifier.trim()))
      //   }
      // }
    }
    selectedQualifier.value = ''
  }

  // Update qualifiers whenever the qcDatastream's graphSeries has finished loading
  let previousLoadingState = false
  watch(
    [loadingStates],
    () => {
      const currentId = qcDatastream.value?.id
      if (!currentId) return
      const currentLoadingState = !!loadingStates.value.get(currentId)
      if (!currentLoadingState && previousLoadingState) updateQualifiers()
      previousLoadingState = currentLoadingState
    },
    { deep: true }
  )

  return {
    things,
    datastreams,
    processingLevels,
    observedProperties,
    selectedThings,
    selectedObservedPropertyNames,
    selectedProcessingLevelNames,
    filteredDatastreams,
    plottedDatastreams,
    beginDate,
    endDate,
    dateOptions,
    loadingStates,
    selectedDateBtnId,
    qcDatastream,
    qualifierSet,
    selectedQualifier,
    selectedData,
    matchesSelectedObservedProperty,
    matchesSelectedProcessingLevel,
    matchesSelectedThing,
    setDateRange,
    onDateBtnClick,
    refreshGraphSeriesArray,
    resetState,
    toggleDatastream,
    // updateOrFetchGraphSeries,
  }
})
