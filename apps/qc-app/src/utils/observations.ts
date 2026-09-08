import { useHydroServer } from '@/store/hydroserver';
import { Datastream } from '@hydroserver/client';
import { storeToRefs } from 'pinia';

export const fetchObservationsSync = async (
  datastream: Datastream,
  startTime?: Date,
  endTime?: Date
): Promise<{ datetimes: number[]; dataValues: number[] }> => {
  const { id, phenomenonBeginTime, phenomenonEndTime } = datastream
  const { hs } = storeToRefs(useHydroServer())
  if (!phenomenonBeginTime || !phenomenonEndTime) {
    return { datetimes: [], dataValues: [] }
  }

  try {
    const result = await hs.value.datastreams.getObservations(id, {
      limit: 50_000,
      phenomenon_time_min: startTime?.toISOString() ?? phenomenonBeginTime,
      phenomenon_time_max: endTime?.toISOString() ?? phenomenonEndTime,
      order_by: ['phenomenonTime'],
      format: 'column',
    })

    if (!result.ok) {
      return { datetimes: [], dataValues: [] }
    }

    const cols = result.data as {
      result: number[]
      phenomenonTime: string[]
    }
    if (!cols.result?.length) {
      return { datetimes: [], dataValues: [] }
    }

    return {
      datetimes: cols.phenomenonTime.map((d: any) => new Date(d).getTime()),
      dataValues: cols.result,
    }
  } catch (error) {
    console.error('Error fetching data:', error)
    return Promise.reject(error)
  }
}
