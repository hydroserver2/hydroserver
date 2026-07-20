/**
 * QC History — Vue-side save / load wrapper.
 *
 * Wraps qc-utils' `serializeHistory` / `parseHistory` / `applyHistory`
 * with the consumer-specific glue:
 *   - reading the active wall-clock window from the data-vis store
 *     for the save side
 *   - file-picker / blob-download plumbing
 *   - fetching the QC history's window into the active datastream's
 *     `ObservationRecord` before replay (qc-utils itself is data-
 *     agnostic; the consumer drives the data fetch)
 */

import { storeToRefs } from 'pinia'
import {
  applyHistory,
  parseHistory,
  serializeHistory,
  type ApplyHistoryReport,
  type ObservationRecord,
  type QcHistory,
} from '@uwrl/qc-utils'
import { usePlotlyStore } from '@/store/plotly'
import { useDataVisStore } from '@/store/dataVisualization'
import { useObservationStore } from '@/store/observations'

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
  const { fetchObservationsInRange } = useObservationStore()

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
    const history = serializeHistory(series as ObservationRecord, {
      startDate: beginDate.value.toISOString(),
      endDate: endDate.value.toISOString(),
    })

    const datastreamName = qcDatastream.value?.name
    downloadJson(history, defaultFilename(datastreamName))
  }

  /**
   * Read a JSON file, parse it as a QcHistory, fetch the QC history's
   * window into the current QC datastream, and replay the
   * operations. Returns the per-op report so the caller can surface
   * a Snackbar / toast summary.
   *
   * No datastream-id matching is enforced — QC histories are reusable
   * across datastreams (see qc-utils' QC_HISTORY.md "Stay reusable").
   */
  async function importHistory(file: File): Promise<ApplyHistoryReport> {
    const series = selectedSeries.value?.data
    const datastream = qcDatastream.value
    if (!series || !datastream) {
      throw new Error('Pick a QC datastream before loading a QC history.')
    }

    const text = await file.text()
    let json: unknown
    try {
      json = JSON.parse(text)
    } catch (e) {
      throw new Error(
        `Couldn't parse ${file.name} as JSON: ${e instanceof Error ? e.message : String(e)}`
      )
    }

    const history: QcHistory = parseHistory(json)

    // Fetch the QC history's authored window into the active record
    // BEFORE replaying. Selection-coupled ops reference indices
    // against this windowed dataset; loading them against a
    // differently-sized window would mis-target.
    await fetchObservationsInRange(
      datastream,
      new Date(history.window.startDate),
      new Date(history.window.endDate)
    )

    return await applyHistory(series as ObservationRecord, history)
  }

  return { exportHistory, importHistory }
}
