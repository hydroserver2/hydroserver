import { valueThresholdCore } from './operation-cores'

self.onmessage = (e) => {
  const { bufferY, start, end, ops, values, matchAll } = e.data
  const arrayY = new Float64Array(bufferY)
  self.postMessage(valueThresholdCore(arrayY, start, end, ops, values, matchAll))
}
