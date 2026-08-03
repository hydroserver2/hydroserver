/**
 * View-mode state for QC sessions (spec section 4 history navigation).
 *
 * Tracks the history's sessions, which one is editable (the single
 * in-progress session) and which one is being viewed. Viewing a committed
 * session puts the editor in read-only mode; `returnToCurrent` restores
 * editing of the in-progress session.
 */

import { defineStore, storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import { useHydroServer } from '@/store/hydroserver'
import { unwrap } from '@/services/qualityControl'
import type { QualityControlSession } from '@hydroserver/client'

export const useQcSessionStore = defineStore('qcSession', () => {
  const historyId = ref<string | null>(null)
  /** Managed datastream the editor was last open on. The only persisted
   *  field; everything else is re-fetched on resume. */
  const resumeDatastreamId = ref<string | null>(null)
  const sessions = ref<QualityControlSession[]>([])
  /** The single in-progress (editable) session, if any. */
  const currentSessionId = ref<string | null>(null)
  /** The session currently being viewed. */
  const viewedSessionId = ref<string | null>(null)
  const isLoading = ref(false)
  const isSwitchingSession = ref(false)

  /** Editing is allowed only while viewing the in-progress session. */
  // TODO(backend): ask for a way to keep editing the most recent session after
  // it is committed, when no newer session exists. Today a commit is terminal:
  // the API rejects updating, deleting, adding operations to, or re-committing
  // a committed session, and the PATCH body carries only `description`. Undoing
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
  const committedSessions = computed(() =>
    sessions.value.filter((s) => s.status === 'committed')
  )
  const viewedSession = computed(
    () => sessions.value.find((s) => s.id === viewedSessionId.value) ?? null
  )

  /**
   * Guarantee every session carries its `operations`, which the previews
   * read. `expand_related` should embed them, but a backend that ignores it
   * returns the summary shape instead. Only the gaps are fetched.
   */
  async function withOperations(
    client: ReturnType<typeof useHydroServer>['hs'],
    id: string,
    list: QualityControlSession[]
  ): Promise<QualityControlSession[]> {
    const missing = list.filter(
      (s) => !(s as { operations?: unknown[] }).operations
    )
    if (!missing.length) return list

    const fetched = new Map<string, unknown[]>()
    await Promise.all(
      missing.map(async (s) => {
        const res = await client.qualityControlOperations.list(id, s.id, {
          fetch_all: true,
        })
        if (res.ok) fetched.set(s.id, res.data)
      })
    )
    return list.map((s) =>
      fetched.has(s.id) ? { ...s, operations: fetched.get(s.id) } : s
    ) as QualityControlSession[]
  }

  /** Load a history's sessions; default the view to the in-progress session. */
  async function loadSessions(id: string): Promise<void> {
    isLoading.value = true
    try {
      const { hs } = storeToRefs(useHydroServer())
      const list = unwrap(
        await hs.value.qualityControlSessions.list(id, {
          fetch_all: true,
          expand_related: true,
        })
      )
      historyId.value = id
      sessions.value = await withOperations(hs.value, id, list)
      const inProgress = list.find((s) => s.status === 'in_progress') ?? null
      currentSessionId.value = inProgress?.id ?? null
      // Default view: the editable session, else the latest committed.
      const latestCommitted = [...list]
        .filter((s) => s.status === 'committed')
        .sort((a, b) => b.phenomenonTimeStart.localeCompare(a.phenomenonTimeStart))[0]
      viewedSessionId.value = inProgress?.id ?? latestCommitted?.id ?? null
    } finally {
      isLoading.value = false
    }
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
    sessions.value = []
    currentSessionId.value = null
    viewedSessionId.value = null
    isLoading.value = false
  }

  return {
    historyId,
    resumeDatastreamId,
    sessions,
    currentSessionId,
    viewedSessionId,
    isLoading,
    isSwitchingSession,
    isReadOnly,
    inProgressSession,
    committedSessions,
    viewedSession,
    loadSessions,
    viewSession,
    returnToCurrent,
    reset,
  }
}, {
  // Only the datastream id survives a reload. Sessions, operations and the
  // read-only flag are all re-derived from the server on resume, so
  // persisting them would just risk showing stale state.
  persist: {
    pick: ['resumeDatastreamId'],
  },
})
