/**
 * Change the time zone dates are shown in. The plot is redrawn in the new
 * zone over the same stretch of time, and the stage band stays where it was.
 */

import { useDataVisStore } from '@/store/dataVisualization'
import { applyZoomState, captureCurrentZoomState } from '@/utils/plotting/zoom'
import { redrawStageShape } from '@/utils/plotting/staging'
import { displayZone, type DisplayZone } from '@/utils/timeZone'

export function useDisplayZone() {
  async function setZone(next: DisplayZone): Promise<void> {
    const current = displayZone.value
    if (current.mode === next.mode && current.zone === next.zone) return
    // Read in the old zone: the snapshot holds real instants.
    const view = captureCurrentZoomState('init')
    displayZone.value = { ...next }
    await useDataVisStore().rebuildPlot()
    if (view) await applyZoomState(view)
    await redrawStageShape()
  }

  return { displayZone, setZone }
}
