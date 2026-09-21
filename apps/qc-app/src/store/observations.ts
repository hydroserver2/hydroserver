import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchObservationsSync } from '@/utils/observations'
import { ObservationRecord } from "@uwrl/qc-utils"
import { Datastream } from '@hydroserver/client'
import {
  mergeIntervals,
  subtractIntervals,
  type Interval,
} from '@/utils/timeIntervals'

export type ObservationData = {
  datetimes: Float64Array<ArrayBuffer>
  dataValues: Float32Array<ArrayBuffer>
}

type FetchedChunk = { datetimes: number[]; dataValues: number[] }

/**
 * The cache with the fetched `chunks` merged in, in time order. Chunks come
 * from disjoint ranges in ascending order; a timestamp the cache already
 * holds (a range endpoint fetched twice) keeps the cached value.
 */
function mergeObservations(
  cached: ObservationData,
  chunks: FetchedChunk[]
): ObservationData {
  const addedX = chunks.flatMap((c) => c.datetimes)
  const addedY = chunks.flatMap((c) => c.dataValues)
  const oldX = cached.datetimes
  const oldY = cached.dataValues
  const x = new Float64Array(oldX.length + addedX.length)
  const y = new Float32Array(oldY.length + addedY.length)
  let i = 0
  let j = 0
  let n = 0
  while (i < oldX.length || j < addedX.length) {
    const takeOld =
      j >= addedX.length ||
      (i < oldX.length && (oldX[i] as number) <= (addedX[j] as number))
    if (takeOld) {
      if (j < addedX.length && oldX[i] === addedX[j]) j++
      x[n] = oldX[i] as number
      y[n++] = oldY[i++] as number
    } else {
      x[n] = addedX[j] as number
      y[n++] = addedY[j++] as number
    }
  }
  return n === x.length
    ? { datetimes: x, dataValues: y }
    : { datetimes: x.slice(0, n), dataValues: y.slice(0, n) }
}

export const useObservationStore = defineStore(
  'observations',
  () => {
    const observations = ref<Record<string, ObservationRecord>>({})
    const observationsRaw = ref<
      Record<
        string,
        ObservationData
      >
    >({})

    // const fetchQcData = async () => {
    //   const { qcDatastream } = storeToRefs(useDataVisStore())
    //   if (qcDatastream.value) {
    //     const { beginDate, endDate } = storeToRefs(useDataVisStore())
    //     const { fetchObservationsInRange } = useObservationStore()
    //     await fetchObservationsInRange(qcDatastream.value, beginDate.value, endDate.value)
    //   }
    // }

    /** The last request queued per datastream. */
    const queued = new Map<string, { key: string; promise: Promise<unknown> }>()

    /** The ranges already asked of the server per datastream, found or not. */
    const covered = new Map<string, Interval[]>()

    type Exclude = { begin: Date; end: Date }

    /**
     * Run `task` after every request already queued for the datastream, so
     * each fills the cache from what the previous one left and the shared
     * record ends on the latest requested window. A request matching the
     * last queued one (same `key`) shares it.
     */
    const enqueue = <T>(
      id: string,
      key: string,
      task: () => Promise<T>
    ): Promise<T> => {
      const last = queued.get(id)
      if (last?.key === key) return last.promise as Promise<T>

      const previous = last?.promise.catch(() => undefined) ?? Promise.resolve()
      const promise = previous.then(task)
      const entry = { key, promise }
      queued.set(id, entry)
      const release = () => {
        if (queued.get(id) === entry) queued.delete(id)
      }
      promise.then(release, release)
      return promise
    }

    const requestKey = (
      kind: string,
      beginTime: Date,
      endTime: Date,
      exclude?: Exclude
    ) =>
      [
        kind,
        beginTime.getTime(),
        endTime.getTime(),
        exclude?.begin.getTime(),
        exclude?.end.getTime(),
      ].join(':')

    /** Fill the cache for `[beginTime, endTime]`, never requesting `exclude`,
     *  and resolve with the whole cache. */
    const loadMissing = async (
      datastream: Datastream,
      beginTime: Date,
      endTime: Date,
      exclude?: Exclude
    ): Promise<ObservationData> => {
      const id = datastream.id
      const wanted = subtractIntervals(
        [[beginTime.getTime(), endTime.getTime()]],
        exclude ? [[exclude.begin.getTime(), exclude.end.getTime()]] : []
      )
      const missing = subtractIntervals(wanted, covered.get(id) ?? [])
      const chunks = await Promise.all(
        missing.map(([start, end]) =>
          fetchObservationsSync(datastream, new Date(start), new Date(end))
        )
      )
      covered.set(id, mergeIntervals([...(covered.get(id) ?? []), ...missing]))

      const cached = observationsRaw.value[id] ?? {
        datetimes: new Float64Array(0),
        dataValues: new Float32Array(0),
      }
      observationsRaw.value[id] = chunks.some((c) => c.dataValues.length)
        ? mergeObservations(cached, chunks)
        : cached
      return observationsRaw.value[id]
    }

    /**
     * The shared record for a datastream, windowed to `[beginTime, endTime]`.
     * The plot draws it, so windowing it moves what the plot shows. `exclude`
     * is a stretch inside the window not to fetch; whatever the cache already
     * holds there stays in the record.
     */
    const fetchObservationsInRange = (
      datastream: Datastream,
      beginTime: Date,
      endTime: Date,
      exclude?: Exclude
    ): Promise<ObservationRecord> => {
      const id = datastream.id
      return enqueue(
        id,
        requestKey('shared', beginTime, endTime, exclude),
        async () => {
          const raw = await loadMissing(datastream, beginTime, endTime, exclude)
          if (!observations.value[id]) {
            observations.value[id] = new ObservationRecord(raw)
          }
          const obsRecord = observations.value[id] as ObservationRecord
          // A no-op when neither the window nor the cache changed, so
          // unrelated replots keep their edits/history.
          await obsRecord.applyWindow(beginTime.getTime(), endTime.getTime(), raw)
          return obsRecord
        }
      )
    }

    /**
     * A record of its own over `[beginTime, endTime]`, filled from the shared
     * cache. For work that builds on the data (a working copy, a snapshot):
     * it never re-windows the shared record the plot draws.
     */
    const fetchDetachedRecord = async (
      datastream: Datastream,
      beginTime: Date,
      endTime: Date
    ): Promise<ObservationRecord> => {
      const raw = await enqueue(
        datastream.id,
        requestKey('detached', beginTime, endTime),
        () => loadMissing(datastream, beginTime, endTime)
      )
      const record = new ObservationRecord(raw)
      await record.applyWindow(beginTime.getTime(), endTime.getTime())
      return record
    }

    return {
      observations,
      observationsRaw,
      fetchObservationsInRange,
      fetchDetachedRecord,
    }
  },
  {
    persist: {
      pick: [
        // TODO: enable only in development mode
        // 'observationsRaw', // TODO: can not save buffers correctly
      ],
    },
  }
)
