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
  presetAroundWindow,
  presetWindow,
  type TimeWindow,
} from '@/utils/timeRangePresets'
import { isSnapshotId } from '@/utils/snapshotId'
import { isContextId, makeContextId } from '@/utils/contextSeriesId'
import { useWorkingCopiesStore } from '@/store/workingCopies'
import { useQcSessionStore } from '@/store/qcSession'
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
        .filter(
          (ds) =>
            ds.id !== qcDatastreamId.value &&
            managedDatastreamIds.value.has(ds.id)
        )
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

  /** Drop copies no longer plotted, which would hide drafts saved since;
   *  the QC target keeps its copy for the editor. */
  function invalidateUnplottedWorkingCopies() {
    const workingCopies = useWorkingCopiesStore()
    const plotted = new Set(seriesDatastreams.value.map((d) => d.id))
    for (const { id } of graphSeriesArray.value) {
      if (plotted.has(id) || id === qcDatastreamId.value) continue
      if (managedDatastreamIds.value.has(id)) workingCopies.invalidate(id)
    }
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

  /** The datastream being edited. Set only by the edit flow, null in Select. */
  const qcDatastreamId = ref<string | null>(null)
  const qcDatastream = computed(() =>
    qcDatastreamId.value
      ? (datastreams.value.find((ds) => ds.id === qcDatastreamId.value) ?? null)
      : null
  )

  /** The edit target's source datastream. */
  const editSourceDatastream = computed(() =>
    qcDatastreamId.value
      ? (managedContext(qcDatastreamId.value)?.source ?? null)
      : null
  )

  /** Whether the edit target's source is drawn around it as context. A
   *  user preference, like the context range. */
  const showSourceContext = ref(true)

  /** Turn the source context on or off, redrawing when editing. */
  async function setShowSourceContext(show: boolean) {
    if (show === showSourceContext.value) return
    showSourceContext.value = show
    if (qcDatastreamId.value) await rebuildPlot()
  }

  /** The grey source context drawn around the edit target, cut around the
   *  session window: the source under a context id of its own (see
   *  `makeContextId`), so the user can also plot the source itself as an
   *  ordinary series. Both read the source's data. Null when context is off. */
  const sourceContextDatastream = computed<Datastream | null>(() => {
    const source = editSourceDatastream.value
    if (!source || !showSourceContext.value) return null
    return { ...source, id: makeContextId(source.id) } as Datastream
  })

  /** What the plot draws, in order: edit target, its source context, then
   *  plotted. */
  const seriesDatastreams = computed<Datastream[]>(() => {
    const edit = qcDatastream.value
    if (!edit) return plottedDatastreams.value
    const pinned: Datastream[] = [edit]
    if (sourceContextDatastream.value) pinned.push(sourceContextDatastream.value)
    const pinnedIds = new Set(pinned.map((d) => d.id))
    return [
      ...pinned,
      ...plottedDatastreams.value.filter((d) => !pinnedIds.has(d.id)),
    ]
  })

  // Qualifiers
  const qualifierSet = ref<Set<string>>(new Set())
  const selectedQualifier = ref('')

  const selectedData = ref<number[] | null>(null)
  /** True when a box/lasso selection shape is drawn on the plot, even if it captured 0 points. */
  const hasSelectionShape = ref(false)

  /** Plot loads and draws started and not yet finished. */
  const pendingPlotWork = ref(0)

  /** Run `work` counted as pending plot work, see `isEditorReady`. */
  async function trackPlotWork(work: () => Promise<void>): Promise<void> {
    pendingPlotWork.value++
    try {
      await work()
    } finally {
      pendingPlotWork.value--
    }
  }

  /** Track the loading status of each datastream to be plotted.
   * Set to true when we get a response from the API. Keyed by datastream id. */
  const loadingStates = ref(new Map<string, boolean>())

  // Time range. Until something with observations is plotted there is no
  // data to anchor a preset to, so the window is a placeholder.
  const endDate = ref<Date>(new Date())
  const beginDate = ref<Date>(subtractMonths(endDate.value, 1))
  /** The Select view's Time range preset. */
  const selectedDateBtnId = ref(DEFAULT_PRESET_ID)
  /** The editor's Context range preset, remembered apart from the Select
   *  view's so neither moves the other. */
  const contextPresetId = ref(DEFAULT_PRESET_ID)
  /** The preset the loaded range follows: Context while an edit target is
   *  set, else the Select view's Time range. */
  const activePresetId = computed({
    get: () =>
      qcDatastreamId.value ? contextPresetId.value : selectedDateBtnId.value,
    set: (id: number) => {
      if (qcDatastreamId.value) contextPresetId.value = id
      else selectedDateBtnId.value = id
    },
  })

  /** The edit session's window, while an edit target has one. */
  const editSessionWindow = computed<TimeWindow | null>(() => {
    if (!qcDatastreamId.value) return null
    const sessions = useQcSessionStore()
    const s = sessions.viewedSession ?? sessions.inProgressSession
    return s
      ? {
          begin: new Date(s.phenomenonTimeStart),
          end: new Date(s.phenomenonTimeEnd),
        }
      : null
  })

  /** The active preset's window; null for a custom range or when there is
   *  nothing to anchor it to. The single place that picks the rule: around
   *  the session window while editing one, otherwise back from the context
   *  data's end. */
  function resolvePresetWindow() {
    if (activePresetId.value === CUSTOM_PRESET_ID) return null
    const workingCopies = useWorkingCopiesStore()
    const context = seriesDatastreams.value.filter(
      (d) => d.id !== qcDatastreamId.value && !isSnapshotId(d.id)
    )
    const extent = dataExtent([
      ...context,
      ...workingCopies.extents(context.map((d) => d.id)),
    ])
    const sessionWindow = editSessionWindow.value
    if (sessionWindow) {
      return presetAroundWindow(activePresetId.value, sessionWindow, extent)
    }
    return extent ? presetWindow(activePresetId.value, extent) : null
  }

  function resetState() {
    selectedThings.value = []
    plottedDatastreams.value = []
    qcDatastreamId.value = null
    selectedObservedPropertyNames.value = []
    selectedProcessingLevelNames.value = []
    // Working copies belong to the workspace being left.
    useWorkingCopiesStore().clear()
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

  /** Add a datastream to the plot. Triggers an explicit plot rebuild, no watcher. */
  async function plotDatastream(ds: Datastream) {
    if (plottedDatastreams.value.some((d) => d.id === ds.id)) return
    plottedDatastreams.value.push(ds)
    await rebuildPlot()
  }

  /** Remove a datastream from the plot. */
  async function unplotDatastream(id: string) {
    const idx = plottedDatastreams.value.findIndex((d) => d.id === id)
    if (idx === -1) return
    plottedDatastreams.value.splice(idx, 1)
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

    orderAndColorSeries()
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
   * from `ids` are unplotted; additions are appended in `ids` order.
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

    plottedDatastreams.value = next
    await rebuildPlot()
  }

  /** Clear every plotted datastream at once. */
  async function clearPlottedDatastreams() {
    if (!plottedDatastreams.value.length) return
    plottedDatastreams.value = []
    await rebuildPlot()
  }

  /** Replace the plotted set wholesale (used by URL hydration). */
  async function setPlottedDatastreams(items: Datastream[]) {
    plottedDatastreams.value = items.slice()
    await rebuildPlot()
  }

  /** Start editing `managedId`. Its data arrives later via `setEditRecord`. */
  async function setEditTarget(managedId: string) {
    dropSnapshotSeries()
    if (managedId !== qcDatastreamId.value) {
      // The session store describes the previous target until its sessions
      // load; drop it so its window is never drawn over this one.
      useQcSessionStore().reset()
      // The rebuild below keeps zoom for an edit target, so drop viewports
      // from the previous view or target here.
      usePlotlyStore().clearZoomHistory()
    }
    qcDatastreamId.value = managedId
    await rebuildPlot()
  }

  /** Put the edit target's record on the plot, adding its series if needed. */
  function setEditRecord(record: ObservationRecord): Promise<void> {
    return trackPlotWork(async () => {
      const edit = qcDatastream.value
      if (!edit) return
      const existing = graphSeriesArray.value.find((s) => s.id === edit.id)
      if (existing) {
        existing.data = record
        await usePlotlyStore().redraw()
        return
      }
      graphSeriesArray.value.push(buildGraphSeries(edit, record))
      orderAndColorSeries()
      updateOptions()
      const { plotlyRef } = storeToRefs(usePlotlyStore())
      if (plotlyRef.value) await handleNewPlot(undefined, { preserveZoom: true })
    })
  }

  /** Stop editing. Plotted datastreams stay as they were. */
  async function clearEditTarget() {
    dropSnapshotSeries()
    const id = qcDatastreamId.value
    if (!id) return
    // Unsaved edits live only on the working copy.
    useWorkingCopiesStore().invalidate(id)
    qcDatastreamId.value = null
    graphSeriesArray.value = graphSeriesArray.value.filter((s) => s.id !== id)
    await rebuildPlot()
  }

  // Plot loads (a rebuild, or a reload of the context range) run one at a
  // time. Concurrent `refreshGraphSeriesArray` passes would both push a series
  // for the same new datastream (duplicate right-side axes) and race their
  // draws. A request made while one runs joins the single queued follow-up,
  // which is a rebuild if any joined request was one, so N rapid clicks settle
  // into at most two loads. Every caller resolves only once a load that
  // started after its change has finished.
  type PlotLoadKind = 'rebuild' | 'range'
  /** Guard against a range that never settles. */
  const MAX_RANGE_PASSES = 5
  let loadInFlight: Promise<void> | null = null
  let queuedLoad: { kind: PlotLoadKind; promise: Promise<void> } | null = null
  /** The `loadKey` the series were last loaded for. */
  let loadedRangeKey: string | null = null

  const rangeKey = (begin: Date, end: Date) =>
    `${begin.getTime()}-${end.getTime()}`

  /** What a load covers: the range, plus the session window the source's
   *  context is cut around. */
  const loadKey = () => {
    const w = editSessionWindow.value
    return (
      rangeKey(beginDate.value, endDate.value) +
      (w ? `|${rangeKey(w.begin, w.end)}` : '')
    )
  }

  function queuePlotLoad(kind: PlotLoadKind): Promise<void> {
    return trackPlotWork(() => nextPlotLoad(kind))
  }

  function nextPlotLoad(kind: PlotLoadKind): Promise<void> {
    // Check the queue first: the in-flight load clears `loadInFlight` a couple
    // of microtasks before its follow-up starts, and a caller landing in that
    // gap would otherwise start a second concurrent load.
    if (queuedLoad) {
      if (kind === 'rebuild') queuedLoad.kind = 'rebuild'
      return queuedLoad.promise
    }
    if (!loadInFlight) return startPlotLoad(kind)
    const queued = { kind, promise: Promise.resolve() }
    queued.promise = loadInFlight
      .catch(() => undefined)
      .then(() => {
        queuedLoad = null
        return startPlotLoad(queued.kind)
      })
    queuedLoad = queued
    return queued.promise
  }

  function startPlotLoad(kind: PlotLoadKind): Promise<void> {
    const run: Promise<void> = (
      kind === 'rebuild' ? doRebuildPlot() : doReloadRange()
    ).finally(() => {
      if (loadInFlight === run) loadInFlight = null
    })
    loadInFlight = run
    return run
  }

  function rebuildPlot(): Promise<void> {
    return queuePlotLoad('rebuild')
  }

  /** Load every series for the current range. Responses for a range that
   *  moved meanwhile are dropped, so load again until it holds still. */
  async function loadCurrentRange(): Promise<void> {
    for (let pass = 0; pass < MAX_RANGE_PASSES; pass++) {
      const begin = beginDate.value
      const end = endDate.value
      const key = loadKey()
      await refreshGraphSeriesArray()
      if (isCurrentRange(begin, end)) {
        loadedRangeKey = key
        return
      }
    }
    console.warn(
      `Plot range still moving after ${MAX_RANGE_PASSES} loads, drawing anyway.`
    )
  }

  /** Rebuild the plot from scratch: rebuild the graph-series array from
   *  `seriesDatastreams`, regenerate Plotly options, and re-render. Select
   *  drops the zoom; the editor keeps it, since context changes never move
   *  the user's view of the session. Runs as a plot load, see above. */
  async function doRebuildPlot(): Promise<void> {
    hasSelectionShape.value = false
    if (!seriesDatastreams.value.length) {
      invalidateUnplottedWorkingCopies()
      clearChartState()
      loadedRangeKey = null
      return
    }
    const keepZoom = !!qcDatastreamId.value
    if (!keepZoom) usePlotlyStore().clearZoomHistory()
    await loadWorkingCopies()
    const presetRange = resolvePresetWindow()
    if (presetRange) {
      beginDate.value = presetRange.begin
      endDate.value = presetRange.end
    }
    await loadCurrentRange()
    updateOptions()
    const { plotlyRef } = storeToRefs(usePlotlyStore())
    if (plotlyRef.value) {
      await handleNewPlot(undefined, { preserveZoom: keepZoom })
    }
  }

  /** Reload the series for a new range and redraw. Skipped when an earlier
   *  load already caught up with the range. */
  async function doReloadRange(): Promise<void> {
    if (!seriesDatastreams.value.length) return
    if (loadedRangeKey === loadKey()) return
    await loadCurrentRange()
    const { redraw, clearZoomHistory } = usePlotlyStore()
    if (qcDatastreamId.value) {
      // Context reload in the editor: the user's view of the session stays put.
      await redraw(false, true)
    } else {
      // The zoom stack refers to the old range, so drop it and let the new
      // range apply instead of copying the live range over it.
      clearZoomHistory()
      await redraw(false, false)
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
    // `?? []`: during a workspace switch `datastreams.value` is
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
    // No-op when neither bound actually moved. Every sidebar path
    // (clicking the already-active preset, date-text-field blur,
    // time-text-field blur, calendar picker confirming the current
    // day) calls this with fresh Date references whose timestamps
    // often match the current range. Without this guard each of those
    // clicks triggers a full data refetch + plot redraw that resets
    // the user's zoom for no reason.
    const sameBegin =
      !begin || begin.getTime() === beginDate.value?.getTime()
    const sameEnd = !end || end.getTime() === endDate.value?.getTime()
    if (sameBegin && sameEnd) return

    if (begin) beginDate.value = begin
    if (end) endDate.value = end
    if (custom) activePresetId.value = CUSTOM_PRESET_ID

    if (update && seriesDatastreams.value.length) {
      await queuePlotLoad('range')
    }
  }

  /** Load the range the active preset resolves to now. A no-op when it
   *  already matches. */
  const applyActivePreset = async () => {
    const range = resolvePresetWindow()
    if (range) {
      await setDateRange({ begin: range.begin, end: range.end, custom: false })
    }
  }

  const onDateBtnClick = async (selectedId: number) => {
    if (!findPreset(selectedId)) return
    activePresetId.value = selectedId
    await applyActivePreset()
  }

  // The editor loads its context before the session is known, so re-anchor
  // the preset once the window arrives or changes. The source waits for the
  // window (its context is cut around it), so its series can appear here, and
  // only a rebuild adds traces. The rebuild resolves the preset itself, never
  // fetches the edit target, keeps the zoom, and reloads only what the cache
  // lacks. A watch rather than a call at each session store write: the window
  // follows sessions being applied, a session viewed, a return to the current
  // one and a failed view reverted. It queues behind any load.
  watch(
    () =>
      editSessionWindow.value &&
      rangeKey(editSessionWindow.value.begin, editSessionWindow.value.end),
    (key) => {
      if (!key) return
      rebuildPlot().catch((error) => {
        console.error('Failed to reload the context range:', error)
        Snackbar.error('Could not reload the context range')
      })
    }
  )

  /** True while editing once the session window is known, the edit record is
   *  on the plot, no session is opening, and every plot load and draw started
   *  so far (including the re-anchor around the window) has finished. */
  const isEditorReady = computed(
    (): boolean =>
      pendingPlotWork.value === 0 &&
      !useQcSessionStore().isSwitchingSession &&
      !!editSessionWindow.value &&
      graphSeriesArray.value.some((s) => s.id === qcDatastreamId.value)
  )

  const isCurrentRange = (start: Date, end: Date) =>
    start.getTime() === beginDate.value.getTime() &&
    end.getTime() === endDate.value.getTime()

  /** The latest load per datastream; only it may clear the loading flag. */
  const latestLoads = new Map<string, object>()

  const updateOrFetchGraphSeries = async (
    datastream: Datastream,
    start: Date,
    end: Date,
    exclude?: TimeWindow
  ) => {
    const load = {}
    latestLoads.set(datastream.id, load)
    // The source context series reads the source's own data.
    const fetchDs = isContextId(datastream.id)
      ? (editSourceDatastream.value ?? datastream)
      : datastream
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
          fetchDs,
          start,
          end,
          exclude
        ).catch((error) => {
          Snackbar.error('Failed to fetch observations')
          console.error('Failed to fetch observations:', error)
          return null
        })
        // The range moved while fetching: the request for the new range writes.
        if (!isCurrentRange(start, end)) return
        // Re-find: the array may have been filtered while fetching.
        const series = graphSeriesArray.value.find((s) => s.id === datastream.id)
        if (obsRecord && series) series.data = obsRecord
      } else {
        const newSeries = await fetchGraphSeries(
          datastream,
          start,
          end,
          exclude,
          fetchDs
        )
        if (!isCurrentRange(start, end)) return
        // Callers of `refreshGraphSeriesArray` outside the plot load queue
        // (the edit history reload) may have pushed this series meanwhile. A
        // duplicate would spawn its own right-side y-axis.
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
      if (latestLoads.get(datastream.id) === load) {
        latestLoads.delete(datastream.id)
        loadingStates.value.set(datastream.id, false)
      }
    }
  }

  /** Sort `graphSeriesArray` to match `seriesDatastreams` and assign colours.
   *  Colour assignment excludes the edit target and its source so context
   *  colours stay stable between Select and Edit. Re-sorting after every
   *  fetch avoids the race where parallel cold fetches land out of order
   *  and the plot's draw-layering / legend order goes out of sync. */
  function orderAndColorSeries() {
    const order = seriesDatastreams.value
    const indexByDs = new Map(order.map((ds, i) => [ds.id, i]))
    graphSeriesArray.value.sort(
      (a, b) => (indexByDs.get(a.id) ?? 0) - (indexByDs.get(b.id) ?? 0)
    )
    const pinned = new Set([qcDatastreamId.value, sourceContextDatastream.value?.id])
    assignSeriesColors(order.map((ds) => ds.id).filter((id) => !pinned.has(id)))
  }

  /** Refreshes the graphSeriesArray based on the current selection of datastreams */
  const refreshGraphSeriesArray = async () => {
    // Remove graphSeries that are no longer selected
    invalidateUnplottedWorkingCopies()
    const currentIds = new Set(seriesDatastreams.value.map((ds) => ds.id))
    graphSeriesArray.value = graphSeriesArray.value.filter((s) =>
      currentIds.has(s.id)
    )

    // The source is drawn only around the session window, so it waits for
    // the window and never fetches what lies inside it.
    const sourceId = sourceContextDatastream.value?.id
    const sessionWindow = editSessionWindow.value
    const updateOrFetchPromises = seriesDatastreams.value
      // Snapshots have no server datastream; the edit target's data belongs to the session.
      .filter((ds) => !isSnapshotId(ds.id) && ds.id !== qcDatastreamId.value)
      .filter((ds) => ds.id !== sourceId || !!sessionWindow)
      .map(async (ds) => {
        loadingStates.value.set(ds.id, true)
        return updateOrFetchGraphSeries(
          ds,
          beginDate.value,
          endDate.value,
          ds.id === sourceId ? (sessionWindow ?? undefined) : undefined
        )
      })

    const results = await Promise.all(updateOrFetchPromises)
    orderAndColorSeries()
    return results
  }

  // The old watcher on `plottedDatastreams` that computed prev/next id
  // diffs and forked between "update time range" and "rebuild plot"
  // has been replaced by explicit actions:
  //   - plotDatastream / unplotDatastream / toggleDatastream
  //   - clearPlottedDatastreams
  //   - setPlottedDatastreams (URL hydration)
  //   - setEditTarget / setEditRecord / clearEditTarget
  // Each mutation site now calls the action so side effects (time range
  // sync, graph-series rebuild, zoom history clear, Plotly re-render)
  // happen inline and in a predictable order, with no reactive cascade.

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
    isEditorReady,
    trackPlotWork,
    selectedDateBtnId,
    contextPresetId,
    activePresetId,
    editSessionWindow,
    showSourceContext,
    setShowSourceContext,
    qcDatastream,
    qcDatastreamId,
    editSourceDatastream,
    sourceContextDatastream,
    seriesDatastreams,
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
    setEditTarget,
    setEditRecord,
    clearEditTarget,
    rebuildPlot,
    // updateOrFetchGraphSeries,
  }
}, {
  // Persist only the user's preset choice. Catalogs, loading maps and
  // filters refetch cleanly on every load; the window resolves from the data.
  persist: {
    pick: ['selectedDateBtnId', 'contextPresetId', 'showSourceContext'],
    // A persisted Custom id (or a stale/unknown one) comes back with no
    // window to resolve against, so the placeholder range would apply
    // instead. Only a real preset survives hydration.
    afterHydrate: (ctx) => {
      const store = ctx.store as unknown as {
        selectedDateBtnId: number
        contextPresetId: number
      }
      if (!findPreset(store.selectedDateBtnId)) {
        store.selectedDateBtnId = DEFAULT_PRESET_ID
      }
      if (!findPreset(store.contextPresetId)) {
        store.contextPresetId = DEFAULT_PRESET_ID
      }
    },
  },
})
