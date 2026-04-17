import { EnumDictionary, TimeUnit } from '@/types'

const SECOND = 1
const MINUTE = SECOND * 60
const HOUR = MINUTE * 60
const DAY = HOUR * 24
const WEEK = DAY * 7
const MONTH = HOUR * 30
const YEAR = DAY * 365

export const timeUnitMultipliers: EnumDictionary<TimeUnit, number> = {
  [TimeUnit.SECOND]: SECOND,
  [TimeUnit.MINUTE]: MINUTE,
  [TimeUnit.HOUR]: HOUR,
  [TimeUnit.DAY]: DAY,
  [TimeUnit.WEEK]: WEEK,
  [TimeUnit.MONTH]: MONTH,
  [TimeUnit.YEAR]: YEAR,
}

export const formatDate = (date: Date) => {
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    hour12: false,
    minute: '2-digit',
    second: '2-digit',
  })
}

export const formatDuration = (duration: number) => {
  let value
  let unit

  if (duration >= MINUTE * 1000) {
    value = duration / (MINUTE * 1000)
    unit = 'm'
  } else if (duration >= 1000) {
    value = duration / 1000
    unit = 's'
  } else {
    value = duration
    unit = 'ms'
  }

  let formattedValue
  if (unit === 'ms') {
    formattedValue = Math.round(value).toString()
  } else {
    formattedValue = value.toFixed(2)
  }

  return `${formattedValue} ${unit}`
}