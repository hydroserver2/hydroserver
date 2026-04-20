import { defineStore, storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import { usePlotlyStore } from './plotly'
import { useObservationStore } from './observations'
import { Snackbar } from '@uwrl/qc-utils'
import { handleNewPlot } from '@/utils/plotting/plotly'
import { subtractDays, subtractMonths, subtractYears } from '@/utils/dateMath'
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
  const plottedDatastreams = ref<Datastream[]>([])
  /**
   * The datastream selected to go through the quality control process.
   *
   * Stored as an id (`qcDatastreamId`) and resolved through a computed
   * (`qcDatastream`) that looks up the live object in
   * `plottedDatastreams`. This avoids stale-object bugs where
   * `qcDatastream` would hold a reference to a datastream no longer in
   * the plot — in that case the old stored-object approach silently
   * broke downstream code (notably the `QC is always black` colour
   * override). With the computed, the QC reference automatically becomes
   * `null` when the id is no longer plotted.
   */
  const qcDatastreamId = ref<string | null>(null)
  const qcDatastream = computed<Datastream | null>(() => {
    if (!qcDatastreamId.value) return null
    return (
      plottedDatastreams.value.find((ds) => ds.id === qcDatastreamId.value) ??
      null
    )
  })

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
    qcDatastreamId.value = null
    selectedObservedPropertyNames.value = []
    selectedProcessingLevelNames.value = []
    endDate.value = new Date()
    beginDate.value = new Date(new Date().getTime() - oneWeek)
    selectedDateBtnId.value = 0
    // Old watcher used to call clearChartState when plottedDatastreams
    // emptied; with the watcher gone, do it here explicitly.
    clearChartState()
  }

  async function toggleDatastream(datastream: Datastream) {
    const exists = plottedDatastreams.value.some(
      (item) => item.id === datastream.id
    )
    if (exists) await unplotDatastream(datastream.id)
    else await plotDatastream(datastream)
  }

  /** Add a datastream to the plot. Promotes it to QC if there isn't one
   *  already. Triggers an explicit plot rebuild — no watcher. */
  async function plotDatastream(ds: Datastream) {
    if (plottedDatastreams.value.some((d) => d.id === ds.id)) return
    plottedDatastreams.value.push(ds)
    if (!qcDatastreamId.value) qcDatastreamId.value = ds.id
    syncTimeRangeToQc()
    await rebuildPlot()
  }

  /** Remove a datastream from the plot. If the QC datastream is being
   *  removed, promote the previous plotted entry (or clear QC). */
  async function unplotDatastream(id: string) {
    const idx = plottedDatastreams.value.findIndex((d) => d.id === id)
    if (idx === -1) return
    plottedDatastreams.value.splice(idx, 1)
    if (qcDatastreamId.value === id) {
      qcDatastreamId.value =
        plottedDatastreams.value[Math.max(idx - 1, 0)]?.id ?? null
    }
    syncTimeRangeToQc()
    await rebuildPlot()
  }

  /** Clear every plotted datastream at once. */
  async function clearPlottedDatastreams() {
    if (!plottedDatastreams.value.length) return
    plottedDatastreams.value = []
    qcDatastreamId.value = null
    await rebuildPlot()
  }

  /** Replace the plotted set wholesale (used by URL hydration). Falls
   *  back to promoting the first item as QC when `qcId` isn't supplied
   *  or points to a datastream not in `items`. */
  async function setPlottedDatastreams(
    items: Datastream[],
    qcId?: string | null
  ) {
    plottedDatastreams.value = items.slice()
    if (qcId !== undefined) {
      const valid = items.some((d) => d.id === qcId)
      qcDatastreamId.value = valid ? (qcId ?? null) : (items[0]?.id ?? null)
    } else if (!items.some((d) => d.id === qcDatastreamId.value)) {
      qcDatastreamId.value = items[0]?.id ?? null
    }
    syncTimeRangeToQc()
    await rebuildPlot()
  }

  /** Change which datastream is under QC. Updates the working time
   *  range to the new QC's phenomenon range but preserves the current
   *  zoom (consistent with the old `PlottedDatastreams#setQcDatastream`). */
  async function setQcDatastream(id: string | null) {
    if (qcDatastreamId.value === id) return
    qcDatastreamId.value = id
    syncTimeRangeToQc()
    updateOptions()
    const { plotlyRef } = storeToRefs(usePlotlyStore())
    if (plotlyRef.value) {
      await handleNewPlot(undefined, { preserveZoom: true })
    }
  }

  /** Recompute beginDate / endDate to fit the QC datastream's range
   *  (falling back to the most recent end time across the plotted set
   *  when there's no QC). Preserves the current window size. */
  function syncTimeRangeToQc() {
    if (
      !plottedDatastreams.value.length ||
      !beginDate.value ||
      !endDate.value
    ) {
      return
    }
    const oldEnd = endDate.value
    const oldBegin = beginDate.value

    endDate.value = qcDatastream.value
      ? new Date(qcDatastream.value.phenomenonEndTime!)
      : getMostRecentEndTime()

    const selectedOption = dateOptions.value.find(
      (option) => option.id === selectedDateBtnId.value
    )
    if (selectedOption) {
      beginDate.value = selectedOption.calculateBeginDate()
    } else {
      const timeDifference = oldEnd.getTime() - oldBegin.getTime()
      beginDate.value = new Date(endDate.value.getTime() - timeDifference)
    }
  }

  /** Rebuild the plot from scratch: drop zoom history, rebuild the
   *  graph-series array from `plottedDatastreams`, regenerate Plotly
   *  options, and re-render. */
  async function rebuildPlot() {
    if (!plottedDatastreams.value.length) {
      clearChartState()
      return
    }
    const { clearZoomHistory } = usePlotlyStore()
    clearZoomHistory()
    await refreshGraphSeriesArray()
    updateOptions()
    const { plotlyRef } = storeToRefs(usePlotlyStore())
    if (plotlyRef.value) {
      await handleNewPlot()
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
    // `?? []` — during a workspace switch `datastreams.value` is
    // briefly cleared in App.vue before the new catalog lands. Without
    // the fallback this computed returns `undefined`, which then
    // propagates into `tableItems.map(...)` in DataVisDatasetsTable
    // and throws during render, tearing the table out of the DOM.
    return (
      datastreams.value?.filter(
        (datastream) =>
          matchesSelectedThing(datastream) &&
          matchesSelectedObservedProperty(datastream) &&
          matchesSelectedProcessingLevel(datastream)
      ) ?? []
    )
  })

  const getEarliestBeginTime = () =>
    plottedDatastreams.value.reduce((earliest, ds) => {
      if (!ds.phenomenonBeginTime) return earliest
      const dsBegin = new Date(ds.phenomenonBeginTime)
      return !earliest || dsBegin < earliest ? dsBegin : earliest
    }, null as Date | null)

  // All relative presets (1w/1m/6m/1y) anchor to the working window's
  // end so the range always lands on data. The subtractors clamp
  // day-of-month correctly across month/year boundaries (see
  // `src/utils/dateMath.ts`) — the old `new Date(y, m - N, d)`
  // constructor silently overflowed on `Aug 31 - 6 months` and friends.
  const dateOptions = ref([
    {
      id: 0,
      icon: 'mdi-calendar-week',
      label: '1w',
      title: 'Last week',
      calculateBeginDate: () => subtractDays(endDate.value, 7),
    },
    {
      id: 1,
      icon: 'mdi-calendar-month',
      label: '1m',
      title: 'Last month',
      calculateBeginDate: () => subtractMonths(endDate.value, 1),
    },
    {
      id: 2,
      icon: 'mdi-calendar-range',
      label: '6m',
      title: 'Last 6 months',
      calculateBeginDate: () => subtractMonths(endDate.value, 6),
    },
    {
      id: 4,
      icon: 'mdi-calendar',
      label: '1y',
      title: 'Last year',
      calculateBeginDate: () => subtractYears(endDate.value, 1),
    },
    {
      id: 3,
      icon: 'mdi-calendar-today',
      label: 'YTD',
      title: 'Year to date',
      // Jan 1 of the year containing the working window's end. The
      // editor overrides this to real calendar year in
      // `Plot.vue#onEditorDatePreset` since zoom-only semantics want
      // "this calendar year so far" regardless of the loaded window.
      calculateBeginDate: () =>
        new Date(endDate.value.getFullYear(), 0, 1),
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
    // No-op when neither bound actually moved. Every sidebar path —
    // clicking the already-active preset, date-text-field blur,
    // time-text-field blur, calendar picker confirming the current
    // day — calls this with fresh Date references whose timestamps
    // often match the current range. Without this guard each of those
    // clicks triggers a full data refetch + plot redraw that resets
    // the user's zoom for no reason.
    const sameBegin =
      !begin || begin.getTime() === beginDate.value?.getTime()
    const sameEnd = !end || end.getTime() === endDate.value?.getTime()
    if (sameBegin && sameEnd) return

    if (begin) beginDate.value = begin
    if (end) endDate.value = end
    if (custom) selectedDateBtnId.value = -1

    if (
      update &&
      beginDate.value &&
      endDate.value &&
      plottedDatastreams.value.length
    ) {
      const { redraw, clearZoomHistory } = usePlotlyStore()
      await refreshGraphSeriesArray()
      // A date-filter change refetches data and drops the zoom window —
      // the recorded zoom stack refers to the OLD time range and would
      // be meaningless after redraw, so clear it.
      clearZoomHistory()
      // The user explicitly changed the date filter — they expect the
      // new window to actually apply, so opt out of the zoom-preserving
      // path in `redraw` (which otherwise copies the live range over
      // the fresh layout and the plot would stay on the old window).
      redraw(false, false)
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

    const results = await Promise.all(updateOrFetchPromises)

    // `updateOrFetchGraphSeries` pushes new series into `graphSeriesArray`
    // in whatever order the parallel fetches resolve. For URL preload
    // (multiple datastream ids loading cold at once) that completion
    // order usually doesn't match the user-facing `plottedDatastreams`
    // order — so the plot iterated traces out of legend order, breaking
    // the draw-layering and per-series colour mapping. Re-sort the
    // array to mirror `plottedDatastreams` now that every fetch has
    // landed; the iteration order downstream is the legend order again.
    const indexByDs = new Map(
      plottedDatastreams.value.map((ds, i) => [ds.id, i])
    )
    graphSeriesArray.value.sort(
      (a, b) => (indexByDs.get(a.id) ?? 0) - (indexByDs.get(b.id) ?? 0)
    )

    return results
  }


  // The old watcher on `plottedDatastreams` that computed prev/next id
  // diffs and forked between "update time range" and "rebuild plot"
  // has been replaced by explicit actions:
  //   - plotDatastream / unplotDatastream / toggleDatastream
  //   - clearPlottedDatastreams
  //   - setPlottedDatastreams (URL hydration)
  //   - setQcDatastream
  // Each mutation site now calls the action so side effects (time range
  // sync, graph-series rebuild, zoom history clear, Plotly re-render)
  // happen inline and in a predictable order — no reactive cascade.

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
    qcDatastreamId,
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
    plotDatastream,
    unplotDatastream,
    clearPlottedDatastreams,
    setPlottedDatastreams,
    setQcDatastream,
    rebuildPlot,
    // updateOrFetchGraphSeries,
  }
}, {
  // Persist only the user's time-range preset choice. Everything else
  // in this store (server catalogs, in-flight loading maps, live
  // filters) should refetch cleanly on every load — persisting them
  // would surface stale data after catalog or role changes. `dateOptions`
  // in particular can't be serialized because it carries closure
  // functions (`calculateBeginDate`).
  persist: {
    pick: ['selectedDateBtnId'],
  },
})
