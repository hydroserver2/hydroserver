/**
 * Unplot everything. The datastream being edited is on the plot too, so the
 * editor closes first, asking about the session the way any exit does.
 */

import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import { useEditEntry } from '@/composables/useEditEntry'

export function useClearPlot() {
  const dataVis = useDataVisStore()
  const { plottedDatastreams, qcDatastream } = storeToRefs(dataVis)
  const { hiddenTraceIds } = storeToRefs(usePlotlyStore())
  const { closeEditor } = useEditEntry()

  const canClearPlot = computed(
    () => !!plottedDatastreams.value.length || !!qcDatastream.value
  )

  async function clearPlot() {
    if (qcDatastream.value && !(await closeEditor())) return
    hiddenTraceIds.value = new Set()
    await dataVis.clearPlottedDatastreams()
  }

  return { canClearPlot, clearPlot }
}
