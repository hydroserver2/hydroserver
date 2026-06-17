import { useHydroServer } from '@/store/hydroserver';
import { Datastream } from '@hydroserver/client';
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
  let page = 1
  const maxPages = Math.ceil(valueCount / pageSize)

  try {
    let datetimes: number[] = []
    let dataValues: number[] = []
    while (page <= maxPages) {
      const result = await hs.value.datastreams.getObservations(
        id,
        {
          page_size: pageSize,
          phenomenon_time_min: startTime?.toISOString() ?? phenomenonBeginTime,
          phenomenon_time_max: endTime?.toISOString() ?? phenomenonEndTime,
          page: page,
          order_by: ['phenomenonTime'],
          format: 'column',
        }
      )

      if (!result.data.result.length) {
        break
      }

      datetimes = [
        ...datetimes,
        ...result.data.phenomenonTime.map((d: any) =>
          new Date(d).getTime()
        ),
      ]
      dataValues = [...dataValues, ...result.data.result]
      page++
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