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
  const sessions = ref<QualityControlSession[]>([])
  /** The single in-progress (editable) session, if any. */
  const currentSessionId = ref<string | null>(null)
  /** The session currently being viewed. */
  const viewedSessionId = ref<string | null>(null)
  const isLoading = ref(false)

  /** Editing is allowed only while viewing the in-progress session. */
  const isReadOnly = computed(
    () => !currentSessionId.value || viewedSessionId.value !== currentSessionId.value
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

  /** Load a history's sessions; default the view to the in-progress session. */
  async function loadSessions(id: string): Promise<void> {
    isLoading.value = true
    try {
      const { hs } = storeToRefs(useHydroServer())
      const list = unwrap(
        await hs.value.qualityControlSessions.list(id, { fetch_all: true })
      )
      historyId.value = id
      sessions.value = list
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
    sessions,
    currentSessionId,
    viewedSessionId,
    isLoading,
    isReadOnly,
    inProgressSession,
    committedSessions,
    viewedSession,
    loadSessions,
    viewSession,
    returnToCurrent,
    reset,
  }
})
