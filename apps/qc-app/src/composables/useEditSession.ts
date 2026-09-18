/**
 * Orchestrates the session-based editing workflow (spec section 5-9),
 * wiring the QC service layer to the app's stores:
 *   - beginEditing: resolve the managed datastream's history, load its
 *     sessions, and resume the in-progress one (or signal that a session
 *     must be started); reports whether it actually resumed,
 *   - startSession: create a session and copy the source window in, or
 *     resume the in-progress one if it already exists,
 *   - saveDraft: persist the record's edit operations to the session
 *     (append-only, so each user's operations keep their creator),
 *   - commit: push the final observations (replace) and lock the session.
 *
 * The QC API client comes from `hs.qualityControl*`; the server stamps every
 * operation/session with the authenticated user.
 */

import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { serializeHistory, applyHistory, Snackbar } from '@uwrl/qc-utils'
import type { Datastream, DatastreamExtended, QualityControlSessionContract } from '@hydroserver/client'
import type { ObservationRecord, HistoryItem } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import { useHydroServer } from '@/store/hydroserver'
import { useObservationStore } from '@/store/observations'
import { useQcSessionStore } from '@/store/qcSession'
import { useWorkingCopiesStore, type SessionWindow } from '@/store/workingCopies'
import {
  findHistoryForDatastream,
  startOrResumeSession,
  loadLatestBase,
  persistSessionOperations,
  commitQcSession,
  reconstructCommittedSession,
  observationsBulkBody,
} from '@/services/qualityControl'

type QcSessionPostBody = QualityControlSessionContract.PostBody

/**
 * Keep a new session's window within the source datastream's observed extent.
 * The window now comes from the session window dialog, so it is normally
 * already valid; this clamp is a backstop for the backend's end-time rule
 * (`phenomenon_time_end cannot extend past the source datastream's current
 * end time`). Resume ignores the spec, so this only shapes freshly-created
 * sessions.
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
    throw new Error('The selected window has no source observations to edit.')
  }
  return {
    ...spec,
    phenomenonTimeStart: new Date(start).toISOString(),
    phenomenonTimeEnd: new Date(end).toISOString(),
  }
}

/** A resume whose working copy was superseded mid-build, so nothing replayed
 *  could be wired in. Editing must not continue over it. */
export class ResumeSupersededError extends Error {
  constructor() {
    super('The edit session changed while it was opening. Open it again to keep editing.')
    this.name = 'ResumeSupersededError'
  }
}

export function useEditSession() {
  const { qcDatastream } = storeToRefs(useDataVisStore())
  const { replaceDatastream, setEditRecord } = useDataVisStore()
  const { selectedSeries } = storeToRefs(usePlotlyStore())
  const { hs } = storeToRefs(useHydroServer())
  const { fetchObservationsInRange } = useObservationStore()
  const sessionStore = useQcSessionStore()
  const workingCopies = useWorkingCopiesStore()

  // The saved-edits snapshot lives in the store so every caller (the editor
  // footer and the nav rail's exit guard) sees the same unsaved state.
  const { sourceDatastream, savedEdits, savedComments } =
    storeToRefs(sessionStore)
  /** True when the managed datastream has no in-progress session to resume. */
  const needsSession = ref(false)
  /** True when the selected datastream has no QC history (not a managed datastream). */
  const needsHistory = ref(false)

  const currentEdits = (): HistoryItem[] =>
    (selectedSeries.value?.data as ObservationRecord | undefined)?.history ?? []
  const commentOf = (item: HistoryItem) => item.comment?.trim() ?? ''
  const snapshotSavedEdits = () => {
    const current = currentEdits()
    savedEdits.value = [...current]
    savedComments.value = current.map(commentOf)
  }

  /** True when the working copy has edits not in the last saved snapshot
   *  (additions, removals, or an edited comment). Always false while
   *  viewing a committed session: it cannot be edited, and replaying its
   *  history swaps entries that an identity check would read as edits. */
  const hasUnsavedChanges = computed(() => {
    if (sessionStore.isReadOnly) return false
    const current = currentEdits()
    const saved = savedEdits.value
    if (current.length !== saved.length) return true
    return current.some(
      (item, i) => item !== saved[i] || commentOf(item) !== savedComments.value[i]
    )
  })

  /** Count of edits added since the last save (the common append case). */
  const unsavedEditCount = computed(() => {
    if (sessionStore.isReadOnly) return 0
    return currentEdits().filter((item) => !savedEdits.value.includes(item))
      .length
  })

  /** Wire in the session's working copy with its saved operations replayed.
   *  Throws if superseded: a bare base would save over those operations. */
  async function resumeWorkingCopy(
    managed: Datastream,
    source: Datastream,
    historyId: string,
    session: SessionWindow
  ): Promise<void> {
    const built = await workingCopies.rebuild(managed, source, historyId, session)
    if (!built) throw new ResumeSupersededError()
    // The edit target may have changed (or been cleared) while the rebuild
    // was in flight; wiring in a record for a stale target would be silent
    // and wrong, since `setEditRecord` upserts whatever `qcDatastream` is now.
    if (qcDatastream.value?.id !== managed.id) throw new ResumeSupersededError()
    await setEditRecord(built.record)
    // The replayed draft operations are the saved baseline.
    snapshotSavedEdits()
    needsSession.value = false
  }

  /** Returns true when an in-progress session's working copy was wired into
   *  the plot, i.e. the editor is now genuinely editable over it. */
  async function beginEditing(): Promise<boolean> {
    const managed = qcDatastream.value
    if (!managed) return false
    needsHistory.value = false

    // Entries can overlap; never write the session store for a target
    // another entry has since taken over.
    const stillOwner = () => {
      if (qcDatastream.value?.id !== managed.id) throw new ResumeSupersededError()
    }

    const history = await findHistoryForDatastream(
      hs.value.qualityControlHistories,
      managed.id
    )
    stillOwner()
    if (!history) {
      // Not a managed datastream: the caller should offer to create one
      // from it (with this datastream as the source).
      needsHistory.value = true
      return false
    }
    const source =
      (await hs.value.datastreams.getItem(history.sourceDatastream.id)) ?? null
    stillOwner()
    sourceDatastream.value = source
    const sessions = await sessionStore.fetchSessions(history.id)
    stillOwner()
    sessionStore.applySessions(history.id, sessions)

    const inProgress = sessionStore.inProgressSession
    if (inProgress && sourceDatastream.value) {
      // A session exists, so a failed resume must never ask to start one.
      needsSession.value = false
      await resumeWorkingCopy(
        managed,
        sourceDatastream.value,
        history.id,
        inProgress
      )
      return true
    } else {
      needsSession.value = true
      return false
    }
  }

  /**
   * Load a committed session for read-only viewing: the data as that
   * session left it, and its own operations in the panel. Returns to the
   * in-progress session when given the editable one.
   */
  async function viewSession(sessionId: string): Promise<void> {
    // Leaving the editor clears the edit target but not the session store,
    // so `historyId`/`source` can outlive it; check the target itself first.
    const managed = qcDatastream.value
    if (!managed) {
      throw new Error('Load a managed datastream for editing first.')
    }
    const historyId = sessionStore.historyId
    const source = sourceDatastream.value
    if (!historyId || !source) {
      throw new Error('Load a managed datastream for editing first.')
    }
    if (sessionId === sessionStore.currentSessionId) {
      // `returnToCurrent` flips to editable before the rebuild; undo that
      // unless the resume actually wires in the working copy.
      const previousSessionId = sessionStore.viewedSessionId
      sessionStore.returnToCurrent()
      sessionStore.isSwitchingSession = true
      try {
        const resumed = await beginEditing()
        if (!resumed && previousSessionId) {
          sessionStore.viewSession(previousSessionId)
          needsSession.value = false
        }
      } catch (e) {
        if (previousSessionId) sessionStore.viewSession(previousSessionId)
        throw e
      } finally {
        sessionStore.isSwitchingSession = false
      }
      return
    }
    // Move the selection first so the loading state appears under the
    // session being opened. Reverted if the load fails.
    const previousSessionId = sessionStore.viewedSessionId
    sessionStore.viewSession(sessionId)
    sessionStore.isSwitchingSession = true
    try {
      const { record } = await reconstructCommittedSession(
        {
          qcSessions: hs.value.qualityControlSessions,
          qcOperations: hs.value.qualityControlOperations,
          fetchInRange: fetchObservationsInRange,
          applyHistory,
        },
        source,
        historyId,
        sessionId
      )
      // Same reasoning as the check in `resumeWorkingCopy`.
      if (qcDatastream.value?.id !== managed.id) throw new ResumeSupersededError()
      await setEditRecord(record)
      // Viewing is read-only, so there is nothing unsaved to track.
      snapshotSavedEdits()
    } catch (e) {
      if (previousSessionId) sessionStore.viewSession(previousSessionId)
      throw e
    } finally {
      sessionStore.isSwitchingSession = false
    }
  }

  async function startSession(spec: QcSessionPostBody): Promise<void> {
    const historyId = sessionStore.historyId
    const source = sourceDatastream.value
    const managed = qcDatastream.value
    if (!historyId || !source || !managed) {
      throw new Error('Load a managed datastream for editing first.')
    }
    const { session, resumed } = await startOrResumeSession(
      hs.value.qualityControlSessions,
      historyId,
      clampSpecToSource(spec, source)
    )
    const sessions = await sessionStore.fetchSessions(historyId)
    // Same ownership rule as `beginEditing`.
    if (qcDatastream.value?.id !== managed.id) throw new ResumeSupersededError()
    sessionStore.applySessions(historyId, sessions)
    if (resumed) {
      // It may already hold saved operations; edit their replay, not a bare base.
      await resumeWorkingCopy(managed, source, historyId, session)
      return
    }
    // Start from the latest committed state (the managed datastream), or the
    // raw source when nothing has been committed yet.
    const base = await loadLatestBase(
      fetchObservationsInRange,
      managed,
      source,
      new Date(session.phenomenonTimeStart),
      new Date(session.phenomenonTimeEnd)
    )
    // The edit target may have changed under this await; same reasoning as
    // the check in `resumeWorkingCopy`.
    if (qcDatastream.value?.id !== managed.id) throw new ResumeSupersededError()
    await setEditRecord(base)
    workingCopies.set(
      managed.id,
      session.id,
      base,
      new Date(session.phenomenonTimeStart),
      new Date(session.phenomenonTimeEnd)
    )
    needsSession.value = false
    // Fresh session: the loaded working copy is the saved baseline.
    snapshotSavedEdits()
  }

  /**
   * Drop everything added since the last save: replay the saved prefix,
   * then put the saved comment text back, since a comment edited in place
   * on a surviving entry survives the replay.
   */
  async function discardUnsavedEdits(): Promise<number[] | undefined> {
    const record = selectedSeries.value?.data as ObservationRecord | undefined
    if (!record) return
    const selection = await record.reloadHistory(savedEdits.value.length - 1)
    record.history.forEach((item, i) => {
      item.comment = savedComments.value[i] || undefined
    })
    snapshotSavedEdits()
    return selection
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

    // The window was chosen when the session started; the description is
    // captured here at commit time. Persist it if it changed.
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
    workingCopies.invalidate(managed.id)
    await sessionStore.loadSessions(historyId)
    snapshotSavedEdits()
    // The push moved the managed datastream's phenomenon times. Refresh last so
    // a network failure does not abort the commit (session is already locked).
    try {
      const refreshed = await hs.value.datastreams.getItem(managed.id, {
        expand_related: true,
      })
      if (!refreshed) throw new Error('Datastream refresh returned no item')
      replaceDatastream(refreshed as Datastream & DatastreamExtended)
    } catch (error) {
      console.error('Failed to refresh managed datastream after commit:', error)
      Snackbar.warn(
        'Session committed, but the datastream details could not be refreshed. Reload to see its updated time range.'
      )
    }
  }

  return {
    sourceDatastream,
    needsSession,
    needsHistory,
    hasUnsavedChanges,
    unsavedEditCount,
    beginEditing,
    startSession,
    viewSession,
    saveDraft,
    discardUnsavedEdits,
    commit,
  }
}
