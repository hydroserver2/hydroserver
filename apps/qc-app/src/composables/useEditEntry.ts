/**
 * Entering and leaving the editor for a managed datastream: set the edit
 * target, resume its in-progress session or start one over a chosen window,
 * and switch views. Shared by the row Edit flow, reload resume and share links.
 *
 * Entries can overlap (a reload resume and a click). Whichever set the target
 * last owns the view, so an entry that finds the target changed after an await
 * stands down without touching view state, the target or the resume pointer.
 *
 * Only `closeEditor` and `leaveEdit` end a session. Switching between the
 * Select and Edit views keeps the target, so `openEditor` and an entry on the
 * open target are pure navigation.
 */

import { storeToRefs } from 'pinia'
import { Snackbar } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'
import { useQcSessionStore } from '@/store/qcSession'
import { DrawerType, useUIStore, type View } from '@/store/userInterface'
import {
  ResumeSupersededError,
  useEditSession,
} from '@/composables/useEditSession'
import { useLeaveSession } from '@/composables/useLeaveSession'
import type { TimeWindow } from '@/utils/timeRangePresets'

export type EnterEditResult =
  | 'editing'
  | 'needs-window'
  | 'not-managed'
  | 'superseded'
  /** The open session was kept, so the requested target was not entered. */
  | 'kept'

type StartOutcome = 'started' | 'superseded' | 'failed'

export function useEditEntry() {
  const dataVis = useDataVisStore()
  const { qcDatastream } = storeToRefs(dataVis)
  const { setEditTarget, clearEditTarget } = dataVis
  const { showView } = useUIStore()
  const { resumeDatastreamId } = storeToRefs(useQcSessionStore())
  const { beginEditing, startSession, needsSession, needsHistory } =
    useEditSession()
  const { requestLeave, forgetSession } = useLeaveSession()

  const owns = (id: string | undefined) => qcDatastream.value?.id === id
  // A cleared target is not a takeover: leaving again is harmless.
  const takenOver = (id: string | undefined) =>
    !!qcDatastream.value && !owns(id)

  /** Show the editor on the current target. Nothing about the session, the
   *  working copy or the staged edits changes. */
  function openEditor() {
    showView(DrawerType.Edit)
  }

  /** End the session and show the Select view. The caller has already asked
   *  the user, or there was nothing to ask about. */
  async function leaveEdit() {
    showView(DrawerType.Select)
    forgetSession()
    await clearEditTarget()
  }

  /** Leave the editor the way a user asks to: decide what happens to the
   *  session, then end it. False means they chose to stay. */
  async function closeEditor(): Promise<boolean> {
    if (!(await requestLeave())) return false
    await leaveEdit()
    return true
  }

  // A superseded start has already left the editor (unless a newer entry
  // owns it); a failed one leaves it open with no session.
  async function tryStartSession(window: TimeWindow): Promise<StartOutcome> {
    const owner = qcDatastream.value?.id
    try {
      await startSession({
        phenomenonTimeStart: window.begin.toISOString(),
        phenomenonTimeEnd: window.end.toISOString(),
      })
      if (!owns(owner)) return 'superseded'
      Snackbar.success('Edit session started.')
      return 'started'
    } catch (e) {
      if (takenOver(owner)) return 'superseded'
      if (e instanceof ResumeSupersededError) {
        await leaveEdit()
        Snackbar.error(e.message)
        return 'superseded'
      }
      Snackbar.error(
        e instanceof Error ? e.message : 'Could not start the session.'
      )
      return 'failed'
    }
  }

  async function startSessionOver(window: TimeWindow): Promise<boolean> {
    return (await tryStartSession(window)) === 'started'
  }

  async function enterEdit(
    managedId: string,
    window?: TimeWindow,
    view: View = DrawerType.Edit
  ): Promise<EnterEditResult> {
    // Already this target: show the view again and leave the session, the
    // working copy and any unsaved edits alone. A window means "start a
    // session over it", which still has work to do.
    if (owns(managedId) && !window) {
      showView(view)
      resumeDatastreamId.value = managedId
      return 'editing'
    }
    if (takenOver(managedId) && !(await requestLeave())) return 'kept'
    try {
      await setEditTarget(managedId)
      await beginEditing()
    } catch (e) {
      if (takenOver(managedId)) return 'superseded'
      await leaveEdit()
      if (!(e instanceof ResumeSupersededError)) throw e
      Snackbar.error(e.message)
      return 'superseded'
    }
    if (!owns(managedId)) return 'superseded'
    if (needsHistory.value) {
      await leaveEdit()
      Snackbar.error('This datastream is not set up for QC editing.')
      return 'not-managed'
    }
    showView(view)
    resumeDatastreamId.value = managedId
    if (!needsSession.value) return 'editing'
    if (!window) return 'needs-window'
    const outcome = await tryStartSession(window)
    if (outcome === 'started') return 'editing'
    return outcome === 'failed' ? 'needs-window' : 'superseded'
  }

  return { enterEdit, startSessionOver, openEditor, leaveEdit, closeEditor }
}
