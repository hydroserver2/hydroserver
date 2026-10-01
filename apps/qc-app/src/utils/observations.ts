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

  const pageSize = 50_000
  const datetimes: number[] = []
  const dataValues: number[] = []
  // Page until a short page: the datastream's value count can be out of date.
  for (let page = 1; ; page++) {
    const result = await hs.value.datastreams.getObservations(id, {
      page_size: pageSize,
      phenomenon_time_min: startTime?.toISOString() ?? phenomenonBeginTime,
      phenomenon_time_max: endTime?.toISOString() ?? phenomenonEndTime,
      page,
      order_by: ['phenomenonTime'],
      format: 'column',
    })
    if (!result.ok) throw new Error(result.message || 'Could not load observations.')

    const cols = result.data as { result: number[]; phenomenonTime: string[] }
    for (let i = 0; i < cols.result.length; i++) {
      datetimes.push(new Date(cols.phenomenonTime[i]!).getTime())
      dataValues.push(cols.result[i]!)
    }
    if (cols.result.length < pageSize) return { datetimes, dataValues }
  }
}
