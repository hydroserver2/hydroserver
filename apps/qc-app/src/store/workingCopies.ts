/**
 * One editable working copy per managed datastream: its in-progress
 * session's latest committed base (or raw source) with the saved draft
 * operations replayed. The Select-view plot and the editor share it, so the
 * preview shows exactly what editing opens.
 */

import { defineStore, storeToRefs } from 'pinia'
import { applyHistory } from '@uwrl/qc-utils'
import type { ObservationRecord } from '@uwrl/qc-utils'
import type { Datastream } from '@hydroserver/client'
import { useHydroServer } from '@/store/hydroserver'
import { useObservationStore } from '@/store/observations'
import {
  getInProgressSession,
  reconstructSession,
} from '@/services/qualityControl'

export interface WorkingCopy {
  sessionId: string
  record: ObservationRecord
  begin: Date
  end: Date
}

export type SessionWindow = {
  id: string
  phenomenonTimeStart: string
  phenomenonTimeEnd: string
}

export const useWorkingCopiesStore = defineStore('workingCopies', () => {
  // Not reactive: records hold large typed arrays that must not be proxied.
  const copies = new Map<string, WorkingCopy>()

  const get = (managedId: string) => copies.get(managedId)

  function set(
    managedId: string,
    sessionId: string,
    record: ObservationRecord,
    begin: Date,
    end: Date
  ) {
    copies.set(managedId, { sessionId, record, begin, end })
  }

  function invalidate(managedId: string) {
    copies.delete(managedId)
  }

  async function rebuild(
    managed: Datastream,
    source: Datastream,
    historyId: string,
    session: SessionWindow
  ): Promise<WorkingCopy> {
    const { hs } = storeToRefs(useHydroServer())
    const { fetchObservationsInRange } = useObservationStore()
    const { record } = await reconstructSession(
      {
        qcSessions: hs.value.qualityControlSessions,
        qcOperations: hs.value.qualityControlOperations,
        fetchInRange: fetchObservationsInRange,
        applyHistory,
      },
      managed,
      source,
      historyId,
      session.id
    )
    const copy: WorkingCopy = {
      sessionId: session.id,
      record,
      begin: new Date(session.phenomenonTimeStart),
      end: new Date(session.phenomenonTimeEnd),
    }
    copies.set(managed.id, copy)
    return copy
  }

  async function load(
    managed: Datastream,
    source: Datastream,
    historyId: string
  ): Promise<WorkingCopy | null> {
    const { hs } = storeToRefs(useHydroServer())
    const session = await getInProgressSession(
      hs.value.qualityControlSessions,
      historyId
    )
    if (!session) {
      copies.delete(managed.id)
      return null
    }
    const cached = copies.get(managed.id)
    if (cached?.sessionId === session.id) return cached
    return rebuild(managed, source, historyId, session)
  }

  function extents(managedIds: string[]) {
    return managedIds.flatMap((id) => {
      const copy = copies.get(id)
      return copy
        ? [
            {
              phenomenonBeginTime: copy.begin.toISOString(),
              phenomenonEndTime: copy.end.toISOString(),
            },
          ]
        : []
    })
  }

  return { get, set, invalidate, load, rebuild, extents }
})
