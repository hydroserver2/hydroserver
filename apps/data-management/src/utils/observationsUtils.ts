import hs, {
  DataArray,
  DataPoint,
  Datastream,
  TimeSpacingUnit,
} from '@hydroserver/client'

export type ObservationArray = Array<[string | number, number]>

export function subtractHours(timestamp: string, hours: number): string {
  const date = new Date(timestamp)
  date.setHours(date.getHours() - hours)
  return date.toISOString()
}

const toObservationRows = (columnar: Record<string, unknown>): DataArray => {
  const times =
    (columnar as any).phenomenonTime ?? (columnar as any).phenomenon_time ?? []
  const results = (columnar as any).result ?? []

  if (!Array.isArray(times) || !Array.isArray(results)) return []
  const length = Math.min(times.length, results.length)
  const rows: DataArray = []
  for (let i = 0; i < length; i += 1) {
    rows.push([times[i] as string, results[i] as number])
  }
  return rows
}

export const fetchObservations = async (
  datastream: Datastream,
  startTime: string | null = null,
  endTime: string | null = null,
  signal?: AbortSignal
) => {
  const { id, phenomenonBeginTime, phenomenonEndTime } = datastream
  if (!phenomenonBeginTime || !phenomenonEndTime) return []

  const options: any = {
    order_by: ['phenomenonTime'],
    page_size: 50_000,
    format: 'column',
    phenomenon_time_min: startTime ?? phenomenonBeginTime,
    phenomenon_time_max: endTime ?? phenomenonEndTime,
  }
  if (signal) options.signal = signal

  const res = await hs.datastreams.getObservations(id, options)

  if (!res.ok || !res.data || typeof res.data !== 'object') return []
  return toObservationRows(res.data as Record<string, unknown>)
}

export function toDataPointArray(dataArray: DataArray | ObservationArray) {
  return (dataArray as ObservationArray).map(([dateValue, value]) => ({
    date: new Date(dateValue),
    value,
  }))
}

// Function to replace 'no data' values with NaN
export function replaceNoDataValues(
  data: DataPoint[],
  noDataValue: number | null | undefined
) {
  if (noDataValue === null || noDataValue === undefined) return data
  const noDataNumeric =
    typeof noDataValue === 'number' ? noDataValue : Number(noDataValue)

  return data.map((d) => {
    const rawValue = d.value as unknown
    if (rawValue === null || rawValue === undefined) {
      return { ...d, value: NaN }
    }
    if (
      typeof rawValue === 'string' &&
      rawValue.trim().toLowerCase() === 'nan'
    ) {
      return { ...d, value: NaN }
    }
    const numericValue =
      typeof rawValue === 'number' ? rawValue : Number(rawValue)
    const isNoData =
      Number.isFinite(noDataNumeric) &&
      Number.isFinite(numericValue) &&
      numericValue === noDataNumeric
    return { ...d, value: isNoData ? NaN : d.value }
  })
}

export function convertTimeSpacingToMilliseconds(
  timeSpacing: number,
  unit: TimeSpacingUnit
): number {
  const unitToMilliseconds = {
    seconds: 1000,
    minutes: 1000 * 60,
    hours: 1000 * 60 * 60,
    days: 1000 * 60 * 60 * 24,
  }

  return timeSpacing * (unitToMilliseconds[unit] || 0)
}

function calculateTimeDifference(point1: DataPoint, point2: DataPoint): number {
  const time1 = new Date(point1.date).getTime()
  const time2 = new Date(point2.date).getTime()

  return Math.abs(time2 - time1)
}

export function addNaNForGaps(data: DataPoint[], maxGap: number): DataPoint[] {
  const modifiedData: DataPoint[] = []
  data.forEach((point, index) => {
    modifiedData.push(point)
    if (index < data.length - 1) {
      const timeDifference = calculateTimeDifference(point, data[index + 1])
      if (timeDifference > maxGap) {
        modifiedData.push({
          date: new Date(point.date.getTime() + 1),
          value: NaN,
        })
      }
    }
  })
  return modifiedData
}

export function preProcessData(
  dataArray: DataArray | ObservationArray,
  datastream: Datastream
) {
  const { noDataValue, intendedTimeSpacing, intendedTimeSpacingUnit } =
    datastream

  let data = toDataPointArray(dataArray)
  data = replaceNoDataValues(data, noDataValue)

  if (intendedTimeSpacingUnit && intendedTimeSpacing) {
    const maxGap = convertTimeSpacingToMilliseconds(
      intendedTimeSpacing,
      intendedTimeSpacingUnit as TimeSpacingUnit
    )

    data = addNaNForGaps(data, maxGap)
  }
  return data
}
