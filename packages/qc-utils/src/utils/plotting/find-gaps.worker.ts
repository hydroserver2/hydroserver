import { findGapsCore } from './operation-cores'

self.onmessage = (e) => {
  const { bufferX, start, endInclusive, threshold } = e.data
  const arrayX = new Float64Array(bufferX)
  self.postMessage(findGapsCore(arrayX, start, endInclusive, threshold))
}
