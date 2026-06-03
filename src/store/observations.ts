import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchObservationsSync } from '@/utils/observations'
import { ObservationRecord } from "@uwrl/qc-utils"
import { Datastream } from '@hydroserver/client'

export type ObservationData = {
  datetimes: Float64Array<ArrayBuffer>
  dataValues: Float32Array<ArrayBuffer>
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

    /**
     * Fetches requested observations that aren't currently in the pinia store,
     * updates the store, then returns the corresponding `ObservationRecord`.
     */
    const fetchObservationsInRange = async (
      datastream: Datastream,
      beginTime: Date,
      endTime: Date
    ): Promise<ObservationRecord> => {
      const id = datastream.id


      let beginDataPromise: Promise<{
        datetimes: number[]
        dataValues: number[]
      }> = Promise.resolve({ datetimes: [], dataValues: [] })
      let endDataPromise: Promise<{
        datetimes: number[]
        dataValues: number[]
      }> = Promise.resolve({ datetimes: [], dataValues: [] })

      if (observationsRaw.value[id]?.dataValues.length) {
        const rawBeginDatetime = new Date(
          observationsRaw.value[id].datetimes[0] as number
        )

        // Strict `<` — skip the request entirely when the requested
        // begin is at or inside the cached window. `<=` used to fire a
        // 1-second range request on exact matches (e.g. re-clicking
        // the same preset), which is pure waste.
        if (beginTime < rawBeginDatetime) {
          // Results in range will be inclusive, so we need to offset by 1
          rawBeginDatetime.setSeconds(rawBeginDatetime.getSeconds() - 1)
          beginDataPromise = fetchObservationsSync(
            datastream,
            beginTime,
            rawBeginDatetime
          )
        }

        const rawEndDatetime = new Date(
          observationsRaw.value[id].datetimes[
          observationsRaw.value[id].datetimes.length - 1
          ] as number
        )

        // Same note as above: only fetch the trailing segment when the
        // requested end is *past* what we've already cached.
        if (endTime > rawEndDatetime) {
          rawEndDatetime.setSeconds(rawEndDatetime.getSeconds() + 1)
          endDataPromise = fetchObservationsSync(
            datastream,
            rawEndDatetime,
            endTime
          )
        }
      } else {
        beginDataPromise = fetchObservationsSync(datastream, beginTime, endTime)
      }

      const [beginData, endData] = await Promise.all([
        beginDataPromise,
        endDataPromise,
      ])

      if (!observationsRaw.value[id]) {
        observationsRaw.value[id] = {
          datetimes: new Float64Array(0),
          dataValues: new Float32Array(0),
        }
      }

      if (beginData.dataValues.length > 0 || endData.dataValues.length > 0) {
        const newLength =
          beginData.dataValues.length +
          endData.dataValues.length +
          observationsRaw.value[id].dataValues.length
        const newBufferX = new ArrayBuffer(
          newLength * Float64Array.BYTES_PER_ELEMENT
        )
        const newBufferY = new ArrayBuffer(
          newLength * Float32Array.BYTES_PER_ELEMENT
        )

        const newArrayX = new Float64Array(newBufferX)
        const newArrayY = new Float32Array(newBufferY)

        // Begin data
        let offset = 0
        newArrayX.set(beginData.datetimes, offset)
        newArrayY.set(beginData.dataValues, offset)

        // Previous data
        offset += beginData.datetimes.length
        newArrayX.set(observationsRaw.value[id].datetimes, offset)
        newArrayY.set(observationsRaw.value[id].dataValues, offset)

        // End data
        offset += endData.datetimes.length
        newArrayX.set(endData.datetimes, offset)
        newArrayY.set(endData.dataValues, offset)

        observationsRaw.value[id].datetimes = newArrayX
        observationsRaw.value[id].dataValues = newArrayY
      }

      // If nothing is stored yet, create a new record
      if (!observations.value[id] && observationsRaw.value[datastream.id]) {
        observations.value[id] = new ObservationRecord(observationsRaw.value[datastream.id] as ObservationData)
      }

      const obsRecord = observations.value[id] as ObservationRecord
      // `rawData` is the full accumulated cache; the record slices it to the
      // selected window (`applyWindow` no-ops when the window is unchanged,
      // so unrelated replots keep their edits/history).
      obsRecord.rawData = observationsRaw.value[id]
      await obsRecord.applyWindow(beginTime.getTime(), endTime.getTime())

      return obsRecord
    }

    return {
      observations,
      observationsRaw,
      fetchObservationsInRange,
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
