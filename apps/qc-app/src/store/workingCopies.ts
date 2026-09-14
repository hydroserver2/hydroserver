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

  // Per-managed-id generation, bumped by invalidate/set and by every new
  // build (load's own build, and rebuild). A build only writes its result
  // to `copies` if its generation is still the latest once its await
  // resolves; otherwise a later invalidate/set/build has already
  // superseded it and the late write is silently dropped. This is what
  // keeps a stale in-flight reconstruction from resurrecting a copy after
  // the session it belongs to was committed or deleted.
  const generations = new Map<string, number>()

  // One in-flight load() build per managed id, so concurrent load() calls
  // for the same datastream share a single reconstruction and resolve to
  // the same record instead of each producing their own (the editor
  // mutates records in place, so two instances would diverge).
  const inFlightLoads = new Map<string, Promise<WorkingCopy | null>>()

  function bump(managedId: string): number {
    const next = (generations.get(managedId) ?? 0) + 1
    generations.set(managedId, next)
    return next
  }

  const get = (managedId: string) => copies.get(managedId)

  function set(
    managedId: string,
    sessionId: string,
    record: ObservationRecord,
    begin: Date,
    end: Date
  ) {
    bump(managedId)
    copies.set(managedId, { sessionId, record, begin, end })
  }

  function invalidate(managedId: string) {
    bump(managedId)
    copies.delete(managedId)
  }

  async function build(
    managed: Datastream,
    source: Datastream,
    historyId: string,
    session: SessionWindow,
    generation: number
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
    if (generations.get(managed.id) === generation) {
      copies.set(managed.id, copy)
    }
    return copy
  }

  async function rebuild(
    managed: Datastream,
    source: Datastream,
    historyId: string,
    session: SessionWindow
  ): Promise<WorkingCopy> {
    // A rebuild always forces a fresh reconstruction, and supersedes any
    // load() build already in flight for this managed id.
    const generation = bump(managed.id)
    inFlightLoads.delete(managed.id)
    return build(managed, source, historyId, session, generation)
  }

  async function performLoad(
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
      invalidate(managed.id)
      return null
    }
    const cached = copies.get(managed.id)
    if (cached?.sessionId === session.id) return cached

    const generation = bump(managed.id)
    const built = await build(managed, source, historyId, session, generation)
    // Superseded while awaiting (invalidate/set/rebuild landed first):
    // don't hand the caller a record that isn't (and won't become) the
    // cached entry. Report whatever is current instead.
    if (generations.get(managed.id) !== generation) {
      return copies.get(managed.id) ?? null
    }
    return built
  }

  function load(
    managed: Datastream,
    source: Datastream,
    historyId: string
  ): Promise<WorkingCopy | null> {
    const existing = inFlightLoads.get(managed.id)
    if (existing) return existing

    const promise = performLoad(managed, source, historyId).finally(() => {
      if (inFlightLoads.get(managed.id) === promise) {
        inFlightLoads.delete(managed.id)
      }
    })
    inFlightLoads.set(managed.id, promise)
    return promise
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
