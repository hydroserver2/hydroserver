export function subtractHours(timestamp: string, hours: number): string {
  const date = new Date(timestamp)
  date.setHours(date.getHours() - hours)
  return date.toISOString()
}

/** Returns the index of the first value that is greater or equal to the target value */
export const findFirstGreaterOrEqual = (
  array: number[] | Float64Array<ArrayBufferLike>,
  target: number
) => {
  let low = 0,
    high = array.length
  while (low < high) {
    const mid = (low + high) >> 1
    if (array[mid] < target) low = mid + 1
    else high = mid
  }
  return low
}

/** Returns the index of the last value that is lesser or equal to the target value */
export const findLastLessOrEqual = (
  array: number[] | Float64Array<ArrayBufferLike>,
  target: number
) => {
  let low = 0,
    high = array.length
  while (low < high) {
    const mid = (low + high) >> 1
    if (array[mid] > target) high = mid
    else low = mid + 1
  }
  return low - 1
}

