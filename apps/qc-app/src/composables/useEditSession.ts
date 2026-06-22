/**
 * Orchestrates the session-based editing workflow (spec section 5-9),
 * wiring the QC service layer to the app's stores:
 *   - beginEditing: resolve the managed datastream's history, load its
 *     sessions, and resume the in-progress one (or signal that a session
 *     must be started),
 *   - startSession: create a session and copy the source window in,
 *   - saveDraft: persist the record's edit operations to the session
 *     (append-only, so each user's operations keep their creator),
 *   - commit: push the final observations (replace) and lock the session.
 *
 * The QC API client comes from `hs.qualityControl*`; the server stamps every
 * operation/session with the authenticated user.
 */

import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { serializeHistory, applyHistory } from '@uwrl/qc-utils'
import type { Datastream, QualityControlSessionContract } from '@hydroserver/client'
import type { ObservationRecord } from '@uwrl/qc-utils'
import { useDataVisStore } from '@/store/dataVisualization'
import { usePlotlyStore } from '@/store/plotly'
import { useHydroServer } from '@/store/hydroserver'
import { useObservationStore } from '@/store/observations'
import { useQcSessionStore } from '@/store/qcSession'
import {
  findHistoryForDatastream,
  startOrResumeSession,
  loadSourceWindow,
  persistSessionOperations,
  commitQcSession,
  reconstructSession,
  observationsBulkBody,
} from '@/services/qualityControl'

type QcSessionPostBody = QualityControlSessionContract.PostBody

export function useEditSession() {
  const { qcDatastream } = storeToRefs(useDataVisStore())
  const { selectedSeries } = storeToRefs(usePlotlyStore())
  const { hs } = storeToRefs(useHydroServer())
  const { fetchObservationsInRange } = useObservationStore()
  const sessionStore = useQcSessionStore()

  const sourceDatastream = ref<Datastream | null>(null)
  /** True when the managed datastream has no in-progress session to resume. */
  const needsSession = ref(false)
  /** True when the selected datastream has no QC history (not a managed datastream). */
  const needsHistory = ref(false)

  async function beginEditing(): Promise<void> {
    const managed = qcDatastream.value
    if (!managed) return
    needsHistory.value = false

    const history = await findHistoryForDatastream(
      hs.value.qualityControlHistories,
      managed.id
    )
    if (!history) {
      // Not a managed datastream: the caller should offer to create one
      // from it (with this datastream as the source).
      needsHistory.value = true
      return
    }
    sourceDatastream.value =
      (await hs.value.datastreams.getItem(history.sourceDatastream.id)) ?? null
    await sessionStore.loadSessions(history.id)

    const inProgress = sessionStore.inProgressSession
    const record = selectedSeries.value?.data
    if (inProgress && sourceDatastream.value && record) {
      // Resume: reconstruct the in-progress session's working state.
      await reconstructSession(
        {
          qcSessions: hs.value.qualityControlSessions,
          fetchInRange: fetchObservationsInRange,
          applyHistory,
        },
        sourceDatastream.value,
        history.id,
        inProgress.id
      )
      needsSession.value = false
    } else {
      needsSession.value = true
    }
  }

  async function startSession(spec: QcSessionPostBody): Promise<void> {
    const historyId = sessionStore.historyId
    if (!historyId || !sourceDatastream.value) {
      throw new Error('Load a managed datastream for editing first.')
    }
    const session = await startOrResumeSession(
      hs.value.qualityControlSessions,
      historyId,
      spec
    )
    await sessionStore.loadSessions(historyId)
    await loadSourceWindow(fetchObservationsInRange, sourceDatastream.value, session)
    needsSession.value = false
  }

  async function saveDraft(): Promise<void> {
    const historyId = sessionStore.historyId
    const session = sessionStore.inProgressSession
    const record = selectedSeries.value?.data
    if (!historyId || !session || !record) {
      throw new Error('No active edit session to save.')
    }
    const operations = serializeHistory(record as ObservationRecord, {
      startDate: session.phenomenonTimeStart,
      endDate: session.phenomenonTimeEnd,
    }).operations
    await persistSessionOperations(
      hs.value.qualityControlOperations,
      historyId,
      session.id,
      operations
    )
  }

  async function commit(): Promise<void> {
    const managed = qcDatastream.value
    const historyId = sessionStore.historyId
    const session = sessionStore.inProgressSession
    const record = selectedSeries.value?.data
    if (!managed || !historyId || !session || !record) {
      throw new Error('No active edit session to commit.')
    }
    await saveDraft()

    const body = observationsBulkBody(record as ObservationRecord)
    await commitQcSession({
      qcSessions: hs.value.qualityControlSessions,
      historyId,
      sessionId: session.id,
      // The real client fetches the source window's X-Checksum header for a
      // genuine integrity check; here we reuse the checksum captured at create.
      currentSourceChecksum: session.sourceChecksum,
      pushObservations: async () => {
        await hs.value.datastreams.createObservations(managed.id, body, {
          mode: 'replace',
        })
      },
    })
    await sessionStore.loadSessions(historyId)
  }

  return {
    sourceDatastream,
    needsSession,
    needsHistory,
    beginEditing,
    startSession,
    saveDraft,
    commit,
  }
}
