/**
 * Entering and leaving the editor for a managed datastream: set the edit
 * target, resume its in-progress session or start one over a chosen window,
 * and switch views. Shared by the row Edit flow, reload resume and share links.
 *
 * Entries can overlap (a reload resume and a click). Whichever set the target
 * last owns the view, so an entry that finds the target changed after an await
 * stands down without touching view state, the target or the resume pointer.
 */

import { storeToRefs } from 'pinia'
import { Snackbar } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'
import { useQcSessionStore } from '@/store/qcSession'
import { DrawerType, useUIStore } from '@/store/userInterface'
import {
  ResumeSupersededError,
  useEditSession,
} from '@/composables/useEditSession'
import type { TimeWindow } from '@/utils/timeRangePresets'

export type EnterEditResult =
  | 'editing'
  | 'needs-window'
  | 'not-managed'
  | 'superseded'

type StartOutcome = 'started' | 'superseded' | 'failed'

export function useEditEntry() {
  const dataVis = useDataVisStore()
  const { qcDatastream } = storeToRefs(dataVis)
  const { setEditTarget, clearEditTarget } = dataVis
  const { currentView, selectedDrawer, isDrawerOpen } = storeToRefs(useUIStore())
  const { resumeDatastreamId } = storeToRefs(useQcSessionStore())
  const { beginEditing, startSession, needsSession, needsHistory } =
    useEditSession()

  const owns = (id: string | undefined) => qcDatastream.value?.id === id
  // A cleared target is not a takeover: leaving again is harmless.
  const takenOver = (id: string | undefined) =>
    !!qcDatastream.value && !owns(id)

  async function leaveEdit() {
    currentView.value = DrawerType.Select
    selectedDrawer.value = DrawerType.Select
    isDrawerOpen.value = true
    resumeDatastreamId.value = null
    await clearEditTarget()
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
    window?: TimeWindow
  ): Promise<EnterEditResult> {
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
    currentView.value = DrawerType.Edit
    selectedDrawer.value = DrawerType.Edit
    isDrawerOpen.value = true
    resumeDatastreamId.value = managedId
    if (!needsSession.value) return 'editing'
    if (!window) return 'needs-window'
    const outcome = await tryStartSession(window)
    if (outcome === 'started') return 'editing'
    return outcome === 'failed' ? 'needs-window' : 'superseded'
  }

  return { enterEdit, startSessionOver, leaveEdit }
}
