/**
 * Orchestrates the session-based editing workflow (spec section 5-9),
 * wiring the QC service layer to the app's stores:
 *   - beginEditing: resolve the managed datastream's history, load its
 *     sessions, and resume the in-progress one (or signal that a session
 *     must be started),
 *   - startSession: create a session and copy the source window in,
 *   - saveDraft: persist the record's edit operations to the session
 *     (append-only, so each user's operations keep their creator),
 *   - commit: push the final observations (replace) and lock the session.
 *
 * The QC API client comes from `hs.qualityControl*`; the server stamps every
 * operation/session with the authenticated user.
 */

import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { serializeHistory, applyHistory } from '@uwrl/qc-utils'
import type { Datastream, QualityControlSessionContract } from '@hydroserver/client'
import type { ObservationRecord, HistoryItem } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import { useHydroServer } from '@/store/hydroserver'
import { useObservationStore } from '@/store/observations'
import { useQcSessionStore } from '@/store/qcSession'
import {
  findHistoryForDatastream,
  startOrResumeSession,
  loadLatestBase,
  persistSessionOperations,
  commitQcSession,
  reconstructSession,
  observationsBulkBody,
} from '@/services/qualityControl'

type QcSessionPostBody = QualityControlSessionContract.PostBody

/**
 * Keep a new session's window within the source datastream's observed extent.
 * The window comes from the display time-range controls, whose end is usually
 * "now" — past the source's last observation — which the backend rejects
 * (`phenomenon_time_end cannot extend past the source datastream's current end
 * time`). Resume ignores the spec, so this only shapes freshly-created sessions.
 */
function clampSpecToSource(
  spec: QcSessionPostBody,
  source: Pick<Datastream, 'phenomenonBeginTime' | 'phenomenonEndTime'>
): QcSessionPostBody {
  let start = new Date(spec.phenomenonTimeStart).getTime()
  let end = new Date(spec.phenomenonTimeEnd).getTime()
  if (source.phenomenonBeginTime) {
    start = Math.max(start, new Date(source.phenomenonBeginTime).getTime())
  }
  if (source.phenomenonEndTime) {
    end = Math.min(end, new Date(source.phenomenonEndTime).getTime())
  }
  if (!(start < end)) {
    throw new Error(
      'The selected time range has no source observations to edit. ' +
        'Pick a range that overlaps the datastream (try the "All" preset).'
    )
  }
  return {
    ...spec,
    phenomenonTimeStart: new Date(start).toISOString(),
    phenomenonTimeEnd: new Date(end).toISOString(),
  }
}

export function useEditSession() {
  const { qcDatastream } = storeToRefs(useDataVisStore())
  const { selectedSeries } = storeToRefs(usePlotlyStore())
  const { hs } = storeToRefs(useHydroServer())
  const { fetchObservationsInRange } = useObservationStore()
  const sessionStore = useQcSessionStore()

  const sourceDatastream = ref<Datastream | null>(null)
  /** True when the managed datastream has no in-progress session to resume. */
  const needsSession = ref(false)
  /** True when the selected datastream has no QC history (not a managed datastream). */
  const needsHistory = ref(false)

  // Snapshot (by item reference) of the operation history at the last
  // load/save, so the editor knows whether there are unsaved edits.
  const savedEdits = ref<HistoryItem[]>([])
  const currentEdits = (): HistoryItem[] =>
    (selectedSeries.value?.data as ObservationRecord | undefined)?.history ?? []
  const snapshotSavedEdits = () => {
    savedEdits.value = [...currentEdits()]
  }

  /** True when the working copy has edits not in the last saved snapshot
   *  (additions or removals). */
  const hasUnsavedChanges = computed(() => {
    const current = currentEdits()
    const saved = savedEdits.value
    if (current.length !== saved.length) return true
    return current.some((item, i) => item !== saved[i])
  })

  /** Count of edits added since the last save (the common append case). */
  const unsavedEditCount = computed(
    () =>
      currentEdits().filter((item) => !savedEdits.value.includes(item)).length
  )

  async function beginEditing(): Promise<void> {
    const managed = qcDatastream.value
    if (!managed) return
    needsHistory.value = false

    const history = await findHistoryForDatastream(
      hs.value.qualityControlHistories,
      managed.id
    )
    if (!history) {
      // Not a managed datastream: the caller should offer to create one
      // from it (with this datastream as the source).
      needsHistory.value = true
      return
    }
    sourceDatastream.value =
      (await hs.value.datastreams.getItem(history.sourceDatastream.id)) ?? null
    await sessionStore.loadSessions(history.id)

    const inProgress = sessionStore.inProgressSession
    const record = selectedSeries.value?.data
    if (inProgress && sourceDatastream.value && record) {
      // Resume: reconstruct the in-progress session's working state (source
      // window + replayed draft operations) and wire it into the QC-target
      // series so the editor shows the saved edits instead of the empty,
      // uncommitted managed datastream.
      const { record: reconstructed } = await reconstructSession(
        {
          qcSessions: hs.value.qualityControlSessions,
          qcOperations: hs.value.qualityControlOperations,
          fetchInRange: fetchObservationsInRange,
          applyHistory,
        },
        managed,
        sourceDatastream.value,
        history.id,
        inProgress.id
      )
      if (selectedSeries.value) selectedSeries.value.data = reconstructed
      // The replayed draft operations are the saved baseline.
      snapshotSavedEdits()
      needsSession.value = false
    } else {
      needsSession.value = true
    }
  }

  async function startSession(spec: QcSessionPostBody): Promise<void> {
    const historyId = sessionStore.historyId
    const source = sourceDatastream.value
    const managed = qcDatastream.value
    if (!historyId || !source || !managed) {
      throw new Error('Load a managed datastream for editing first.')
    }
    const session = await startOrResumeSession(
      hs.value.qualityControlSessions,
      historyId,
      clampSpecToSource(spec, source)
    )
    await sessionStore.loadSessions(historyId)
    // Start from the latest committed state (the managed datastream), or the
    // raw source when nothing has been committed yet.
    const base = await loadLatestBase(
      fetchObservationsInRange,
      managed,
      source,
      new Date(session.phenomenonTimeStart),
      new Date(session.phenomenonTimeEnd)
    )
    if (selectedSeries.value) selectedSeries.value.data = base
    needsSession.value = false
    // Fresh session: the loaded working copy is the saved baseline.
    snapshotSavedEdits()
  }

  async function saveDraft(): Promise<void> {
    const historyId = sessionStore.historyId
    const session = sessionStore.inProgressSession
    const record = selectedSeries.value?.data
    if (!historyId || !session || !record) {
      throw new Error('No active edit session to save.')
    }
    const operations = serializeHistory(record as ObservationRecord, {
      startDate: session.phenomenonTimeStart,
      endDate: session.phenomenonTimeEnd,
    }).operations
    await persistSessionOperations(
      hs.value.qualityControlOperations,
      historyId,
      session.id,
      operations
    )
    snapshotSavedEdits()
  }

  async function commit(description?: string): Promise<void> {
    const managed = qcDatastream.value
    const historyId = sessionStore.historyId
    const session = sessionStore.inProgressSession
    const record = selectedSeries.value?.data
    if (!managed || !historyId || !session || !record) {
      throw new Error('No active edit session to commit.')
    }
    await saveDraft()

    // The window was chosen earlier by the time-range controls; the
    // description is captured here at commit time. Persist it if it changed.
    const trimmed = description?.trim()
    if (trimmed !== undefined && trimmed !== (session.description ?? '')) {
      const res = await hs.value.qualityControlSessions.update(
        historyId,
        session.id,
        { description: trimmed || null }
      )
      if (!res.ok) {
        throw new Error(res.message || 'Could not save the session description.')
      }
    }

    const body = observationsBulkBody(record as ObservationRecord)
    await commitQcSession({
      qcSessions: hs.value.qualityControlSessions,
      historyId,
      sessionId: session.id,
      // The real client fetches the source window's X-Checksum header for a
      // genuine integrity check; here we reuse the checksum captured at create.
      currentSourceChecksum: session.sourceChecksum,
      pushObservations: async () => {
        await hs.value.datastreams.createObservations(managed.id, body, {
          mode: 'replace',
        })
      },
    })
    await sessionStore.loadSessions(historyId)
    snapshotSavedEdits()
  }

  return {
    sourceDatastream,
    needsSession,
    needsHistory,
    hasUnsavedChanges,
    unsavedEditCount,
    beginEditing,
    startSession,
    saveDraft,
    commit,
  }
}
