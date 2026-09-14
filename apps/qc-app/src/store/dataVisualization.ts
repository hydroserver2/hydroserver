import { defineStore, storeToRefs } from 'pinia'
import { computed, ref, watch } from 'vue'
import { usePlotlyStore } from './plotly'
import { useObservationStore } from './observations'
import { Snackbar } from '@uwrl/qc-utils'
import { handleNewPlot } from '@/utils/plotting/plotly'
import { subtractMonths } from '@/utils/dateMath'
import {
  CUSTOM_PRESET_ID,
  DEFAULT_PRESET_ID,
  dataExtent,
  findPreset,
  presetWindow,
} from '@/utils/timeRangePresets'
import { isSnapshotId } from '@/utils/snapshotId'
import { DrawerType, useUIStore } from '@/store/userInterface'
import { useWorkingCopiesStore } from '@/store/workingCopies'
import type { SnapshotMeta } from '@/types'
import type { ObservationRecord } from '@uwrl/qc-utils'
import {
  Datastream,
  type DatastreamExtended,
  ObservedProperty,
  ProcessingLevel,
  type QualityControlHistory,
  Thing,
} from '@hydroserver/client'

export const useDataVisStore = defineStore('dataVisualization', () => {
  const {
    // resetChartZoom,
    updateOptions,
    clearChartState,
    fetchGraphSeries,
    buildGraphSeries,
    assignSeriesColors,
  } = usePlotlyStore()
  const { fetchObservationsInRange } = useObservationStore()

  const { graphSeriesArray } = storeToRefs(usePlotlyStore())

  // To only fetch these once per page
  const things = ref<Thing[]>([])
  const datastreams = ref<(Datastream & DatastreamExtended)[]>([])
  // QC histories for the workspace (each links a managed datastream to its
  // source). Drives hiding managed datastreams from the catalog and the
  // source -> managed lookup used by the "Start editing" chooser.
  const qcHistories = ref<QualityControlHistory[]>([])

  const historyManagedId = (h: QualityControlHistory): string | undefined =>
    (h as any).managedDatastreamId ?? (h as any).managedDatastream?.id
  const historySourceId = (h: QualityControlHistory): string | undefined =>
    (h as any).sourceDatastreamId ?? (h as any).sourceDatastream?.id

  /** History and catalog source for a managed datastream, if both are known. */
  function managedContext(managedId: string) {
    const history = qcHistories.value.find((h) => historyManagedId(h) === managedId)
    const sourceId = history ? historySourceId(history) : undefined
    const source = sourceId ? datastreams.value.find((d) => d.id === sourceId) : undefined
    return history && source ? { historyId: (history as any).id as string, source } : null
  }

  /** Load or reuse the working copy of every plotted managed datastream. */
  async function loadWorkingCopies() {
    const workingCopies = useWorkingCopiesStore()
    await Promise.all(
      plottedDatastreams.value
        .filter((ds) => managedDatastreamIds.value.has(ds.id))
        .map(async (ds) => {
          const context = managedContext(ds.id)
          if (!context) return
          try {
            await workingCopies.load(ds, context.source, context.historyId)
          } catch (error) {
            // Plotting still works from the committed observations.
            console.error(`Failed to load the working copy for ${ds.id}:`, error)
          }
        })
    )
  }

  /** Ids of every managed datastream; these are hidden from the catalog. */
  const managedDatastreamIds = computed(() => {
    const ids = new Set<string>()
    for (const h of qcHistories.value) {
      const id = historyManagedId(h)
      if (id) ids.add(id)
    }
    return ids
  })

  /** Add a newly-created QC history so the new managed datastream is hidden
   *  from the catalog and listed in the chooser without a full reload. */
  function addQcHistory(history: QualityControlHistory) {
    if (qcHistories.value.some((h) => (h as any).id === (history as any).id)) {
      return
    }
    qcHistories.value = [...qcHistories.value, history]
  }

  /** Drop a deleted managed datastream + its history from local state so it
   *  vanishes from the chooser and doesn't resurface in the catalog. */
  function removeManagedDatastream(historyId: string, managedId: string) {
    qcHistories.value = qcHistories.value.filter(
      (h) => (h as any).id !== historyId
    )
    datastreams.value = datastreams.value.filter((d) => d.id !== managedId)
  }

  /** Swap in a fresh copy of a datastream wherever it is referenced. */
  function replaceDatastream(ds: Datastream & DatastreamExtended) {
    datastreams.value = datastreams.value.map((d) => (d.id === ds.id ? ds : d))
    plottedDatastreams.value = plottedDatastreams.value.map((d) =>
      d.id === ds.id ? ds : d
    )
  }

  /** sourceDatastreamId -> the histories linking its managed datastreams. */
  const historiesBySource = computed(() => {
    const map = new Map<string, QualityControlHistory[]>()
    for (const h of qcHistories.value) {
      const sourceId = historySourceId(h)
      if (!sourceId) continue
      ;(map.get(sourceId) ?? map.set(sourceId, []).get(sourceId)!).push(h)
    }
    return map
  })
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

  // Time range. Until something with observations is plotted there is no
  // data to anchor a preset to, so the window is a placeholder.
  const endDate = ref<Date>(new Date())
  const beginDate = ref<Date>(subtractMonths(endDate.value, 1))
  const selectedDateBtnId = ref(DEFAULT_PRESET_ID)

  /** The active preset's window over the plotted data; null for a custom
   *  range or when nothing plotted has observations. */
  function resolvePresetWindow() {
    if (selectedDateBtnId.value === CUSTOM_PRESET_ID) return null
    const workingCopies = useWorkingCopiesStore()
    const extent = dataExtent([
      ...plottedDatastreams.value,
      ...workingCopies.extents(plottedDatastreams.value.map((d) => d.id)),
    ])
    return extent ? presetWindow(selectedDateBtnId.value, extent) : null
  }

  function resetState() {
    selectedThings.value = []
    plottedDatastreams.value = []
    qcDatastreamId.value = null
    selectedObservedPropertyNames.value = []
    selectedProcessingLevelNames.value = []
    // selectedDateBtnId is a user preference, not workspace state.
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

  /**
   * Add a frozen history snapshot as an extra line. The synthetic datastream
   * carries the snapshot id so the legend, colour assignment and visibility
   * toggles work unchanged; `refreshGraphSeriesArray` skips its fetch.
   */
  async function addSnapshotSeries(
    id: string,
    record: ObservationRecord,
    meta: SnapshotMeta
  ) {
    if (plottedDatastreams.value.some((d) => d.id === id)) return

    const qcSeries = graphSeriesArray.value.find(
      (s) => s.id === qcDatastreamId.value
    )
    plottedDatastreams.value.push({ id, name: meta.sessionLabel } as Datastream)
    graphSeriesArray.value.push({
      id,
      name: meta.sessionLabel,
      data: record,
      yAxisLabel: qcSeries?.yAxisLabel ?? '',
      color: '',
      intendedSpacingMs: qcSeries?.intendedSpacingMs ?? null,
      snapshot: meta,
    })

    assignSeriesColors(plottedDatastreams.value.map((d) => d.id))
    updateOptions()
    const { plotlyRef } = storeToRefs(usePlotlyStore())
    if (plotlyRef.value) await handleNewPlot(undefined, { preserveZoom: true })
  }

  /** Drop every snapshot line, without redrawing. Callers redraw themselves. */
  function dropSnapshotSeries() {
    if (!plottedDatastreams.value.some((d) => isSnapshotId(d.id))) return
    plottedDatastreams.value = plottedDatastreams.value.filter(
      (d) => !isSnapshotId(d.id)
    )
    graphSeriesArray.value = graphSeriesArray.value.filter(
      (s) => !isSnapshotId(s.id)
    )
  }

  /** Drop a snapshot line. Never touches the QC target. */
  async function removeSnapshotSeries(id: string) {
    const idx = plottedDatastreams.value.findIndex((d) => d.id === id)
    if (idx === -1) return
    plottedDatastreams.value.splice(idx, 1)
    graphSeriesArray.value = graphSeriesArray.value.filter((s) => s.id !== id)

    updateOptions()
    const { plotlyRef } = storeToRefs(usePlotlyStore())
    if (plotlyRef.value) await handleNewPlot(undefined, { preserveZoom: true })
  }

  /** The source datastream plus every managed datastream derived from it. */
  function sourceGroupIds(sourceId: string): string[] {
    const ids = [sourceId]
    for (const h of historiesBySource.value.get(sourceId) ?? []) {
      const id = historyManagedId(h)
      if (id) ids.push(id)
    }
    return ids
  }

  /**
   * Apply a whole "what to plot for this source" choice at once: `ids` is
   * the complete set wanted from that source's group. Group members absent
   * from `ids` are unplotted; additions are appended in `ids` order, so the
   * first-plotted-wins QC rule sees the caller's ordering.
   *
   * Batched rather than looping plot/unplot so the QC target is promoted
   * once against the final set instead of drifting through each
   * intermediate state.
   */
  async function plotSourceSelection(sourceId: string, ids: string[]) {
    const group = new Set(sourceGroupIds(sourceId))
    const wanted = ids.filter((id) => group.has(id))
    const wantedSet = new Set(wanted)

    const kept = plottedDatastreams.value.filter(
      (d) => !group.has(d.id) || wantedSet.has(d.id)
    )
    const present = new Set(kept.map((d) => d.id))
    const added = wanted
      .filter((id) => !present.has(id))
      .map((id) => datastreams.value.find((d) => d.id === id))
      .filter((d): d is Datastream & DatastreamExtended => !!d)

    const next = [...kept, ...added]
    const unchanged =
      next.length === plottedDatastreams.value.length &&
      next.every((d, i) => d.id === plottedDatastreams.value[i]?.id)
    if (unchanged) return

    const previousIndex = plottedDatastreams.value.findIndex(
      (d) => d.id === qcDatastreamId.value
    )
    plottedDatastreams.value = next
    if (!next.some((d) => d.id === qcDatastreamId.value)) {
      // Same promotion rule as `unplotDatastream`: the entry before the one
      // that left, clamped into the surviving set.
      const idx = Math.max(Math.min(previousIndex - 1, next.length - 1), 0)
      qcDatastreamId.value = next[idx]?.id ?? null
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

  /**
   * Enter editing on a freshly-created managed datastream by reusing the
   * source's already-loaded series as the managed datastream's working copy,
   * rather than adding a second, empty plotted item. The managed datastream
   * is empty on the server, so re-fetching it would blank the plot; the QC
   * editor zooms (never re-fetches), so this working copy survives until the
   * first commit materializes the managed datastream.
   */
  async function adoptManagedDatastream(managed: Datastream, sourceId: string) {
    const idx = plottedDatastreams.value.findIndex((d) => d.id === sourceId)
    if (idx >= 0) plottedDatastreams.value.splice(idx, 1, managed)
    else plottedDatastreams.value.push(managed)
    qcDatastreamId.value = managed.id

    // Re-key the loaded series to the managed datastream, keeping its data.
    const series = graphSeriesArray.value.find((s) => s.id === sourceId)
    if (series) {
      series.id = managed.id
      series.name = managed.name
    }
    const ids = new Set(plottedDatastreams.value.map((d) => d.id))
    graphSeriesArray.value = graphSeriesArray.value.filter((s) => ids.has(s.id))

    assignSeriesColors(plottedDatastreams.value.map((d) => d.id))
    updateOptions()
    const { plotlyRef } = storeToRefs(usePlotlyStore())
    if (plotlyRef.value) {
      await handleNewPlot(undefined, { preserveZoom: true })
    }
  }

  /**
   * Inverse of `adoptManagedDatastream`, for leaving the editor. Managed
   * datastreams are hidden from the catalog, so without this the Select
   * view shows a plot with no row selected. No-op when the QC target isn't
   * managed or its source isn't in the catalog. Snapshots are dropped
   * regardless: they have no place in the Select view.
   */
  async function releaseManagedDatastream() {
    dropSnapshotSeries()

    const managedId = qcDatastreamId.value
    if (!managedId) return
    const history = qcHistories.value.find(
      (h) => historyManagedId(h) === managedId
    )
    const sourceId = history ? historySourceId(history) : undefined
    const source = sourceId
      ? datastreams.value.find((d) => d.id === sourceId)
      : undefined
    if (!source) return

    const idx = plottedDatastreams.value.findIndex((d) => d.id === managedId)
    if (idx < 0) return
    // The source can already be plotted alongside its managed datastream
    // (both picked in the plot chooser); replacing would duplicate it.
    if (plottedDatastreams.value.some((d) => d.id === source.id)) {
      plottedDatastreams.value.splice(idx, 1)
    } else {
      plottedDatastreams.value.splice(idx, 1, source)
    }
    qcDatastreamId.value = source.id

    // The working copy holds uncommitted edits; `rebuildPlot` refetches.
    graphSeriesArray.value = graphSeriesArray.value.filter(
      (s) => s.id !== managedId
    )

    await rebuildPlot()
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
    await loadWorkingCopies()
    // Presets re-anchor only in the Select view. In the Edit view the
    // loaded window is the edit session's window; moving it here would
    // refetch the working copy over a different range and corrupt what
    // gets committed. `useUIStore()` is called lazily here, not at this
    // store's setup top level, since userInterface.ts imports this store
    // back and calling it during setup would recurse into a store that
    // isn't finished constructing.
    if (useUIStore().currentView !== DrawerType.Edit) {
      const presetRange = resolvePresetWindow()
      if (presetRange) {
        beginDate.value = presetRange.begin
        endDate.value = presetRange.end
      }
    }
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
          // Managed (QC) datastreams are reached through the "Start editing"
          // chooser on their source, not picked directly from the catalog.
          !managedDatastreamIds.value.has(datastream.id) &&
          matchesSelectedThing(datastream) &&
          matchesSelectedObservedProperty(datastream) &&
          matchesSelectedProcessingLevel(datastream)
      ) ?? []
    )
  })

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
    if (custom) selectedDateBtnId.value = CUSTOM_PRESET_ID

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

  const onDateBtnClick = async (selectedId: number) => {
    if (!findPreset(selectedId)) return
    selectedDateBtnId.value = selectedId
    const range = resolvePresetWindow()
    if (range) {
      await setDateRange({ begin: range.begin, end: range.end, custom: false })
    }
  }

  const updateOrFetchGraphSeries = async (
    datastream: Datastream,
    start: Date,
    end: Date
  ) => {
    try {
      // A managed datastream with a session in progress plots its working
      // copy: it spans the session window and is never re-windowed, since a
      // window change would reload it and drop the replayed edits.
      const workingCopy = useWorkingCopiesStore().get(datastream.id)
      if (workingCopy) {
        const existing = graphSeriesArray.value.find((s) => s.id === datastream.id)
        if (existing) existing.data = workingCopy.record
        else graphSeriesArray.value.push(buildGraphSeries(datastream, workingCopy.record))
        return
      }

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

    const updateOrFetchPromises = plottedDatastreams.value
      // Frozen replays: no server-side datastream to fetch.
      .filter((ds) => !isSnapshotId(ds.id))
      .map(async (ds) => {
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
    qcHistories,
    managedDatastreamIds,
    historiesBySource,
    addQcHistory,
    removeManagedDatastream,
    replaceDatastream,
    processingLevels,
    observedProperties,
    selectedThings,
    selectedObservedPropertyNames,
    selectedProcessingLevelNames,
    filteredDatastreams,
    plottedDatastreams,
    beginDate,
    endDate,
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
    refreshGraphSeriesArray,
    resetState,
    toggleDatastream,
    plotDatastream,
    unplotDatastream,
    sourceGroupIds,
    plotSourceSelection,
    clearPlottedDatastreams,
    addSnapshotSeries,
    removeSnapshotSeries,
    setPlottedDatastreams,
    setQcDatastream,
    adoptManagedDatastream,
    releaseManagedDatastream,
    rebuildPlot,
    // updateOrFetchGraphSeries,
  }
}, {
  // Persist only the user's preset choice. Catalogs, loading maps and
  // filters refetch cleanly on every load; the window resolves from the data.
  persist: {
    pick: ['selectedDateBtnId'],
    // A persisted Custom id (or a stale/unknown one) comes back with no
    // window to resolve against, so the placeholder range would apply
    // instead. Only a real preset survives hydration.
    afterHydrate: (ctx) => {
      const store = ctx.store as unknown as { selectedDateBtnId: number }
      if (!findPreset(store.selectedDateBtnId)) {
        store.selectedDateBtnId = DEFAULT_PRESET_ID
      }
    },
  },
})
