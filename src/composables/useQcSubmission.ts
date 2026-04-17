import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import { useHydroServer } from '@/store/hydroserver'
import { Snackbar } from '@uwrl/qc-utils'
import { storeToRefs } from 'pinia'

/**
 * ObservationBulkPostBody is a local type inside @hydroserver/client's
 * datastream.service and is not re-exported from the package entry. Define
 * its structural shape here to keep the composable type-safe without
 * reaching into internal module paths.
 */
type ObservationBulkPostBody = {
  fields: ('phenomenonTime' | 'result')[]
  data: unknown[][]
}

/**
 * Encapsulates the QC submission flow: guard checks, serialization of the
 * edited ObservationRecord into ObservationBulkPostBody, calling
 * hs.datastreams.createObservations with mode 'replace', user-facing
 * Snackbar feedback, and clearing the edit history on a committed signal.
 */
export function useQcSubmission() {
  const { hs } = storeToRefs(useHydroServer())
  const { selectedSeries, isSubmitting } = storeToRefs(usePlotlyStore())
  const { qcDatastream } = storeToRefs(useDataVisStore())

  const submitQcEdits = async () => {
    // Guard: need a selected series, a QC datastream id, and at least one edit
    if (
      !selectedSeries.value ||
      !qcDatastream.value?.id ||
      !selectedSeries.value.data.history.length
    ) {
      Snackbar.info('No edits to submit')
      return
    }

    const { dataX, dataY } = selectedSeries.value.data

    // TODO: resultQualifierCodes serialization is deferred — qualifier
    // tracking in useDataVisStore is still stubbed. Submit only
    // phenomenonTime + result for now.
    const body: ObservationBulkPostBody = {
      fields: ['phenomenonTime', 'result'],
      data: Array.from(dataX as ArrayLike<number>).map((ts, i) => [
        new Date(ts).toISOString(),
        (dataY as ArrayLike<number>)[i],
      ]),
    }

    isSubmitting.value = true
    try {
      await hs.value.datastreams.createObservations(
        qcDatastream.value.id,
        body,
        { mode: 'replace' }
      )
      Snackbar.success('Quality-controlled observations submitted')
      // Clear history in-place so the Pinia editHistory ref (which points
      // to the same underlying array via storeToRefs sync in plotly.ts:207
      // and :387) reflects the cleared state without needing a re-sync.
      // Reassigning (history = []) would desync the reactive ref and leave
      // EditHistory.vue rendering stale entries (MH-17 E2E regression).
      selectedSeries.value.data.history.length = 0
    } catch (err: any) {
      Snackbar.error(
        'Failed to submit observations: ' + (err?.message ?? 'unknown error')
      )
      // Swallow — UI does not need the error propagated.
    } finally {
      isSubmitting.value = false
    }
  }

  return { submitQcEdits }
}
