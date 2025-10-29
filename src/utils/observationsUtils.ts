import { useHydroServer } from '@/store/hydroserver';
import { ApiResponse, Datastream } from '@hydroserver/client';
import { storeToRefs } from 'pinia';

export const fetchObservationsSync = async (
  datastream: Datastream,
  startTime?: Date,
  endTime?: Date
): Promise<{ datetimes: number[]; dataValues: number[] }> => {
  const { id, phenomenonBeginTime, phenomenonEndTime, valueCount } = datastream
  const { hs } = storeToRefs(useHydroServer())
  if (!phenomenonBeginTime || !phenomenonEndTime) {
    return { datetimes: [], dataValues: [] }
  }

  const pageSize = 50_000
  const promises: Promise<ApiResponse<any>>[] = []
  let page = 1
  const maxPages = Math.ceil(valueCount / pageSize)

  while (page <= maxPages) {
    // TODO: this endpoint now returns a single array of objects which contain datetime and values, but also more redundant properties.
    // All endpoints seem to return Promise<ApiResponse<any>>. We need to strongly type each one.
    promises.push(
      hs.value.datastreams.getObservations(
        id,
        {
          page_size: pageSize,
          phenomenon_time_min: startTime?.toISOString() ?? phenomenonBeginTime,
          phenomenon_time_max: endTime?.toISOString() ?? phenomenonEndTime,
          page: page,
          order_by: ["phenomenonTime"]
        }
      )
    )
    page++
  }


  try {
    let datetimes: number[] = []
    let dataValues: number[] = []

    for (const p of promises) {
      const result = await p
      if (!result.data.length) {
        break
      }

      datetimes = [
        ...datetimes,
        ...result.data.map((r: any) =>
          new Date(r.phenomenonTime).getTime()
        ),
      ]
      dataValues = [...dataValues, ...result.data.map((r: any) => r.result)]
    }

    return {
      datetimes,
      dataValues,
    }
  } catch (error) {
    console.error('Error fetching data:', error)
    return Promise.reject(error)
  }
}