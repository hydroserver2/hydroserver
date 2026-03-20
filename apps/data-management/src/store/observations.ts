import { defineStore } from 'pinia'
import { ref } from 'vue'
import hs, { Datastream, GraphSeries, DataPoint } from '@hydroserver/client'
import {
  fetchObservations,
  preProcessData,
  ObservationArray,
} from '@/utils/observationsUtils'
import { Snackbar } from '@/utils/notifications'

export const useObservationStore = defineStore('observations', () => {
  type ObservationRecordLocal = {
    dataArray: ObservationArray
    beginTime: string
    endTime: string
    loading: boolean
  }

  type ObservationRaw = {
    datetimes: Float64Array
    dataValues: Float32Array
  }

  const observations = ref<Record<string, ObservationRecordLocal>>({})
  const observationsRaw = ref<Record<string, ObservationRaw>>({})
  const activeControllers = ref<Record<string, AbortController>>({})
  const requestCounters = ref<Record<string, number>>({})

  const isAbortError = (error: unknown) =>
    typeof error === 'object' &&
    error !== null &&
    'name' in error &&
    (error as { name?: string }).name === 'AbortError'

  const createAbortError = () => {
    try {
      return new DOMException('Aborted', 'AbortError')
    } catch {
      return { name: 'AbortError' }
    }
  }

  const parseObservationRows = (rows: ObservationArray) => {
    const length = rows.length
    const datetimes = new Float64Array(length)
    const dataValues = new Float32Array(length)
    for (let i = 0; i < length; i += 1) {
      const [dateValue, rawValue] = rows[i]
      const time =
        typeof dateValue === 'number' ? dateValue : Date.parse(dateValue)
      datetimes[i] = Number.isFinite(time) ? time : NaN
      dataValues[i] =
        typeof rawValue === 'number' ? rawValue : Number(rawValue)
    }
    return { datetimes, dataValues }
  }

  const findFirstGreaterOrEqual = (arr: Float64Array, value: number) => {
    let low = 0
    let high = arr.length
    while (low < high) {
      const mid = Math.floor((low + high) / 2)
      if (arr[mid] < value) {
        low = mid + 1
      } else {
        high = mid
      }
    }
    return low
  }

  const sliceRawToRows = (
    raw: ObservationRaw,
    beginTime: number,
    endTime: number
  ): ObservationArray => {
    if (!raw.datetimes.length) return []
    const startIdx = findFirstGreaterOrEqual(raw.datetimes, beginTime)
    const endIdx = findFirstGreaterOrEqual(raw.datetimes, endTime + 1)
    const rows: ObservationArray = []
    for (let i = startIdx; i < endIdx; i += 1) {
      rows.push([raw.datetimes[i], raw.dataValues[i]])
    }
    return rows
  }

  /**
   * Fetches requested observations that aren't currently in the pinia store,
   * updates the store, then returns the requested observations.
   */
  const fetchObservationsInRange = async (
    datastream: Datastream,
    beginTime: string,
    endTime: string
  ): Promise<ObservationArray> => {
    const id = datastream.id
    const newBeginTime = Date.parse(beginTime)
    const newEndTime = Date.parse(endTime)
    const requestId = (requestCounters.value[id] ?? 0) + 1
    requestCounters.value[id] = requestId

    if (activeControllers.value[id]) {
      activeControllers.value[id].abort()
    }
    const controller = new AbortController()
    activeControllers.value[id] = controller
    const { signal } = controller

    const ensureLatest = () => {
      if (signal.aborted || requestCounters.value[id] !== requestId) {
        throw createAbortError()
      }
    }

    if (!observations.value[id]) {
      observations.value[id] = {
        dataArray: [],
        beginTime,
        endTime,
        loading: true,
      }
    } else {
      observations.value[id].loading = true
    }

    try {
      // If nothing is stored yet, create a new record and fetch the data in range
      if (!observationsRaw.value[id]) {
        const fetchedData = (await fetchObservations(
          datastream,
          beginTime,
          endTime,
          signal
        )) as ObservationArray
        ensureLatest()
        observationsRaw.value[id] = parseObservationRows(fetchedData)
        observations.value[id].dataArray = []

        ensureLatest()
        return fetchedData
      }

      const existingRecord = observations.value[id]
      const storedBeginTime = new Date(existingRecord.beginTime).getTime()
      const storedEndTime = new Date(existingRecord.endTime).getTime()

      let beginDataPromise: Promise<ObservationArray> = Promise.resolve([])
      let endDataPromise: Promise<ObservationArray> = Promise.resolve([])

      // Check if new data before the stored data is needed
      if (newBeginTime < storedBeginTime) {
        const storedStart = storedBeginTime - 1000
        beginDataPromise = fetchObservations(
          datastream,
          beginTime,
          new Date(storedStart).toISOString(),
          signal
        ) as Promise<ObservationArray>
      }

      // Check if new data after the stored data is needed
      if (newEndTime > storedEndTime) {
        const storedEnd = storedEndTime + 1000
        endDataPromise = fetchObservations(
          datastream,
          new Date(storedEnd).toISOString(),
          endTime,
          signal
        ) as Promise<ObservationArray>
      }

      // Fetch and update in parallel if needed
      const [beginData, endData] = await Promise.all([
        beginDataPromise,
        endDataPromise,
      ])
      ensureLatest()

      const hasBegin = beginData.length > 0
      const hasEnd = endData.length > 0
      if (hasBegin || hasEnd) {
        const existingRaw =
          observationsRaw.value[id] ||
          parseObservationRows(existingRecord.dataArray)
        const beginRaw = hasBegin ? parseObservationRows(beginData) : null
        const endRaw = hasEnd ? parseObservationRows(endData) : null

        const beginLen = beginRaw?.datetimes.length || 0
        const existingLen = existingRaw.datetimes.length
        const endLen = endRaw?.datetimes.length || 0
        const newLength = beginLen + existingLen + endLen

        const newDatetimes = new Float64Array(newLength)
        const newValues = new Float32Array(newLength)

        let offset = 0
        if (beginRaw) {
          newDatetimes.set(beginRaw.datetimes, offset)
          newValues.set(beginRaw.dataValues, offset)
          offset += beginLen
        }
        newDatetimes.set(existingRaw.datetimes, offset)
        newValues.set(existingRaw.dataValues, offset)
        offset += existingLen
        if (endRaw) {
          newDatetimes.set(endRaw.datetimes, offset)
          newValues.set(endRaw.dataValues, offset)
        }

        observationsRaw.value[id] = {
          datetimes: newDatetimes,
          dataValues: newValues,
        }
      } else if (!observationsRaw.value[id]) {
        observationsRaw.value[id] = parseObservationRows(existingRecord.dataArray)
      }

      if (hasBegin) {
        existingRecord.beginTime = beginTime
      }
      if (hasEnd) {
        existingRecord.endTime = endTime
      }

      const raw = observationsRaw.value[id]
      if (raw) {
        ensureLatest()
        return sliceRawToRows(raw, newBeginTime, newEndTime)
      }

      // Return only the data within the requested range
      ensureLatest()
      return observations.value[id].dataArray.filter(([dateString, _]) => {
        const observationTimestamp =
          typeof dateString === 'number'
            ? dateString
            : new Date(dateString).getTime()
        return (
          observationTimestamp >= newBeginTime &&
          observationTimestamp <= newEndTime
        )
      })
    } finally {
      if (
        observations.value[id] &&
        requestCounters.value[id] === requestId
      ) {
        observations.value[id].loading = false
      }
      if (activeControllers.value[id] === controller) {
        delete activeControllers.value[id]
      }
    }
  }

  const fetchGraphSeriesData = async (
    datastream: Datastream,
    start: string,
    end: string
  ): Promise<DataPoint[] | null> => {
    try {
      const observations = await fetchObservationsInRange(
        datastream,
        start,
        end
      )
      return preProcessData(observations, datastream)
    } catch (error) {
      if (isAbortError(error)) return null
      Snackbar.error('Failed to fetch observations')
      console.error('Failed to fetch observations:', error)
      return null
    }
  }

  const fetchGraphSeries = async (
    datastream: Datastream,
    start: string,
    end: string
  ): Promise<GraphSeries | null> => {
    const observationsPromise = fetchObservationsInRange(
      datastream,
      start,
      end
    ).catch((error) => {
      if (!isAbortError(error)) {
        Snackbar.error('Failed to fetch observations')
        console.error('Failed to fetch observations:', error)
      }
      return null
    })
    const fetchUnitPromise = hs.units
      .getItem(datastream.unitId)
      .catch((error) => {
        console.error('Failed to fetch Unit:', error)
        return null
      })
    const fetchObservedPropertyPromise = hs.observedProperties
      .getItem(datastream.observedPropertyId)
      .catch((error) => {
        console.error('Failed to fetch ObservedProperty:', error)
        return null
      })

    const [observations, unit, observedProperty] = await Promise.all([
      observationsPromise,
      fetchUnitPromise,
      fetchObservedPropertyPromise,
    ])

    if (observations === null) {
      return null
    }

    const processedData = preProcessData(observations ?? [], datastream)

    const yAxisLabel =
      observedProperty && unit
        ? `${observedProperty.name} (${unit.symbol})`
        : 'Unknown'

    return {
      id: datastream.id,
      name: datastream.name,
      data: processedData,
      yAxisLabel,
      lineColor: '#5571c7', // default to blue,
    } as GraphSeries
  }

  return {
    observations,
    observationsRaw,
    fetchObservationsInRange,
    fetchGraphSeriesData,
    fetchGraphSeries,
  }
})
