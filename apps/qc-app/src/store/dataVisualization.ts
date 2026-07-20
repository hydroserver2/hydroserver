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
    assignSeriesColors,
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
  /** True when a box/lasso selection shape is drawn on the plot, even if it captured 0 points. */
  const hasSelectionShape = ref(false)

  /** Track the loading status of each datastream to be plotted.
   * Set to true when we get a response from the API. Keyed by datastream id. */
  const loadingStates = ref(new Map<string, boolean>())

  // Time range
  const endDate = ref<Date>(new Date())
  const oneWeek = 7 * 24 * 60 * 60 * 1000
  const beginDate = ref<Date>(new Date(endDate.value.getTime() - oneWeek))
  const selectedDateBtnId = ref(0)

  // Re-derive the loaded window [beginDate, endDate] from the active
  // preset. Only `selectedDateBtnId` is persisted; beginDate/endDate keep
  // their fixed 1-week defaults until this runs. Without it, a restored
  // preset (e.g. "All") is highlighted but the first datastream load
  // fetches the stale default window until the chip is clicked again.
  function syncRangeToPreset() {
    endDate.value = new Date()
    const option = dateOptions.value.find(
      (o) => o.id === selectedDateBtnId.value
    )
    beginDate.value = option
      ? option.calculateBeginDate()
      : new Date(endDate.value.getTime() - oneWeek)
  }

  function resetState() {
    selectedThings.value = []
    plottedDatastreams.value = []
    qcDatastreamId.value = null
    selectedObservedPropertyNames.value = []
    selectedProcessingLevelNames.value = []
    // Re-apply the persisted preset so the chosen time range survives
    // workspace switches. selectedDateBtnId is intentionally NOT reset here —
    // it's a user preference, not workspace-specific state, and resetting it
    // would overwrite the persisted localStorage value.
    syncRangeToPreset()
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
    await rebuildPlot()
  }

  /** Change which datastream is under QC. Preserves the current zoom. */
  async function setQcDatastream(id: string | null) {
    if (qcDatastreamId.value === id) return
    qcDatastreamId.value = id
    updateOptions()
    const { plotlyRef } = storeToRefs(usePlotlyStore())
    if (plotlyRef.value) {
      await handleNewPlot(undefined, { preserveZoom: true })
    }
  }

  // Coalescing lock for `rebuildPlot`. Rapid checkbox toggles in the
  // Select view call `plotDatastream` in quick succession; each call
  // pushes into `plottedDatastreams` and then awaits `rebuildPlot`.
  // Without a lock, the rebuilds interleave: two concurrent
  // `refreshGraphSeriesArray` passes both see the same
  // `graphSeriesArray` before either has pushed, both enter the
  // "fetch new series" branch for the same datastream, and each
  // pushes its own copy — so the downstream `createPlotlyOption`
  // emits duplicate right-side y-axes. The `handleNewPlot` calls
  // also race, which can leave stale axis chrome from the earlier
  // render on top of the latest plot.
  //
  // Strategy: serialize rebuilds and coalesce queued ones. While a
  // rebuild is in flight, extra callers just flip `rebuildQueued`
  // and await the outcome. When the in-flight rebuild finishes and
  // there's at least one queued request, we run exactly one more
  // rebuild with the latest `plottedDatastreams` snapshot. N rapid
  // clicks therefore settle into at most two rebuilds (in-flight +
  // final), with no concurrent fetches or concurrent `newPlot`s.
  let rebuildInFlight: Promise<void> | null = null
  let rebuildQueued = false

  async function rebuildPlot(): Promise<void> {
    if (rebuildInFlight) {
      rebuildQueued = true
      try {
        await rebuildInFlight
      } catch {
        /* swallow — original error already surfaced to its caller */
      }
      // Another queued caller may have already claimed the follow-up
      // rebuild (and cleared the flag). Only the caller that still
      // sees the flag kicks off the coalesced final rebuild.
      if (!rebuildQueued) return
      rebuildQueued = false
      return rebuildPlot()
    }
    rebuildInFlight = doRebuildPlot()
    try {
      await rebuildInFlight
    } finally {
      rebuildInFlight = null
    }
    // A rebuild queued while we were running needs exactly one more
    // pass to reflect the latest state.
    if (rebuildQueued) {
      rebuildQueued = false
      return rebuildPlot()
    }
  }

  /** Rebuild the plot from scratch: drop zoom history, rebuild the
   *  graph-series array from `plottedDatastreams`, regenerate Plotly
   *  options, and re-render. Must run serialized — see the lock in
   *  `rebuildPlot` above. */
  async function doRebuildPlot() {
    hasSelectionShape.value = false
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
      calculateBeginDate: () => new Date(0),
    },
  ])

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
      // Presets always anchor end to today so the window is relative to now.
      // Set endDate first so calculateBeginDate closures read the new value.
      endDate.value = new Date()
      const newBeginDate = selectedOption.calculateBeginDate()
      selectedDateBtnId.value = selectedId
      setDateRange({ begin: newBeginDate, end: endDate.value, custom: false })
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
        // Add new graph series. The await spans a network fetch, so
        // another caller may have already pushed a series for this
        // datastream by the time we resume (the `rebuildPlot` lock
        // prevents the main rapid-click path, but other callers of
        // `refreshGraphSeriesArray` — edit history, navigation rail —
        // aren't serialized with it). Re-check before pushing so we
        // don't stack duplicate series, which would each spawn their
        // own right-side y-axis in `createPlotlyOption`.
        const newSeries = await fetchGraphSeries(datastream, start, end)
        const alreadyPresent = graphSeriesArray.value.some(
          (s) => s.id === datastream.id
        )
        if (!alreadyPresent) graphSeriesArray.value.push(newSeries)
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

    // Colour assignment runs once per refresh, after every fetch
    // has landed and the array is in legend order. Doing it here
    // (rather than inline in `fetchGraphSeries`) eliminates the
    // race where two parallel cold fetches both read the array
    // before either's push had landed and ended up claiming the
    // same colour slot — visible as two non-QC traces sharing a
    // line colour, and as different colours rolling on each reload
    // depending on which fetch resolved first.
    assignSeriesColors(plottedDatastreams.value.map((ds) => ds.id))

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
    hasSelectionShape,
    matchesSelectedObservedProperty,
    matchesSelectedProcessingLevel,
    matchesSelectedThing,
    setDateRange,
    onDateBtnClick,
    syncRangeToPreset,
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
    // Only the preset id is persisted, so the loaded window must be
    // recomputed from it after hydration — otherwise beginDate/endDate
    // keep their fixed 1-week defaults and the first datastream load
    // ignores the restored preset until the chip is clicked again.
    afterHydrate: (ctx) => {
      ;(ctx.store as unknown as { syncRangeToPreset: () => void }).syncRangeToPreset()
    },
  },
})
