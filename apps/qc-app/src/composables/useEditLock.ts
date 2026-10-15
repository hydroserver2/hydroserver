import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { usePlotlyStore } from '@/store/plotly'
import { useQcSessionStore } from '@/store/qcSession'

/**
 * Why the edit record can't take new operations right now, or null when it
 * can. `readOnly`: a committed session is on screen (after a commit, or
 * picked from the session list). `preview`: an earlier history step is shown.
 * Every surface that starts an edit (operation drawer and panels, plot
 * selections, table cells) checks this one value.
 */
export type EditLock = 'readOnly' | 'preview' | null

export function useEditLock() {
  const { previewIndex } = storeToRefs(usePlotlyStore())
  const { isReadOnly } = storeToRefs(useQcSessionStore())

  const editLock = computed<EditLock>(() => {
    if (isReadOnly.value) return 'readOnly'
    if (previewIndex.value !== null) return 'preview'
    return null
  })

  return { editLock }
}
