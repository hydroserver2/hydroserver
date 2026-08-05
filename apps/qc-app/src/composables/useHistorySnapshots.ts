/**
 * Add and remove history snapshots: frozen replays of a session's state at a
 * chosen operation, plotted as extra comparison lines.
 */

import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ObservationRecord, Snackbar, applyHistory } from '@uwrl/qc-utils'
import type { Datastream, QualityControlSession } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
import { useDataVisStore } from '@/store/dataVisualization'
import { useObservationStore, type ObservationData } from '@/store/observations'
import { usePlotlyStore } from '@/store/plotly'
import { useQcSessionStore } from '@/store/qcSession'
import { buildSnapshotRecord } from '@/services/qualityControl/buildSnapshot'
import { formatDateRange } from '@/utils/time'
import { SNAPSHOT_BASELINE_INDEX, makeSnapshotId } from '@/utils/snapshotId'
import type { SnapshotMeta } from '@/types'

/** The operation shape the session list embeds. */
interface SessionOperation {
  operationType?: string
  createdBy?: { name?: string; email?: string }
}

export function useHistorySnapshots() {
  const isBuilding = ref(false)
  const dataVis = useDataVisStore()
  const sessionStore = useQcSessionStore()
  const { plottedDatastreams } = storeToRefs(dataVis)
  const { selectedSeries } = storeToRefs(usePlotlyStore())
  const { hs } = storeToRefs(useHydroServer())
  const { observationsRaw } = storeToRefs(useObservationStore())
  const { fetchObservationsInRange } = useObservationStore()

  /**
   * The observation store hands back one shared record per datastream, and the
   * replay mutates whatever it is given, so build on an independent record.
   */
  const fetchDetached = async (ds: Datastream, start: Date, end: Date) => {
    await fetchObservationsInRange(ds, start, end)
    const raw: ObservationData = observationsRaw.value[ds.id] ?? {
      datetimes: new Float64Array(0),
      dataValues: new Float32Array(0),
    }
    const record = new ObservationRecord(raw)
    await record.applyWindow(start.getTime(), end.getTime())
    return record
  }

  const isSnapshotPlotted = (sessionId: string, opIndex: number): boolean => {
    const id = makeSnapshotId(sessionId, opIndex)
    return plottedDatastreams.value.some((d) => d.id === id)
  }

  const toggleSnapshot = async (sessionId: string, opIndex: number) => {
    const id = makeSnapshotId(sessionId, opIndex)
    if (isSnapshotPlotted(sessionId, opIndex)) {
      await dataVis.removeSnapshotSeries(id)
      return
    }

    const historyId = sessionStore.historyId
    const session = sessionStore.sessions.find((s) => s.id === sessionId)
    const source = sessionStore.sourceDatastream
    const managed = dataVis.qcDatastream
    if (!historyId || !session || !source || !managed) {
      Snackbar.error('Load a managed datastream for editing first.')
      return
    }

    isBuilding.value = true
    try {
      // Only the session on screen has drafts that are not yet on the server.
      const liveHistory =
        session.id === sessionStore.viewedSessionId
          ? [...(selectedSeries.value?.data.history ?? [])]
          : undefined

      const record = await buildSnapshotRecord(
        {
          qcSessions: hs.value.qualityControlSessions,
          qcOperations: hs.value.qualityControlOperations,
          fetchInRange: fetchDetached,
          applyHistory,
        },
        { historyId, session, source, managed, opIndex, liveHistory }
      )

      await dataVis.addSnapshotSeries(id, record, metaFor(session, opIndex))
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      Snackbar.error(`Couldn't build the snapshot: ${msg}`)
    } finally {
      isBuilding.value = false
    }
  }

  return { toggleSnapshot, isSnapshotPlotted, isBuilding }
}

function metaFor(
  session: QualityControlSession,
  opIndex: number
): SnapshotMeta {
  const s = session as QualityControlSession & {
    description?: string
    operations?: SessionOperation[]
  }
  const ops = s.operations ?? []
  const op = opIndex >= SNAPSHOT_BASELINE_INDEX + 1 ? ops[opIndex] : undefined
  const performedBy = op?.createdBy?.name?.trim() || op?.createdBy?.email?.trim()
  return {
    sessionId: s.id,
    sessionLabel:
      s.description ||
      formatDateRange(s.phenomenonTimeStart, s.phenomenonTimeEnd),
    opIndex,
    opCount: ops.length,
    opName: op?.operationType ? formatMethod(op.operationType) : '',
    ...(performedBy ? { performedBy } : {}),
    createdAt: s.createdAt,
  }
}

function formatMethod(method: string): string {
  return method
    .toLowerCase()
    .split('_')
    .map((w) => (w ? w[0]!.toUpperCase() + w.slice(1) : ''))
    .join(' ')
}
