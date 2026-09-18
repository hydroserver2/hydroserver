/**
 * Leaving an edit session: the one decision every exit goes through, and the
 * work the user's choice implies.
 *
 * Every way out of the editor (the footer's Close, the nav rail's Home,
 * workspace switch and log out, editing a different datastream, and in-app
 * navigation) calls `requestLeave` and only proceeds when it resolves true.
 * The prompt state is module-wide because one dialog serves all of them, and
 * the stores are resolved on use, since the dialog and the router guard hold
 * this composable long before anything is being edited.
 *
 * Switching between the Select and Edit views does not end the session, so it
 * never asks. The native `beforeunload` prompt covers a reload or a closed
 * tab, where the browser allows no dialog of ours.
 */

import { ref } from 'vue'
import { Snackbar } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import { useQcSessionStore } from '@/store/qcSession'
import { useWorkingCopiesStore } from '@/store/workingCopies'
import { useEditSession } from '@/composables/useEditSession'
import { useManagedDatastreams } from '@/composables/useManagedDatastreams'
import { hasDependents } from '@/utils/sessionGraph'

/** What the user stands to lose by leaving right now. */
export type LeaveCase =
  /** Nothing to decide: no edit target, no session, or committed history. */
  | 'none'
  /** Edits that never reached the session. */
  | 'unsaved'
  /** A session holding no operations at all. */
  | 'empty'
  /** Everything saved; the session stays in progress. */
  | 'saved'

export interface LeavePrompt {
  kind: Exclude<LeaveCase, 'none'>
  /** Edits made since the last save. */
  unsavedCount: number
  /** False when no session is open, so there is nowhere to save to. */
  canSave: boolean
}

/** The choice being carried out, while it runs. */
export type LeaveWork = 'save' | 'discard-edits' | 'discard-session' | null

const leavePrompt = ref<LeavePrompt | null>(null)
const leaveWork = ref<LeaveWork>(null)
let answer: ((leave: boolean) => void) | null = null

const messageOf = (e: unknown, fallback: string) =>
  e instanceof Error ? e.message : fallback

/** What leaving costs, decided the moment the exit is requested. */
function leaveCase(): LeaveCase {
  const { qcDatastream } = useDataVisStore()
  const session = useQcSessionStore()
  if (!qcDatastream) return 'none'
  // Viewing committed history edits nothing, so there is nothing to lose.
  if (session.isReadOnly) return 'none'
  if (useEditSession().hasUnsavedChanges.value) return 'unsaved'
  if (!session.inProgressSession) return 'none'
  return session.hasSessionOperations ? 'saved' : 'empty'
}

function show(kind: Exclude<LeaveCase, 'none'>): void {
  leavePrompt.value = {
    kind,
    unsavedCount: useEditSession().unsavedEditCount.value,
    canSave: !!useQcSessionStore().inProgressSession,
  }
}

function settle(leave: boolean): void {
  const resolve = answer
  answer = null
  leavePrompt.value = null
  leaveWork.value = null
  resolve?.(leave)
}

/**
 * Ask what should happen to the open session and carry the answer out.
 * Resolves true when the caller may go on with its exit, false when the user
 * chose to stay, in which case nothing has changed.
 */
async function requestLeave(): Promise<boolean> {
  const kind = leaveCase()
  if (kind === 'none') return true
  // A second exit request supersedes the first, whose caller stays put.
  answer?.(false)
  show(kind)
  return new Promise<boolean>((resolve) => {
    answer = resolve
  })
}

/** Stay in the session, exactly where the user was. */
function cancelLeave(): void {
  if (!leaveWork.value) settle(false)
}

/** Leave with the session untouched, still in progress. */
function keepSession(): void {
  if (!leaveWork.value) settle(true)
}

/** Keeping it, under the word the user sees when nothing is at stake. */
function closeSession(): void {
  keepSession()
}

async function saveAndLeave(): Promise<void> {
  if (leaveWork.value || !leavePrompt.value?.canSave) return
  leaveWork.value = 'save'
  try {
    await useEditSession().saveDraft()
    Snackbar.success('Draft saved.')
  } catch (e) {
    Snackbar.error(messageOf(e, 'Could not save the draft.'))
    return
  } finally {
    leaveWork.value = null
  }
  settle(true)
}

async function discardEditsAndLeave(): Promise<void> {
  if (leaveWork.value) return
  leaveWork.value = 'discard-edits'
  try {
    await useEditSession().discardUnsavedEdits()
    await usePlotlyStore().redraw()
  } catch (e) {
    Snackbar.error(messageOf(e, 'Could not discard the edits.'))
    return
  } finally {
    leaveWork.value = null
  }
  // Dropping them can leave the session with nothing in it at all, which is
  // its own decision rather than a silent exit.
  const session = useQcSessionStore()
  if (session.inProgressSession && !session.hasSessionOperations) {
    show('empty')
    return
  }
  settle(true)
}

async function discardSessionAndLeave(): Promise<void> {
  const store = useQcSessionStore()
  const session = store.inProgressSession
  const historyId = store.historyId
  if (leaveWork.value || !session || !historyId) return
  leaveWork.value = 'discard-session'
  try {
    // The in-progress session is the newest one, so nothing can be built on
    // it. Refuse rather than cascade the delete into committed work.
    if (hasDependents(store.sessions, session.id)) {
      throw new Error(
        'Another session was built on this one, so it cannot be discarded.'
      )
    }
    await useManagedDatastreams().deleteSessionChain(historyId, [session.id])
  } catch (e) {
    Snackbar.error(messageOf(e, 'Could not discard the session.'))
    return
  } finally {
    leaveWork.value = null
  }
  // The session is gone from the server, so drop it here too rather than
  // wait for the next load to contradict the store.
  store.applySessions(
    historyId,
    store.sessions.filter((s) => s.id !== session.id)
  )
  const { qcDatastream } = useDataVisStore()
  if (qcDatastream) useWorkingCopiesStore().invalidate(qcDatastream.id)
  Snackbar.success('Session discarded.')
  settle(true)
}

/** Forget which datastream the editor was on, so the next load starts in the
 *  Select view. Exits that unmount the editor need nothing else. */
function forgetSession(): void {
  useQcSessionStore().resumeDatastreamId = null
}

export function useLeaveSession() {
  return {
    leaveCase,
    requestLeave,
    cancelLeave,
    keepSession,
    closeSession,
    saveAndLeave,
    discardEditsAndLeave,
    discardSessionAndLeave,
    forgetSession,
    leavePrompt,
    leaveWork,
  }
}
