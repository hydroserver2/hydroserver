/**
 * View-mode state for QC sessions.
 *
 * Tracks the history's sessions, which one is editable (the single
 * in-progress session) and which one is being viewed. Viewing a committed
 * session puts the editor in read-only mode; `returnToCurrent` restores
 * editing of the in-progress session.
 */

import { defineStore, storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import { useHydroServer } from '@/store/hydroserver'
import { useEditResumeStore } from '@/store/editResume'
import { unwrap, withOperations } from '@/services/qualityControl'
import { commitOrder } from '@/utils/sessionGraph'
import type { Datastream } from '@hydroserver/client'
import type { HistoryItem } from '@uwrl/qc-utils'
import { sessionOperations, type QcSession } from '@/utils/qcHistory'

export const useQcSessionStore = defineStore('qcSession', () => {
  const historyId = ref<string | null>(null)
  /** Managed datastream the editor was last open on. The only field that
   *  survives a reload (see `editResume`); everything else is re-fetched on
   *  resume. */
  const { resumeDatastreamId } = storeToRefs(useEditResumeStore())
  /** Raw datastream behind the managed one, resolved when editing begins. */
  const sourceDatastream = ref<Datastream | null>(null)
  const sessions = ref<QcSession[]>([])
  /** The single in-progress (editable) session, if any. */
  const currentSessionId = ref<string | null>(null)
  /** The session currently being viewed. */
  const viewedSessionId = ref<string | null>(null)
  const isSwitchingSession = ref(false)
  /** Managed datastream whose editor is loading its history, sessions and
   *  working copy. Keyed by id since entries can overlap. */
  const openingDatastreamId = ref<string | null>(null)
  /** Edit history entries (by reference) at the last load or save, the
   *  baseline `useEditSession` compares against for unsaved edits. Kept here
   *  so the editor and the leave flow agree. */
  const savedEdits = ref<HistoryItem[]>([])
  /** Comment text of `savedEdits`, since comments are edited in place. */
  const savedComments = ref<string[]>([])

  /** Editing is allowed only while viewing the in-progress session. */
  // TODO(backend): ask for a way to keep editing the most recent session after
  // it is committed, when no newer session exists. Today a commit is terminal:
  // the API rejects updating, adding operations to, or re-committing a
  // committed session, and the PATCH body carries only `description`. Undoing
  // a commit also has to roll back what it wrote (the replayed observations on
  // the managed datastream plus the history's checksum and time extent), so
  // this is a real backend change, not just lifting the status guard.
  // Guarded on `sessions.length` so editing outside the session workflow
  // isn't treated as read-only.
  const isReadOnly = computed(
    () =>
      sessions.value.length > 0 &&
      viewedSessionId.value !== currentSessionId.value
  )

  const inProgressSession = computed(
    () => sessions.value.find((s) => s.status === 'in_progress') ?? null
  )
  const viewedSession = computed(
    () => sessions.value.find((s) => s.id === viewedSessionId.value) ?? null
  )

  /**
   * True when the in-progress session holds any work at all: the operations
   * the server returned with it, plus anything saved since (a save writes
   * operations this copy of the session doesn't have yet, and leaves them in
   * `savedEdits`). The leave flow uses it to tell an untouched session from
   * one worth keeping.
   */
  const hasSessionOperations = computed(() => {
    const session = inProgressSession.value
    if (!session) return false
    return sessionOperations(session).length > 0 || savedEdits.value.length > 0
  })

  /** A history's sessions with their operations. Writes nothing, so a caller
   *  can drop the result if it went stale while loading. */
  async function fetchSessions(id: string): Promise<QcSession[]> {
    const { hs } = storeToRefs(useHydroServer())
    const list = unwrap(
      await hs.value.qualityControlSessions.list(id, { fetch_all: true })
    )
    return withOperations(hs.value.qualityControlOperations, id, list)
  }

  /** Adopt a history's sessions; default the view to the in-progress session. */
  function applySessions(id: string, list: QcSession[]): void {
    historyId.value = id
    sessions.value = list
    const inProgress = list.find((s) => s.status === 'in_progress') ?? null
    currentSessionId.value = inProgress?.id ?? null
    // Default view: the editable session, else the last one committed (the
    // one a commit just made).
    const latestCommitted = [...list]
      .filter((s) => s.status === 'committed')
      .sort((a, b) => commitOrder(b).localeCompare(commitOrder(a)))[0]
    viewedSessionId.value = inProgress?.id ?? latestCommitted?.id ?? null
  }

  /** View a session read-only (no-op for an unknown id). */
  function viewSession(sessionId: string): void {
    if (sessions.value.some((s) => s.id === sessionId)) {
      viewedSessionId.value = sessionId
    }
  }

  /** Return to the editable in-progress session. */
  function returnToCurrent(): void {
    viewedSessionId.value = currentSessionId.value
  }

  function reset(): void {
    historyId.value = null
    sourceDatastream.value = null
    sessions.value = []
    currentSessionId.value = null
    viewedSessionId.value = null
    savedEdits.value = []
    savedComments.value = []
  }

  return {
    historyId,
    resumeDatastreamId,
    sourceDatastream,
    sessions,
    currentSessionId,
    viewedSessionId,
    isSwitchingSession,
    openingDatastreamId,
    savedEdits,
    savedComments,
    isReadOnly,
    inProgressSession,
    viewedSession,
    hasSessionOperations,
    fetchSessions,
    applySessions,
    viewSession,
    returnToCurrent,
    reset,
  }
})
