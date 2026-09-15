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

  // Bumped by every invalidate/set/clear and new build; a build caches its
  // result only if its generation is still current.
  const generations = new Map<string, number>()

  // Shared so concurrent loads resolve to one record (edits mutate in place).
  const inFlightLoads = new Map<string, Promise<WorkingCopy | null>>()

  // The latest in-flight rebuild; loads and superseded rebuilds join it.
  const activeRebuild = new Map<string, Promise<WorkingCopy | null>>()

  function bump(managedId: string): number {
    const next = (generations.get(managedId) ?? 0) + 1
    generations.set(managedId, next)
    activeRebuild.delete(managedId)
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
    inFlightLoads.delete(managedId)
    copies.set(managedId, { sessionId, record, begin, end })
  }

  function invalidate(managedId: string) {
    bump(managedId)
    inFlightLoads.delete(managedId)
    copies.delete(managedId)
  }

  /** Drop every copy and supersede every in-flight build. */
  function clear() {
    // A load still listing sessions has no generation yet; bump it too.
    const ids = new Set([...generations.keys(), ...inFlightLoads.keys()])
    for (const managedId of ids) bump(managedId)
    copies.clear()
    inFlightLoads.clear()
    activeRebuild.clear()
  }

  /** Reconstruct and cache the result; null when superseded while awaiting. */
  async function build(
    managed: Datastream,
    source: Datastream,
    historyId: string,
    session: SessionWindow,
    generation: number
  ): Promise<WorkingCopy | null> {
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
    if (generations.get(managed.id) !== generation) return null
    const copy: WorkingCopy = {
      sessionId: session.id,
      record,
      begin: new Date(session.phenomenonTimeStart),
      end: new Date(session.phenomenonTimeEnd),
    }
    copies.set(managed.id, copy)
    return copy
  }

  /** What a superseded build resolves to: a newer rebuild's result, else the cache. */
  async function current(managedId: string): Promise<WorkingCopy | null> {
    const rebuilding = activeRebuild.get(managedId)
    if (rebuilding) return rebuilding
    return copies.get(managedId) ?? null
  }

  /** Always reconstructs, superseding any in-flight load or earlier rebuild. */
  function rebuild(
    managed: Datastream,
    source: Datastream,
    historyId: string,
    session: SessionWindow
  ): Promise<WorkingCopy | null> {
    const generation = bump(managed.id)
    inFlightLoads.delete(managed.id)
    const promise: Promise<WorkingCopy | null> = build(
      managed,
      source,
      historyId,
      session,
      generation
    )
      .then(async (built) => {
        if (built) return built
        const winner = activeRebuild.get(managed.id)
        if (winner && winner !== promise) return winner
        return copies.get(managed.id) ?? null
      })
      .finally(() => {
        if (activeRebuild.get(managed.id) === promise) {
          activeRebuild.delete(managed.id)
        }
      })
    activeRebuild.set(managed.id, promise)
    return promise
  }

  async function performLoad(
    managed: Datastream,
    source: Datastream,
    historyId: string
  ): Promise<WorkingCopy | null> {
    const startGeneration = generations.get(managed.id)
    const { hs } = storeToRefs(useHydroServer())
    const session = await getInProgressSession(
      hs.value.qualityControlSessions,
      historyId
    )
    // Superseded while listing sessions: never bump over what replaced us.
    if (generations.get(managed.id) !== startGeneration) {
      return current(managed.id)
    }
    if (!session) {
      invalidate(managed.id)
      return null
    }
    const cached = copies.get(managed.id)
    if (cached?.sessionId === session.id) return cached

    const generation = bump(managed.id)
    const built = await build(managed, source, historyId, session, generation)
    return built ?? current(managed.id)
  }

  function load(
    managed: Datastream,
    source: Datastream,
    historyId: string
  ): Promise<WorkingCopy | null> {
    const rebuilding = activeRebuild.get(managed.id)
    if (rebuilding) return rebuilding
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

  return { get, set, invalidate, clear, load, rebuild, extents }
})
