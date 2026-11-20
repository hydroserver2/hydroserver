import { useHydroServer } from '@/store/hydroserver'
import { Datastream, ObservationProfile } from '@hydroserver/client'
import { storeToRefs } from 'pinia'

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

  // getObservations follows pages until a short one, so an out-of-date value
  // count on the datastream can't cut the series short.
  const result = await hs.value.datastreams.getObservations(id, {
    limit: 50_000,
    datetime: `${startTime?.toISOString() ?? phenomenonBeginTime}/${
      endTime?.toISOString() ?? phenomenonEndTime
    }`,
    sortby: ['phenomenonTime'],
    profile: [ObservationProfile.Column],
    properties: ['phenomenonTime', 'result'],
  })
  if (!result.ok) throw new Error(result.message || 'Could not load observations.')

  const [group] = result.data as unknown as {
    columns: { result: number[]; phenomenonTime: string[] }
  }[]
  const cols = group?.columns
  if (!cols?.result?.length) return { datetimes: [], dataValues: [] }

  return {
    datetimes: cols.phenomenonTime.map((d) => new Date(d).getTime()),
    dataValues: cols.result,
  }
}
