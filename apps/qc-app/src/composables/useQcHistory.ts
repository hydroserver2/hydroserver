/**
 * Download the current QC history as JSON, windowed to the session (or,
 * with no session, the loaded range).
 */

import { storeToRefs } from 'pinia'
import { serializeHistory, type ObservationRecord } from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useDataVisStore } from '@/store/dataVisualization'
import { useQcSessionStore } from '@/store/qcSession'

/** Filename for downloaded QC histories: `qc-history-<datastream>-<isoTimestamp>.json`. */
function defaultFilename(datastreamName?: string): string {
  const safe = (datastreamName ?? 'datastream')
    .replace(/[^a-z0-9-_]+/gi, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60)
  const ts = new Date().toISOString().replace(/[:.]/g, '-')
  return `qc-history-${safe || 'datastream'}-${ts}.json`
}

/** Trigger a JSON download via a transient `<a download>` click. */
function downloadJson(payload: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Defer revoke past the click so Firefox finishes streaming.
  setTimeout(() => URL.revokeObjectURL(url), 1_000)
}

export function useQcHistory() {
  const { selectedSeries } = storeToRefs(usePlotlyStore())
  const { qcDatastream, beginDate, endDate } = storeToRefs(useDataVisStore())
  const { viewedSession, inProgressSession } = storeToRefs(useQcSessionStore())

  // While editing, `beginDate`/`endDate` follow the context range, not the
  // window the edits were made over.
  function historyWindow() {
    const session = viewedSession.value ?? inProgressSession.value
    if (!session) {
      return {
        startDate: beginDate.value.toISOString(),
        endDate: endDate.value.toISOString(),
      }
    }
    return {
      startDate: new Date(session.phenomenonTimeStart).toISOString(),
      endDate: new Date(session.phenomenonTimeEnd).toISOString(),
    }
  }

  /**
   * Serialize the current QC history to JSON and trigger a browser
   * download. Throws if no QC datastream is selected (the user
   * shouldn't be able to invoke this from the UI in that state, but
   * we guard defensively).
   */
  async function exportHistory(): Promise<void> {
    const series = selectedSeries.value?.data
    if (!series) throw new Error('No QC series loaded.')

    // qc-utils' `ObservationRecord` exposes a deep typed shape; the
    // cast pins the value to that public type so vue-tsc doesn't try
    // to structurally re-derive it from the live worker bindings.
    const history = serializeHistory(
      series as ObservationRecord,
      historyWindow()
    )

    const datastreamName = qcDatastream.value?.name
    downloadJson(history, defaultFilename(datastreamName))
  }

  return { exportHistory }
}
